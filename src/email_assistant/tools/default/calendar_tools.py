from datetime import datetime
from langchain_core.tools import tool

@tool
def schedule_meeting(
    attendees: list[str], subject: str, duration_minutes: int, preferred_day: datetime, start_time: int
) -> str:
    """安排日历会议（示例实现）。"""
    # 占位响应：真实应用应查询并写入实际日历
    date_str = preferred_day.strftime("%A, %B %d, %Y")
    return f"Meeting '{subject}' scheduled on {date_str} at {start_time} for {duration_minutes} minutes with {len(attendees)} attendees"

@tool
def check_calendar_availability(day: str) -> str:
    """检查指定日期的日历空闲时间段（示例实现）。"""
    # 占位响应：真实应用应查询实际日历数据
    return f"Available times on {day}: 9:00 AM, 2:00 PM, 4:00 PM"
