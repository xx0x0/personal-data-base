从飞书收件箱拉取新素材到 raw/clips/。

执行 `python3 tools/feishu_sync.py`（首次或排查时可先 `--dry-run`）。

完成后汇报：同步了几条、跳过几条、失败原因；如有新素材，提示用户是否接着 `ingest raw/clips/`。

若报缺少配置，引导用户 `cp .env.example .env` 并填写飞书凭证，不要替用户猜测凭证。
