# WeChat Hot Writer Preferences
#
# Copy this file to one of:
# - .baoyu-skills/wechat-hot-writer/EXTEND.md
# - ${XDG_CONFIG_HOME:-$HOME/.config}/baoyu-skills/wechat-hot-writer/EXTEND.md
# - ~/.baoyu-skills/wechat-hot-writer/EXTEND.md
#
# This file is for non-secret preferences only.
# Keep API keys and WeChat credentials in .env.

lane: 通用家庭提醒与银发服务
fallback_query: 家庭 健康 防骗 消费 出行 提醒
min_reader_relevance: 0.42
max_risk: 0.35

title_templates:
- 看到「{title}」，先替家里人核对这几件事
- 别把「{title}」只当新闻，很多家庭真正要注意的是这几点
- 说到「{title}」，普通人更该看懂的是后面这一步

style_notes:
- 先把事实讲清楚，再下判断。
- 少用圈内黑话，尽量让家里人一看就懂。
- 服务或福利类内容，要写清适用人群、时间点、核对入口。
- 结尾要落到普通人今天能做什么。
