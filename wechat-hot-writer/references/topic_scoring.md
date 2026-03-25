# Topic Schema And Scoring

## Stable topic schema

Every discovered topic should keep these fields:

```json
{
  "source": "weibo",
  "title": "这类吃法，很多中老年人还在天天做",
  "url": "https://example.com",
  "freshness": 0.92,
  "heat": 0.81,
  "reader_relevance": 0.93,
  "shareability": 0.88,
  "compliance_risk": 0.12,
  "angle_candidates": [
    "别复述热搜，先说这件事和哪类人最相关",
    "把容易误解的点和真正该注意的点拆开",
    "最后落到普通家庭今天就能做到的动作"
  ],
  "facts": [
    {
      "claim": "标题来自原始热榜或新闻源",
      "source_url": "https://example.com",
      "source_name": "weibo",
      "status": "reported"
    }
  ]
}
```

The implementation may add `score`, `score_breakdown`, `category`, or `raw`, but the fields above are the contract.

## Source priority

Use this order by default:

1. 微博热搜
2. 知乎热榜
3. B站热门
4. Google News fallback

The point is not “most viral”. The point is “fresh enough, close enough to ordinary life, easy enough to explain, safe enough to publish, and naturally convertible into middle-aged-reader writing”.

## Score formula

Use:

```text
final_score =
  freshness
  * reader_relevance
  * explainability
  * shareability
  * (1 - compliance_risk)
  * (0.55 + 0.45 * heat)
```

Interpretation:

- `freshness`: how current the topic looks
- `reader_relevance`: can this topic naturally serve readers roughly 45+ and their family caregivers
- `explainability`: is there a concrete angle beyond empty commentary
- `shareability`: does it have obvious forwarding potential inside family or friend groups
- `compliance_risk`: how likely the topic is to drag the account into restricted or high-liability lanes
- `heat`: tie-breaker, not the sole driver

## Editorial priority

Bias toward:

- 健康、养生、睡眠、饮食、走路、关节、血糖、消化、季节性提醒
- 银发生活、退休、社区、父母照护、家庭代际关系
- 防骗提醒、日常消费提醒、公共生活风险提醒
- 人物、情感、社会观察，但要能映射回普通家庭现实
- 大众食品或消费热点，只保留普通人立刻能关心的角度

Default exclusions:

- 纯 AI 产品更新、模型发布、融资、开源、圈内工具新闻
- 太依赖年轻互联网语境的梗
- 空泛热点复述

AI exception:

- 如果 AI 和大众生活热点强绑定，可以保留。
- 例如：食品、消费、民生、家庭场景里的 AI 争议或变化。
- 如果只是行业内部更新，直接降权。

## Compliance filters

Default high-risk lanes:

- 财经、证券、基金、保险、银行、理财、投资建议
- 药品、疾病诊断、治疗方案、医院具体建议、医生结论
- 法律、律师、法院、诉讼、合规结论
- 教育、升学、考试、培训认证
- 政治、时政、国际冲突、敏感公共事件

Default behavior:

- Filter hard if the title is mainly about one of those lanes.
- Health and wellness topics are allowed only when they stay in daily habits, common misunderstanding cleanup, or conservative reminders.
- If a topic naturally invites miracle-cure framing,神药 framing, or hard medical advice, either drop it or rewrite the angle to a safer general-information level.

## Angle generation

Every kept topic should have 3 angles. Bias toward:

- “这件事和哪类中老年读者或家庭最相关”
- “哪些说法最容易把人带偏，真正该注意的是什么”
- “普通人今天就能做的动作，和哪些情况不该自己扛”

Avoid:

- 空泛总结
- 纯情绪跟风
- 只会制造焦虑，不给边界和动作
- 用热点当借口硬拐到 AI / 科技评论
