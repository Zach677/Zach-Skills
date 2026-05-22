# Render WeChat HTML

`publisher_ops.py render` performs a small dependency-free Markdown conversion
for API draft creation.

It handles:

- frontmatter title/summary extraction
- headings, paragraphs, blockquotes, lists, bold, emphasis, inline code
- local image tags
- external links converted to numbered citations at the bottom
- basic inline styles for WeChat compatibility

This is intentionally smaller than WeWrite or Baoyu's full renderer. If richer
theme rendering is later needed, add a locked adapter; do not call `npx` or pull
runtime dependencies during a publish run.
