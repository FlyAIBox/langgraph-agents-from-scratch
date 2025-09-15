from typing import Literal

from langchain.chat_models import init_chat_model

from langgraph.graph import StateGraph, START, END
from langgraph.store.base import BaseStore
from langgraph.types import interrupt, Command

from email_assistant.tools import get_tools, get_tools_by_name
from email_assistant.tools.gmail.prompt_templates import GMAIL_TOOLS_PROMPT
from email_assistant.tools.gmail.gmail_tools import mark_as_read
from email_assistant.prompts import triage_system_prompt, triage_user_prompt, agent_system_prompt_hitl_memory, default_triage_instructions, default_background, default_response_preferences, default_cal_preferences, MEMORY_UPDATE_INSTRUCTIONS, MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT
from email_assistant.schemas import State, RouterSchema, StateInput, UserPreferences
from email_assistant.utils import parse_gmail, format_for_display, format_gmail_markdown
from dotenv import load_dotenv

load_dotenv(".env")

# 获取工具集合（包含 Gmail 工具）
tools = get_tools(["send_email_tool", "schedule_meeting_tool", "check_calendar_tool", "Question", "Done"], include_gmail=True)
tools_by_name = get_tools_by_name(tools)

# 初始化用于路由/结构化输出的聊天模型（LLM）
llm = init_chat_model("openai:gpt-4.1", temperature=0.0)
llm_router = llm.with_structured_output(RouterSchema) 

# 初始化用于 Agent 的模型，强制必须调用工具（tool_choice="required"）
llm = init_chat_model("openai:gpt-4.1", temperature=0.0)
llm_with_tools = llm.bind_tools(tools, tool_choice="required")

def get_memory(store, namespace, default_content=None):
    """从存储中读取偏好记忆；若不存在则以默认值初始化。"""
    # 检索现有记忆
    user_preferences = store.get(namespace, "user_preferences")
    
    # 若存在则返回其 value
    if user_preferences:
        return user_preferences.value
    
    # 若不存在则写入默认值后返回
    else:
        # Namespace, key, value
        store.put(namespace, "user_preferences", default_content)
        user_preferences = default_content
    
    # 返回默认内容
    return user_preferences 

def update_memory(store, namespace, messages):
    """更新存储中的用户偏好（记忆）。"""

    # 读取现有记忆
    user_preferences = store.get(namespace, "user_preferences")
    # 基于结构化输出模型更新记忆
    llm = init_chat_model("openai:gpt-4.1", temperature=0.0).with_structured_output(UserPreferences)
    result = llm.invoke(
        [
            {"role": "system", "content": MEMORY_UPDATE_INSTRUCTIONS.format(current_profile=user_preferences.value, namespace=namespace)},
        ] + messages
    )
    # 将更新后的偏好写回存储
    store.put(namespace, "user_preferences", result.user_preferences)

# Nodes 
def triage_router(state: State, store: BaseStore) -> Command[Literal["triage_interrupt_handler", "response_agent", "__end__"]]:
    """分析 Gmail 邮件内容，决定回复/通知/忽略。结合记忆偏好做个性化判定。"""
    
    # 解析 Gmail 邮件输入
    author, to, subject, email_thread, email_id = parse_gmail(state["email_input"])
    user_prompt = triage_user_prompt.format(
        author=author, to=to, subject=subject, email_thread=email_thread
    )

    # 若为通知场景，为 Agent Inbox 生成 Gmail 邮件 Markdown  
    email_markdown = format_gmail_markdown(subject, author, to, email_thread, email_id)

    # 读取分拣偏好记忆
    triage_instructions = get_memory(store, ("email_assistant", "triage_preferences"), default_triage_instructions)

    # 组合系统提示词（背景 + 分拣偏好）
    system_prompt = triage_system_prompt.format(
        background=default_background,
        triage_instructions=triage_instructions,
    )

    # 运行路由模型
    result = llm_router.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    # 分类结果
    classification = result.classification

    # Process the classification decision
    if classification == "respond":
        print("📧 Classification: RESPOND - This email requires a response")
        # 下一步
        goto = "response_agent"
        # 更新状态
        update = {
            "classification_decision": result.classification,
            "messages": [{"role": "user",
                            "content": f"Respond to the email: {email_markdown}"
                        }],
        }
        
    elif classification == "ignore":
        print("🚫 Classification: IGNORE - This email can be safely ignored")

        # Next node
        goto = END
        # Update the state
        update = {
            "classification_decision": classification,
        }

    elif classification == "notify":
        print("🔔 Classification: NOTIFY - This email contains important information") 

        # 下一步
        goto = "triage_interrupt_handler"
        # 更新状态
        update = {
            "classification_decision": classification,
        }

    else:
        raise ValueError(f"Invalid classification: {classification}")
    
    return Command(goto=goto, update=update)

def triage_interrupt_handler(state: State, store: BaseStore) -> Command[Literal["response_agent", "__end__"]]:
    """处理分拣阶段中断（由 Agent Inbox 人审阅），并据此调整后续流程。"""
    
    # 解析 Gmail 邮件输入
    author, to, subject, email_thread, email_id = parse_gmail(state["email_input"])

    # 为 Agent Inbox 生成展示用的 Gmail 邮件 Markdown  
    email_markdown = format_gmail_markdown(subject, author, to, email_thread, email_id)

    # 构造消息
    messages = [{"role": "user",
                "content": f"Email to notify user about: {email_markdown}"
                }]

    # 构造 Agent Inbox 中断请求
    request = {
        "action_request": {
            "action": f"Email Assistant: {state['classification_decision']}",
            "args": {}
        },
        "config": {
            "allow_ignore": True,  # 允许忽略
            "allow_respond": True, # 允许回复
            "allow_edit": False,   # 不允许编辑
            "allow_accept": False, # 不允许直接接受
        },
        # Agent Inbox 中展示的邮件描述
        "description": email_markdown,
    }

    # 发送到 Agent Inbox 并等待响应
    response = interrupt([request])[0]

    # 若用户提供反馈：转入回复 Agent，并基于反馈撰写邮件   
    if response["type"] == "response":
        # 将反馈加入消息 
        user_input = response["args"]
        messages.append({"role": "user",
                        "content": f"User wants to reply to the email. Use this feedback to respond: {user_input}"
                        })
        # 用反馈更新分拣偏好记忆
        update_memory(store, ("email_assistant", "triage_preferences"), [{
            "role": "user",
            "content": f"The user decided to respond to the email, so update the triage preferences to capture this."
        }] + messages)

        goto = "response_agent"

    # 若用户忽略，则结束
    elif response["type"] == "ignore":
        # 记录用户忽略该邮件的决策
        messages.append({"role": "user",
                        "content": f"The user decided to ignore the email even though it was classified as notify. Update triage preferences to capture this."
                        })
        # 更新分拣偏好记忆 
        update_memory(store, ("email_assistant", "triage_preferences"), messages)
        goto = END

    # Catch all other responses
    else:
        raise ValueError(f"Invalid response: {response}")

    # 更新状态 
    update = {
        "messages": messages,
    }

    return Command(goto=goto, update=update)

def llm_call(state: State, store: BaseStore):
    """LLM 判断是否需要调用工具，并注入记忆化偏好。"""
    
    # 读取日历偏好记忆
    cal_preferences = get_memory(store, ("email_assistant", "cal_preferences"), default_cal_preferences)
    
    # 读取回复偏好记忆
    response_preferences = get_memory(store, ("email_assistant", "response_preferences"), default_response_preferences)

    return {
        "messages": [
            llm_with_tools.invoke(
                [
                    {"role": "system", "content": agent_system_prompt_hitl_memory.format(
                        tools_prompt=GMAIL_TOOLS_PROMPT,
                        background=default_background,
                        response_preferences=response_preferences, 
                        cal_preferences=cal_preferences
                    )}
                ]
                + state["messages"]
            )
        ]
    }
    
def interrupt_handler(state: State, store: BaseStore) -> Command[Literal["llm_call", "__end__"]]:
    """创建人工审阅工具调用的中断；必要时回写记忆。"""
    
    # 累积要写回状态的消息
    result = []

    # 默认回到 LLM 调用节点
    goto = "llm_call"

    # 遍历上一条消息中的工具调用
    for tool_call in state["messages"][-1].tool_calls:
        
        # HITL 白名单工具
        hitl_tools = ["send_email_tool", "schedule_meeting_tool", "Question"]
        
        # 非白名单：直接执行，不中断
        if tool_call["name"] not in hitl_tools:

            # 直接执行（如 search_memory 等）
            tool = tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            result.append({"role": "tool", "content": observation, "tool_call_id": tool_call["id"]})
            continue
            
        # 从状态中获取原始 Gmail 邮件
        email_input = state["email_input"]
        author, to, subject, email_thread, email_id = parse_gmail(email_input)
        original_email_markdown = format_gmail_markdown(subject, author, to, email_thread, email_id)
        
        # 组合工具调用展示，前置原始邮件内容
        tool_display = format_for_display(tool_call)
        description = original_email_markdown + tool_display

        # 配置 Agent Inbox 的可用动作
        if tool_call["name"] == "send_email_tool":
            config = {
                "allow_ignore": True,
                "allow_respond": True,
                "allow_edit": True,
                "allow_accept": True,
            }
        elif tool_call["name"] == "schedule_meeting_tool":
            config = {
                "allow_ignore": True,
                "allow_respond": True,
                "allow_edit": True,
                "allow_accept": True,
            }
        elif tool_call["name"] == "Question":
            config = {
                "allow_ignore": True,
                "allow_respond": True,
                "allow_edit": False,
                "allow_accept": False,
            }
        else:
            raise ValueError(f"Invalid tool call: {tool_call['name']}")

        # 构造中断请求
        request = {
            "action_request": {
                "action": tool_call["name"],
                "args": tool_call["args"]
            },
            "config": config,
            "description": description,
        }

        # 发送到 Agent Inbox 并等待响应
        response = interrupt([request])[0]

        # 处理响应类型 
        if response["type"] == "accept":

            # 接受：按原参数执行
            tool = tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            result.append({"role": "tool", "content": observation, "tool_call_id": tool_call["id"]})
                        
        elif response["type"] == "edit":

            # 工具选择 
            tool = tools_by_name[tool_call["name"]]
            initial_tool_call = tool_call["args"]
            
            # 从 Agent Inbox 获取编辑后的参数
            edited_args = response["args"]["args"]

            # 使用编辑内容更新 AI 消息中的工具调用（保持不可变式）
            ai_message = state["messages"][-1]
            current_id = tool_call["id"]
            
            # 过滤并替换，避免原地修改
            updated_tool_calls = [tc for tc in ai_message.tool_calls if tc["id"] != current_id] + [
                {"type": "tool_call", "name": tool_call["name"], "args": edited_args, "id": current_id}
            ]

            # 通过消息副本更新 tool_calls，避免副作用
            result.append(ai_message.model_copy(update={"tool_calls": updated_tool_calls}))

            # 保存反馈并执行编辑后的工具
            if tool_call["name"] == "send_email_tool":
                
                # Execute the tool with edited args
                observation = tool.invoke(edited_args)
                
                # Add only the tool response message
                result.append({"role": "tool", "content": observation, "tool_call_id": current_id})

                # 新增：更新记忆（回复偏好）
                update_memory(store, ("email_assistant", "response_preferences"), [{
                    "role": "user",
                    "content": f"User edited the email response. Here is the initial email generated by the assistant: {initial_tool_call}. Here is the edited email: {edited_args}. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
                }])
            
            # 保存反馈并执行编辑后的会议工具
            elif tool_call["name"] == "schedule_meeting_tool":
                
                # Execute the tool with edited args
                observation = tool.invoke(edited_args)
                
                # Add only the tool response message
                result.append({"role": "tool", "content": observation, "tool_call_id": current_id})

                # 新增：更新记忆（日历偏好）
                update_memory(store, ("email_assistant", "cal_preferences"), [{
                    "role": "user",
                    "content": f"User edited the calendar invitation. Here is the initial calendar invitation generated by the assistant: {initial_tool_call}. Here is the edited calendar invitation: {edited_args}. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
                }])
            
            # 兜底：未知工具类型
            else:
                raise ValueError(f"Invalid tool call: {tool_call['name']}")

        elif response["type"] == "ignore":

            if tool_call["name"] == "send_email_tool":
                # 不执行工具，提示 Agent 如何收尾
                result.append({"role": "tool", "content": "User ignored this email draft. Ignore this email and end the workflow.", "tool_call_id": tool_call["id"]})
                # Go to END
                goto = END
                # 新增：更新分拣偏好
                update_memory(store, ("email_assistant", "triage_preferences"), state["messages"] + result + [{
                    "role": "user",
                    "content": f"The user ignored the email draft. That means they did not want to respond to the email. Update the triage preferences to ensure emails of this type are not classified as respond. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
                }])

            elif tool_call["name"] == "schedule_meeting_tool":
                # 不执行工具，提示 Agent 如何收尾
                result.append({"role": "tool", "content": "User ignored this calendar meeting draft. Ignore this email and end the workflow.", "tool_call_id": tool_call["id"]})
                # Go to END
                goto = END
                # 新增：更新分拣偏好
                update_memory(store, ("email_assistant", "triage_preferences"), state["messages"] + result + [{
                    "role": "user",
                    "content": f"The user ignored the calendar meeting draft. That means they did not want to schedule a meeting for this email. Update the triage preferences to ensure emails of this type are not classified as respond. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
                }])

            elif tool_call["name"] == "Question":
                # 不执行工具，提示 Agent 如何收尾
                result.append({"role": "tool", "content": "User ignored this question. Ignore this email and end the workflow.", "tool_call_id": tool_call["id"]})
                # Go to END
                goto = END
                # 新增：更新分拣偏好
                update_memory(store, ("email_assistant", "triage_preferences"), state["messages"] + result + [{
                    "role": "user",
                    "content": f"The user ignored the Question. That means they did not want to answer the question or deal with this email. Update the triage preferences to ensure emails of this type are not classified as respond. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
                }])

            else:
                raise ValueError(f"Invalid tool call: {tool_call['name']}")

        elif response["type"] == "response":
            # 用户提供了反馈
            user_feedback = response["args"]
            if tool_call["name"] == "send_email_tool":
                # 不执行工具，追加包含用户反馈的消息
                result.append({"role": "tool", "content": f"User gave feedback, which can we incorporate into the email. Feedback: {user_feedback}", "tool_call_id": tool_call["id"]})
                # 新增：更新记忆（回复偏好）
                update_memory(store, ("email_assistant", "response_preferences"), state["messages"] + result + [{
                    "role": "user",
                    "content": f"User gave feedback, which we can use to update the response preferences. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
                }])

            elif tool_call["name"] == "schedule_meeting_tool":
                # 不执行工具，追加包含用户反馈的消息
                result.append({"role": "tool", "content": f"User gave feedback, which can we incorporate into the meeting request. Feedback: {user_feedback}", "tool_call_id": tool_call["id"]})
                # 新增：更新记忆（日历偏好）
                update_memory(store, ("email_assistant", "cal_preferences"), state["messages"] + result + [{
                    "role": "user",
                    "content": f"User gave feedback, which we can use to update the calendar preferences. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}."
                }])

            elif tool_call["name"] == "Question":
                # 不执行工具，追加包含用户反馈的消息
                result.append({"role": "tool", "content": f"User answered the question, which can we can use for any follow up actions. Feedback: {user_feedback}", "tool_call_id": tool_call["id"]})

            else:
                raise ValueError(f"Invalid tool call: {tool_call['name']}")

    # Update the state 
    update = {
        "messages": result,
    }

    return Command(goto=goto, update=update)

# 条件边函数
def should_continue(state: State, store: BaseStore) -> Literal["interrupt_handler", "mark_as_read_node"]:
    """若调用 Done 则转入标记已读节点；否则进入人工审阅节点。"""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls: 
            if tool_call["name"] == "Done":
                # TODO: 此处可将最终回复信息存入背景记忆，便于后续跟进。
                return "mark_as_read_node"
            else:
                return "interrupt_handler"

def mark_as_read_node(state: State):
    email_input = state["email_input"]
    author, to, subject, email_thread, email_id = parse_gmail(email_input)
    mark_as_read(email_id)

# 构建工作流
agent_builder = StateGraph(State)

# 添加节点（包含 store 参数）
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("interrupt_handler", interrupt_handler)
agent_builder.add_node("mark_as_read_node", mark_as_read_node)

# 添加边
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    {
        "interrupt_handler": "interrupt_handler",
        "mark_as_read_node": "mark_as_read_node",
    },
)
agent_builder.add_edge("mark_as_read_node", END)

# 编译 Agent
response_agent = agent_builder.compile()

# 构建包含 store/checkpointer 的整体工作流
overall_workflow = (
    StateGraph(State, input=StateInput)
    .add_node(triage_router)
    .add_node(triage_interrupt_handler)
    .add_node("response_agent", response_agent)
    .add_node("mark_as_read_node", mark_as_read_node)
    .add_edge(START, "triage_router")
    .add_edge("mark_as_read_node", END)
)

email_assistant = overall_workflow.compile()