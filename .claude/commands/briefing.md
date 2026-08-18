每日开工简报。

按 AGENTS.md 项目记忆规则执行：
1. 读 projects/index.md，只筛 status: active 的项目（禁止全量读取 projects/）
2. 定向读这些项目的 log.md（最近条目）
3. 输出：今天最重要的 3 项任务、当前阻塞、需要参考的历史资料（含 wiki 页链接）
4. 存档到 projects/briefings/YYYY-MM-DD.md（frontmatter 带 derived: true）
