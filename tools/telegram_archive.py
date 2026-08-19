"""把 Telegram bot 提取到的视频文案归档进 raw/clips/，并推到私有库。

给 douyin-bot-v2 的 bot.py 调用。设计约束：

- 纯同步、零第三方依赖；调用方用 asyncio.to_thread 包一层即可，不阻塞事件循环
- 任何失败都不向上抛 —— bot 主流程绝不能被归档拖垮
- 幂等：同一条 Telegram 消息重复调用只写一次
- 只写 whisper 逐字稿（原始层）。ollama 的 AI 梳理属于派生内容，按 AGENTS.md
  的「raw 只读 / 派生隔离」规则不进 raw/，留在 Telegram 里给人看即可

文件名与 frontmatter 格式与 feishu_sync.py 保持一致，两条摄取路径产出同构。
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLIPS_DIR = ROOT / "raw" / "clips"

# 与 feishu_sync.py 同步维护
PLATFORM_PATTERNS = [
    ("douyin", ("douyin.com", "v.douyin.com", "iesdouyin.com", "tiktok.com")),
    ("xiaohongshu", ("xiaohongshu.com", "xhslink.com")),
    ("bilibili", ("bilibili.com", "b23.tv")),
    ("x", ("twitter.com", "x.com")),
    ("youtube", ("youtube.com", "youtu.be")),
]

# git 操作串行化：bot 可能并发处理多条消息
_GIT_LOCK = threading.Lock()


def slugify(text: str, limit: int = 40) -> str:
    """与 feishu_sync.slugify 行为一致。"""
    text = re.sub(r"[\s/\:*?\"<>|#\[\]]+", "-", text.strip())
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:limit] or "untitled"


def detect_platform(url: str) -> str:
    low = (url or "").lower()
    for name, hosts in PLATFORM_PATTERNS:
        if any(h in low for h in hosts):
            return name
    return "unknown"


def extract_tags(raw_text: str) -> list[str]:
    """从消息原文抓 #标签。中文标签也要能抓，所以不用 \w。"""
    if not raw_text:
        return []
    found = re.findall(r"#([^\s#，,。.]+)", raw_text)
    seen, out = set(), []
    for t in found:
        t = t.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def _archived_message_ids() -> set[str]:
    """扫已落盘文件的 frontmatter，用于幂等。"""
    ids = set()
    if not CLIPS_DIR.exists():
        return ids
    for f in CLIPS_DIR.glob("*.md"):
        try:
            head = f.read_text(encoding="utf-8")[:600]
        except Exception:
            continue
        m = re.search(r"^telegram_message_id:\s*(\S+)", head, re.M)
        if m:
            ids.add(m.group(1))
    return ids


def _git_push(paths: list[Path], summary: str) -> str:
    """提交并推送。返回状态描述，不抛异常。"""
    with _GIT_LOCK:
        try:
            rel = [str(p.relative_to(ROOT)) for p in paths]
            subprocess.run(["git", "add", "--"] + rel, cwd=ROOT, check=True,
                           capture_output=True, timeout=60)
            r = subprocess.run(["git", "commit", "-m", summary], cwd=ROOT,
                               capture_output=True, text=True, timeout=60)
            if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
                return f"commit 失败: {r.stderr.strip()[:200]}"
            # 先 pull --rebase，避免和另一台机器的提交撞车
            subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=ROOT,
                           capture_output=True, timeout=120)
            p = subprocess.run(["git", "push"], cwd=ROOT,
                               capture_output=True, text=True, timeout=120)
            if p.returncode != 0:
                return f"已提交，push 失败（下次会补推）: {p.stderr.strip()[:200]}"
            return "已提交并推送"
        except Exception as e:
            return f"git 异常（文件已落盘）: {e}"


def archive_clip(url: str, title: str, transcript: str, raw_text: str = "",
                 message_id: str | int | None = None, push: bool = True) -> str | None:
    """写一条素材页。返回文件名，跳过或失败返回 None。"""
    try:
        if not transcript or not transcript.strip():
            return None

        mid = str(message_id) if message_id is not None else ""
        if mid and mid in _archived_message_ids():
            print(f"[pkb] 跳过（已归档）: {mid}")
            return None

        CLIPS_DIR.mkdir(parents=True, exist_ok=True)

        platform = detect_platform(url)
        # 标签两个来源合并：视频标题自带的 #tag + 用户消息里手打的 #tag
        tags = extract_tags(f"{title or ''} {raw_text}")
        title = (title or "").strip() or transcript.strip().splitlines()[0][:30]
        today = date.today().isoformat()

        path = CLIPS_DIR / f"{today}-{platform}-{slugify(title)}.md"
        n = 2
        while path.exists():
            path = CLIPS_DIR / f"{today}-{platform}-{slugify(title)}-{n}.md"
            n += 1

        tag_yaml = "[" + ", ".join(f'"{t}"' for t in tags) + "]"
        safe_title = title.replace('"', "'")
        content = (
            f"---\ntitle: \"{safe_title}\"\nplatform: {platform}\nsource_url: {url}\n"
            f"tags: {tag_yaml}\ncaptured_at: {today}\ntelegram_message_id: {mid or 'na'}\n"
            f"transcribed_by: whisper\n---\n\n## 逐字稿\n\n{transcript.strip()}\n"
        )
        path.write_text(content, encoding="utf-8")

        status = _git_push([path], f"clip: {safe_title[:60]}") if push else "仅落盘"
        print(f"[pkb] ✓ {path.name} — {status}")
        return path.name
    except Exception as e:
        print(f"[pkb] ✗ 归档失败（不影响 bot）: {e}")
        return None
