# WeChat Hot Writer Preferences
#
# Copy this file to one of:
# - .baoyu-skills/wechat-hot-writer/EXTEND.md
# - ${XDG_CONFIG_HOME:-$HOME/.config}/baoyu-skills/wechat-hot-writer/EXTEND.md
# - ~/.baoyu-skills/wechat-hot-writer/EXTEND.md
#
# This file is for non-secret preferences only.
# Keep API keys and WeChat credentials in .env.

lane: 通用家庭与公共话题
fallback_query: 民生 家庭 健康 防骗 消费 提醒
min_reader_relevance: 0.32
max_risk: 0.4

title_templates:
- 从「{title}」说起，普通人真正要留意的是这几点
- 看到「{title}」，先别急着下结论
- 别只盯着「{title}」，更重要的是后面这一步

style_notes:
- 先把事实讲清楚，再下判断。
- 少用圈内黑话，尽量让家里人一看就懂。
- 结尾要落到普通人今天能做什么。
