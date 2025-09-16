#!/usr/bin/env python
"""
Gmail API 集成的初始化脚本。

本脚本完成 Gmail API 的 OAuth 授权流程：
1. 创建 `.secrets` 目录（若不存在）
2. 读取 `.secrets/secrets.json` 中的 client 凭据
3. 打开浏览器完成用户授权
4. 将 access token 写入 `.secrets/token.json`
"""

import os
import sys
import json
from pathlib import Path

# Add project root to sys.path for imports to work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

# Import required Google libraries
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

def main():
    """执行 Gmail 认证初始化流程。"""
    # Create .secrets directory
    secrets_dir = Path(__file__).parent.absolute() / ".secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查 secrets.json 是否存在
    secrets_path = secrets_dir / "secrets.json"
    if not secrets_path.exists():
        print(f"Error: Client secrets file not found at {secrets_path}")
        print("请在 Google Cloud Console 下载 OAuth client ID JSON")
        print("并保存为 .secrets/secrets.json")
        return 1
    
    print("开始 Gmail API 认证流程...")
    print("将打开浏览器窗口完成授权。")
    
    # This will trigger the OAuth flow and create token.json
    try:
        # 定义所需的 OAuth scopes
        SCOPES = [
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/calendar'
        ]
        
        # 读取 client secrets
        with open(secrets_path, 'r') as f:
            client_config = json.load(f)
        
        # 基于 secrets 文件创建 OAuth 流程
        flow = InstalledAppFlow.from_client_secrets_file(
            str(secrets_path),
            SCOPES
        )
        
        # 启动本地 OAuth 回调服务器并完成授权
        credentials = flow.run_local_server(port=0)
        
        # 将凭据保存到 token.json
        token_path = secrets_dir / "token.json"
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'universe_domain': 'googleapis.com',
            'account': '',
            'expiry': credentials.expiry.isoformat() + "Z"
        }
        
        with open(token_path, 'w') as token_file:
            json.dump(token_data, token_file)
            
        print("\n认证成功！")
        print(f"Access token 已保存至: {token_path}")
        return 0
    except Exception as e:
        print(f"认证失败: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())