# 个人知识库 — Claude Code 入口

本库全部工作规范在 **[AGENTS.md](AGENTS.md)**，请完整阅读并严格遵循其中的核心规则与工作流。

## 快捷指令速查

| 指令 | 作用 |
|---|---|
| `sync` | 从飞书收件箱拉取新视频素材 → `raw/clips/` |
| `ingest <文件>` | 两阶段摄取：先报影响清单，确认后编译进 wiki |
| `query: <问题>` | 基于 wiki 检索作答，可沉淀为 synthesis |
| `health` | 结构体检（每次会话先跑，零成本） |
| `lint` | 内容质检（每周一次） |
| `build graph` | 生成知识图谱 |
| `briefing` | 每日开工简报（读 active 项目） |
| `save-session` | 会话收尾：结论和进度写回 `projects/` |

## 日常节奏

1. 手机上随手转发抖音/小红书到飞书机器人（顺手打标签）
2. 电脑开工：`health` → `sync` → `ingest raw/clips/`（批量时先看影响清单）
3. 每周跑一次 `lint`
4. 复杂问答用 `query:`，有价值的答案沉淀到 syntheses
5. 项目工作结束前跑 `save-session`
