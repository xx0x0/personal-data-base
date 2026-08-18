会话收尾：把本次会话的结论和进度写回项目记忆。

按 AGENTS.md 项目记忆规则执行：
1. 判断本次会话涉及哪个项目（不确定就问用户）
2. decisions.md：追加本次新决策（决定/理由/放弃的备选）；被推翻的旧决策加 superseded_by + 日期，原文保留
3. log.md：追加进展、阻塞、下一步（只记后续真正需要的信息，不记对话过程）
4. 新项目：建目录三件套（参照 projects/_example/），并登记进 projects/index.md
5. 禁止写入任何密钥、token、密码
6. 追加 wiki/log.md：## [日期] save-session | <项目名>
