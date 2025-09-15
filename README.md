# 从零构建智能体（Agents From Scratch） 

本仓库是一份从零构建智能体（Agent）的实践指南。我们最终将完成一种可称为“环境型”（ambient）的邮件助理，它可连接 Gmail API 管理你的邮件。项目分为 4 个部分，每部分包含一个配套的 Notebook 与对应的代码（位于 `src/email_assistant` 目录）。内容从 Agent 基础、到评测（Evaluation）、再到人机协同（HITL），最终加入记忆（Memory）。这些能力汇总成一个可部署的智能体，同时其方法也可迁移到其他任务场景。

![overview](notebooks/img/overview.png)

## 环境准备 

### Python 版本

* 请使用 Python 3.11 或更高版本。
* 该版本对 LangGraph 的兼容性更佳。

```shell
python3 --version
```

### API 密钥

* 如无 OpenAI API Key，可在此注册获取：<https://openai.com/index/openai-api/>
* 注册 LangSmith：<https://smith.langchain.com/>
* 生成你的 LangSmith API Key。

### 设置环境变量

* 在项目根目录创建 `.env` 文件：
```shell
# 从示例复制
cp .env.example .env
```

* 将以下内容填入 `.env`：
```shell
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT="interrupt-workshop"
OPENAI_API_KEY=your_openai_api_key
```

* 也可在终端直接导出环境变量：
```shell
export LANGSMITH_API_KEY=your_langsmith_api_key
export LANGSMITH_TRACING=true
export OPENAI_API_KEY=your_openai_api_key
```

### 依赖安装

**推荐：使用 uv（更快更稳定）**

```shell
# 如未安装 uv，请先安装
pip install uv

# 安装本项目及开发依赖
uv sync --extra dev

# 激活虚拟环境
source .venv/bin/activate
```

**可选：使用 pip**

```shell
$ python3 -m venv .venv
$ source .venv/bin/activate
# 升级 pip（pyproject.toml 的可编辑安装需要较新版本）
$ python3 -m pip install --upgrade pip
# 以可编辑模式安装项目
$ pip install -e .
```

> **⚠️ 重要**：不要跳过安装步骤！可编辑安装是笔记本顺利运行的必要前提。安装后，包名为 `interrupt_workshop`，导入名为 `email_assistant`，因此可在任意位置使用 `from email_assistant import ...` 进行导入。

## 结构 

本仓库分为 4 个部分，每部分对应一个 Notebook，并在 `src/email_assistant` 中提供配套代码。

### 序：LangGraph 101
若需快速了解 LangGraph 及本仓库所用核心概念，请参阅 [LangGraph 101 笔记本](notebooks/langgraph_101.ipynb)。内容涵盖：聊天模型与工具调用、Agent 与工作流的区别、LangGraph 的节点 / 边 / 记忆，以及 LangGraph Studio 的基本使用。

### 构建一个 Agent 
* Notebook：[/notebooks/agent.ipynb](/notebooks/agent.ipynb)
* 代码：[/src/email_assistant/email_assistant.py](/src/email_assistant/email_assistant.py)

![overview-agent](notebooks/img/overview_agent.png)

该笔记本展示如何构建邮件助理：先进行[邮件分拣（Triage）](https://langchain-ai.github.io/langgraph/tutorials/workflows/)，再由 Agent 完成回复。完整实现可见 `src/email_assistant/email_assistant.py`。

![Screenshot 2025-04-04 at 4 06 18 PM](notebooks/img/studio.png)

### 评测（Evaluation） 
* Notebook：[/notebooks/evaluation.ipynb](/notebooks/evaluation.ipynb)

![overview-eval](notebooks/img/overview_eval.png)

该笔记本演示如何使用电子邮件数据集进行评测（数据集定义见 [/eval/email_dataset.py](/eval/email_dataset.py)）。同时介绍如何借助 Pytest 与 LangSmith 的 `evaluate` API 运行评测，包括：基于“大模型判官（LLM-as-a-judge）”的回复质量评测、对工具调用与分拣决策的评测等。

![Screenshot 2025-04-08 at 8 07 48 PM](notebooks/img/eval.png)

### 人机协同（HITL） 
* Notebook：[/notebooks/hitl.ipynb](/notebooks/hitl.ipynb)
* 代码：[/src/email_assistant/email_assistant_hitl.py](/src/email_assistant/email_assistant_hitl.py)

![overview-hitl](notebooks/img/overview_hitl.png)

该笔记本演示如何将人机协同（HITL）加入系统，使用户可审阅并批准特定的工具调用（如发送邮件、安排会议）。我们使用 [Agent Inbox](https://github.com/langchain-ai/agent-inbox) 作为人机协同界面。完整实现见 [/src/email_assistant/email_assistant_hitl.py](/src/email_assistant/email_assistant_hitl.py)。

![Agent Inbox showing email threads](notebooks/img/agent-inbox.png)

### 记忆（Memory）  
* Notebook：[/notebooks/memory.ipynb](/notebooks/memory.ipynb)
* 代码：[/src/email_assistant/email_assistant_hitl_memory.py](/src/email_assistant/email_assistant_hitl_memory.py)

![overview-memory](notebooks/img/overview_memory.png)  

该笔记本展示如何为邮件助理加入记忆，使其能从用户反馈中学习、并随时间贴合偏好。带记忆的实现（[/src/email_assistant/email_assistant_hitl_memory.py](/src/email_assistant/email_assistant_hitl_memory.py)）基于 [LangGraph Store](https://langchain-ai.github.io/langgraph/concepts/memory/#long-term-memory) 持久化记忆。完整实现见同路径文件。

## 连接外部 API  

上述笔记本默认使用模拟的邮件与日历工具。

### Gmail 集成与部署

请按 [Gmail 工具 README](src/email_assistant/tools/gmail/README.md) 的指引配置 Google API 凭据。

该 README 亦说明了如何将图（Graph）部署到 LangGraph Platform。

Gmail 集成的完整实现见 [/src/email_assistant/email_assistant_hitl_memory_gmail.py](/src/email_assistant/email_assistant_hitl_memory_gmail.py)。

## 运行测试

本仓库提供自动化测试套件以评估邮件助理。

测试将结合 LangSmith 记录，验证工具调用是否正确、回复质量是否达标。

### 使用 [/tests/run_all_tests.py](/tests/run_all_tests.py) 运行

```shell
python tests/run_all_tests.py
```

### 查看测试结果

测试结果会记录在 LangSmith 中，项目名由 `.env` 中的 `LANGSMITH_PROJECT` 指定。你可以：
- 可视化地检查 Agent 的执行轨迹（traces）
- 查看详尽的评测指标
- 对比不同实现的效果

### 可测试的实现

当前提供：
- `email_assistant` —— 基础邮件助理

### 测试笔记本

你也可以测试所有笔记本是否能无错执行：

```shell
# 运行全部笔记本测试
python tests/test_notebooks.py

# 或通过 pytest 运行
pytest tests/test_notebooks.py -v
```

## 后续扩展

可引入 [LangMem](https://langchain-ai.github.io/langmem/) 管理记忆：
* 维护一组“背景记忆”集合
* 提供记忆工具，用于查询与检索背景记忆中的事实




