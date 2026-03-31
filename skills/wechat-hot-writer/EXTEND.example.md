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
fallback_query: 民生 家庭 健康 防骗 适老消费 智能手机 老年大学 清明
min_reader_relevance: 0.4
max_risk: 0.38

title_templates:
- 看到「{title}」，普通家庭真正该留意的是这几点
- 别急着被「{title}」带着走，先把这件事看明白
- 别只把「{title}」当热闹，更该提醒家里人的是这一步

style_notes:
- 先把事实讲清楚，再下判断。
- 少用圈内黑话，尽量让家里人一看就懂。
- 结尾要落到普通人今天能做什么。
- 多写提醒、核对、步骤，少写围观感和卖惨感叹。
