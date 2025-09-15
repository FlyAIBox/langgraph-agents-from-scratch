from typing import Literal

from langchain.chat_models import init_chat_model

from email_assistant.tools import get_tools, get_tools_by_name
from email_assistant.tools.default.prompt_templates import AGENT_TOOLS_PROMPT
from email_assistant.prompts import triage_system_prompt, triage_user_prompt, agent_system_prompt, default_background, default_triage_instructions, default_response_preferences, default_cal_preferences
from email_assistant.schemas import State, RouterSchema, StateInput
from email_assistant.utils import parse_email, format_email_markdown

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from dotenv import load_dotenv
load_dotenv(".env")

# 获取工具集合
tools = get_tools()
tools_by_name = get_tools_by_name(tools)

# 初始化用于路由/结构化输出的聊天模型（LLM）
llm = init_chat_model("openai:gpt-4.1", temperature=0.0)
llm_router = llm.with_structured_output(RouterSchema) 

# 初始化用于 Agent 的模型，允许使用任意可用工具（tool_choice="any"）
llm = init_chat_model("openai:gpt-4.1", temperature=0.0)
llm_with_tools = llm.bind_tools(tools, tool_choice="any")

# 图中的节点（Nodes）
def llm_call(state: State):
    """LLM 判断是否需要调用工具。

    初学者提示：在 Agent-Tool 模式中，LLM 会基于系统提示词与对话状态，选择直接回复或发起一个/多个工具调用。
    """

    return {
        "messages": [
            llm_with_tools.invoke(
                [
                    {"role": "system", "content": agent_system_prompt.format(
                        tools_prompt=AGENT_TOOLS_PROMPT,
                        background=default_background,
                        response_preferences=default_response_preferences, 
                        cal_preferences=default_cal_preferences)
                    },
                    
                ]
                + state["messages"]
            )
        ]
    }

def tool_node(state: State):
    """执行工具调用。

    遍历上一条 AI 消息中的 tool_calls，逐一根据名称取出工具并执行，其结果作为 tool 角色消息写回状态。
    """

    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append({"role": "tool", "content" : observation, "tool_call_id": tool_call["id"]})
    return {"messages": result}

# 条件边（Conditional Edge）函数
def should_continue(state: State) -> Literal["Action", "__end__"]:
    """路由到下一步 Action；若调用了 Done 工具则结束流程。"""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls: 
            if tool_call["name"] == "Done":
                return END
            else:
                return "Action"

# 构建工作流（Workflow）
agent_builder = StateGraph(State)

# 添加节点
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("environment", tool_node)

# 添加边以连接节点
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    {
        # should_continue 返回的名称 : 下一步要访问的节点名
        "Action": "environment",
        END: END,
    },
)
agent_builder.add_edge("environment", "llm_call")

# 编译 Agent（得到可运行的图）
agent = agent_builder.compile()

def triage_router(state: State) -> Command[Literal["response_agent", "__end__"]]:
    """分析邮件内容，决定“回复（respond）/通知（notify）/忽略（ignore）”。

    该分拣（triage）步骤可避免助手在如下邮件上浪费时间：
    - 市场邮件与垃圾邮件
    - 全公司公告
    - 明显与当前团队无关的邮件
    """
    author, to, subject, email_thread = parse_email(state["email_input"])
    system_prompt = triage_system_prompt.format(
        background=default_background,
        triage_instructions=default_triage_instructions
    )

    user_prompt = triage_user_prompt.format(
        author=author, to=to, subject=subject, email_thread=email_thread
    )

    # 若为通知场景，为 Agent Inbox 生成可读的邮件 Markdown  
    email_markdown = format_email_markdown(subject, author, to, email_thread)

    # 运行路由用的 LLM（结构化输出分类结果）
    result = llm_router.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    # 分类决策结果
    classification = result.classification

    if classification == "respond":
        print("📧 Classification: RESPOND - This email requires a response")
        goto = "response_agent"
        # 将“需回复的邮件内容”加入消息，交由回复 Agent 处理
        update = {
            "classification_decision": result.classification,
            "messages": [{"role": "user",
                            "content": f"Respond to the email: {email_markdown}"
                        }],
        }
    elif result.classification == "ignore":
        print("🚫 Classification: IGNORE - This email can be safely ignored")
        update =  {
            "classification_decision": result.classification,
        }
        goto = END
    elif result.classification == "notify":
        # 生产环境下，此处可触发通知管道（此示例直接结束）
        print("🔔 Classification: NOTIFY - This email contains important information")
        update = {
            "classification_decision": result.classification,
        }
        goto = END
    else:
        raise ValueError(f"Invalid classification: {result.classification}")
    return Command(goto=goto, update=update)

# 构建整体工作流（分拣 -> 回复 Agent）
overall_workflow = (
    StateGraph(State, input=StateInput)
    .add_node(triage_router)
    .add_node("response_agent", agent)
    .add_edge(START, "triage_router")
)

email_assistant = overall_workflow.compile()