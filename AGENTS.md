# 本仓库中的智能体（Agents）

## 概览

本仓库演示如何使用 LangGraph 从零构建智能体（Agent），重点围绕一个“邮件助理”场景，能力包括：
- 对新收邮件进行分拣与优先级判定（Triage）
- 擬写并完善合适的邮件回复
- 执行动作（例如：日程安排等）
- 引入人工反馈（Human-in-the-Loop）
- 基于历史交互持续学习与记忆

注：本文面向大模型与 LangGraph 技术的初学者，力求清晰、严谨、信雅达。

## 环境准备

**推荐：使用 uv（更快、更稳定）**

```bash
# 如未安装 uv，请先安装
pip install uv

# 安装包含开发依赖的本项目
uv sync --extra dev
```

**可选：使用 pip**

```bash
# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 升级 pip（pyproject.toml 的可编辑安装需要较新版本）
python3 -m pip install --upgrade pip

# 以可编辑模式安装本项目
pip install -e .
```

## 智能体实现

### 脚本 

在 `src/email_assistant` 目录中包含多种由浅入深的实现：

1. **LangGraph 101**（`langgraph_101.py`）
   - LangGraph 基础概念与最小示例

2. **基础邮件助理**（`email_assistant.py`）
   - 核心的邮件分拣与邮件回复能力

3. **人机协同（HITL）**（`email_assistant_hitl.py`）
   - 支持关键动作由人审阅与批准

4. **带记忆的人机协同**（`email_assistant_hitl_memory.py`）
   - 引入可持久化的记忆，从用户反馈中学习

5. **Gmail 集成**（`email_assistant_hitl_memory_gmail.py`）
   - 连接 Gmail API 处理真实邮件

### 笔记本（Notebooks）

每个能力点均配有讲解笔记本：
- `notebooks/langgraph_101.ipynb`：LangGraph 基础
- `notebooks/agent.ipynb`：基础智能体实现
- `notebooks/evaluation.ipynb`：智能体评测方法
- `notebooks/hitl.ipynb`：人机协同（HITL）
- `notebooks/memory.ipynb`：加入记忆能力

## 运行测试

### 脚本实现测试

用于验证各实现是否可用：

```bash
# 运行全部实现的测试
python tests/run_all_tests.py --all
```

（说明：这不会包含 Gmail 实现 `email_assistant_hitl_memory_gmail` 的测试。）

### 笔记本测试

验证所有笔记本可无错误执行：

```bash
# 直接运行全部笔记本测试
python tests/test_notebooks.py
```

—— 完 ——
