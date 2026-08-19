# personal-data-base

个人自生长知识库骨架：**手机转发短视频 → Telegram bot 提取逐字稿 → 自动落盘 → Agent 编译成 wiki → Obsidian / 网页浏览**。

架构合并自 [Karpathy LLM Wiki](https://x.com/karpathy) 方法论与 [llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent)（MIT 底座），外加：Telegram bot 直写归档、项目记忆层（projects/）、派生内容隔离、两阶段摄取、curation 策略等防腐规则。完整规范见 [AGENTS.md](AGENTS.md)。

> 本仓库只含骨架、工具与方法论。真实素材放在你自己的私有库里——建议双仓库分工，公开库永不放内容。

## 数据流（两条摄取路径，产出同构文件）

**路径 A：Telegram bot 直写（推荐）**

```
📱 短视频分享 → Telegram bot（whisper 转录；消息可带 #标签）
      ↓ tools/telegram_archive.py（bot 内嵌调用，见 docs/telegram-bot-patch.md）
💾 raw/clips/*.md（只读原始层，自动 commit + push）
      ↓ Agent: ingest（两阶段编译，建议每周批量、按标签聚类）
📚 wiki/ → 🔍 Obsidian / query 问答 / build graph / Quartz 网页版
```

**路径 B：飞书多维表格收件箱**（`tools/feishu_sync.py` + `.env`，见 `.env.example`）

## 快速开始

1. **克隆并作为 Obsidian Vault 打开**：Obsidian → Open folder as vault → 选本仓库目录
2. **接入你的 bot**：按 `docs/telegram-bot-patch.md` 三处补丁把 `telegram_archive.py` 嵌进你的转录 bot；或走飞书路径配置 `.env`
3. **用 Claude Code / Codex 打开本目录**，日常动作：
   ```
   health                # 每次开工先跑（零成本结构体检）
   ingest raw/clips/     # 批量编译进 wiki（先看影响清单再确认）
   lint                  # 每周一次内容质检
   query: <问题>          # 基于 wiki 检索问答
   ```

## 多知识库

同一个 bot 可支撑多个库（比如帮朋友建一个他主题的库）。`tools/tg_group_export.py` 从 [telegram-search](https://github.com/GramSearch/telegram-search) 的 postgres 按群 ID 导出 bot 文字稿：

```bash
python3 tools/tg_group_export.py --chat-id <群ID> --out <目标库>/raw/clips
# 幂等可重跑；跳过 AI 梳理/处理中消息；4000 字分段自动拼回
```

## Curation 策略

时效新闻、水货听写、纯引流内容——raw 与 wiki 一并删除（在 wiki/log.md 留痕）；长期可用的工具/方法类保留。知识库是长期资产，不是新闻存档。

## 分享给别人看

- 私有 GitHub 仓库 + 邀请协作者（零成本）
- [Quartz](https://github.com/jackyzha0/quartz) 把 wiki/ 构建成静态站（双链/图谱/搜索齐全），托管到 Cloudflare Pages（免费、不绑卡）
- 私密访问：`tools/deploy_kb_site.sh` 一条龙——构建 + Basic Auth 密码门禁（Pages Worker 实现，无需 Zero Trust）+ noindex + 部署

## 依赖

- Python 3.10+（`pip install -r requirements.txt`，仅 lint/graph 需要；归档/导出零第三方依赖）
- bot 侧：whisper + ffmpeg
- 可选：`gitleaks` 做 commit 前密钥扫描

## 回滚

一切变更都在 git 里：`git revert <commit>` 回滚任意一次 ingest/归档。

## 致谢

底座：[SamurAIGPT/llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent)（MIT License，见 LICENSE）
