**Claude Code 中的 Agent Harness 实践解析**  
（基于 https://deepwiki.com/ChinaSiro/claude-code-sourcemap/2-core-architecture 的源码映射分析）

Claude Code（Anthropic 官方推出的长时编码 Agent CLI 工具）是目前最接近“生产级 Agent Harness”的开源/半开源实现之一。它**没有显式地叫 “Harness” 这个名字**，但整个系统正是通过 **QueryEngine + Agent Loop + Tool System + State Management + Permission Layer** 这些模块，完整构建了一个高度工程化的 Agent Harness。

下面我按照源码结构（`restored-src/` 目录下的真实映射）逐层拆解，告诉你 Harness 在 Claude Code 里是怎么“驾驭” Claude 模型，让它能可靠地跑几天、写几万行生产代码的。

### 1. Harness 的核心引擎：QueryEngine + ask() 循环（Agent Loop）
这是整个 Harness 的“大脑和心脏”。

- **文件位置**：`restored-src/src/QueryEngine.ts`
- **核心函数**：`ask()` / `askLoop`
- **工作方式**（伪代码简化）：
  ```ts
  while (true) {  // 多轮 tool-use 循环
    normalizeMessagesForAPI();           // 消息标准化 + 上下文组装
    assembleToolPool();                  // 动态加载工具池
    callClaudeApi(streaming);            // 调用 Claude Messages API
    if (tool_use) {
      runPreToolUseHooks();
      checkPermissions();
      tool.call();                       // 执行真实操作
      appendToolResultToHistory();
      // 继续循环，直到模型不再调用工具或达到最大轮次
    }
  }
  ```

**Harness 实践亮点**：
- 不是一次性对话，而是**状态驱动的持续循环**（stateful agent loop）。
- 支持 streaming + tool delta，实时在 TUI（React Terminal UI）里展示思考过程。
- 自动处理多轮 tool-use（模型一次可以调用多个工具，Harness 按顺序执行并回填结果）。
- 这就是典型的“模型只负责思考，Harness 负责执行+循环+状态”的分层设计。

### 2. 上下文与内存层（Context Compaction & Memory）
这是解决模型“失忆”和上下文爆炸的核心 Harness 组件。

- **自动微压缩（Micro-compaction）**：`compact/apiMicrocompact.ts`
  - 把重复的 `ls`、`cat` 等工具输出自动折叠成一行摘要。
  - 老消息自动总结，保持在上下文窗口内。
- **持久化内存系统（Memdir）**：`memdir/memdir.ts`
  - 项目级内存存放在 `~/.claude/projects/<slug>/memory/`
  - `MEMORY.md`（全局索引，最多 200 行 / 25KB）
  - 每个事实单独存成 `.md` 文件，支持 `@-import` 语法自动加载。
- **CLAUDE.md 发现机制**：`attachments.ts`
  - 启动时自动扫描项目根目录、用户目录、全局目录的 `CLAUDE.md`，把规则、偏好、知识注入上下文。

**实践效果**：让 Agent 能跨几天、跨机器继续工作，而不会丢失项目上下文。这正是传统 LLM 做不到的“持久状态”能力。

### 3. 工具执行层（Tool Execution Layer）
Harness 把“模型想做什么”变成“真实做了什么”的桥梁。

- **统一 Tool 接口**：`restored-src/src/Tool.ts`（`buildTool`）
  - 每个工具必须实现：`inputSchema`（Zod）、`validateInput`、`checkPermissions`、`call()`、`render UI`
- **执行流水线**（每一步都被 Harness 拦截）：
  1. Schema 验证
  2. 权限检查（见下文）
  3. Pre/Post Hooks
  4. 真实执行（`call()`）
  5. 结果映射回 Anthropic `tool_result` 格式
- **关键工具示例**：
  - `FileEditTool`、`BashTool`、`LSPTool`（语言服务器）
  - `AgentTool`（生成子 Agent，实现多 Agent Swarm）
  - 支持 `shouldDefer: true` 的延迟加载，节省上下文。

**Harness 实践**：工具不是裸调用，而是被“全生命周期管理”，包括沙箱、日志、结果格式化，保证安全和可审计。

### 4. 验证与安全层（Permission & Safety System）
这是 Claude Code Harness 最强、最 opinionated 的部分。

- **多模式权限**：`default`、`plan`、`auto`、`bypassPermissions`
- **PermissionDecision 流程**（源码中有 Mermaid 图）：
  - Tool Call → `checkPermissions()` → 匹配规则 → allow / ask / deny
  - `plan` 模式下先只读规划，用户确认后才真正执行（经典 Human-in-the-Loop）。
- **Bash 安全分类器**：`bashClassifier` 自动判断 shell 命令危险程度。
- **SandboxManager**：隔离高危命令。

**实践意义**：Harness 不是“信任模型”，而是强制“模型只能在安全沙箱里干活”，这正是生产落地的关键。

### 5. 状态持久化与会话管理（State & Session Layer）
让 Agent 真正“下班后还能继续上班”。

- **Session ID + JSON 持久化**：`~/.claude/sessions/<uuid>.json`
- 支持 `--continue`、`--resume`、`/resume` 交互式恢复。
- **FileHistorySnapshot**：支持 `/rewind` 回滚任意历史版本。
- **Teleport**（跨机器续接）：OAuth + Git 同步，实现“在笔记本上开始，在服务器上继续”。
- **Worktree Sessions**：每个任务开独立 Git 分支，实验失败直接丢弃。

### 6. 初始化与多 Agent 协调（Initialization + Orchestration）
- **启动序列**（`main.tsx`）：
  - 并行预取密钥、内存、设置。
  - 初始化 AppStateStore（React 全局状态）。
- **多 Agent Swarm**：
  - `TeamCreateTool`、`TaskCreateTool`、`SendMessageTool`
  - 通过文件（`TeamFile`、`Mailbox`）实现子 Agent 通信。
  - Team Lead 负责任务分解和协调。

### 总结：Claude Code Harness 的工程哲学
根据源码映射，Claude Code 的 Harness 完全体现了“**模型是 CPU，Harness 是 OS**”的理念：

| Harness 能力       | Claude Code 实现模块                  | 解决的模型原生痛点       |
|--------------------|---------------------------------------|--------------------------|
| 持久状态           | Memdir + Session JSON + Teleport     | 无记忆、会话结束就忘     |
| 上下文管理         | Micro-compaction + CLAUDE.md         | 上下文爆炸               |
| 工具可靠执行       | Tool 接口 + Pre/Post Hooks + 沙箱    | 无法安全执行真实操作     |
| 验证闭环           | Permission System + Plan 模式        | 容易漂移、幻觉           |
| 长时任务协调       | askLoop + Multi-Agent Swarm          | 任务半途而废             |
| 可恢复性           | Git Worktree + Rewind + Resume       | 失败后无法继续           |

这就是为什么 Claude Code 能让 Claude 模型真正“写完整应用”而非只“生成一段代码”——**所有模型做不到的工程可靠性，都被 Harness 补齐了**。

如果你想继续看：
- 具体某个文件的源码细节（比如 `QueryEngine.ts` 的完整 ask 循环）
- 对比 Anthropic 官方 SDK 的 Harness
- 或者看第 1 部分 / 第 3 部分的源码解析
