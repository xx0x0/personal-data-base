# 个人知识库 — Agent 工作规范（Schema 层）

本库由 Agent（Claude Code / Codex / Gemini CLI 等）全权维护 wiki 层，人只负责投喂资料和关键判断。
底座基于 [llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent)（MIT），在其上合并了飞书收件箱同步、项目记忆层和若干防腐规则。

## 快捷指令

| 说法 | 触发的工作流 |
|---|---|
| `ingest <文件>` | 摄取工作流（两阶段） |
| `query: <问题>` | 查询工作流 |
| `health` | 结构体检（快，零 LLM 调用，每次会话先跑） |
| `lint` | 内容质检（贵，每 10–15 次 ingest 跑一次 / 每周） |
| `build graph` | 知识图谱 |
| `sync` | 从飞书收件箱拉取新素材到 `raw/clips/` |
| `briefing` | 每日开工简报 |
| `save-session` | 会话收尾：把结论和进度写回项目记忆 |

用自然语言描述也可以，Agent 自动匹配工作流。

---

## 目录结构

```
raw/            # 原始资料层 —— 只读，Agent 禁止修改、删除、移动其中任何文件
  clips/        # 抖音/小红书等视频素材（飞书 sync 落盘，含逐字稿）
  articles/     # 剪藏的文章、网页
  chats/        # 有价值的 AI 对话记录
  notes/        # 随手记的灵感碎片
wiki/           # 编译产物层 —— Agent 全权维护
  index.md      # 全局索引，每次 ingest 后更新
  log.md        # 变更日志，只追加
  overview.md   # 跨来源的活综述
  sources/      # 来源摘要页（一份 raw 对应一页）
  entities/     # 实体页：人物、公司、产品、工具
  concepts/     # 概念页：理论、方法、框架
  syntheses/    # 问答沉淀页（派生内容，见「派生隔离」规则）
projects/       # 项目记忆层 —— 与 wiki 分开检索，见「项目记忆」规则
  index.md      # 项目状态表：active / paused / done
  briefings/    # 每日简报存档
  <项目名>/
    context.md    # 背景、约束、长期偏好
    decisions.md  # 决策记录，只追加
    log.md        # 进度、阻塞、下一步
graph/          # 图谱数据（build_graph.py 生成）
tools/          # 独立脚本：health.py lint.py ingest.py query.py build_graph.py feishu_sync.py
```

---

## 核心规则（每次工作前必读）

1. **先查再写**：处理新资料前，先检索 `wiki/` 已有页面，判断是补充旧页还是新建页。
2. **raw 只读**：`raw/` 是事实来源，禁止改写、删除、移动其中文件。
3. **来源可追溯**：所有事实性内容标注来源（`[[wikilink]]` + raw 路径）；无法确认的内容显式标注 `⚠️待核实`。
4. **分歧不覆盖**：新旧资料结论冲突时，同时保留双方说法及各自的来源、时间、适用范围，禁止用新结论静默覆盖旧结论。
5. **派生隔离**：`wiki/syntheses/` 与 `projects/` 下的内容是模型的二手推理，frontmatter 必须带 `derived: true`。后续编译和回答中，派生内容**只能作线索，不能作证据**；与 `raw/` 冲突时一律以 `raw/` 为准。
6. **增量维护**：每次只更新受影响的页面，并同步维护相关双链、`index.md` 和 `log.md`。不做全量重建。
7. **只追加日志**：`log.md` 与各项目 `decisions.md` 只追加。推翻旧决策时给旧条目加 `superseded_by: <日期/新决策>`，保留原文。
8. **不擅自删除**：不删除现有文件；同名文件已存在时先读取、合并必要内容。
9. **拿不准就问**：信息不足、或判断会影响整体结构时，暂停执行并向用户提问。
10. **禁写密钥**：任何文件不得写入密码、token、API key、个人身份证件信息。（此规则另有机械防线：`.gitignore` 排除 `.env`，commit 前建议跑 gitleaks。）
11. **链接不硬凑**：lint 发现孤岛页时，输出的是「为什么孤立」的判断（边缘该删？缺中间概念页？），不是机械补链。禁止为满足链接数指标制造语义弱的 wikilink。

---

## 页面格式

所有 wiki 页面 frontmatter：

```yaml
---
title: "页面标题"
type: source | entity | concept | synthesis
tags: []
sources: []          # 支撑本页的来源 slug 列表
last_updated: YYYY-MM-DD
derived: true        # 仅 synthesis 类型必带
---
```

页面间用 `[[PageName]]` 双链。

### 命名约定
- 来源页 slug：`kebab-case`，与 raw 文件名一致
- 实体/概念页：`TitleCase.md`（如 `RAG.md`、`Karpathy.md`）
- 视频素材：`raw/clips/YYYY-MM-DD-<平台>-<标题slug>.md`

### 视频素材页格式（raw/clips/，由 sync 生成，只读）

```markdown
---
title: "视频标题"
platform: douyin | xiaohongshu | bilibili
source_url: https://...
tags: []            # 手机分享时打的粗标签，仅作提示
captured_at: YYYY-MM-DD
feishu_record_id: recXXXX
---

## 逐字稿
（bot 提取的正文）
```

### 来源摘要页格式（wiki/sources/）

```markdown
---
title: "来源标题"
type: source
tags: []
date: YYYY-MM-DD
source_file: raw/...
---

## 摘要
2–4 句。

## 核心观点
- 观点 1（含证据强度判断）

## 关键引文
> "原文" — 上下文

## 关联
- [[实体]] — 关系
- [[概念]] — 关系

## 矛盾与待核实
- 与 [[某页]] 在 X 上冲突：双方来源/时间/适用范围
- ⚠️待核实：...
```

---

## 摄取工作流（两阶段，触发词 `ingest <文件>`）

**阶段一：影响清单（只读，不动手）**
1. 完整阅读源文件（非 markdown 先经 markitdown 转换）
2. 读 `wiki/index.md` 和 `wiki/overview.md` 获取全局上下文
3. 输出计划：将新建哪些页、补充哪些页、可能与哪些现有结论冲突
4. **等用户确认后才进入阶段二**（用户说「直接做」或批量场景下可跳过确认，但必须先打印清单）

**阶段二：执行**
5. 写 `wiki/sources/<slug>.md`（按来源摘要页格式）
6. 更新 `wiki/index.md`、`wiki/overview.md`
7. 更新/新建相关实体页、概念页
8. 标记与现有内容的矛盾（**摄取时标记，不等查询时才暴露**）
9. 追加 `wiki/log.md`：`## [YYYY-MM-DD] ingest | <标题>`
10. 摄后自检：检查断链、确认新页已入 index、打印变更摘要

**批量摄取 `raw/clips/` 时**：先按 tags 和标题聚类，同主题的视频尽量汇入同一概念页，避免一视频一孤页。`价值` 初筛已在飞书完成，落盘到 clips 的都应处理。

---

## 查询工作流（触发词 `query: <问题>`）

1. 读 `wiki/index.md` 定位相关页面
2. 读页面（必要时沿双链回读 raw 原文）
3. 综合作答，行内引用 `[[PageName]]`，事实追溯到 raw 路径
4. 问用户是否将答案沉淀为 `wiki/syntheses/<slug>.md`（frontmatter 含 `question`、`asked_at`、`sources`、`derived: true`，正文含 TL;DR / 结论 / 证据 / **不确定性**）

---

## 体检与质检

**health**（每次会话先跑）：`python tools/health.py` —— 空页/存根、index 与磁盘不同步、log 缺失。零 LLM 调用。

**lint**（每周或每 10–15 次 ingest）：孤岛页（给判断不硬凑链接，见规则 11）、断链、跨页矛盾、过期摘要、高频实体缺页、数据缺口。报告存 `wiki/lint-report.md`。图谱增强检查见 `tools/build_graph.py --report`。

先 health 后 lint —— 对空文件做语义质检是浪费 token。

---

## 飞书同步工作流（触发词 `sync`）

运行 `python tools/feishu_sync.py`（配置见 `.env`，模板在 `.env.example`）：

1. 拉取多维表格中 `状态 = 已提取` 的记录
2. 每条生成 `raw/clips/YYYY-MM-DD-<平台>-<slug>.md`（按视频素材页格式）
3. 成功落盘后将该记录状态改为 `已入库`
4. 打印本次同步清单；失败的记录保持原状态，重跑即可，不会重复落盘（按 `feishu_record_id` 去重）

**单向铁律**：数据只从飞书流向本库，永不回写内容（只回写状态字段）。

---

## 项目记忆（projects/）

与 wiki 分开的原因：wiki 回答「这个概念是什么」，projects 回答「我上次为什么这么决定」。检索模式不同，禁止混放。

**启动时**：读 `projects/index.md`，只加载 `status: active` 且与当前任务相关的项目。禁止全量读取 `projects/`。

**写入时**（`save-session` 触发，或上下文用量过半时主动落一次盘）：
- `decisions.md` 只追加；推翻旧决策 → 旧条目加 `superseded_by` + 日期，保留原文
- `log.md` 记进度、阻塞、下一步；不记对话过程，只留后续真正需要的信息
- 新项目 → 建目录 + 三件套，并在 `projects/index.md` 登记

**briefing**（每日开工）：读 `projects/index.md` 过滤 active 项目 → 定向读其 `log.md` → 输出今天最重要的 3 项任务、当前阻塞、需参考的历史资料，存 `projects/briefings/YYYY-MM-DD.md`（`derived: true`）。

---

## 图谱工作流（触发词 `build graph`）

`python tools/build_graph.py --open`。硬规则：图谱层禁止从断链自动建页（只报告）；自动推断的边标 `INFERRED` + 置信度，先 DRAFT 后 promote，页面出链 ≥2 才允许物化为正文 wikilink。

## 日志格式

`## [YYYY-MM-DD] <操作> | <标题>`，操作：`ingest` / `query` / `health` / `lint` / `graph` / `sync` / `briefing` / `save-session`
