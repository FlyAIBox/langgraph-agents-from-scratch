# Gmail 集成工具（Gmail Integration Tools）

将你的邮件助理连接到 Gmail 与 Google Calendar API。

## 图（Graph）

`src/email_assistant/email_assistant_hitl_memory_gmail.py` 已配置为使用 Gmail 工具。
  
按下述步骤完成凭据配置后，即可用你的邮箱运行此图。

## 凭据配置（Setup Credentials）

### 1. 创建 Google Cloud 项目并启用所需 API

#### 启用 Gmail 与 Calendar API

1. 前往 [Google APIs Library 启用 Gmail API](https://developers.google.com/workspace/gmail/api/quickstart/python#enable_the_api)
2. 前往 [Google APIs Library 启用 Google Calendar API](https://developers.google.com/workspace/calendar/api/quickstart/python#enable_the_api)

#### 创建 OAuth 凭据

1. 在此为桌面应用授权凭据：[链接](https://developers.google.com/workspace/gmail/api/quickstart/python#authorize_credentials_for_a_desktop_application)
2. 前往 Credentials → Create Credentials → OAuth Client ID
3. Application Type 选择 "Desktop app"
4. 点击 "Create"

> 注意：若使用个人 Gmail（非 Workspace），在 "Audience" 下选择 "External"

<img width="1496" alt="Screenshot 2025-04-26 at 7 43 57 AM" src="https://github.com/user-attachments/assets/718da39e-9b10-4a2a-905c-eda87c1c1126" />

> 然后将你自己添加为 Test User
 
5. 保存下载的 JSON 文件（下一步需要）

### 2. 设置认证文件

1. 将下载的 client secret JSON 放置到 `.secrets` 目录

```bash
# 创建 secrets 目录
mkdir -p src/email_assistant/tools/gmail/.secrets

# 将下载的 client secret 移动到 secrets 目录
mv /path/to/downloaded/client_secret.json src/email_assistant/tools/gmail/.secrets/secrets.json
```

2. 运行 Gmail 初始化脚本

```bash
# 运行初始化脚本
python src/email_assistant/tools/gmail/setup_gmail.py
```

- 将打开浏览器完成 Google 账户授权
- 将在 `.secrets` 目录生成 `token.json`
- 后续 Gmail API 访问将使用该 token

## 本地部署中使用（Use With A Local Deployment）

### 1. 启动 LangGraph 本地服务并运行 Gmail 摄取脚本

1. 完成认证后，本地启动 LangGraph 服务：

```
langgraph dev
```

2. 在另一个终端中运行摄取脚本：

```bash
python src/email_assistant/tools/gmail/run_ingest.py --email lance@langgraph.dev --minutes-since 1000
```

- 默认使用本地部署 URL（http://127.0.0.1:2024）并拉取过去 1000 分钟的邮件
- 使用 LangGraph SDK 将每封邮件发送给本地运行的邮件助理
- 使用 `email_assistant_hitl_memory_gmail` 图（已配置 Gmail 工具）

#### 参数（Parameters）:

- `--graph-name`: Name of the LangGraph to use (default: "email_assistant_hitl_memory_gmail")
- `--email`: The email address to fetch messages from (alternative to setting EMAIL_ADDRESS)
- `--minutes-since`: Only process emails that are newer than this many minutes (default: 60)
- `--url`: URL of the LangGraph deployment (default: http://127.0.0.1:2024)
- `--rerun`: Process emails that have already been processed (default: false)
- `--early`: Stop after processing one email (default: false)
- `--include-read`: Include emails that have already been read (by default only unread emails are processed)
- `--skip-filters`: Process all emails without filtering (by default only latest messages in threads where you're not the sender are processed)

#### 故障排查（Troubleshooting）

- **找不到邮件？** Gmail API 默认会应用一些过滤（如仅重要/主收件箱）。可尝试：
  - 增大 `--minutes-since`（如 1000）扩大时间窗口
  - 使用 `--include-read` 处理已读邮件（默认仅未读）
  - 使用 `--skip-filters` 包含所有消息（不仅是线程最新，且包含你发送的）
  - 组合使用：`--include-read --skip-filters --minutes-since 1000`
  - 使用 `--mock` 以模拟邮件进行测试

### 2. 连接 Agent Inbox

摄取完成后，可在 Agent Inbox（https://dev.agentinbox.ai/）查看所有被中断（需人工审阅）的线程：
* Deployment URL: http://127.0.0.1:2024
* Assistant/Graph ID: `email_assistant_hitl_memory_gmail`
* Name: `Graph Name`

## 运行托管部署（Run A Hosted Deployment）

### 1. 部署到 LangGraph Platform

1. 在 LangSmith 的 deployments 页面创建部署
2. 点击 New Deployment
3. 连接到你 fork 的 [本仓库](https://github.com/langchain-ai/agents-from-scratch) 与目标分支
4. 命名如 `Yourname-Email-Assistant`
5. 添加以下环境变量：
   * `OPENAI_API_KEY`
   * `GMAIL_SECRET` - This is the full dictionary in `.secrets/secrets.json`
   * `GMAIL_TOKEN` - This is the full dictionary in `.secrets/token.json`
6. 点击 Submit 
7. 在部署页面获取 `API URL`（如 https://your-email-assistant-xxx.us.langgraph.app） 

### 2. 在托管部署上运行摄取

部署就绪后，可以通过下述命令测试邮件摄取：

```bash
python src/email_assistant/tools/gmail/run_ingest.py --email lance@langchain.dev --minutes-since 2440 --include-read --url https://your-email-assistant-xxx.us.langgraph.app
```

### 3. 连接 Agent Inbox

摄取完成后，可在 Agent Inbox（https://dev.agentinbox.ai/）查看需人工审阅的线程：
* Deployment URL: https://your-email-assistant-xxx.us.langgraph.app
* Assistant/Graph ID: `email_assistant_hitl_memory_gmail`
* Name: `Graph Name`
* LangSmith API Key: `LANGSMITH_API_KEY`

### 4. 设置 Cron 任务

在托管部署上，可以设置定时任务按固定频率执行摄取脚本。

To automate email ingestion, set up a scheduled cron job using the included setup script:

```bash
python src/email_assistant/tools/gmail/setup_cron.py --email lance@langchain.dev --url https://lance-email-assistant-4681ae9646335abe9f39acebbde8680b.us.langgraph.app 
```

#### 参数（Parameters）：

- `--email`: Email address to fetch messages for (required)
- `--url`: LangGraph deployment URL (required)
- `--minutes-since`: Only fetch emails newer than this many minutes (default: 60)
- `--schedule`: Cron schedule expression (default: "*/10 * * * *" = every 10 minutes)
- `--graph-name`: Name of the graph to use (default: "email_assistant_hitl_memory_gmail")
- `--include-read`: Include emails marked as read (by default only unread emails are processed) (default: false)

#### Cron 工作方式（How the Cron Works）

该 cron 包含两个核心组件：

1. **`src/email_assistant/cron.py`**: Defines a simple LangGraph graph that:
   - Calls the same `fetch_and_process_emails` function used by `run_ingest.py`
   - Wraps this in a simple graph so that it can be run as a hosted cron using LangGraph Platform

2. **`src/email_assistant/tools/gmail/setup_cron.py`**: Creates the scheduled cron job:
   - Uses LangGraph SDK `client.crons.create` to create a cron job for the hosted `cron.py` graph

#### 管理 Cron 任务（Managing Cron Jobs）

To view, update, or delete existing cron jobs, you can use the LangGraph SDK:

```python
from langgraph_sdk import get_client

# Connect to deployment
client = get_client(url="https://your-deployment-url.us.langgraph.app")

# List all cron jobs
cron_jobs = await client.crons.list()
print(cron_jobs)

# Delete a cron job
await client.crons.delete(cron_job_id)
```

## Gmail 摄取流程（How Gmail Ingestion Works）

整体分为三个阶段：

### 1. CLI 参数 → Gmail 查询语句

CLI parameters are translated into a Gmail search query:

- `--minutes-since 1440` → `after:TIMESTAMP` (emails from the last 24 hours)
- `--email you@example.com` → `to:you@example.com OR from:you@example.com` (emails where you're sender or recipient)
- `--include-read` → removes `is:unread` filter (includes read messages)

例如：
```
python run_ingest.py --email you@example.com --minutes-since 1440 --include-read
```

将构造类似如下的查询：
```
(to:you@example.com OR from:you@example.com) after:1745432245
```

### 2. 搜索结果 → 线程处理

For each message returned by the search:

1. The script obtains the thread ID
2. Using this thread ID, it fetches the **complete thread** with all messages
3. Messages in the thread are sorted by date to identify the latest message
4. Depending on filtering options, it processes either:
   - The specific message found in the search (default behavior)
   - The latest message in the thread (when using `--skip-filters`)

### 3. 默认过滤与 `--skip-filters` 的影响

#### 默认过滤策略

Without `--skip-filters`, the system applies these three filters in sequence:

1. **Unread Filter** (controlled by `--include-read`):
   - Default behavior: Only processes unread messages 
   - With `--include-read`: Processes both read and unread messages
   - Implementation: Adds `is:unread` to the Gmail search query
   - This filter happens at the search level before any messages are retrieved

2. **Sender Filter**:
   - Default behavior: Skips messages sent by your own email address
   - Implementation: Checks if your email appears in the "From" header
   - Logic: `is_from_user = email_address in from_header`
   - This prevents the assistant from responding to your own emails

3. **Thread-Position Filter**:
   - Default behavior: Only processes the most recent message in each thread
   - Implementation: Compares message ID with the last message in thread
   - Logic: `is_latest_in_thread = message["id"] == last_message["id"]`
   - Prevents processing older messages when a newer reply exists
   
The combination of these filters means only the latest message in each thread that was not sent by you and is unread (unless `--include-read` is specified) will be processed.

#### `--skip-filters` 的作用

When `--skip-filters` is enabled:

1. **Bypasses Sender and Thread-Position Filters**:
   - Messages sent by you will be processed
   - Messages that aren't the latest in thread will be processed
   - Logic: `should_process = skip_filters or (not is_from_user and is_latest_in_thread)`

2. **Changes Which Message Is Processed**:
   - Without `--skip-filters`: Uses the specific message found by search
   - With `--skip-filters`: Always uses the latest message in the thread
   - Even if the latest message wasn't found in the search results

3. **Unread Filter Still Applies (unless overridden)**:
   - `--skip-filters` does NOT bypass the unread filter
   - To process read messages, you must still use `--include-read`
   - This is because the unread filter happens at the search level

小结：
- Default: Process only unread messages where you're not the sender and that are the latest in their thread
- `--skip-filters`: Process all messages found by search, using the latest message in each thread
- `--include-read`: Include read messages in the search
- `--include-read --skip-filters`: Most comprehensive, processes the latest message in all threads found by search

## Gmail API 的一些限制

这些限制会影响摄取体验：

1. **Search-Based API**: Gmail doesn't provide a direct "get all emails from timeframe" endpoint
   - All email retrieval relies on Gmail's search functionality
   - Search results can be delayed for very recent messages (indexing lag)
   - Search results might not include all messages that technically match criteria

2. **Two-Stage Retrieval Process**:
   - Initial search to find relevant message IDs
   - Secondary thread retrieval to get complete conversations
   - This two-stage process is necessary because search doesn't guarantee complete thread information