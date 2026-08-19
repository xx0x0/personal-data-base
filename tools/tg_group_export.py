"""从 telegram-search 的 postgres 导出某个群里 bot 发的视频文字稿，落盘为 raw/clips/*.md。

用法:
    python3 tools/tg_group_export.py --chat-id <群ID> --out ~/pkb-friend/raw/clips

设计约束（与 telegram_archive.py 同构）:
- 只保存文字稿（原始层）。"📝 AI 梳理"是派生内容，跳过。
- bot 消息超 4000 字符会分段，本脚本按时间序把后续段拼回同一条。
- 幂等：按输出文件名去重，重跑不重复落盘。
- 视频文件不下载，只存文案。
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PG_CONTAINER = "telegram-search-pgvector-1"
BOT_SENDERS = ("douyin-bot", "抖音视频文案提取")

TITLE_RE = re.compile(r"^视频标题：(.+)")
URL_RE = re.compile(r"🔗\s*(https?://\S+)")
BODY_MARK_RE = re.compile(r"^(原文案|文案)：\s*$", re.M)
SKIP_PREFIXES = ("⏳", "❌", "📝 AI 梳理", "✅")

# 与 telegram_archive.py 保持一致
PLATFORM_PATTERNS = [
    ("douyin", ("douyin.com", "v.douyin.com", "iesdouyin.com", "tiktok.com")),
    ("xiaohongshu", ("xiaohongshu.com", "xhslink.com")),
    ("bilibili", ("bilibili.com", "b23.tv")),
    ("x", ("twitter.com", "x.com")),
    ("youtube", ("youtube.com", "youtu.be")),
]


def slugify(text: str, limit: int = 40) -> str:
    text = re.sub(r"[\s/\\:*?\"<>|#\[\]]+", "-", text.strip())
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:limit] or "untitled"


def detect_platform(url: str) -> str:
    low = (url or "").lower()
    for name, hosts in PLATFORM_PATTERNS:
        if any(h in low for h in hosts):
            return name
    return "douyin"  # 该群主要来源


def extract_tags(text: str) -> list[str]:
    found = re.findall(r"#([^\s#，,。.]+)", text or "")
    seen: set[str] = set()
    out: list[str] = []
    for t in found:
        t = t.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def fetch_messages(chat_id: str) -> list[dict]:
    sql = (
        "COPY (SELECT platform_message_id, from_name, platform_timestamp, content "
        "FROM chat_messages WHERE in_chat_id='" + chat_id + "' AND deleted_at=0 "
        "ORDER BY platform_timestamp, platform_message_id) TO STDOUT WITH CSV HEADER"
    )
    r = subprocess.run(
        ["docker", "exec", PG_CONTAINER, "psql", "-U", "postgres", "-d", "postgres", "-c", sql],
        capture_output=True, text=True, check=True, timeout=120,
    )
    return list(csv.DictReader(io.StringIO(r.stdout)))


def parse_records(messages: list[dict]) -> list[dict]:
    """按时间序把 bot 消息聚合成「一条视频 = 标题 + 文案 + URL」。"""
    records: list[dict] = []
    cur: dict | None = None

    def close(rec: dict | None) -> None:
        if rec and rec.get("transcript", "").strip():
            records.append(rec)

    for m in messages:
        if m["from_name"] not in BOT_SENDERS:
            continue
        content = (m["content"] or "").strip()
        if not content or content.startswith(SKIP_PREFIXES):
            continue

        title_match = TITLE_RE.match(content)
        if title_match:
            has_body = bool(BODY_MARK_RE.search(content))
            url_match = URL_RE.search(content)
            if has_body:
                # 新的一条文字稿开始
                close(cur)
                body = BODY_MARK_RE.split(content, maxsplit=1)[-1]
                body = URL_RE.sub("", body).strip()
                cur = {
                    "title": URL_RE.sub("", title_match.group(1)).strip(),
                    "transcript": body,
                    "url": url_match.group(1) if url_match else "",
                    "ts": int(m["platform_timestamp"]),
                    "mid": m["platform_message_id"],
                }
            elif url_match and cur and not cur["url"] and cur["title"] in content:
                cur["url"] = url_match.group(1)  # 「标题 + 🔗」的独立消息
            continue

        if cur is not None:
            # 无标题头的续段：拼回当前文字稿
            url_match = URL_RE.search(content)
            cur["transcript"] += "\n" + URL_RE.sub("", content).strip()
            if url_match and not cur["url"]:
                cur["url"] = url_match.group(1)

    close(cur)
    return records


def write_clip(rec: dict, out_dir: Path) -> Path | None:
    day = datetime.fromtimestamp(rec["ts"], tz=timezone.utc).date().isoformat()
    platform = detect_platform(rec["url"])
    path = out_dir / f"{day}-{platform}-{slugify(rec['title'])}.md"
    if path.exists():
        return None  # 幂等
    tags = "[" + ", ".join(f'"{t}"' for t in extract_tags(rec["title"])) + "]"
    safe_title = rec["title"].replace('"', "'")
    path.write_text(
        f"---\ntitle: \"{safe_title}\"\nplatform: {platform}\n"
        f"source_url: {rec['url'] or '⚠️待核实'}\ntags: {tags}\ncaptured_at: {day}\n"
        f"tg_group_message_id: {rec['mid']}\ntranscribed_by: whisper\n---\n\n"
        f"## 逐字稿\n\n{rec['transcript'].strip()}\n",
        encoding="utf-8",
    )
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-id", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    messages = fetch_messages(args.chat_id)
    records = parse_records(messages)
    written, skipped = [], 0
    for rec in records:
        p = write_clip(rec, out_dir)
        if p:
            written.append(p.name)
        else:
            skipped += 1

    print(f"群消息 {len(messages)} 条 → 识别文字稿 {len(records)} 条 → 新写 {len(written)}，跳过(已存在) {skipped}")
    for name in written:
        print(f"  + {name}")


if __name__ == "__main__":
    main()
