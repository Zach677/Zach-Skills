import fs from "node:fs";
import path from "node:path";
import process from "node:process";

import {
  FONT_FAMILY_MAP,
  cleanSummaryText,
  extractSummaryFromBody,
  extractTitleFromMarkdown,
  parseFrontmatter,
  renderMarkdownDocument,
  resolveColorToken,
  serializeFrontmatter,
  stripWrappingQuotes,
} from "baoyu-md";

const REFERENCE_HEADING_WORDS = new Set([
  "参考资料",
  "资料来源",
  "参考来源",
  "引用来源",
  "参考链接",
]);

interface Args {
  article: string;
  output: string;
  theme: string;
  color?: string;
  fontSize?: string;
  noCite: boolean;
}

interface Citation {
  label: string;
  url: string;
}

function printUsage(exitCode = 0): never {
  console.log(`Render WeChat article HTML with baoyu-md

Usage:
  bun render_wechat_with_baoyu.ts --article <article.md> --output <article.wechat.html> [options]

Options:
  --theme <name>      baoyu-md theme name. Default: default
  --color <name|hex>  Primary color token or hex value. Default: blue
  --font-size <size>  Font size passed to baoyu-md, e.g. 16px
  --no-cite           Disable baoyu-md bottom citations
  --help              Show this help
`);
  process.exit(exitCode);
}

function parseArgs(argv: string[]): Args {
  const args: Args = {
    article: "",
    output: "",
    theme: process.env.ZACH_WECHAT_RENDER_THEME || "default",
    color: process.env.ZACH_WECHAT_RENDER_COLOR || "blue",
    fontSize: process.env.ZACH_WECHAT_RENDER_FONT_SIZE || undefined,
    noCite: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]!;
    const next = argv[i + 1];
    if (arg === "--help" || arg === "-h") {
      printUsage(0);
    } else if (arg === "--article" && next) {
      args.article = next;
      i += 1;
    } else if (arg === "--output" && next) {
      args.output = next;
      i += 1;
    } else if (arg === "--theme" && next) {
      args.theme = next;
      i += 1;
    } else if (arg === "--color" && next) {
      args.color = next;
      i += 1;
    } else if (arg === "--font-size" && next) {
      args.fontSize = next;
      i += 1;
    } else if (arg === "--no-cite") {
      args.noCite = true;
    } else {
      throw new Error(`Unknown or incomplete argument: ${arg}`);
    }
  }

  if (!args.article) {
    throw new Error("Missing --article");
  }
  if (!args.output) {
    throw new Error("Missing --output");
  }
  return args;
}

function isReferenceHeading(text: string): boolean {
  const normalized = text.trim().replace(/[：:]\s*$/, "").replace(/\s+/g, "");
  return REFERENCE_HEADING_WORDS.has(normalized);
}

function stripMatchingLeadingTitle(body: string, title: string): string {
  const lines = body.split(/\r?\n/);
  let index = 0;
  while (index < lines.length && !lines[index]!.trim()) {
    index += 1;
  }
  const match = lines[index]?.trim().match(/^#\s+(.+?)\s*$/);
  if (!match) {
    return body.trim();
  }
  const heading = match[1]!.replace(/\s+/g, "");
  const titleText = title.replace(/\s+/g, "");
  if (heading === titleText) {
    lines.splice(index, 1);
  }
  return lines.join("\n").trim();
}

function rewriteReferenceLinks(body: string): string {
  let inReferences = false;
  const lines = body.split(/\r?\n/);
  return lines
    .map((line) => {
      const heading = line.trim().match(/^(#{1,6})\s+(.+)$/);
      if (heading) {
        inReferences = isReferenceHeading(heading[2]!);
      }
      if (!inReferences) {
        return line;
      }
      return line.replace(
        /(?<!!)\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
        (_match, label: string, url: string) => `${label}：${url}`,
      );
    })
    .join("\n");
}

function collectCitations(body: string): Citation[] {
  const citations: Citation[] = [];
  const seen = new Set<string>();
  let inReferences = false;
  for (const line of body.split(/\r?\n/)) {
    const heading = line.trim().match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      inReferences = isReferenceHeading(heading[2]!);
    }
    if (inReferences) {
      continue;
    }
    const matches = line.matchAll(/(?<!!)\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g);
    for (const match of matches) {
      const label = match[1]!.trim();
      const url = match[2]!.trim();
      if (!label || seen.has(url)) {
        continue;
      }
      seen.add(url);
      citations.push({ label, url });
    }
  }
  return citations;
}

function extractHtmlContent(html: string): string {
  const match = html.match(/<div id="output"[^>]*>([\s\S]*?)<\/div>\s*<\/body>/i);
  if (match) {
    return match[1]!.trim();
  }
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  return bodyMatch ? bodyMatch[1]!.trim() : html;
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const articlePath = path.resolve(args.article);
  const outputPath = path.resolve(args.output);
  const markdown = fs.readFileSync(articlePath, "utf-8");
  const { frontmatter, body } = parseFrontmatter(markdown);

  let title = stripWrappingQuotes(frontmatter.title ?? "") || extractTitleFromMarkdown(body);
  if (!title) {
    title = path.basename(articlePath, path.extname(articlePath));
  }
  const author = stripWrappingQuotes(frontmatter.author ?? "");
  const frontmatterSummary = stripWrappingQuotes(frontmatter.description ?? "")
    || stripWrappingQuotes(frontmatter.summary ?? "");
  const summary = cleanSummaryText(frontmatterSummary) || extractSummaryFromBody(body, 120);

  const strippedBody = stripMatchingLeadingTitle(body, title);
  const rewrittenBody = rewriteReferenceLinks(strippedBody);
  const rewrittenMarkdown = `${serializeFrontmatter(frontmatter)}${rewrittenBody}`;
  const citations = args.noCite ? [] : collectCitations(strippedBody);

  const result = await renderMarkdownDocument(rewrittenMarkdown, {
    codeTheme: "github",
    citeStatus: !args.noCite,
    countStatus: false,
    defaultTitle: title,
    fontFamily: FONT_FAMILY_MAP.sans,
    fontSize: args.fontSize || "16px",
    isMacCodeBlock: true,
    isShowLineNumber: false,
    keepTitle: true,
    legend: "alt",
    primaryColor: resolveColorToken(args.color),
    theme: args.theme,
  });
  let contentHtml = extractHtmlContent(result.html);
  contentHtml = contentHtml.replace(/>引用链接</g, ">资料来源<");
  contentHtml = contentHtml.replace(/\\_/g, "_");

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${contentHtml}\n`, "utf-8");

  console.log(JSON.stringify({
    renderer: "baoyu-md",
    rendererVersion: "0.1.0",
    html_path: outputPath,
    title,
    summary,
    author,
    theme: args.theme,
    color: args.color || "",
    citations,
  }, null, 2));
}

await main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
