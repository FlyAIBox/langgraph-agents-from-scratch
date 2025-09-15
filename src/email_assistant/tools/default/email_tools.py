from typing import Literal
from pydantic import BaseModel
from langchain_core.tools import tool

@tool
def write_email(to: str, subject: str, content: str) -> str:
    """撰写并发送邮件（示例版）。"""
    # 占位实现：真实应用中应调用邮件发送服务
    return f"Email sent to {to} with subject '{subject}' and content: {content}"

@tool
def triage_email(category: Literal["ignore", "notify", "respond"]) -> str:
    """将邮件分拣为三类之一：ignore / notify / respond。"""
    return f"Classification Decision: {category}"

@tool
class Done(BaseModel):
    """表示邮件已发送，流程可结束。"""
    done: bool

@tool
class Question(BaseModel):
      """向用户发问以收集必要信息。"""
      content: str
