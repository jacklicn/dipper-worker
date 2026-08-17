# Workflow Documentation

This directory hosts the **Open Workflow Specification for AI Agents**: a filesystem-based, reusable process asset that lets an AI agent turn "what the user wants to do" into a stable sequence of tool-calling steps with explicit rules, inputs and outputs. It is both a **specification** and a **live runtime feature**: workflows are seeded into the workspace, surfaced to the agent in the system prompt, and executed as ordered tool-calling steps.

- **English specification** → `[index.md](./index.md)`
- **中文规范** → `[zh-cn/index.md](./zh-cn/index.md)`
- Examples: [code-review](./examples/code-review/) · [release-notes](./examples/release-notes/) · 中文示例见 `[zh-cn/examples/](./zh-cn/examples/)`
- Authoring skill (docs): `[skills/workflow-creator/SKILL.md](./skills/workflow-creator/SKILL.md)`

---

## How Workflows Run (Current Implementation)

- **Auto-seeding**: on workspace setup, builtin workflows are copied into `<workspace>/workflows/` (idempotent — existing workflow directories are never overwritten). A workspace workflow with the same name as a builtin one **overrides** the builtin.
- **Progressive disclosure in the system prompt**: `loadWorkflowsPrompt` builds a compact, relevance-ranked workflow catalog (token-budgeted) so the agent knows which `WORKFLOW.md` to read for a multi-step task — full instructions stay off-context until triggered.
- **Dedicated tools**: `workflow_list` (discover available workflows, workspace + builtin) and `workflow_get <name>` (read the full `WORKFLOW.md`: frontmatter inputs/outputs, mermaid flow, steps, rules, tool-call conventions).
- **Execution**: the agent reads the `WORKFLOW.md`, validates inputs, then runs the steps in order, calling tools per step and checking each step's `Check` criteria before moving on.

### Built-in workflows

| Workflow | Structure |
| --- | --- |
| `code-review` | full three-level example — `WORKFLOW.md` + `references/` + `scripts/check_summary.py` |
| `release-notes` | concise example — `WORKFLOW.md` only |

Users can add more via the `workflow-creator` skill (also bundled as a builtin skill at `skills/workflow-creator/SKILL.md`); agents can evolve learned routines into workspace workflows following the spec.

---

## Workflow 的运行时实现（当前功能）

- **自动播种**：工作区初始化时，内置 workflow 会被复制到 `<workspace>/workflows/`（幂等——已存在的 workflow 目录不会被覆盖）。同名时，工作区 workflow **覆盖**内置 workflow。
- **系统提示中的渐进式披露**：`loadWorkflowsPrompt` 按与请求的相关度生成一个紧凑的 workflow 目录（受 token 预算约束），让 Agent 知道多步骤任务该读哪份 `WORKFLOW.md`——完整指令在触发前不占用上下文。
- **专用工具**：`workflow_list`（列出可用 workflow，工作区 + 内置）与 `workflow_get <name>`（读取完整 `WORKFLOW.md`：frontmatter 的 inputs/outputs、mermaid 流程图、步骤、规则、工具调用规范）。
- **执行**：Agent 读取 `WORKFLOW.md`、校验输入，然后按顺序执行各步骤，每步按工具调用并满足该步的 `Check` 校验后才进入下一步。

### 内置 workflow

| Workflow | 结构 |
| --- | --- |
| `code-review` | 完整三级示例——`WORKFLOW.md` + `references/` + `scripts/check_summary.py` |
| `release-notes` | 简洁示例——仅 `WORKFLOW.md` |

更多 workflow 可通过 `workflow-creator` 技能创建（同时以内置技能形式打包于 `skills/workflow-creator/SKILL.md`）；Agent 也可把学到的多步骤套路按本规范固化为工作区 workflow。

---

> **Workflow vs Skill — what's the difference?**
>
> - A **Skill** is *knowledge*: it tells the agent **how to do something** — the expertise, techniques and reusable capabilities of a domain. It answers *"Do I know how to do this?"*
> - A **Workflow** is *process*: it tells the agent **in what order to do it** — the step-by-step orchestration of a task. It answers *"What comes first, what next, and which tool does each step use?"*
>
> They complement each other: **one Workflow can reference multiple Skills** to compose a complex task. For example, an OCR workflow may pull in a recognition skill, a text-processing skill, and a file-output skill as its building blocks.
>
> **Workflow 与 Skill 的区别：**
>
> - **Skill 是"知识"**：告诉 Agent **怎么做好一件事** —— 某个领域的专业能力、技巧与可复用的经验。它回答的是"这事我会不会做？"
> - **Workflow 是"流程"**：告诉 Agent **按什么顺序做事** —— 对一项任务的步骤编排。它回答的是"先做哪步、后做哪步、每步用什么工具？"
>
> 两者互补：**一个 Workflow 可以引用多个 Skill** 来组合完成复杂任务。例如一个 OCR 工作流可以引用识别、文本处理、文件输出等多个技能作为其组成部分。

---



## Why an open workflow specification?

**What problem does a workflow solve?**

A one-shot prompt cannot guarantee that the same kind of task runs through the same steps, rules and tools, in the same order, every single time. Recurring tasks — code review, release notes, batch processing — need a repeatable process, not improvised one-off sequences. Traditional workflow engines (e.g. CWL) target subprocess orchestration and are too heavy for an LLM agent that executes by calling tools step by step.

The AI Agent workflow specification fills this gap:

- **Procedural and auditable**: a `WORKFLOW.md` declares inputs/outputs, an ordered step list, a mermaid flowchart, process rules and tool-call conventions, so execution is deterministic and reviewable.
- **Context-frugal**: built on Progressive Disclosure — metadata always loads, instructions load on trigger, resources load on demand. Dozens of workflows can be installed without meaningful context cost.
- **Agent-native**: steps are executed by the agent calling tools (read_file, exec, ask_user, …), not by an engine spawning subprocesses; conditional branches and parallel groups are expressed in plain markdown.

**Why is it open?**

Workflow assets are shared infrastructure: the more high-quality, battle-tested workflows exist, the more capable every agent becomes. An open specification lets the community define, reuse and improve process assets together instead of each tool reinventing its own private format. It also keeps the format transparent and auditable — critical for an asset that can direct agent tool calls and code execution.

**We welcome your contribution.**

This is an open specification and it grows with the community. You are welcome to:

- add new workflow examples or reusable workflows to `examples/` and the `workflows/` directory;
- improve best practices, the flowchart/step-correspondence rules, or any part of the spec;
- report problems you hit while executing workflows, or open PRs and issues with suggestions.

Every contribution helps build a healthier agent workflow ecosystem. Thanks for being part of it.

---



## 为什么需要一套开放的 Workflow 规范？

**Workflow 要解决什么问题？**

一次性提示（prompt）无法保证同类任务每次都按相同的步骤、规则和工具、以相同的顺序完整跑通。代码审查、发布说明、批量处理这类高频可复用任务，需要的是可重复执行的流程，而不是临时拼凑的一次性操作序列。传统工作流引擎（如 CWL）面向子进程拉起编排，对通过逐步调用工具来完成任务的 AI Agent 来说过于笨重。

AI Agent 的 Workflow 规范正好填补了这一空白：

- **流程化、可审计**：一份 `WORKFLOW.md` 显式声明输入/输出、有序步骤、mermaid 流程图、流程规则与工具调用规范，执行过程确定且可复查。
- **节省上下文**：基于渐进式披露——元数据始终加载、指令触发时加载、资源按需加载，安装大量 workflow 也不会造成明显的上下文开销。
- **面向 Agent 原生设计**：步骤由 Agent 调用工具（`read_file`、`exec`、`ask_user` 等）完成，而非由引擎拉起子进程；条件分支与并行组用纯 Markdown 表达。

**为什么开放？**

Workflow 资产是共享的基础设施：高质量、经过实战检验的 workflow 越多，每个 Agent 的能力就越强。开放规范让社区一起定义、复用、改进流程资产，而不是每个工具各自发明私有不兼容的格式。同时，开放的格式透明、可审计——对于能够指挥 Agent 调用工具和执行代码的资产来说，这一点至关重要。

**欢迎大家一起完善。**

这是一份开放规范，它随社区一起成长。我们欢迎大家：

- 向 `examples/` 与 `workflows/` 目录贡献新的 workflow 示例或可复用流程；
- 改进最佳实践、图步对应规则，或规范中的任何部分；
- 报告执行 workflow 时遇到的问题，或通过 PR / issue 提交建议。

每一份贡献都在帮助构建更健康的 Agent 流程编排生态。感谢你的参与。