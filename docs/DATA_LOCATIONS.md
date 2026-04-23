# 爬取数据位置说明

## 📂 数据位置总览

### 1. **主要数据库** (推荐使用)
```
/Users/json/Desktop/findit/data/findit.db
```
**大小**: 1.17 MB
**内容**: 1,801条帖子 + 1,688个作者
**用途**: 主要查询和分析

**查询示例**:
```bash
# 查看所有交友相关评论
sqlite3 data/findit.db "
SELECT content, likes
FROM posts
WHERE content LIKE '%找对象%' OR content LIKE '%交友%'
ORDER BY likes DESC
LIMIT 10;"

# 查看作者统计
sqlite3 data/findit.db "
SELECT COUNT(*) as total_authors FROM authors;"
```

---

### 2. **MediaCrawler原始数据** (JSONL格式)
```
~/Desktop/MediaCrawler/data/xhs/jsonl/
```

#### 今天的爬取数据 (2026-04-23):
- `search_contents_2026-04-23.jsonl` (39KB) - 笔记内容
- `search_comments_2026-04-23.jsonl` (115KB) - 评论内容 (200条)

#### 历史数据:
- `search_contents_2026-04-11.jsonl` (226KB) - 之前爬取的笔记
- `search_comments_2026-04-11.jsonl` (391KB) - 之前爬取的评论 (738条)
- `search_contents_2026-04-10.jsonl` (138KB)
- `search_comments_2026-04-10.jsonl` (314KB) (592条)
- `search_contents_2026-04-05.jsonl` (31KB)
- `search_comments_2026-04-05.jsonl` (111KB) (200条)

**数据格式**:
```json
{
  "comment_id": "65fcdffb000000000b0166f4",
  "create_time": 1711071228000,
  "ip_location": "湖北",
  "note_id": "65ae84960000000011009f6a",
  "content": "主页还有完整的分析笔记~记得要翻牌[种草R]",
  "user_id": "5f1c737a0000000001001a82",
  "nickname": "卜鹿心理",
  "avatar": "https://sns-avatar-qc.xhscdn.com/avatar/...",
  "sub_comment_count": "37",
  "like_count": "123"
}
```

---

### 3. **测试数据** (开发调试用)
```
/Users/json/Desktop/findit/data/playwright_pages/
/Users/json/Desktop/findit/data/test_pages/
/Users/json/Desktop/findit/data/raw_pages/
```
- HTML页面快照
- 解析结果测试
- 调试输出

---

## 📊 数据统计

| 类型 | 数量 | 来源 |
|------|------|------|
| 总帖子 | 1,801 | 数据库 |
| 笔记 (posts) | ~179 | 搜索结果 |
| 评论 (comments) | 1,622 | 搜索结果 |
| 作者 | 1,688 | 唯一用户 |
| 交友相关 | 61 | 关键词匹配 |

---

## 🎯 如何使用

### 查看数据库内容
```bash
# 进入数据库
sqlite3 data/findit.db

# 查看表结构
.schema

# 查看前10条帖子
SELECT id, substr(content, 1, 50) as content, likes
FROM posts
ORDER BY likes DESC
LIMIT 10;

# 退出
.quit
```

### 查看原始JSONL数据
```bash
# 查看今天的评论
head -5 ~/Desktop/MediaCrawler/data/xhs/jsonl/search_comments_2026-04-23.jsonl | jq

# 统计今天的评论数
wc -l ~/Desktop/MediaCrawler/data/xhs/jsonl/search_comments_2026-04-23.jsonl

# 搜索交友关键词
grep "找对象\|交友\|相亲" ~/Desktop/MediaCrawler/data/xhs/jsonl/search_comments_2026-04-23.jsonl
```

---

## 💾 备份建议

**重要数据** (需要备份):
1. `data/findit.db` - 主数据库
2. `~/Desktop/MediaCrawler/data/xhs/jsonl/` - 原始数据
3. `~/Desktop/MediaCrawler/cookies/xhs_cookies.json` - 登录凭证

**可选备份**:
4. 测试数据和HTML页面 (占用空间较大)

---

## 🔄 数据更新

**重新导入数据**:
```bash
# 如果数据库丢失，可以重新导入
python3 scripts/import_mediacrawler_data.py
```

**继续爬取**:
```bash
# 使用MediaCrawler继续爬取
cd ~/Desktop/MediaCrawler
python3 main.py --platform xhs --lt cookie --type search --keywords "深圳相亲"
```

**增量导入**:
```bash
# 只导入最新的数据
python3 scripts/import_mediacrawler_data.py
# (脚本会自动去重，只导入新数据)
```

---

## 📝 数据质量

**评论质量示例**:

### 高质量交友信息 (28岁女护士):
```
"深圳 96女。护士 三观正。有点黏人。做饭超好吃，
蹲一个成熟稳重的男朋友[害羞R]"
```
- 年龄: 28岁
- 职业: 护士
- 地点: 深圳
- 特点: 做饭、三观正
- 要求: 成熟稳重

### 详细个人信息 (30岁有房男):
```
"94广东潮汕人定居深圳，粤语/211本科毕业，INTJ，颜控，
深圳有车有房（钓鱼中介月老别来[失望R]）"
```
- 年龄: 30岁
- 学历: 211本科
- 性格: INTJ、颜控
- 经济: 有车有房
- 籍贯: 潮汕

### 真实交友经历:
```
"聊着聊着没信了，过几天在看账号就被封了，所以账号就
一个找对象贴的基本就是钓鱼"
```
- 痛点: 断联、账号被封
- 观察: 单一找对象贴可能是钓鱼
