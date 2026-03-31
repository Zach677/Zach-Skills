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
It may also add:

- `seo`: keyword suggestions, related keywords, and an SEO score
- `topic_keywords`: the keyword set that should be written into history
- `history`: recent-overlap penalty info for de-duplication

## Source priority

Use this order by default:

1. 微博热搜
2. 知乎热榜
3. B站热门
4. Google News fallback

The point is not “most viral”. The point is “fresh enough, close enough to ordinary life, easy enough to explain, safe enough to publish, and naturally convertible into middle-aged-reader writing”.

In practice, prefer `hybrid` collection:

1. `opencli` hot sources when browser discovery is healthy
2. direct hot-board APIs from Weibo, Toutiao, and Baidu
3. Google News fallback only when needed

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
  * seo_multiplier
  * history_multiplier
```

Interpretation:

- `freshness`: how current the topic looks
- `reader_relevance`: can this topic naturally serve readers roughly 45+ and their family caregivers
- `explainability`: is there a concrete angle beyond empty commentary
- `shareability`: does it have obvious forwarding potential inside family or friend groups
- `compliance_risk`: how likely the topic is to drag the account into restricted or high-liability lanes
- `heat`: tie-breaker, not the sole driver
- `seo_multiplier`: reward topics whose wording maps to real search demand
- `history_multiplier`: down-rank topics that repeat the same core keywords inside the recent history window

Recommended implementation:

- `seo_multiplier = 0.82 + 0.18 * seo_score`
- `history_multiplier = 1 - history_penalty`
- `seo_score` should come from real suggestion counts, not vibes
- `history_penalty` should come from your own article history, usually the last 7 days

## Editorial priority

Bias toward:

- 健康、养生、睡眠、饮食、走路、关节、血糖、消化、季节性提醒
- 节令/天气触发的实用题，例如花粉、晨练、暴走、春菜、清明、返乡、祭扫
- 银发生活、退休、社区、父母照护、家庭代际关系
- 防骗提醒、日常消费提醒、公共生活风险提醒、适老服务 friction
- 人物、情感、社会观察，但要能映射回普通家庭现实
- 大众食品或消费热点，只保留普通人立刻能关心的角度

Default exclusions:

- 纯 AI 产品更新、模型发布、融资、开源、圈内工具新闻
- 太依赖年轻互联网语境的梗
- 空泛热点复述
- 纯卖惨、纯悲情、纯明星围观，尤其是没有行动建议的故事

Additional keepers worth rescuing from generic hot boards:

- 实用消费提醒，例如回收、价格、买菜、家电、日常踩坑
- 节令/家庭节点，例如清明、祭扫、返乡、照护安排
- 银发数字生活，例如智能手机、微信、挂号、买票、课程、补贴、社区服务
- 轻文旅/社区/健身类银发生活内容，但前提是能落回普通家庭今天怎么用

AI exception:

- 如果 AI 和大众生活热点强绑定，可以保留。
- 例如：食品、消费、民生、家庭场景里的 AI 争议或变化。
- 银发学习、数字鸿沟、手机/微信实操、AI 诈骗、老年大学里的 AI 入门，也可以保留。
- 如果只是行业内部更新，直接降权。

## Reader-fit quick gate

Before a topic enters the final shortlist, ask five yes/no questions:

1. `看得懂`: 标题不靠圈内词，45+ 读者第一眼能懂。
2. `说得出`: 核心判断能被家里人复述成一句提醒。
3. `做得到`: 今天就能给出一个动作、步骤、核对项，不能只剩情绪。
4. `贴当前`: 最好能挂到季节、天气、当季食物、日常服务、家庭角色、常见症状、固定习惯之一。
5. `不过线`: 健康不装诊断，消费不装官方结论，故事不靠煽情偷分。

Rule of thumb:

- 满足 4-5 条，优先保留。
- 满足 3 条，只能在热点很强且角度明确时保留。
- 低于 3 条，默认淘汰。

Current fit notes from recent public pattern checks:

- 能转成 `提醒 / 核对 / 步骤 / 清单` 的题，通常比纯情绪讨论更稳。
- 节令、家庭安排、消费避坑、适老数字生活，和中老年家庭的转述场景更贴近。
- 人物故事不是不能写，但如果只剩悲情、猎奇、围观，就不该进默认池。

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
- 标题只剩“震惊/痛哭/崩溃/刷屏”这种情绪词，没有可执行提醒
- 卖惨、煽情、纯悲剧消费

## History feedback loop

After a draft is accepted or published:

1. write `title`, `published_at`, `topic_keywords`, `media_id`, and `word_count` into `history.json`
2. later sync WeChat article summary stats back into the same history file
3. on the next run, down-rank topics that hit the same core keywords within the recent window

The point is not “never repeat a lane”. The point is “stop repeating the same hook too fast”.
