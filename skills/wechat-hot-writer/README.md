# WeChat Hot Writer

`wechat-hot-writer` is an opinionated skill for the full WeChat publishing loop:

- discover hot topics
- scaffold and package articles
- prepare cover and illustration briefs
- stage WeChat draft delivery
- record history and sync article stats

It still defaults to a middle-aged / family-caregiver lane, but it now supports an `EXTEND.md` preference layer so another user can swap the lane, fallback query, title templates, and style notes without editing the skill code.

## Layout

```text
skills/wechat-hot-writer/
├── SKILL.md
├── README.md
├── EXTEND.example.md
├── agents/
├── references/
└── scripts/
```

## Working Directory

Run the commands below from this directory:

```bash
cd skills/wechat-hot-writer
```

Default runtime outputs will then stay under this skill's own `out/` directory.

## Requirements

Required for the full workflow:

- `python3`
- `bun`
- `opencli`

Usually needed as well:

- Google Chrome
- the OpenCLI browser bridge extension
- a logged-in browser session for browser-backed sources or WeChat draft staging

## Configuration

There are three separate config surfaces.

### 1. Preferences via `EXTEND.md`

Search order:

1. `.baoyu-skills/wechat-hot-writer/EXTEND.md`
2. `${XDG_CONFIG_HOME:-$HOME/.config}/baoyu-skills/wechat-hot-writer/EXTEND.md`
3. `~/.baoyu-skills/wechat-hot-writer/EXTEND.md`

Start by copying [EXTEND.example.md](EXTEND.example.md).

Supported keys:

- `lane`
- `fallback_query`
- `min_reader_relevance`
- `max_risk`
- `title_templates`
- `style_notes`

Use `EXTEND.md` for non-secret account preferences only. Keep credentials out of it.

### 2. Secrets via `.env`

The script checks these files:

- `.baoyu-skills/.env`
- `~/.baoyu-skills/.env`

WeChat draft API credentials:

```bash
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret
```

Important:

- these are only for WeChat draft APIs
- the current outbound IP still needs to be whitelisted in the WeChat platform
- draft creation is not subscriber publish

Image providers are auto-detected from configured keys:

| Provider | Required keys |
|---|---|
| `google` | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` |
| `dashscope` | `DASHSCOPE_API_KEY` |
| `seedream` | `ARK_API_KEY` |
| `jimeng` | `JIMENG_ACCESS_KEY_ID` and `JIMENG_SECRET_ACCESS_KEY` |
| `replicate` | `REPLICATE_API_TOKEN` |

### 3. Optional Baoyu skill interop

This skill can reuse local installs of:

- `baoyu-post-to-wechat`
- `baoyu-markdown-to-html`
- `baoyu-image-gen`
- `baoyu-cover-image`
- `baoyu-article-illustrator`

Baoyu skill discovery order:

1. `BAOYU_SKILLS_ROOT`
2. `BAOYU_SKILLS_DIRS`
3. `$CODEX_HOME/skills`
4. `~/.agents/skills`
5. `~/.codex/skills`

## Quick Start

### 1. Discover topics

```bash
python3 scripts/wechat_hot_writer.py discover-topics \
  --source-mode hybrid \
  --limit 8 \
  --history-file out/history.json \
  --output out/topics.json
```

### 2. Create a draft scaffold

```bash
python3 scripts/wechat_hot_writer.py write-article \
  --topic out/topics.json \
  --topic-index 0 \
  --scaffold out/draft.json
```

### 3. Fill the draft

Edit `out/draft.json` with the actual article content.

### 4. Package the article

```bash
python3 scripts/wechat_hot_writer.py write-article \
  --topic out/topics.json \
  --topic-index 0 \
  --draft out/draft.json \
  --output out/article-package.json
```

### 5. Prepare visuals

```bash
python3 scripts/wechat_hot_writer.py prepare-visuals \
  --package out/article-package.json \
  --output-dir out/visuals
```

### 6. Stage WeChat delivery

```bash
python3 scripts/wechat_hot_writer.py deliver-weixin \
  --package out/article-package.json \
  --staging-dir out/weixin \
  --dry-run
```

### 7. Record history

```bash
python3 scripts/wechat_hot_writer.py record-history \
  --package out/article-package.json \
  --history-file out/history.json \
  --media-id your_media_id
```

### 8. Sync WeChat stats back into history

```bash
python3 scripts/wechat_hot_writer.py sync-history-stats \
  --history-file out/history.json \
  --days 7
```

## Verification

From the repo root:

```bash
python3 -m unittest discover -s tests -q
```

From this skill directory:

```bash
python3 -m unittest ../../tests/test_topic_intelligence.py -q
```

## References

- Topic scoring and filters: [references/topic_scoring.md](references/topic_scoring.md)
- Article package contract: [references/article_package.md](references/article_package.md)
- Visual asset prep: [references/visual_assets.md](references/visual_assets.md)
- WeChat delivery flow: [references/weixin_delivery.md](references/weixin_delivery.md)
