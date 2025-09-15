#!/usr/bin/env python
"""
简易的 Gmail 邮件摄取（ingestion）脚本，基于测试流程整理，并可配合 LangSmith 追踪。

用途：将 Gmail 邮件最小化地摄取并发送到 LangGraph 服务端，同时保证稳定的 LangSmith Tracing。
"""

import base64
import json
import uuid
import hashlib
import asyncio
import argparse
import os
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langgraph_sdk import get_client
from dotenv import load_dotenv

load_dotenv()

# Setup paths
_ROOT = Path(__file__).parent.absolute()
_SECRETS_DIR = _ROOT / ".secrets"
TOKEN_PATH = _SECRETS_DIR / "token.json"

def extract_message_part(payload):
    """从消息分段结构中抽取文本内容。"""
    # 若为 multipart，优先选择 text/plain
    if payload.get("parts"):
        # First try to find text/plain part
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain" and part.get("body", {}).get("data"):
                data = part["body"]["data"]
                return base64.urlsafe_b64decode(data).decode("utf-8")
                
        # If no text/plain found, try text/html
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/html" and part.get("body", {}).get("data"):
                data = part["body"]["data"]
                return base64.urlsafe_b64decode(data).decode("utf-8")
                
        # If we still haven't found content, recursively check for nested parts
        for part in payload["parts"]:
            content = extract_message_part(part)
            if content:
                return content
    
    # 非 multipart，直接取 body.data
    if payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8")

    return ""

def load_gmail_credentials():
    """
    从 token.json 或环境变量加载 Gmail 凭据（优先级：环境变量 GMAIL_TOKEN -> 本地 .secrets/token.json）。
    
    Returns:
        Google OAuth2 Credentials 对象；若无法加载则返回 None
    """
    token_data = None
    
    # 1. Try environment variable
    env_token = os.getenv("GMAIL_TOKEN")
    if env_token:
        try:
            token_data = json.loads(env_token)
            print("Using GMAIL_TOKEN environment variable")
        except Exception as e:
            print(f"Could not parse GMAIL_TOKEN environment variable: {str(e)}")
    
    # 2. Try local file as fallback
    if token_data is None:
        if TOKEN_PATH.exists():
            try:
                with open(TOKEN_PATH, "r") as f:
                    token_data = json.load(f)
                print(f"Using token from {TOKEN_PATH}")
            except Exception as e:
                print(f"Could not load token from {TOKEN_PATH}: {str(e)}")
        else:
            print(f"Token file not found at {TOKEN_PATH}")
    
    # If we couldn't get token data from any source, return None
    if token_data is None:
        print("Could not find valid token data in any location")
        return None
    
    try:
        # Create credentials object
        credentials = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"])
        )
        return credentials
    except Exception as e:
        print(f"Error creating credentials object: {str(e)}")
        return None

def extract_email_data(message):
    """从 Gmail 消息中提取关键信息。"""
    headers = message['payload']['headers']
    
    # Extract key headers
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
    from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
    to_email = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown Recipient')
    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
    
    # Extract message content
    content = extract_message_part(message['payload'])
    
    # Create email data object
    email_data = {
        "from_email": from_email,
        "to_email": to_email,
        "subject": subject,
        "page_content": content,
        "id": message['id'],
        "thread_id": message['threadId'],
        "send_time": date
    }
    
    return email_data

async def ingest_email_to_langgraph(email_data, graph_name, url="http://127.0.0.1:2024"):
    """将单封邮件摄取（ingest）到 LangGraph。"""
    # 连接到 LangGraph 服务
    client = get_client(url=url)
    
    # 为线程创建可复用的稳定 UUID
    raw_thread_id = email_data["thread_id"]
    thread_id = str(
        uuid.UUID(hex=hashlib.md5(raw_thread_id.encode("UTF-8")).hexdigest())
    )
    print(f"Gmail thread ID: {raw_thread_id} → LangGraph thread ID: {thread_id}")
    
    thread_exists = False
    try:
        # Try to get existing thread info
        thread_info = await client.threads.get(thread_id)
        thread_exists = True
        print(f"Found existing thread: {thread_id}")
    except Exception as e:
        # If thread doesn't exist, create it
        print(f"Creating new thread: {thread_id}")
        thread_info = await client.threads.create(thread_id=thread_id)
    
    # 若线程已存在，清理历史 runs 防止状态污染
    if thread_exists:
        try:
            # List all runs for this thread
            runs = await client.runs.list(thread_id)
            
            # Delete all previous runs to avoid state accumulation
            for run_info in runs:
                run_id = run_info.id
                print(f"Deleting previous run {run_id} from thread {thread_id}")
                try:
                    await client.runs.delete(thread_id, run_id)
                except Exception as e:
                    print(f"Failed to delete run {run_id}: {str(e)}")
        except Exception as e:
            print(f"Error listing/deleting runs: {str(e)}")
    
    # 使用当前 email ID 更新线程元数据
    await client.threads.update(thread_id, metadata={"email_id": email_data["id"]})
    
    # 新建 run 以处理该邮件
    print(f"Creating run for thread {thread_id} with graph {graph_name}")
    
    run = await client.runs.create(
        thread_id,
        graph_name,
        input={"email_input": {
            "from": email_data["from_email"],
            "to": email_data["to_email"],
            "subject": email_data["subject"],
            "body": email_data["page_content"],
            "id": email_data["id"]
        }},
        multitask_strategy="rollback",
    )
    
    print(f"Run created successfully with thread ID: {thread_id}")
    
    return thread_id, run

async def fetch_and_process_emails(args):
    """从 Gmail 拉取邮件，并经由 LangGraph 处理。"""
    # 加载 Gmail 凭据
    credentials = load_gmail_credentials()
    if not credentials:
        print("Failed to load Gmail credentials")
        return 1
        
    # 构建 Gmail service
    service = build("gmail", "v1", credentials=credentials)
    
    # 处理邮件
    processed_count = 0
    
    try:
        # 针对指定邮箱构造查询
        email_address = args.email
        
        # 构造 Gmail 查询语句
        query = f"to:{email_address} OR from:{email_address}"
        
        # 如指定时间窗口，则加入过滤
        if args.minutes_since > 0:
            # Calculate timestamp for filtering
            from datetime import timedelta
            after = int((datetime.now() - timedelta(minutes=args.minutes_since)).timestamp())
            query += f" after:{after}"
            
        # 默认仅处理未读；若 include_read，则包含已读
        if not args.include_read:
            query += " is:unread"
            
        print(f"Gmail search query: {query}")
        
        # 执行搜索
        results = service.users().messages().list(userId="me", q=query).execute()
        messages = results.get("messages", [])
        
        if not messages:
            print("No emails found matching the criteria")
            return 0
            
        print(f"Found {len(messages)} emails")
        
        # 逐封处理
        for i, message_info in enumerate(messages):
            # 若指定 early，则仅处理一封后退出
            if args.early and i > 0:
                print(f"Early stop after processing {i} emails")
                break
                
            # 若未启用 rerun，可在此加入“是否已处理”的去重逻辑
            if not args.rerun:
                # TODO: Add check for already processed emails
                pass
                
            # 拉取邮件详情
            message = service.users().messages().get(userId="me", id=message_info["id"]).execute()
            
            # 提取关键信息
            email_data = extract_email_data(message)
            
            print(f"\nProcessing email {i+1}/{len(messages)}:")
            print(f"From: {email_data['from_email']}")
            print(f"Subject: {email_data['subject']}")
            
            # 摄取到 LangGraph
            thread_id, run = await ingest_email_to_langgraph(
                email_data, 
                args.graph_name,
                url=args.url
            )
            
            processed_count += 1
            
        print(f"\nProcessed {processed_count} emails successfully")
        return 0
        
    except Exception as e:
        print(f"Error processing emails: {str(e)}")
        return 1

def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="简易 Gmail 摄取（含稳定追踪）")
    
    parser.add_argument(
        "--email", 
        type=str, 
        required=True,
        help="要拉取往来邮件的邮箱地址"
    )
    parser.add_argument(
        "--minutes-since", 
        type=int, 
        default=120,
        help="仅获取距今 N 分钟内的邮件"
    )
    parser.add_argument(
        "--graph-name", 
        type=str, 
        default="email_assistant_hitl_memory_gmail",
        help="要使用的 LangGraph 图名称"
    )
    parser.add_argument(
        "--url", 
        type=str, 
        default="http://127.0.0.1:2024",
        help="LangGraph 部署的 URL"
    )
    parser.add_argument(
        "--early", 
        action="store_true",
        help="仅处理一封邮件后提前结束"
    )
    parser.add_argument(
        "--include-read",
        action="store_true",
        help="包含已读邮件"
    )
    parser.add_argument(
        "--rerun", 
        action="store_true",
        help="即使已处理过仍重复处理（不去重）"
    )
    parser.add_argument(
        "--skip-filters",
        action="store_true",
        help="跳过发件人/线程位置等过滤逻辑"
    )
    return parser.parse_args()

if __name__ == "__main__":
    # Get command line arguments
    args = parse_args()
    
    # Run the script
    exit(asyncio.run(fetch_and_process_emails(args)))