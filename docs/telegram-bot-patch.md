# douyin-bot-v2 接入 pkb 的补丁

目标：bot 处理完视频后，把 whisper 逐字稿写成 `raw/clips/*.md` 并推到私有库；
Windows 这边 `git pull` 就拿到素材。

**bot 继续跑在 Mac，不改架构，不新增 bot。**

## 为什么不新开一个 bot

`bot.py` 用的是 `app.run_polling()`。**一个 bot token 只允许一个 polling 消费者** ——
再写个 sync 脚本用 `getUpdates` 拉同一个 bot，两边会抢消息、报 409、随机丢消息。

bot 已经拿到了标题、干净链接、逐字稿，正是素材页需要的全部字段，直接落盘即可。

## 为什么 AI 梳理不入库

`AGENTS.md` 规定 raw 是只读原始层、派生内容要隔离。

- whisper 逐字稿 = 音频的忠实转录 → **算原始，入库**
- ollama 梳理 = 对内容的解释 → **算派生，不入 raw/**，留在 Telegram 给人看

ingest 阶段 agent 会自己做分析，不需要预先塞一份进原始层。

---

## Mac 上的三步

### 1. clone 私有库

```bash
git clone https://github.com/<你>/<你的私有库>.git ~/pkb
```

### 2. `.env` 加一行

```bash
PKB_DIR=/Users/<你的用户名>/pkb
```

### 3. 改 `bot.py`，三处

**① 配置区之后（约 20 行附近，`BOT_OWNER = ...` 那行下面）加载归档模块：**

```python
# ---- pkb 归档（失败不影响 bot 主流程）----
PKB_DIR = os.environ.get("PKB_DIR", os.path.expanduser("~/pkb"))
sys.path.insert(0, os.path.join(PKB_DIR, "tools"))
try:
    from telegram_archive import archive_clip
except Exception as _e:
    archive_clip = None
    print(f"[pkb] 归档模块未加载，本次不落盘: {_e}")
```

**② `_process` 里 `text_only` 分支** —— 找到这两行：

```python
    if mode == "text_only":
        transcript = await _run_whisper(video_path)
```

在 `if transcript:` 之前插入：

```python
        if transcript and archive_clip:
            await asyncio.to_thread(
                archive_clip, clean_url, title, transcript,
                getattr(msg, "text", "") or "", getattr(msg, "message_id", None))
```

**③ `_process` 主流程** —— 找到这三行：

```python
    transcript = await _maybe_transcript(video_path)
    need_analysis = bool(transcript) and len(transcript) > 800
    analysis = analyze_transcript(transcript, title) if need_analysis else ""
```

紧接着插入（注意缩进是 4 空格，函数体一级）：

```python
    if transcript and archive_clip:
        await asyncio.to_thread(
            archive_clip, clean_url, title, transcript,
            getattr(msg, "text", "") or "", getattr(msg, "message_id", None))
```

---

## 用法

发消息时顺手带标签，会写进 frontmatter 的 `tags`：

```
https://v.douyin.com/xxxxx #穿搭 #沟通
```

中文标签可以。标签解析在 `tools/telegram_archive.py::extract_tags`，不需要第二个 bot。

## 落盘格式

与 `feishu_sync.py` 产出同构，两条摄取路径的文件可以混用：

```markdown
---
title: "视频标题"
platform: douyin
source_url: https://www.douyin.com/video/xxx
tags: ["穿搭", "沟通"]
captured_at: 2026-08-20
telegram_message_id: 12345
transcribed_by: whisper
---

## 逐字稿

……
```

## 行为保证

| 情况 | 结果 |
|---|---|
| 逐字稿为空 | 不写文件（避免空壳页） |
| 同一条消息重复处理 | 按 `telegram_message_id` 去重，只写一次 |
| git push 失败 | 文件已落盘，只打日志，下次提交会一并推上去 |
| 归档任何异常 | 捕获后打印，**不向上抛**，bot 该发的消息照发 |
| 并发多条消息 | git 操作有线程锁串行化，先 `pull --rebase --autostash` 再 push |

## Windows 这边

```bash
cd <你的Windows侧目录>
git pull
health          # 结构体检
ingest raw/clips/
```

## 回滚

删掉 `bot.py` 里那三段即可，bot 回到原状。已落盘的素材在 git 里，`git revert` 可撤。
