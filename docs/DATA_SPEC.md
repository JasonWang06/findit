# FindIt 数据契约（Data Spec）

> 目的：在改爬虫之前，先讲清楚"什么数据要爬、什么算中介、什么才算合格的入库记录"。
> 写完这份 spec，过滤逻辑、数据库 schema、爬虫流水线都按它对齐。

---

## 1. 爬取流水线

```
Step 1: 关键词搜索   →  得到 帖子(post) + 帖子作者
Step 2: 帖子评论区   →  得到 评论(comment) + 评论作者
   ↓
[早期中介筛查]  对 nickname / bio / post.content 跑 §3 Rule A + Rule B
   ├─ 命中  →  作者直接置为 filtered_out，不再爬主页（省请求）
   └─ 未命中 →  进入 Step 3
   ↓
Step 3: 作者主页     →  补全 ip_location / followers / notes / bio
                       然后再跑一次 §3（含 notes_summary）做最终判定
```

**关键原则：**
- 凡是从 Step 1/2 拿到的作者，未被早期筛查命中的，**都要走 Step 3**。
- 现状 Step 3 默认关掉（`crawl_include_profiles=False`），导致 88% 作者被打成 `empty_account`。
- 早期筛查省请求 + Step 3 补全字段，两件事各自负责。

### 1.1 Step 1：搜索帖子

- 入口：`/search_result?keyword=...`
- 关键词：见 `SEARCH_KEYWORDS`（找对象/蹲boyfriend/CPDD/...)
- 抓字段：post_id、title、content、author_id、likes、comments_count、`xsec_token`
- 入库表：`posts`（`source_type='post'`）

### 1.2 Step 2：评论区

- 入口：`/explore/<post_id>?xsec_token=...`
- 抓字段：评论 id、content、author_id、likes、created_at
- **过滤：** 评论本身先过 `COMMENT_DATING_KEYWORDS`，命中才入库
- 入库表：`posts`（`source_type='comment'`，借用同一张表）

### 1.3 Step 3：作者主页

- **触发条件**：未被早期中介筛查命中的作者
- 入口：`/user/profile/<author_id>?xsec_token=...`
- 抓字段：
  - `nickname`、`avatar_url`、`bio`
  - `ip_location`（**必须**，匹配的核心字段）
  - `followers`、`following`、`likes_collected`
  - `notes_summary`：最近 N 条笔记的标题/正文摘要（用于中介补刀 + 兴趣推断）
- 入库表：`authors` + `notes_summary`
- 主页爬完后再跑一次 §3，因为 `notes_summary` 此时才有，可能补刀掉早期漏判

---

## 2. 入库门槛（什么样的作者才存）

把 `is_filtered_out` 一个字段塞两种语义的做法停掉，拆成三态：

| 状态 | 含义 | 处理 |
|------|------|------|
| `pending_profile` | 从搜索/评论拿到 ID，未被早期筛查命中，主页还没爬 | **不算入库**，进队列等 Step 3 |
| `kept` | 通过所有过滤，进入匹配池 | 正常使用 |
| `filtered_out` | 被规则判为中介或主页爬完后字段仍不合格 | 永久排除，记 `filter_reason` |

**入库为 `kept` 的最低要求（Step 3 完成后判定）：**

- ✅ `ip_location` 非空
- ✅ 至少有一条 ≥12 字的 `post.content` **或** `bio` 非空
- ✅ 不命中 §3 的中介规则

`filter_reason` 取值：
- `matchmaker_keyword`（§3 Rule A 命中"红娘"）
- `matchmaker_proxy_post`（§3 Rule B 命中代发）
- `low_quality_content`（数据量不足，未来可重爬）

---

## 3. 中介识别规则

只两条规则，命中即丢，永久排除。其他软信号（粉丝比、发文频率等）暂不考虑。

### Rule A — 出现"红娘"二字

判定字段：`nickname` / `bio` / `post.content` / `notes_summary`（任一）

```python
MATCHMAKER_KEYWORD = "红娘"
```

只要任一字段包含"红娘"两字，立即标 `filter_reason='matchmaker_keyword'`。
不再要求"自称 + 服务"组合。

### Rule B — 代发帖

判定字段：`post.content`（含搜索结果的帖子 + 抓到的评论）

命中以下任一关键词或正则：

```python
PROXY_POST_KEYWORDS = [
    # 显式代发
    "代发", "代友发", "帮朋友发", "帮闺蜜发", "代闺蜜发",
    "替朋友发", "朋友委托", "本人委托",
    # 撇清"非本人"
    "非本人", "不是本人", "不是我本人",
    # 本人不在
    "本人不在小红书", "本人没小红书", "本人不刷小红书",
]
# 注：刻意没有放"已获本人同意/经本人同意/本人同意"——会误伤"其本人同意公开"
# 这种法律披露语境。真代发帖几乎一定同时出现"代发/代闺蜜发/帮朋友发"等显式
# 信号，已被上面的关键词或下面的正则覆盖。

PROXY_POST_PATTERNS = [
    r"代[一-龥]{1,3}发",   # "代闺蜜发"、"代表妹发"
    r"帮[一-龥]{1,3}发",   # "帮朋友发"、"帮表姐发"
    r"替[一-龥]{1,3}发",   # "替哥哥发"
]
```

逻辑：哪怕真的是朋友帮发，这个账号也无法直接私信到本人，匹配后无法触达，
所以一律不要。命中后标 `filter_reason='matchmaker_proxy_post'`。

### 触发时机

| 阶段 | 检查范围 |
|------|----------|
| 早期筛查（Step 1/2 之后） | Rule A 看 `nickname/bio/post.content`；Rule B 看 `post.content` |
| 主页补刀（Step 3 之后） | Rule A 增加 `notes_summary` 字段一起看 |

早期命中即可短路掉 Step 3，省请求。

---

## 4. Schema 改动建议

```sql
-- authors 表
ALTER TABLE authors ADD COLUMN crawl_state TEXT
    DEFAULT 'pending_profile';  -- pending_profile | kept | filtered_out
ALTER TABLE authors ADD COLUMN profile_crawled_at TEXT;  -- Step 3 完成时间

-- 评论入 posts 表时，post_url 写成评论 deeplink，方便人工核查
```

`is_filtered_out` 保留作旧字段兼容，新逻辑读 `crawl_state`。
`filter_reason` 取值见 §2。

---

## 5. 回填策略（已有 1925 个作者）

不要丢掉现在 DB 里的数据，按以下顺序处理：

1. 对全量 1925 个作者跑一遍**早期筛查**（Rule A + Rule B 在已有 `nickname/bio` +
   该作者已抓 `post.content` 上跑），命中的直接标 `filtered_out`
2. 剩下未命中的，把 `is_filtered_out=1 AND filter_reason='empty_account'` 的
   （≈1598 个）重置为 `crawl_state='pending_profile'`
3. 跑 Step 3（主页爬取）补全 `ip_location` / `notes_summary` 等字段
4. 主页补全后再跑一次 §3 做最终判定 + §2 入库门槛检查
5. 通过的进匹配池；通不过的按 §2 写明 `filter_reason`

预期效果：从 137 个有 `ip_location` 提升到 ≥1000 个可匹配作者；
中介命中数从 9 提升到匹配真实分布的水平。

---

## 6. 不在本 spec 范围

- 匹配算法（按标签打分）— 见 `MATCHING_REPORT.md`
- AI 标签提取 — 见 `AI_TAG_EXTRACTION.md`
- 破冰话术生成 — 待写

---

更新时间：2026-05-05
