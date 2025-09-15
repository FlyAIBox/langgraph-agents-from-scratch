from pydantic import BaseModel, Field
from typing_extensions import TypedDict, Literal
from langgraph.graph import MessagesState

class RouterSchema(BaseModel):
    """分析未读邮件，并依据其内容进行路由。

    面向初学者说明：模型需要给出分类理由（reasoning）以及分类结果（classification），
    以便后续的分拣/通知/回复流程作出正确决策。
    """

    reasoning: str = Field(
        description="Step-by-step reasoning behind the classification."
    )
    classification: Literal["ignore", "respond", "notify"] = Field(
        description="The classification of an email: 'ignore' for irrelevant emails, "
        "'notify' for important information that doesn't need a response, "
        "'respond' for emails that need a reply",
    )

class StateInput(TypedDict):
    # 这是写入图状态（State）的输入
    email_input: dict

class State(MessagesState):
    # 该状态类内置 messages 键，用于保存对话消息
    email_input: dict
    classification_decision: Literal["ignore", "respond", "notify"]

class EmailData(TypedDict):
    id: str
    thread_id: str
    from_email: str
    subject: str
    page_content: str
    send_time: str
    to_email: str

class UserPreferences(BaseModel):
    """基于用户反馈更新得到的用户偏好（Profile）。"""
    chain_of_thought: str = Field(description="关于需要新增/更新哪些偏好的推理过程（面向开发者，可用于审计）")
    user_preferences: str = Field(description="更新后的用户偏好文本描述")