两阶段摄取源文件进 wiki。

用法: /wiki-ingest $ARGUMENTS （raw/ 下的文件或目录，如 `raw/clips/` 批量）

严格按 AGENTS.md 的摄取工作流执行：

**阶段一（只读）**：读源文件 + wiki/index.md + wiki/overview.md，输出影响清单（将新建/补充哪些页、可能与哪些现有结论冲突），等用户确认。

**阶段二（确认后）**：
1. 写 wiki/sources/<slug>.md（按来源摘要页格式，事实标来源，存疑标 ⚠️待核实）
2. 更新 wiki/index.md 与 wiki/overview.md
3. 创建/补充实体页、概念页（分歧不覆盖：保留双方来源/时间/适用范围）
4. 摄取时即标记矛盾
5. 追加 wiki/log.md
6. 摄后自检：断链检查、index 完整性，打印变更摘要

批量处理 raw/clips/ 时先按 tags 聚类，同主题汇入同一概念页。
