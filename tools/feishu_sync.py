#!/usr/bin/env python3
"""飞书多维表格 → raw/clips/ 单向同步器。

流程：
  1. 拉取多维表格中 状态=已提取 的记录
  2. 每条生成 raw/clips/YYYY-MM-DD-<平台>-<slug>.md（含逐字稿与元数据）
  3. 成功落盘后把该记录状态改为 已入库（唯一的回写，只碰状态字段）

幂等性：以 feishu_record_id 去重，重跑安全；失败记录保持原状态，下次重试。

配置（.env 或环境变量，模板见 .env.example）：
  FEISHU_APP_ID / FEISHU_APP_SECRET   自建应用凭证
  FEISHU_BITABLE_APP_TOKEN            多维表格 app_token（URL 中 base/ 后那段）
  FEISHU_TABLE_ID                     数据表 table_id（URL 中 table= 那段）

表格需要的列（列名可在下方 FIELD_* 常量处修改）：
  视频链接 | 标签 | 正文 | 平台 | 状态 | 标题(可选)

用法：
  python tools/feishu_sync.py            # 正式同步
  python tools/feishu_sync.py --dry-run  # 只打印将做什么，不写文件不改状态
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIPS_DIR = ROOT / "raw" / "clips"

# ---- 列名映射：与你的多维表格列名保持一致，改这里即可 ----
FIELD_URL = "视频链接"
FIELD_TAGS = "标签"
FIELD_BODY = "正文"
FIELD_PLATFORM = "平台"
FIELD_STATUS = "状态"
FIELD_TITLE = "标题"          # 可选列；没有则从正文首行截取
STATUS_READY = "已提取"
STATUS_DONE = "已入库"

API = "https://open.feishu.cn/open-apis"


def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def http(method: str, url: str, token: str | None = None, payload: dict | None = None) -> dict:
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(payload).encode() if payload is not None else None
    with urllib.request.urlopen(req, data=data, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    if body.get("code") != 0:
        raise RuntimeError(f"飞书 API 错误 code={body.get('code')} msg={body.get('msg')} url={url}")
    return body


def get_tenant_token(app_id: str, app_secret: str) -> str:
    body = http("POST", f"{API}/auth/v3/tenant_access_token/internal",
                payload={"app_id": app_id, "app_secret": app_secret})
    return body["tenant_access_token"]


def cell_text(value) -> str:
    """多维表格字段值可能是 str / list[dict] / dict，统一转纯文本。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("text") or value.get("link") or "").strip()
    if isinstance(value, list):
        return "".join(cell_text(v) for v in value).strip()
    return str(value).strip()


def cell_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [cell_text(v) for v in value if cell_text(v)]
    text = cell_text(value)
    return [t for t in re.split(r"[,，;；\s]+", text) if t]


PLATFORM_MAP = {"抖音": "douyin", "小红书": "xiaohongshu", "b站": "bilibili", "B站": "bilibili",
                "douyin": "douyin", "xiaohongshu": "xiaohongshu", "bilibili": "bilibili"}


def slugify(text: str, limit: int = 40) -> str:
    text = re.sub(r"[\s/\\:*?\"<>|#\[\]]+", "-", text.strip())
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:limit] or "untitled"


def existing_record_ids() -> set[str]:
    ids = set()
    for f in CLIPS_DIR.glob("*.md"):
        m = re.search(r"^feishu_record_id:\s*(\S+)", f.read_text(encoding="utf-8"), re.M)
        if m:
            ids.add(m.group(1))
    return ids


def fetch_ready_records(token: str, app_token: str, table_id: str) -> list[dict]:
    records, page_token = [], None
    while True:
        url = (f"{API}/bitable/v1/apps/{app_token}/tables/{table_id}/records/search?page_size=100"
               + (f"&page_token={page_token}" if page_token else ""))
        payload = {"filter": {"conjunction": "and", "conditions": [
            {"field_name": FIELD_STATUS, "operator": "is", "value": [STATUS_READY]}]}}
        body = http("POST", url, token, payload)
        data = body.get("data", {})
        records += data.get("items", [])
        if not data.get("has_more"):
            return records
        page_token = data.get("page_token")


def update_status(token: str, app_token: str, table_id: str, record_id: str):
    http("PUT", f"{API}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
         token, {"fields": {FIELD_STATUS: STATUS_DONE}})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不写文件不改状态")
    args = parser.parse_args()

    load_env()
    missing = [k for k in ("FEISHU_APP_ID", "FEISHU_APP_SECRET",
                           "FEISHU_BITABLE_APP_TOKEN", "FEISHU_TABLE_ID") if not os.environ.get(k)]
    if missing:
        sys.exit(f"缺少配置：{', '.join(missing)}。请复制 .env.example 为 .env 并填写。")

    token = get_tenant_token(os.environ["FEISHU_APP_ID"], os.environ["FEISHU_APP_SECRET"])
    app_token, table_id = os.environ["FEISHU_BITABLE_APP_TOKEN"], os.environ["FEISHU_TABLE_ID"]

    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    seen = existing_record_ids()
    records = fetch_ready_records(token, app_token, table_id)
    print(f"待同步（状态={STATUS_READY}）：{len(records)} 条；本地已有 {len(seen)} 条 clips")

    ok, skipped, failed = 0, 0, 0
    for rec in records:
        rid = rec.get("record_id", "")
        fields = rec.get("fields", {})
        try:
            if rid in seen:
                # 已落盘但状态没改成功（上次中断）→ 补状态
                if not args.dry_run:
                    update_status(token, app_token, table_id, rid)
                skipped += 1
                print(f"  跳过（已存在，补状态）: {rid}")
                continue

            url = cell_text(fields.get(FIELD_URL))
            body_text = cell_text(fields.get(FIELD_BODY))
            platform_raw = cell_text(fields.get(FIELD_PLATFORM))
            platform = PLATFORM_MAP.get(platform_raw, slugify(platform_raw) or "unknown")
            tags = cell_tags(fields.get(FIELD_TAGS))
            title = cell_text(fields.get(FIELD_TITLE)) or (body_text.splitlines()[0][:30] if body_text else rid)

            if not body_text:
                failed += 1
                print(f"  失败（正文为空，保持原状态待 bot 回填）: {title}")
                continue

            today = date.today().isoformat()
            fname = f"{today}-{platform}-{slugify(title)}.md"
            path = CLIPS_DIR / fname
            n = 2
            while path.exists():
                path = CLIPS_DIR / f"{today}-{platform}-{slugify(title)}-{n}.md"
                n += 1

            tag_yaml = "[" + ", ".join(f'"{t}"' for t in tags) + "]"
            content = (f"---\ntitle: \"{title}\"\nplatform: {platform}\nsource_url: {url}\n"
                       f"tags: {tag_yaml}\ncaptured_at: {today}\nfeishu_record_id: {rid}\n---\n\n"
                       f"## 逐字稿\n\n{body_text}\n")

            if args.dry_run:
                print(f"  [dry-run] 将写入: {path.name}")
            else:
                path.write_text(content, encoding="utf-8")
                update_status(token, app_token, table_id, rid)
                print(f"  ✓ {path.name}")
            ok += 1
        except Exception as e:  # 单条失败不中断整体
            failed += 1
            print(f"  ✗ 失败（保持原状态，下次重试）: {rid} — {e}")

    print(f"\n完成：成功 {ok}，跳过 {skipped}，失败 {failed}"
          + ("（dry-run，未实际写入）" if args.dry_run else ""))
    if ok and not args.dry_run:
        print("下一步：在 Agent 中运行 `ingest raw/clips/` 编译进 wiki。")


if __name__ == "__main__":
    main()
