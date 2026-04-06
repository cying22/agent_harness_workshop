# Agent Harness Workshop 设计文档

> **日期:** 2026-04-02
> **形式:** 半天 (3-4小时) Hands-on Coding Workshop
> **学员:** 有经验的开发者（熟悉 Python、LLM API、用过 Claude Code 或类似工具）
> **语言:** Python + AnthropicBedrock SDK
> **格式:** Jupyter Notebook (.ipynb)，含完整中文说明
> **代码仓库:** `labs/` 递进式 notebook 系列

---

## 设计哲学

### 核心理念：痛点驱动的递进建造 — 6 Lab 对齐 6 层架构

Agent Loop 作为贯穿始终的基座，在 Lab 1 中引入。6 个 Lab 分别对应 Harness 六层核心组件，每个 Lab 暴露一个真实痛点，然后用一层 harness 解决它。

```
Lab 1: ❶ 提示与引导层  → 痛点「裸 LLM 无规则，行为混乱」
  ↓ 有了引导，但说了做不了
Lab 2: ❷ 工具与执行层  → 痛点「能做了，但长对话爆 token」
  ↓
Lab 3: ❸ 上下文与内存层 → 痛点「记忆管好了，但不安全」
  ↓
Lab 4: ❹ 验证与安全层  → 痛点「安全了，但复杂任务忙不过来」
  ↓
Lab 5: ❺ 规划与协调层  → 痛点「能协作了，但关掉就丢失一切」
  ↓
Lab 6: ❻ 状态与持久层  → 完整 Mini Harness ✅
```

### 每个 Lab 的统一结构

| 阶段 | 时间 | 内容 |
|------|------|------|
| 痛点演示 | 5min | 运行上一个 Lab 的代码，碰到天花板 |
| 源码对照 | 5min | 展示 Claude Code 中对应模块的真实设计 |
| 动手编码 | 20-30min | 写这一层的简化实现 |
| 验证运行 | 5min | 运行增强后的 agent，验证问题解决 |

### 代码组织

```
labs/
├── lab1_prompt_guidance.ipynb    # Lab 1: ❶ 提示与引导层
├── lab2_tool_execution.ipynb     # Lab 2: ❷ 工具与执行层
├── lab3_context_memory.ipynb     # Lab 3: ❸ 上下文与内存层
├── lab4_safety_permission.ipynb  # Lab 4: ❹ 验证与安全层
├── lab5_planning_coordination.ipynb # Lab 5: ❺ 规划与协调层
├── lab6_state_persistence.ipynb  # Lab 6: ❻ 状态与持久层
├── CLAUDE.md                     # Lab 1/3 用的示例项目记忆文件
├── .sessions/                    # Lab 6 会话存储目录（运行时生成）
└── requirements.txt              # anthropic[bedrock]
```

### Notebook 结构规范

每个 `.ipynb` 是一个自包含的完整实验，包含以下 cell 类型：

1. **标题 + 学习目标** (markdown) — 本Lab要学什么、解决什么痛点
2. **背景知识** (markdown) — 对应的 harness 概念解释 + Claude Code 源码对照
3. **环境准备** (code) — import + client 初始化
4. **痛点体验** (code + markdown) — 运行上一Lab的代码感受局限
5. **逐步实现** (code + markdown) — Phase A/B/C 分步骤编码
6. **验证运行** (code) — 完整运行增强后的 agent
7. **小结** (markdown) — 本Lab收获 + 下一Lab预告

所有 markdown cell 使用**完整中文**编写，包含概念说明、源码对照、设计思考。
代码 cell 中的注释也使用中文。

每个 notebook 完全自包含——**不依赖外部 .py 模块文件**。
前一个 Lab 的代码以"回顾 cell"的形式复制到下一个 notebook 开头，学员可以直接运行。

### SDK 配置

所有 Lab 统一使用 AnthropicBedrock 客户端：

```python
from anthropic import AnthropicBedrock

client = AnthropicBedrock(
    aws_region="us-west-2",  # 或学员所在region
)
MODEL = "anthropic.claude-sonnet-4-20250514"
```

---

## Lab 1: The Bare Agent Loop

> **时间:** 30分钟 | **代码量:** ~60行 | **文件:** `lab1_agent_loop.ipynb`

### 教学目标

理解 agent loop 的本质——observe-think-act 循环，以及"裸 LLM"的局限性。

### 对应 Claude Code 源码

`QueryEngine.ts` — 核心 ask() 循环

### 痛点演示 (5min)

运行最简单的 Claude 对话循环，要求它"创建一个 hello.py 文件"。LLM 回复"好的，已为你创建"——**但实际上什么也没发生**。这就是没有 harness 的 agent。

### 实验内容

**Phase A: 最简循环 (~15行)**

```python
from anthropic import AnthropicBedrock

client = AnthropicBedrock()
messages = []

while True:
    user_input = input("\nYou: ")
    if user_input.lower() == "exit":
        break
    messages.append({"role": "user", "content": user_input})
    
    response = client.messages.create(
        model="anthropic.claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=messages,
    )
    
    assistant_msg = response.content[0].text
    print(f"\nAssistant: {assistant_msg}")
    messages.append({"role": "assistant", "content": response.content})
```

- 纯对话循环，无 tool、无记忆、无任何执行能力
- 学员体验：模型"声称"做了事情，但什么都没发生

**Phase B: 加入 tool_use 骨架 (~45行)**

```python
# 定义工具schema（不实现执行）
tools = [
    {
        "name": "read_file",
        "description": "Read a file from disk",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
]

# 增强的循环：处理 tool_use block
while True:
    user_input = input("\nYou: ")
    messages.append({"role": "user", "content": user_input})
    
    response = client.messages.create(
        model="anthropic.claude-sonnet-4-20250514",
        max_tokens=4096,
        tools=tools,
        messages=messages,
    )
    
    messages.append({"role": "assistant", "content": response.content})
    
    for block in response.content:
        if block.type == "text":
            print(f"\nAssistant: {block.text}")
        elif block.type == "tool_use":
            # 只打印tool call，不执行
            print(f"\n[TOOL CALL] {block.name}({block.input})")
            print("[!] No execution layer — tool call ignored!")
            
            # 返回一个假结果让循环继续
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Error: No tool execution layer available",
                }],
            })
```

- 模型会"尝试"调用工具，但只能打印出 intent，无法执行
- **关键体验：** 模型有意图(intent)，harness 提供执行(execution)

### 源码对照 (5min)

展示 `QueryEngine.ts` 的核心循环伪代码：

```
while (!shouldStop) {
    response = await api.call(messages, tools)
    for (block of response.content) {
        if (block.type === 'tool_use')
            → 查找工具 → 执行 → 收集结果
        if (block.type === 'text')
            → 展示给用户
    }
    messages.push(assistantMessage, toolResults)
}
```

### 学员收获

- Agent = Loop + Tool Use Protocol
- **没有执行层的 agent 只是个聊天机器人**
- 理解 `tool_use` / `tool_result` 的消息协议

---

## Lab 2: Tool System

> **时间:** 40分钟 | **代码量:** ~80行增量 | **文件:** `lab2_tool_system.ipynb`

### 教学目标

理解统一工具接口设计和 validation → execution → result 管道。

### 对应 Claude Code 源码

`Tool.ts`（统一接口）、`tools/BashTool/`、`tools/FileEditTool/`、`tools/FileReadTool/`

### 痛点演示 (5min)

运行 Lab 1 代码，模型返回 `tool_use` 但无法执行。让学员手动复制 tool call 去终端执行再粘贴回来——极其痛苦。

### 实验内容

**Phase A: 统一 Tool 接口 (~20行)**

```python
# tools/base.py
from abc import ABC, abstractmethod

class Tool(ABC):
    name: str
    description: str
    input_schema: dict  # JSON Schema
    
    @abstractmethod
    def validate(self, tool_input: dict) -> bool:
        """校验输入是否合法"""
        pass
    
    @abstractmethod
    def execute(self, tool_input: dict) -> str:
        """执行工具，返回结果字符串"""
        pass
    
    def to_api_schema(self) -> dict:
        """转换为 Anthropic API 的 tool 格式"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
```

对应 Claude Code 的 `Tool.ts` 统一接口——30+ 工具都实现同一个接口。

**Phase B: 实现 3 个核心工具 (~40行)**

```python
# tools/read_file.py
class ReadFileTool(Tool):
    name = "read_file"
    description = "Read the contents of a file"
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "File path"}},
        "required": ["path"],
    }
    
    def validate(self, tool_input):
        return "path" in tool_input
    
    def execute(self, tool_input):
        path = tool_input["path"]
        with open(path, "r") as f:
            return f.read()

# tools/write_file.py
class WriteFileTool(Tool):
    name = "write_file"
    description = "Write content to a file"
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }
    
    def validate(self, tool_input):
        return "path" in tool_input and "content" in tool_input
    
    def execute(self, tool_input):
        with open(tool_input["path"], "w") as f:
            f.write(tool_input["content"])
        return f"Written to {tool_input['path']}"

# tools/bash.py
import subprocess

class BashTool(Tool):
    name = "bash"
    description = "Execute a bash command"
    input_schema = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }
    
    def validate(self, tool_input):
        return "command" in tool_input
    
    def execute(self, tool_input):
        result = subprocess.run(
            tool_input["command"], shell=True,
            capture_output=True, text=True, timeout=30,
        )
        return result.stdout + result.stderr
```

**Phase C: 接入 Agent Loop (~20行)**

```python
# lab2_tools.py 核心变化
TOOLS = [ReadFileTool(), WriteFileTool(), BashTool()]
tool_map = {t.name: t for t in TOOLS}

# 在循环中处理 tool_use
for block in response.content:
    if block.type == "tool_use":
        tool = tool_map.get(block.name)
        if tool and tool.validate(block.input):
            result = tool.execute(block.input)
            print(f"\n[TOOL] {block.name} → {result[:200]}")
        else:
            result = f"Error: Unknown tool {block.name}"
        
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result,
        })
```

### 源码对照 (5min)

Claude Code 的工具管道：
```
tool_use block
  → tool_map[name] 查找 Tool
  → tool.validate(input) 校验
  → permissionCheck(tool, input)   ← Lab 3 加
  → tool.execute(input) 执行
  → format result → 送回 messages
```

Claude Code 有 30+ 工具（BashTool, FileEditTool, FileReadTool, GlobTool, GrepTool, LSPTool, AgentTool, WebSearchTool...），但都遵循同一个 `Tool` 接口。

### 实验验证 (5min)

对 agent 说：
> "读取当前目录下的文件列表，然后创建一个 hello.py 写入 print('hello world')，最后运行它"

观察 agent 成功执行：`bash(ls)` → `write_file(hello.py)` → `bash(python hello.py)` → 返回 "hello world"

### 学员收获

- **统一接口模式（Factory Pattern）** 的威力——新工具只需实现 Tool 接口
- Tool calling 的完整管道：schema → API → dispatch → execute → result → next turn
- **新痛点：** BashTool 可以执行 `rm -rf /`——没有任何安全检查！

---

## Lab 3: Permission & Safety

> **时间:** 30分钟 | **代码量:** ~70行增量 | **文件:** `lab3_permissions.ipynb`

### 教学目标

理解权限中间件模式——如何在工具执行前插入安全拦截层，以及 HITL（Human-in-the-Loop）设计。

### 对应 Claude Code 源码

`utils/permissions/`、`hooks/useCanUseTool.js`、bash classifier

### 痛点演示 (5min)

运行 Lab 2 代码，对 agent 说："删除当前目录所有文件"。它会毫不犹豫地执行 `rm -rf *`。**这太危险了。**

### 实验内容

**Phase A: Permission 规则引擎 (~25行)**

```python
# permissions/checker.py
from dataclasses import dataclass
from typing import Literal

@dataclass
class PermissionRule:
    tool_name: str                                    # 匹配工具名
    behavior: Literal["allow", "deny", "ask"]         # 行为
    pattern: str | None = None                        # 可选匹配模式

class PermissionChecker:
    def __init__(self):
        self.rules: list[PermissionRule] = [
            # 只读工具默认允许
            PermissionRule("read_file", "allow"),
            # 写文件需要确认
            PermissionRule("write_file", "ask"),
            # bash 命令走分类器
            PermissionRule("bash", "ask"),
        ]
    
    def check(self, tool_name: str, tool_input: dict) -> str:
        for rule in self.rules:
            if rule.tool_name == tool_name:
                return rule.behavior
        return "ask"  # 默认需要确认
```

对应 Claude Code 的 4 种权限模式：
- `default` — 危险操作需确认
- `plan` — 只读模式，执行前需审批
- `auto` — 分类器自动判断
- `bypassPermissions` — 全放行（仅开发用）

**Phase B: 注入到工具执行管道 (~15行)**

```python
# 在 tool.execute() 之前插入权限检查
permission = checker.check(block.name, block.input)

if permission == "deny":
    result = "Permission denied: this action is not allowed"
elif permission == "ask":
    print(f"\n⚠️  Agent wants to execute: {block.name}({block.input})")
    confirm = input("Allow? (y/n): ")
    if confirm.lower() != "y":
        result = "Permission denied by user"
    else:
        result = tool.execute(block.input)
else:  # allow
    result = tool.execute(block.input)
```

**Phase C: 简单 Bash 命令分类器 (~30行)**

```python
# permissions/bash_classifier.py
DANGEROUS_PATTERNS = [
    "rm ", "rm\t", "rmdir",           # 删除
    "sudo ",                           # 提权
    "chmod ", "chown ",                # 权限修改
    "> /dev/", "mkfs",                 # 设备操作
    "curl | sh", "wget | sh",         # 远程执行
    "dd if=",                          # 磁盘操作
    ":(){:|:&};:",                     # fork bomb
]

SAFE_PATTERNS = [
    "ls", "cat", "head", "tail",       # 只读
    "echo", "pwd", "whoami",           # 信息
    "python ", "node ",                # 运行脚本
    "git status", "git log", "git diff", # git只读
]

def classify_bash(command: str) -> str:
    """返回 allow / deny / ask"""
    cmd_lower = command.lower().strip()
    
    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd_lower:
            return "ask"    # 危险命令需确认
    
    for pattern in SAFE_PATTERNS:
        if cmd_lower.startswith(pattern):
            return "allow"  # 安全命令自动放行
    
    return "ask"  # 未知命令默认需确认
```

对应 Claude Code 的 `bashClassifier`——通过模式匹配评估命令安全性。

**增强 PermissionChecker 使用分类器：**

```python
def check(self, tool_name: str, tool_input: dict) -> str:
    if tool_name == "bash":
        return classify_bash(tool_input.get("command", ""))
    # ... 其他规则
```

### 源码对照 (5min)

Claude Code 的权限决策流：
```
Tool Call
  → PermissionChecker
  → rules 匹配 → allow / deny / ask
  → mode='auto' → bashClassifier 评估危险度
    → 高危 → 弹出确认 (HITL)
    → 低危 → 自动放行
```

### 实验验证 (5min)

| 指令 | 预期行为 |
|------|---------|
| "删除所有文件" | ⚠️ 拦截，等待确认 |
| "读取 README.md" | ✅ 自动放行 |
| "运行 ls -la" | ✅ 自动放行 |
| "执行 sudo rm -rf /" | ⚠️ 拦截，等待确认 |
| "运行 python hello.py" | ✅ 自动放行 |

### 学员收获

- **中间件/拦截器模式** 在 agent 安全中的关键作用
- 分级权限（allow/deny/ask）比二元开关灵活得多
- HITL 设计：AI 做判断，人做最终决策
- **新痛点：** 长对话后 agent 开始忘记之前做了什么

---

## Lab 4: Context & Memory

> **时间:** 35分钟 | **代码量:** ~90行增量 | **文件:** `lab4_memory.ipynb`

### 教学目标

理解 context window 管理的核心挑战——micro-compaction、会话持久化、项目记忆加载。Claude Code 的三层记忆架构。

### 对应 Claude Code 源码

`compact/apiMicrocompact.ts`、`memdir/`、`history.ts`

### 痛点演示 (5min)

运行 Lab 3 代码，让 agent 执行一系列文件操作（读 5 个文件、修改 3 个）。对话历史急剧膨胀。或者关掉程序重新打开，一切记忆归零。

### 实验内容

**Phase A: Micro-Compaction（上下文压缩）(~35行)**

```python
# memory/compaction.py

def estimate_tokens(text: str) -> int:
    """粗略估算token数（1 token ≈ 4 chars for English, 2 chars for CJK）"""
    return len(text) // 3

def compact_tool_result(tool_name: str, tool_input: dict, result: str) -> str:
    """将冗长的工具输出压缩为摘要"""
    if len(result) > 500:
        preview = result[:200] + "..."
        return f"[Compacted] {tool_name}({tool_input}) → {len(result)} chars, preview: {preview}"
    return result

class ContextManager:
    def __init__(self, max_tokens: int = 50000):
        self.max_tokens = max_tokens
    
    def should_compact(self, messages: list) -> bool:
        total = sum(estimate_tokens(str(m)) for m in messages)
        return total > self.max_tokens * 0.8  # 80% 阈值
    
    def compact(self, messages: list) -> list:
        """压缩策略：保留最近消息，摘要老消息中的 tool_result"""
        if len(messages) <= 6:
            return messages
        
        # 保留 system + 最近 4 轮对话
        keep_recent = 8
        old = messages[:-keep_recent]
        recent = messages[-keep_recent:]
        
        # 将旧消息中的 tool_result 压缩
        compacted_old = []
        for msg in old:
            if isinstance(msg.get("content"), list):
                new_content = []
                for block in msg["content"]:
                    if block.get("type") == "tool_result" and len(str(block.get("content", ""))) > 200:
                        block = {**block, "content": f"[Compacted] {block['content'][:100]}..."}
                    new_content.append(block)
                msg = {**msg, "content": new_content}
            compacted_old.append(msg)
        
        # 插入压缩边界标记
        boundary = {"role": "user", "content": "[System: older context was compacted to save tokens]"}
        return compacted_old + [boundary] + recent
```

对应 Claude Code 的 `apiMicrocompact.ts`——将冗长工具输出折叠为摘要。

**Phase B: 会话持久化 (~30行)**

```python
# memory/session_store.py
import json, os, uuid
from datetime import datetime

class SessionStore:
    def __init__(self, store_dir: str = ".sessions"):
        self.store_dir = store_dir
        os.makedirs(store_dir, exist_ok=True)
    
    def save(self, session_id: str, messages: list, metadata: dict = None):
        data = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "messages": messages,
            "metadata": metadata or {},
        }
        path = os.path.join(self.store_dir, f"{session_id}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load(self, session_id: str) -> tuple[list, dict]:
        path = os.path.join(self.store_dir, f"{session_id}.json")
        with open(path, "r") as f:
            data = json.load(f)
        return data["messages"], data.get("metadata", {})
    
    def list_sessions(self) -> list[dict]:
        sessions = []
        for fname in os.listdir(self.store_dir):
            if fname.endswith(".json"):
                with open(os.path.join(self.store_dir, fname)) as f:
                    data = json.load(f)
                sessions.append({
                    "id": data["session_id"],
                    "time": data["timestamp"],
                })
        return sorted(sessions, key=lambda x: x["time"], reverse=True)
    
    def new_session_id(self) -> str:
        return str(uuid.uuid4())[:8]
```

对应 Claude Code 的 session persistence——支持 `/resume` 恢复会话。

**Phase C: 项目记忆（CLAUDE.md 模式）(~25行)**

```python
# memory/project_memory.py
import os

class ProjectMemory:
    MEMORY_FILES = ["CLAUDE.md", ".claude/CLAUDE.md", "AGENTS.md"]
    
    def discover(self, work_dir: str) -> str | None:
        """搜索项目记忆文件"""
        for fname in self.MEMORY_FILES:
            path = os.path.join(work_dir, fname)
            if os.path.exists(path):
                with open(path, "r") as f:
                    return f.read()
        return None
    
    def build_system_prompt(self, base_prompt: str, work_dir: str) -> str:
        """将项目记忆注入 system prompt"""
        memory = self.discover(work_dir)
        if memory:
            return f"{base_prompt}\n\n# Project Context\n{memory}"
        return base_prompt
```

对应 Claude Code 的 `memdir/` 系统——自动发现并加载项目级指导。

**接入 Agent Loop：**

```python
# lab4_memory.py 关键改动
ctx_manager = ContextManager(max_tokens=50000)
session_store = SessionStore()
project_memory = ProjectMemory()

# 启动时
session_id = args.resume or session_store.new_session_id()
if args.resume:
    messages, _ = session_store.load(session_id)
    print(f"Resumed session {session_id} with {len(messages)} messages")

# system prompt 注入项目记忆
system_prompt = project_memory.build_system_prompt(BASE_PROMPT, os.getcwd())

# 每轮循环后
if ctx_manager.should_compact(messages):
    messages = ctx_manager.compact(messages)
    print("[System] Context compacted to save tokens")

# 退出时
session_store.save(session_id, messages)
print(f"Session saved: {session_id}")
```

### 源码对照 (5min)

Claude Code 的三层记忆架构：
```
Layer 1: Micro-compaction
  → 对话内自动压缩（apiMicrocompact.ts）
  → 折叠旧的 tool_result 为摘要
  → 插入 SystemCompactBoundaryMessage

Layer 2: Session persistence
  → 跨会话恢复（/resume 命令）
  → 保存到 .sessions/{uuid}.json
  → 包含 messages + metadata + cost

Layer 3: Project memory
  → 跨项目知识（CLAUDE.md + memdir/）
  → 层级发现：cwd → 父目录 → home
  → 自动注入 system prompt
```

### 实验验证 (5min)

1. 长对话后观察 `[System] Context compacted` 消息
2. 退出程序 → 重新启动 `python lab4_memory.py --resume <session_id>` → 对话恢复
3. 在当前目录创建 `CLAUDE.md` 写入 "所有回答用中文"，重启后 agent 自动遵守

### 学员收获

- Context window 是 agent 的"工作记忆"，需要主动管理
- 三层记忆（对话内 / 跨会话 / 跨项目）各解决不同时间尺度的问题
- **新痛点：** 复杂任务一个 agent 忙不过来

---

## Lab 5: Multi-Agent Coordination

> **时间:** 25分钟 | **代码量:** ~70行增量 | **文件:** `lab5_multi_agent.ipynb`

### 教学目标

理解"Team Lead"模式的多智能体协作——任务分解、子 agent 生成、基于消息的通信。

### 对应 Claude Code 源码

`tools/AgentTool/`、`tools/TeamCreateTool/`、`tools/TaskCreateTool/`、`tools/SendMessageTool/`

### 痛点演示 (5min)

给 Lab 4 的 agent 一个复杂任务："同时分析 lab1 到 lab4 这 4 个 Python 文件的代码结构"。单个 agent 串行处理，context 膨胀。

### 实验内容

**Phase A: AgentTool——生成子 Agent (~30行)**

```python
# tools/agent.py
class AgentTool(Tool):
    name = "dispatch_agent"
    description = "Spawn a sub-agent to handle a specific task independently"
    input_schema = {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "Task description for the sub-agent"},
        },
        "required": ["task"],
    }
    
    def __init__(self, available_tools: list[Tool]):
        self.available_tools = available_tools
    
    def validate(self, tool_input):
        return "task" in tool_input
    
    def execute(self, tool_input):
        """创建独立的子 agent 运行子任务"""
        from lab4_memory import run_agent_loop  # 复用已有的 agent loop
        
        task = tool_input["task"]
        print(f"\n  [Sub-Agent] Starting: {task[:80]}...")
        
        # 子 agent 拥有独立的 messages 和 context
        result = run_agent_loop(
            system_prompt=f"You are a sub-agent. Complete this task concisely:\n{task}",
            tools=self.available_tools,  # 共享工具（不包含 AgentTool 自身，防递归）
            max_turns=5,                 # 限制子 agent 轮数
            interactive=False,           # 非交互模式
        )
        
        print(f"  [Sub-Agent] Done: {result[:100]}...")
        return result
```

对应 Claude Code 的 `AgentTool`——主 agent 可以生成拥有独立 context 的子 agent。

**Phase B: 任务管理系统 (~25行)**

```python
# tools/tasks.py
class TaskManager:
    _tasks: dict = {}
    _counter: int = 0
    
    def create(self, subject: str, description: str) -> str:
        self._counter += 1
        task_id = str(self._counter)
        self._tasks[task_id] = {
            "subject": subject,
            "description": description,
            "status": "pending",
        }
        return task_id
    
    def update(self, task_id: str, status: str):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = status
    
    def list_all(self) -> list:
        return [{"id": k, **v} for k, v in self._tasks.items()]

# 作为工具暴露
task_mgr = TaskManager()

class TaskCreateTool(Tool):
    name = "create_task"
    description = "Create a task to track work"
    input_schema = {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["subject"],
    }
    def execute(self, tool_input):
        tid = task_mgr.create(tool_input["subject"], tool_input.get("description", ""))
        return f"Task {tid} created: {tool_input['subject']}"

class TaskListTool(Tool):
    name = "list_tasks"
    description = "List all tasks and their status"
    input_schema = {"type": "object", "properties": {}}
    def execute(self, tool_input):
        tasks = task_mgr.list_all()
        return "\n".join(f"[{t['status']}] #{t['id']}: {t['subject']}" for t in tasks) or "No tasks"
```

对应 Claude Code 的 `TaskCreateTool` / `TaskListTool`——Team Lead 用任务系统协调工作。

**Phase C: 组装完整 Mini Harness (~15行)**

```python
# lab5_multi_agent.py
# 基础工具（不含 AgentTool）
base_tools = [ReadFileTool(), WriteFileTool(), BashTool()]

# 完整工具集（含 AgentTool 和 Task 工具）
all_tools = base_tools + [
    AgentTool(available_tools=base_tools),  # 子agent只能用基础工具
    TaskCreateTool(),
    TaskListTool(),
]

# 运行主 agent（Team Lead 角色）
run_agent_loop(
    system_prompt="You are a team lead agent. For complex tasks, break them into subtasks and dispatch sub-agents.",
    tools=all_tools,
    interactive=True,
)
```

### 源码对照 (5min)

Claude Code 的多 agent 架构：
```
Team Lead (主 agent)
  ├── TaskCreate    → 创建任务（分解复杂工作）
  ├── TaskList      → 查看任务状态
  ├── AgentTool     → 生成子 agent（独立 context）
  ├── SendMessage   → 与子 agent 通信
  └── TaskUpdate    → 标记任务完成

Sub-Agent (子 agent)
  ├── 拥有基础工具（read/write/bash）
  ├── 独立的 messages 历史（隔离 context）
  ├── 有限的轮数（防失控）
  └── 完成后向 Team Lead 返回结果
```

关键设计决策：
- 子 agent **不**拥有 AgentTool（防止递归嵌套）
- 子 agent 有独立 context（不污染主 agent）
- 通过 tool_result 返回结果（而非共享内存）

### 实验验证 (5min)

对 agent 说：
> "分析 mini_harness 目录下的所有 Python 文件，报告每个文件的行数、函数数、以及主要功能"

观察：
1. 主 agent 创建 tasks
2. 主 agent dispatch 子 agent 处理各文件
3. 子 agent 独立执行并返回结果
4. 主 agent 汇总输出报告

### 学员收获

- **Team Lead 协调模式** 是生产级 agent 系统的核心
- 子 agent 独立 context 的重要性：隔离 + 聚焦 + 防 token 膨胀
- 完成了从裸循环到多 agent 的完整 mini harness 建造

---

## 时间安排总览

| 顺序 | Lab | 主题 | 时间 | 累计 |
|------|-----|------|------|------|
| 1 | Lab 1 | Bare Agent Loop | 30min | 0:30 |
| - | 休息 | - | 10min | 0:40 |
| 2 | Lab 2 | Tool System | 40min | 1:20 |
| 3 | Lab 3 | Permission & Safety | 30min | 1:50 |
| - | 休息 | - | 10min | 2:00 |
| 4 | Lab 4 | Context & Memory | 35min | 2:35 |
| 5 | Lab 5 | Multi-Agent | 25min | 3:00 |
| - | 总结 | 回顾 + Q&A | 15min | 3:15 |

**总计：约 3 小时 15 分钟**（含休息和 Q&A）

---

## 前置准备

### 学员环境要求

```bash
# Python 3.11+
python3 --version

# Jupyter 环境
pip install jupyter

# 安装依赖
pip install "anthropic[bedrock]"

# AWS credentials 配置（用于 Bedrock）
aws configure
# 或设置环境变量
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-west-2
```

### 讲师准备

1. 准备完整的 5 个 `.ipynb` notebook（含完整中文说明和可运行代码）
2. 测试所有 notebook 在 Bedrock 上的完整运行
3. 准备 `CLAUDE.md` 示例文件（Lab 4 用）
4. 准备参考幻灯片（可直接使用 `presentation.html`）

### Notebook 发放策略

每个 notebook 自包含完整的中文说明和代码，学员按顺序打开运行即可。
不需要 skeleton/solution 分离——notebook 的 markdown cell 本身就是教材，code cell 就是可运行的实验代码。

---

## 扩展选项（时间充裕时）

### 可选 Lab 6: Hooks & Middleware

- 实现 PreToolUse / PostToolUse hook 机制
- 在工具执行前后注入自定义逻辑（日志、审计、限流）
- 对应 Claude Code 的 hooks 系统

### 可选 Lab 7: MCP Tool Integration

- 实现简单的 MCP client，连接外部 tool server
- 理解标准化工具协议的设计
- 对应 Claude Code 的 `tools/MCPTool/`

---

## 关键教学映射

| Workshop 概念 | Mini Harness 实现 | Claude Code 源码 |
|--------------|-------------------|-----------------|
| Agent Loop | `while True` + messages API | `QueryEngine.ts` |
| 统一工具接口 | `Tool` 基类 | `Tool.ts` |
| 工具分发 | `tool_map[name].execute()` | `tools.ts` |
| 权限中间件 | `PermissionChecker.check()` | `utils/permissions/` |
| Bash 分类器 | `classify_bash()` | bash classifier |
| 上下文压缩 | `ContextManager.compact()` | `apiMicrocompact.ts` |
| 会话持久化 | `SessionStore.save/load()` | session persistence |
| 项目记忆 | `ProjectMemory.discover()` | `memdir/` |
| 子 Agent 生成 | `AgentTool.execute()` | `tools/AgentTool/` |
| 任务协调 | `TaskManager` | `tools/TaskCreateTool/` |
