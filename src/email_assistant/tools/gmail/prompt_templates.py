"""Gmail 集成的工具提示模版。"""

# 用于注入 Agent 系统提示的 Gmail 工具描述
GMAIL_TOOLS_PROMPT = """
1. fetch_emails_tool(email_address, minutes_since) - 从 Gmail 拉取近期邮件
2. send_email_tool(email_id, response_text, email_address, additional_recipients) - 回复邮件线程
3. check_calendar_tool(dates) - 查询 Google Calendar 指定日期的可用性
4. schedule_meeting_tool(attendees, title, start_time, end_time, organizer_email, timezone) - 安排会议并发送邀请
5. triage_email(ignore, notify, respond) - 邮件三分类分拣
6. Done - 邮件已发送
"""

# 完整集成（默认工具 + Gmail）的工具描述
COMBINED_TOOLS_PROMPT = """
1. fetch_emails_tool(email_address, minutes_since) - 从 Gmail 拉取近期邮件
2. send_email_tool(email_id, response_text, email_address, additional_recipients) - 回复邮件线程
3. check_calendar_tool(dates) - 查询 Google Calendar 指定日期的可用性
4. schedule_meeting_tool(attendees, title, start_time, end_time, organizer_email, timezone) - 安排会议并发送邀请
5. write_email(to, subject, content) - 擬写并发送邮件
6. triage_email(ignore, notify, respond) - 邮件三分类分拣
7. check_calendar_availability(day) - 检查指定日期的空闲时段
8. Done - 邮件已发送
"""