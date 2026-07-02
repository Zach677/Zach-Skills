# Render WeChat HTML

The target publishing repo renders Markdown through
`scripts/wechat_render.ts`. That command calls this skill's locked Bun adapter
at `scripts/render_wechat_with_baoyu.ts`, which uses `baoyu-md@0.1.0` directly.

This stays aligned with Baoyu's renderer without adding browser automation. The
daily workflow remains API-only and does not use browser publishing, OpenCLI,
Chrome, CDP, QR login, captcha handling, or editor automation.

## Runtime Contract

- This skill's `scripts/package.json` pins `baoyu-md` to `0.1.0`.
- `scripts/wechat_render.ts` in the target repo locates this skill directory
  from `ZACH_WECHAT_DAILY_PUBLISHER_ROOT`, `--skill-root`, or the sibling
  `Zach-Skills` checkout.
- If renderer dependencies are missing, the target repo command runs
  `bun install --frozen-lockfile` in this skill's `scripts/` directory.
- The rendered `.wechat.html` file is the WeChat body fragment extracted from
  Baoyu's inlined HTML document, not a full browser page.
- The adapter passes explicit Baoyu render options for theme, color, font,
  code theme, citation status, and title handling so global renderer defaults
  do not drift the daily output.
- `ZACH_WECHAT_RENDER_THEME`, `ZACH_WECHAT_RENDER_COLOR`, and
  `ZACH_WECHAT_RENDER_FONT_SIZE` can override the default theme settings.

## Editorial Style Contract

- The WeChat draft title field is the title. Do not duplicate it as a large H1
  at the top of the article body.
- If the Markdown starts with a matching `# title`, the adapter strips it before
  calling `baoyu-md`.
- If the body starts with an opening paragraph or an H2, the adapter preserves
  that content.
- Write real Markdown lists for action checklists and warning signs.
- Use one or two standalone bold reminder lines at most.
- `## 参考资料`, `## 资料来源`, `## 参考来源`, `## 引用来源`, and `## 参考链接`
  are treated as explicit source sections. Links there show the source URL and
  are not duplicated into Baoyu's bottom citation block.
- Ordinary external links outside source sections become bottom `资料来源`
  citations.

## Validation

From the target publishing repo, run:

```bash
bun scripts/wechat_render.ts --self-test
bun run test
```

To check the adapter directly from this skill, run:

```bash
bun /path/to/skill/scripts/render_wechat_with_baoyu.ts --help
```
