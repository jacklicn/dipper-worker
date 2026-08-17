---
name: workflow-creator
description: >-
  Guide for creating high-quality reusable Workflows (WORKFLOW.md) for Dipper Agent.
  Use when the user wants to create a new workflow, turn a multi-step procedure into a
  reusable flow, capture a task process as mermaid steps, or edit/improve an existing
  workflow. 创建流程规范、把多步骤任务固化为流程、编写 WORKFLOW.md、修改已有 workflow。
version: 1
---
# Workflow 创建指南

一个 Workflow 是把"用户想做什么"翻译成"先做什么、再做什么、每步用什么工具、产出什么"的可复用流程单元。本技能指导你从用户需求出发，产出符合 `docs/workflow/index.md` 规范的 `WORKFLOW.md`。

创建前先阅读规范：`docs/workflow/index.md`（渐进式披露三级结构、图步一一对应、流程规则、工具调用规范）。

## 何时使用

- 用户要求"创建一个 workflow / 流程 / 规范流程"
- 用户把一个多步骤任务描述给你，希望固化成下次自动执行的流程
- 用户要求修改或改进已有 workflow
- 用户在会话中做了一件可复用的多步事情，说"把这个流程固化下来"

## 创建流程

### Phase 1: 理解意图

先访谈清楚，不要急着写文件：

1. **要解决什么任务**？给出一类任务的名字（如"代码审查""发布说明"）。
2. **触发场景**：用户在什么情况下会用到？收集触发词（中文+英文）。
3. **输入输出**：需要哪些输入（文件/目录/字符串）？产出什么（文件/报告）？
4. **是否有既定步骤**：用户是否已有习惯流程？从会话历史中提取工具调用序列、纠错、输入输出格式。
5. **边界与规则**：哪些不能做？产物写到哪里？失败如何处理？

缺失的信息用 `ask_user` 补齐后再进入下一步。

### Phase 2: 设计流程图

用 mermaid 画出执行流，**遵循图步对应规则**（规范 5.2.1）：

- 每个节点必须有对应的步骤小节；每个步骤必须在图中出现一次
- 节点名与步骤名称完全一致，全局唯一（`step-N` 前缀不必写进节点）
- 判断节点用菱形 `{}`，同样要有步骤小节，并用 `分支` 说明去向
- 并行步骤（scatter）在图中是一个节点
- 图要完整：起始、分支、终点

先画图给用户确认，再写步骤。

### Phase 3: 编写 WORKFLOW.md

在 `<workspace>/workflows/<name>/` 下创建目录与文件：

1. **frontmatter**（Level 1 元数据）：
   - `name`: kebab-case，与目录名一致，仅小写字母/数字/连字符
   - `description`: 功能 + 使用时机 + 触发词（中英），决定触发率
   - `inputs` / `outputs`: 显式声明，标注 required
   - `version` / `tags`: 可选
2. **流程总览**：一段话说清做什么、何时用、产出什么
3. **流程图**：与 Phase 2 一致的 mermaid 图
4. **步骤**：每个步骤一个 `### <id>: <名称>` 小节，属性：`工具` / `输入` / `前置` / `动作` / `校验`（判断节点加 `分支`，可选 `when`）
5. **流程规则**：顺序约束、数据依赖、校验门禁、副作用约束、终态检查
6. **工具调用规范**：优先内置工具、脚本兜底、读多写少、路径规范

> 渐进式披露：长文档与表格放 `references/`，确定性逻辑放 `scripts/`，模板与数据放 `assets/`，主体精炼（<500 行）。

### Phase 4: 自检与验证

写完对照规范自查：

- 图步一一对应：图里没有"孤儿"节点，步骤里没有"孤儿"步骤
- 节点名唯一且与步骤名一致
- 每步有具体的、可判定的 `校验`（如"文件存在且非空"，而非"确认成功"）
- 工具名精确（`read_file` / `exec`，而非"查看文件"）
- `inputs` / `outputs` 与步骤引用一致
- 规则覆盖失败处理（重试 / 回滚 / 询问用户）
- frontmatter `description` 包含功能与触发词

用 `workflow_list` 确认新 workflow 已被发现，用 `workflow_get <name>` 验证可读。

### Phase 5: 交付

告知用户：

- workflow 名称与路径
- 触发场景（什么话会触发它）
- 流程概览（几个步骤、判断/并行情况）
- 可选：建议 2-3 个真实测试请求验证效果

## 修改已有 Workflow

- 先 `workflow_get <name>` 读取现有内容
- 保留 frontmatter 的 `name` 与目录名不变
- 改动遵循同样规范；改完跑 Phase 4 自检

## 注意事项

- **只写工作区 `workflows/`**，不修改内置只读 workflow；同名时工作区覆盖内置
- 一个 workflow 只解决一类任务，不要堆砌不相干流程
- steps 控制在 3–8 个；超过则拆分或引用子流程
- 不编写恶意/误导性指令；规则要能被审计
