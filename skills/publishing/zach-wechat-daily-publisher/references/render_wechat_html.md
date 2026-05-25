# Render WeChat HTML

`publisher_ops.py render` keeps the repo-local Python command surface, but the
Markdown renderer is the locked Bun adapter in `scripts/render_wechat_with_baoyu.ts`.
That adapter calls `baoyu-md@0.1.0` directly.

This is intentionally aligned with Baoyu's renderer instead of maintaining a
separate hand-rolled Markdown converter. The daily workflow still uses API-only
publishing and does not use browser automation, OpenCLI, Chrome, CDP, QR login,
captcha handling, or editor automation.

## Runtime Contract

- `scripts/package.json` pins `baoyu-md` to `0.1.0`.
- `publisher_ops.py render` checks for `scripts/node_modules/baoyu-md`.
- If dependencies are missing, it runs `bun install --frozen-lockfile` in the
  skill `scripts/` directory.
- The rendered `.wechat.html` file is the WeChat body fragment extracted from
  Baoyu's inlined HTML document, not a full browser page.
- The adapter passes explicit Baoyu render options for theme, color, font,
  code theme, citation status, and title handling so global `.baoyu-skills`
  renderer defaults do not drift the daily output.
- `ZACH_WECHAT_RENDER_THEME`, `ZACH_WECHAT_RENDER_COLOR`, and
  `ZACH_WECHAT_RENDER_FONT_SIZE` can override the default theme settings.

## Editorial Style Contract

- The WeChat draft title field is the title. Do not duplicate it as a large H1
  at the top of the article body.
- If the Markdown starts with a matching `# title`, the adapter strips it before
  calling `baoyu-md`.
- If the body starts with an opening paragraph or an H2, the adapter preserves
  that content. It does not let Baoyu's title-removal step accidentally drop the
  first section heading.
- Write real Markdown lists for action checklists and warning signs.
- Use one or two standalone bold reminder lines at most.
- `## 参考资料`, `## 资料来源`, `## 参考来源`, `## 引用来源`, and `## 参考链接`
  are treated as explicit source sections. Links there show the source URL and
  are not duplicated into Baoyu's bottom citation block.
- Ordinary external links outside source sections become bottom `资料来源`
  citations.

## Validation

Run:

```bash
python3 -m unittest discover \
  -s skills/publishing/zach-wechat-daily-publisher/tests -q
python3 -m py_compile \
  skills/publishing/zach-wechat-daily-publisher/scripts/publisher_ops.py
bun \
  skills/publishing/zach-wechat-daily-publisher/scripts/render_wechat_with_baoyu.ts \
  --help
```
