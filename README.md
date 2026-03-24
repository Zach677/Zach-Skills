# WeChat Hot Writer

`wechat-hot-writer` is a Codex-style skill package for:

- finding WeChat-friendly hot topics
- drafting AI / tech commentary articles
- preparing cover and illustration assets
- staging drafts into WeChat Official Account workflows

It is designed around a practical publishing loop:

1. discover topics
2. scaffold and write the article
3. prepare visuals
4. stage or publish a WeChat draft

This repository contains the skill package itself, not a standalone web app.

## What Is In The Repo

```text
wechat-hot-writer/
├── SKILL.md
├── agents/openai.yaml
├── references/
└── scripts/wechat_hot_writer.py
```

The repo root also contains:

- `README.md` for setup and usage
- `LICENSE` with the MIT license
- `.gitignore` that excludes runtime output such as `out/` and `.opencli/`

## Prerequisites

You need these before the full workflow is usable:

- `python3`
- `bun`
- `opencli`

You will also usually want:

- Google Chrome
- the OpenCLI browser bridge extension
- a logged-in browser session for any source or flow that depends on browser cookies

## External Skills This Skill Can Reuse

This repo can integrate with Baoyu's skills when they are installed locally.

Supported integrations:

- `baoyu-post-to-wechat`
- `baoyu-markdown-to-html`
- `baoyu-image-gen`
- `baoyu-cover-image`
- `baoyu-article-illustrator`

### How Baoyu skill discovery works

The script looks for Baoyu skills in this order:

1. `BAOYU_SKILLS_ROOT`
2. `BAOYU_SKILLS_DIRS` separated by your OS path separator
3. `$CODEX_HOME/skills` if `CODEX_HOME` is set
4. `~/.agents/skills`
5. `~/.codex/skills`

If your Baoyu skills live somewhere unusual, set one of:

```bash
export BAOYU_SKILLS_ROOT=/path/to/skills
```

or

```bash
export BAOYU_SKILLS_DIRS=/path/one:/path/two
```

## Configuration

There are three separate config surfaces to understand.

### 1. Topic discovery

Topic discovery uses `opencli`.

Some sources can work unauthenticated, but browser-backed sources are more reliable when Chrome is open and already logged in:

- Weibo
- X / Twitter
- Zhihu
- Bilibili

Fallback Google News does not require a browser login.

Sanity check:

```bash
opencli doctor
```

### 2. WeChat draft publishing

For the API route, create one of these files:

- `<repo>/.baoyu-skills/.env`
- `~/.baoyu-skills/.env`

and set:

```bash
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret
```

Important:

- these are used for WeChat draft APIs
- your current outbound IP must be whitelisted in the WeChat platform
- success here means a draft is created, not that the article is sent to subscribers

If the API route is unavailable, you can still use browser draft flows with `baoyu-post-to-wechat` or `opencli`.

### 3. Image generation

Visual generation is auto-detected from configured keys.

Supported providers and required keys:

| Provider | Required keys |
|---|---|
| `google` | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` |
| `dashscope` | `DASHSCOPE_API_KEY` |
| `seedream` | `ARK_API_KEY` |
| `jimeng` | `JIMENG_ACCESS_KEY_ID` and `JIMENG_SECRET_ACCESS_KEY` |
| `replicate` | `REPLICATE_API_TOKEN` |

Optional model overrides:

```bash
GOOGLE_IMAGE_MODEL=gemini-3.1-flash-image-preview
OPENAI_IMAGE_MODEL=gpt-image-1.5
OPENROUTER_IMAGE_MODEL=google/gemini-3.1-flash-image-preview
DASHSCOPE_IMAGE_MODEL=qwen-image-2.0-pro
SEEDREAM_IMAGE_MODEL=doubao-seedream-5-0-260128
JIMENG_IMAGE_MODEL=jimeng_t2i_v40
REPLICATE_IMAGE_MODEL=google/nano-banana-pro
```

The script auto-detects the first available provider in this order:

1. `google`
2. `openai`
3. `openrouter`
4. `dashscope`
5. `seedream`
6. `jimeng`
7. `replicate`

## Quick Start

### 1. Discover topics

```bash
python3 wechat-hot-writer/scripts/wechat_hot_writer.py discover-topics \
  --limit 8 \
  --output out/topics.json
```

### 2. Create a draft scaffold

```bash
python3 wechat-hot-writer/scripts/wechat_hot_writer.py write-article \
  --topic out/topics.json \
  --topic-index 0 \
  --scaffold out/draft.json
```

Edit `out/draft.json` with your actual article content.

### 3. Package the article

```bash
python3 wechat-hot-writer/scripts/wechat_hot_writer.py write-article \
  --topic out/topics.json \
  --topic-index 0 \
  --draft out/draft.json \
  --output out/article-package.json
```

This generates:

- packaged JSON
- WeChat-safe HTML
- a Baoyu-styled HTML variant when `baoyu-markdown-to-html` is available

### 4. Prepare visuals

```bash
python3 wechat-hot-writer/scripts/wechat_hot_writer.py prepare-visuals \
  --package out/article-package.json \
  --output-dir out/visuals
```

This generates:

- `out/visuals/cover/cover-brief.md`
- `out/visuals/illustrations/outline.md`
- `out/visuals/illustrations/prompts/*.md`
- `out/visuals/illustrations/batch.json`
- `out/visuals/commands.json`

If image credentials are configured, you can then generate visuals with the emitted command set.

### 5. Stage WeChat delivery

```bash
python3 wechat-hot-writer/scripts/wechat_hot_writer.py deliver-weixin \
  --package out/article-package.json \
  --staging-dir out/weixin \
  --dry-run
```

This generates:

- a delivery manifest
- staged local body images
- a WeChat body HTML file
- ready-to-run Baoyu API and browser commands when available

## Command Reference

### `discover-topics`

```bash
python3 wechat-hot-writer/scripts/wechat_hot_writer.py discover-topics [options]
```

Important options:

- `--limit`
- `--per-source`
- `--allow-high-risk`
- `--max-risk`
- `--min-ai-relevance`
- `--output`

### `write-article`

Scaffold mode:

```bash
python3 wechat-hot-writer/scripts/wechat_hot_writer.py write-article \
  --topic out/topics.json \
  --topic-index 0 \
  --scaffold out/draft.json
```

Package mode:

```bash
python3 wechat-hot-writer/scripts/wechat_hot_writer.py write-article \
  --topic out/topics.json \
  --topic-index 0 \
  --draft out/draft.json \
  --output out/article-package.json
```

### `prepare-visuals`

Auto-detect provider:

```bash
python3 wechat-hot-writer/scripts/wechat_hot_writer.py prepare-visuals \
  --package out/article-package.json \
  --output-dir out/visuals
```

Force a provider and model:

```bash
python3 wechat-hot-writer/scripts/wechat_hot_writer.py prepare-visuals \
  --package out/article-package.json \
  --output-dir out/visuals \
  --provider google \
  --model gemini-3.1-flash-image-preview
```

### `deliver-weixin`

```bash
python3 wechat-hot-writer/scripts/wechat_hot_writer.py deliver-weixin \
  --package out/article-package.json \
  --staging-dir out/weixin \
  --dry-run
```

## Public Repo Notes

This repo intentionally does not include:

- any API keys
- any WeChat credentials
- any generated `out/` artifacts
- any `.opencli/` capture output

Before publishing your fork, double-check:

- `git status`
- `.gitignore`
- local `.baoyu-skills/.env` files are not tracked

## License

This repository is released under the MIT License. See [LICENSE](LICENSE).
