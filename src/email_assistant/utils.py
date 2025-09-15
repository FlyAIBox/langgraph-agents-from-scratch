from typing import List, Any
import json
import html2text

def format_email_markdown(subject, author, to, email_thread, email_id=None):
    """将邮件详情格式化为 Markdown，方便展示。

    说明：该函数仅做展示用的格式拼接，不改变原始内容。
    
    Args:
        subject: 邮件主题
        author: 发件人
        to: 收件人
        email_thread: 邮件正文（线程）
        email_id: 可选的邮件 ID（Gmail API 场景）
    """
    id_section = f"\n**ID**: {email_id}" if email_id else ""
    
    return f"""

**Subject**: {subject}
**From**: {author}
**To**: {to}{id_section}

{email_thread}

---
"""

def format_gmail_markdown(subject, author, to, email_thread, email_id=None):
    """将 Gmail 邮件详情格式化为 Markdown，并在必要时将 HTML 正文转换为纯文本。

    注意：会检测常见 HTML 结构并做转换；其它情况保留原样。
    
    Args:
        subject: 邮件主题
        author: 发件人
        to: 收件人
        email_thread: 邮件正文（可能为 HTML）
        email_id: 可选的邮件 ID（Gmail API 场景）
    """
    id_section = f"\n**ID**: {email_id}" if email_id else ""
    
    # Check if email_thread is HTML content and convert to text if needed
    if email_thread and (email_thread.strip().startswith("<!DOCTYPE") or 
                          email_thread.strip().startswith("<html") or
                          "<body" in email_thread):
        # Convert HTML to markdown text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0  # Don't wrap text
        email_thread = h.handle(email_thread)
    
    return f"""

**Subject**: {subject}
**From**: {author}
**To**: {to}{id_section}

{email_thread}

---
"""

def format_for_display(tool_call):
    """将工具调用内容格式化为 Agent Inbox 可读的展示。
    
    Args:
        tool_call: 待展示的工具调用
    """
    # Initialize empty display
    display = ""
    
    # Add tool call information
    if tool_call["name"] == "write_email":
        display += f"""# Email Draft

**To**: {tool_call["args"].get("to")}
**Subject**: {tool_call["args"].get("subject")}

{tool_call["args"].get("content")}
"""
    elif tool_call["name"] == "schedule_meeting":
        display += f"""# Calendar Invite

**Meeting**: {tool_call["args"].get("subject")}
**Attendees**: {', '.join(tool_call["args"].get("attendees"))}
**Duration**: {tool_call["args"].get("duration_minutes")} minutes
**Day**: {tool_call["args"].get("preferred_day")}
"""
    elif tool_call["name"] == "Question":
        # Special formatting for questions to make them clear
        display += f"""# Question for User

{tool_call["args"].get("content")}
"""
    else:
        # Generic format for other tools
        display += f"""# Tool Call: {tool_call["name"]}

Arguments:"""
        
        # Check if args is a dictionary or string
        if isinstance(tool_call["args"], dict):
            display += f"\n{json.dumps(tool_call['args'], indent=2)}\n"
        else:
            display += f"\n{tool_call['args']}\n"
    return display

def parse_email(email_input: dict) -> dict:
    """解析通用邮件输入字典，提取关键信息。

    Args:
        email_input (dict): 含以下字段：
            - author: 发件人（姓名/邮箱）
            - to: 收件人（姓名/邮箱）
            - subject: 主题
            - email_thread: 正文（完整线程）
    
    Returns:
        tuple[str, str, str, str]: 依次为 author、to、subject、email_thread
    """
    return (
        email_input["author"],
        email_input["to"],
        email_input["subject"],
        email_input["email_thread"],
    )

def parse_gmail(email_input: dict) -> tuple[str, str, str, str, str]:
    """解析 Gmail 输入，包含邮件 ID。
    
    说明：在通用解析的基础上，额外返回 Gmail 的 `id` 字段，以便后续 API 操作。

    Args:
        email_input (dict): Gmail 结构：
            - from: 发件邮箱
            - to: 收件邮箱
            - subject: 主题
            - body: 正文
            - id: Gmail 消息 ID
            
    Returns:
        tuple[str, str, str, str, str]: 依次为 author、to、subject、email_thread、email_id
    """

    print("!Email_input from Gmail!")
    print(email_input)

    # Gmail schema
    return (
        email_input["from"],
        email_input["to"],
        email_input["subject"],
        email_input["body"],
        email_input["id"],
    )
    
def extract_message_content(message) -> str:
    """从不同消息类型中提取字符串内容，尽量规避递归结构。
    
    Args:
        message: 消息对象（HumanMessage / AIMessage / ToolMessage）
        
    Returns:
        str: 提取出的纯文本内容
    """
    content = message.content
    
    # Check for recursion marker in string
    if isinstance(content, str) and '<Recursion on AIMessage with id=' in content:
        return "[Recursive content]"
    
    # Handle string content
    if isinstance(content, str):
        return content
        
    # Handle list content (AIMessage format)
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and 'text' in item:
                text_parts.append(item['text'])
        return "\n".join(text_parts)
    
    # Don't try to handle recursion to avoid infinite loops
    # Just return string representation instead
    return str(content)

def format_few_shot_examples(examples):
    """将少样本示例格式化为可读字符串，便于放入提示词。

    Args:
        examples (List[Item]): 向量库返回的示例条目，每条的 value 大致形如：
            'Email: {...} Original routing: {...} Correct routing: {...}'

    Returns:
        str: 汇总后的多示例字符串，每个示例按如下模板排版：
            Example:
            Email: {email_details}
            Original Classification: {original_routing}
            Correct Classification: {correct_routing}
            ---
    """
    formatted = []
    for example in examples:
        # Parse the example value string into components
        email_part = example.value.split('Original routing:')[0].strip()
        original_routing = example.value.split('Original routing:')[1].split('Correct routing:')[0].strip()
        correct_routing = example.value.split('Correct routing:')[1].strip()
        
        # Format into clean string
        formatted_example = f"""Example:
Email: {email_part}
Original Classification: {original_routing}
Correct Classification: {correct_routing}
---"""
        formatted.append(formatted_example)
    
    return "\n".join(formatted)

def extract_tool_calls(messages: List[Any]) -> List[str]:
    """从消息列表中提取工具调用名称；安全处理无 tool_calls 的消息。"""
    tool_call_names = []
    for message in messages:
        # Check if message is a dict and has tool_calls
        if isinstance(message, dict) and message.get("tool_calls"):
            tool_call_names.extend([call["name"].lower() for call in message["tool_calls"]])
        # Check if message is an object with tool_calls attribute
        elif hasattr(message, "tool_calls") and message.tool_calls:
            tool_call_names.extend([call["name"].lower() for call in message.tool_calls])
    
    return tool_call_names

def format_messages_string(messages: List[Any]) -> str:
    """将消息合并为单一字符串，便于分析或记录。"""
    return '\n'.join(message.pretty_repr() for message in messages)

def show_graph(graph, xray=False):
    """展示 LangGraph 的 Mermaid 图，带超时降级渲染。
    
    若 mermaid.ink 超时，则回退到 pyppeteer 渲染方式。
    
    Args:
        graph: 具有 get_graph() 方法的 LangGraph 对象
    """
    from IPython.display import Image
    try:
        # Try the default renderer first
        return Image(graph.get_graph(xray=xray).draw_mermaid_png())
    except Exception as e:
        # Fall back to pyppeteer if the default renderer fails
        import nest_asyncio
        nest_asyncio.apply()
        from langchain_core.runnables.graph import MermaidDrawMethod
        return Image(graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.PYPPETEER))