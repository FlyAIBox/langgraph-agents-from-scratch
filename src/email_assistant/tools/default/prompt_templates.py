"""邮件助理的工具提示模版集合。"""

# Standard tool descriptions for insertion into prompts
STANDARD_TOOLS_PROMPT = """
1. triage_email(ignore, notify, respond) - 将邮件分拣为三类
2. write_email(to, subject, content) - 发送邮件给指定收件人
3. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - 安排会议（preferred_day 为 datetime 对象）
4. check_calendar_availability(day) - 检查指定日期的空闲时间段
5. Done - 邮件已发送
"""

# Tool descriptions for HITL workflow
HITL_TOOLS_PROMPT = """
1. write_email(to, subject, content) - 发送邮件给指定收件人
2. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - 安排会议（preferred_day 为 datetime 对象）
3. check_calendar_availability(day) - 检查指定日期的空闲时间段
4. Question(content) - 向用户提出后续问题
5. Done - 邮件已发送
"""

# Tool descriptions for HITL with memory workflow
# Note: Additional memory specific tools could be added here 
HITL_MEMORY_TOOLS_PROMPT = """
1. write_email(to, subject, content) - 发送邮件给指定收件人
2. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - 安排会议（preferred_day 为 datetime 对象）
3. check_calendar_availability(day) - 检查指定日期的空闲时间段
4. Question(content) - 向用户提出后续问题
5. Done - 邮件已发送
"""

# Tool descriptions for agent workflow without triage
AGENT_TOOLS_PROMPT = """
1. write_email(to, subject, content) - 发送邮件给指定收件人
2. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - 安排会议（preferred_day 为 datetime 对象）
3. check_calendar_availability(day) - 检查指定日期的空闲时间段
4. Done - 邮件已发送
"""