# Zach WeChat Daily Publisher Preferences
#
# Copy this file to one of:
# - .baoyu-skills/zach-wechat-daily-publisher/EXTEND.md
# - ${XDG_CONFIG_HOME:-$HOME/.config}/baoyu-skills/zach-wechat-daily-publisher/EXTEND.md
# - ~/.baoyu-skills/zach-wechat-daily-publisher/EXTEND.md
#
# This file is for non-secret preferences only.
# Keep API keys and WeChat credentials in .env.

lane: 中老年健康与银发生活
fallback_query: 中老年 健康 睡眠 饮食 家庭 防骗 消费 出行 预约 认证 辟谣 提醒
min_reader_relevance: 0.46
max_risk: 0.35
default_author: zachaics
default_theme: default
default_color: blue
need_open_comment: 1
only_fans_can_comment: 0

cover:
  aspect: "2.35:1"
  rendering: flat-vector
  text: title-only
  mood: balanced
  font: clean

title_templates:
- 家里有老人会碰到「{title}」的，先把入口、条件和时间点看明白
- 「{title}」这种消息，最怕只看一半，普通家庭先核对这3件事
- 父母真碰上「{title}」，别慌，先看哪类人受影响、去哪核实

style_notes:
- 先把事实讲清楚，再下判断。
- 少用圈内黑话，尽量让家里人一看就懂。
- 服务或福利类内容，要写清适用人群、时间点、核对入口。
- 谣言、假通知、新规传闻先核官方来源，不要把传闻当事实放大。
- 养老金、社保、高龄津贴类提醒，要写清谁需要认证、什么时候办、去哪核对。
- 涉及身份证、刷脸、验证码、链接时，要写清什么不能给、去哪核实。
- 结尾要落到普通人今天能做什么。
