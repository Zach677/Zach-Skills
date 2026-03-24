# Topic Schema And Scoring

## Stable topic schema

Every discovered topic should keep these fields:

```json
{
  "source": "weibo",
  "title": "OpenAI 发布新模型",
  "url": "https://example.com",
  "freshness": 0.92,
  "heat": 0.81,
  "ai_relevance": 0.97,
  "compliance_risk": 0.08,
  "angle_candidates": [
    "别复述热搜，解释它对 AI 工具链意味着什么",
    "从普通人今天就能做的动作切入",
    "把事件翻成 30 天内的机会和风险"
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
2. X 趋势
3. 知乎热榜
4. B 站热门
5. Google News fallback

The point is not “most viral”. The point is “fresh enough, explainable enough, safe enough, and naturally convertible into AI/tech writing”.

## Score formula

Use:

```text
final_score =
  freshness
  * ai_relevance
  * explainability
  * (1 - compliance_risk)
  * (0.6 + 0.4 * heat)
```

Interpretation:

- `freshness`: how current the topic looks
- `ai_relevance`: can this become a real AI or tech article
- `explainability`: is there a concrete angle beyond empty commentary
- `compliance_risk`: how likely the topic is to drag the account into restricted lanes
- `heat`: tie-breaker, not the sole driver

## Compliance filters

Default high-risk lanes:

- 财经、证券、基金、保险、银行、理财、投资建议
- 医疗、药品、疾病、诊断、医院、医生建议
- 法律、律师、法院、诉讼、合规结论
- 教育、升学、考试、培训认证
- 政治、时政、国际冲突、敏感公共事件

Default behavior:

- Filter hard if the title is mainly about one of those lanes.
- If a topic is mixed but has an AI/tech angle, keep it only when the article can stay in product, workflow, tooling, or trend-analysis territory.

## Angle generation

Every kept topic should have 3 angles. Bias toward:

- “这事对普通人的工具和工作流意味着什么”
- “为什么现在发生，而不是上个月”
- “这波变化接下来 30 天的实际影响”

Avoid:

- 空泛总结
- 纯情绪跟风
- 没有事实挂钩的观点输出
