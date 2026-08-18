# personal-data-base

个人自生长知识库：**手机转发抖音/小红书 → 飞书收件箱 → bot 提取逐字稿 → 同步落盘 → Agent 编译成 wiki → Obsidian 浏览**。

架构合并自 [Karpathy LLM Wiki](https://x.com/karpathy) 方法论、[llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent)（MIT 底座）及若干实践者的规范，外加：飞书收件箱单向同步、项目记忆层（projects/）、派生内容隔离、两阶段摄取等防腐规则。完整规范见 [AGENTS.md](AGENTS.md)。

## 数据流

```
📱 抖音/小红书 分享 → 飞书机器人（打粗标签）
      ↓ 飞书自动化触发提取 bot，回填逐字稿，状态=已提取
📋 飞书多维表格（收件箱）
      ↓ python tools/feishu_sync.py（单向，只回写状态）
💾 raw/clips/*.md（只读原始层）
      ↓ Agent: ingest（两阶段编译）
📚 wiki/（sources/entities/concepts/syntheses）
      ↓
🔍 Obsidian 浏览 / query: 问答 / build graph 图谱
```

## 快速开始

1. **克隆并作为 Obsidian Vault 打开**：Obsidian → Open folder as vault → 选本仓库目录
2. **配置飞书**：`cp .env.example .env`，填入自建应用凭证和多维表格 ID
   - 多维表格需要列：`视频链接 | 标签 | 正文 | 平台 | 状态`（列名可在 `tools/feishu_sync.py` 顶部改）
   - 你的提取 bot 负责把逐字稿写进 `正文` 列并把 `状态` 改为 `已提取`
3. **用 Claude Code / Codex 打开本目录**，日常四个动作：
   ```
   health                # 每次开工先跑（零成本结构体检）
   sync                  # 拉取飞书新素材 → raw/clips/
   ingest raw/clips/     # 两阶段编译进 wiki（先看影响清单再确认）
   lint                  # 每周一次内容质检
   ```
4. **首次验证**：手机转发 1 条视频 → 确认飞书表状态变为 `已提取` → `sync` → `ingest` → 在 Obsidian 里看到 wiki 页面和双链

## 依赖

- Python 3.10+（`pip install -r requirements.txt`，仅 lint/graph 需要；sync 零第三方依赖）
- 可选：`gitleaks` 做 commit 前密钥扫描

## 回滚

一切变更都在 git 里：`git log` 查历史，`git revert <commit>` 回滚任意一次 ingest/sync。飞书侧状态字段改回 `已提取` 即可重新同步。

## 致谢

底座：[SamurAIGPT/llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent)（MIT License，见 LICENSE）
