from typing import Dict, List, Callable, Any, Optional
from langchain_core.tools import BaseTool

def get_tools(tool_names: Optional[List[str]] = None, include_gmail: bool = False) -> List[BaseTool]:
    """获取指定的工具；若未指定则返回全部工具。

    Args:
        tool_names: 可选的工具名列表；为 None 时返回全部工具。
        include_gmail: 是否包含 Gmail 工具，默认为 False。
        
    Returns:
        工具对象列表（List[BaseTool]）
    """
    # Import default tools
    from email_assistant.tools.default.email_tools import write_email, Done, Question
    from email_assistant.tools.default.calendar_tools import schedule_meeting, check_calendar_availability
    
    # Base tools dictionary
    all_tools = {
        "write_email": write_email,
        "Done": Done,
        "Question": Question,
        "schedule_meeting": schedule_meeting,
        "check_calendar_availability": check_calendar_availability,
    }
    
    # 如需要，加入 Gmail 工具
    if include_gmail:
        try:
            from email_assistant.tools.gmail.gmail_tools import (
                fetch_emails_tool,
                send_email_tool,
                check_calendar_tool,
                schedule_meeting_tool
            )
            
            all_tools.update({
                "fetch_emails_tool": fetch_emails_tool,
                "send_email_tool": send_email_tool,
                "check_calendar_tool": check_calendar_tool,
                "schedule_meeting_tool": schedule_meeting_tool,
            })
        except ImportError:
            # 若 Gmail 工具不可用，忽略并继续
            pass
    
    if tool_names is None:
        return list(all_tools.values())
    
    return [all_tools[name] for name in tool_names if name in all_tools]

def get_tools_by_name(tools: Optional[List[BaseTool]] = None) -> Dict[str, BaseTool]:
    """按名称返回工具映射字典。

    若未传入 tools，则先获取全部工具。
    """
    if tools is None:
        tools = get_tools()
    
    return {tool.name: tool for tool in tools}
