from typing import Literal
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.graph import MessagesState, StateGraph, END, START
from dotenv import load_dotenv
load_dotenv(".env")

@tool
def write_email(to: str, subject: str, content: str) -> str:
    """撰写并发送邮件（示例）。"""
    # 占位实现：真实应用应调用发送服务
    return f"Email sent to {to} with subject '{subject}' and content: {content}"

llm = init_chat_model("openai:gpt-4.1", temperature=0)
model_with_tools = llm.bind_tools([write_email], tool_choice="any")

def call_llm(state: MessagesState) -> MessagesState:
    """调用 LLM（可携带工具）"""

    output = model_with_tools.invoke(state["messages"])
    return {"messages": [output]}

def run_tool(state: MessagesState) -> MessagesState:
    """执行工具调用"""

    result = []
    for tool_call in state["messages"][-1].tool_calls:
        observation = write_email.invoke(tool_call["args"])
        result.append({"role": "tool", "content": observation, "tool_call_id": tool_call["id"]})
    return {"messages": result}

def should_continue(state: MessagesState) -> Literal["run_tool", "__end__"]:
    """若需要工具则进入 run_tool；否则结束。"""
    
    # Get the last message
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message is a tool call, check if it's a Done tool call
    if last_message.tool_calls:
        return "run_tool"
    # Otherwise, we stop (reply to the user)
    return END

workflow = StateGraph(MessagesState)
workflow.add_node("call_llm", call_llm)
workflow.add_node("run_tool", run_tool)
workflow.add_edge(START, "call_llm")
workflow.add_conditional_edges("call_llm", should_continue, {"run_tool": "run_tool", END: END})
workflow.add_edge("run_tool", END)

app = workflow.compile()