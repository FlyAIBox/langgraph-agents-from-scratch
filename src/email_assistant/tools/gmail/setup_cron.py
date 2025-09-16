#!/usr/bin/env python
"""
在 LangGraph 中为邮件摄取创建定时任务（cron）。

本脚本会在 LangGraph 上创建一个按计划运行的 cron 任务，周期性触发邮件摄取图以处理新邮件。
"""

import argparse
import asyncio
from typing import Optional
from langgraph_sdk import get_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main(
    email: str,
    url: Optional[str] = None,
    minutes_since: int = 60,
    schedule: str = "*/10 * * * *",
    graph_name: str = "email_assistant_hitl_memory_gmail",
    include_read: bool = False,
):
    """创建用于邮件摄取的 cron 任务。"""
    # 连接 LangGraph 服务
    if url is None:
        client = get_client(url="http://127.0.0.1:2024")
    else:
        client = get_client(url=url)
    
    # 构造 cron 任务输入参数
    cron_input = {
        "email": email,
        "minutes_since": minutes_since,
        "graph_name": graph_name,
        "url": url if url else "http://127.0.0.1:2024",
        "include_read": include_read,
        "rerun": False,
        "early": False,
        "skip_filters": False
    }
    
    # 注册 cron 任务
    cron = await client.crons.create(
        "cron",              # The graph name for the cron
        schedule=schedule,   # Cron schedule expression
        input=cron_input     # Input parameters for the cron graph
    )
    
    print(f"Cron 创建成功，调度表达式: {schedule}")
    print(f"将为邮箱执行摄取: {email}")
    print(f"处理过去 {minutes_since} 分钟内的邮件")
    print(f"使用图: {graph_name}")
    
    return cron

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="为 LangGraph 邮件摄取创建 cron 任务")
    
    parser.add_argument(
        "--email",
        type=str,
        required=True,
        help="要拉取往来邮件的邮箱地址",
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="LangGraph 服务 URL",
    )
    parser.add_argument(
        "--minutes-since",
        type=int,
        default=60,
        help="仅处理距今 N 分钟内的邮件",
    )
    parser.add_argument(
        "--schedule",
        type=str,
        default="*/10 * * * *",
        help="Cron 调度表达式（默认每 10 分钟）",
    )
    parser.add_argument(
        "--graph-name",
        type=str,
        default="email_assistant_hitl_memory_gmail",
        help="用于处理邮件的图名称",
    )
    parser.add_argument(
        "--include-read",
        action="store_true",
        help="包含已读邮件",
    )
    
    args = parser.parse_args()
    
    asyncio.run(
        main(
            email=args.email,
            url=args.url,
            minutes_since=args.minutes_since,
            schedule=args.schedule,
            graph_name=args.graph_name,
            include_read=args.include_read,
        )
    )