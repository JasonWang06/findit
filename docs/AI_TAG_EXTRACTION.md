# FindIt AI 标签提取使用指南

## 功能概述

AI 标签提取功能使用 Claude API 从小红���帖子/评论内容中自动提取结构化信息：

- **个人信息**：性别、年龄、身高、学历、地区、职业
- **交友要求**：期望的性别、年龄范围、身高、学历、地区
- **交友意图**：认真度评分、意图类型、紧急程度
- **标签提取**：自动提取关键标签
- **置信度评分**：AI 对提取结果的置信度

## 安装和配置

### 1. 安装依赖

```bash
pip install anthropic
```

### 2. 配置 API Key

编辑 `.env` 文件，添加你的 Anthropic API Key：

```
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### 3. 数据库迁移

运行数据库迁移，添加 `ai_tags` 列：

```bash
python scripts/migrate_add_tags.py
```

## 使用方法

### 提取单个帖子的标签

```bash
python scripts/extract_tags.py --post-id comment_6850665c000000000401c39f
```

### 批量提取标签（最新10个帖子）

```bash
python scripts/extract_tags.py --limit 10
```

### 只处理评论

```bash
python scripts/extract_tags.py --limit 20 --source-type comment
```

### 重新处理已处理的帖子

```bash
python scripts/extract_tags.py --limit 5 --reprocess
```

## 输出格式

标签提取结果以 JSON 格式存储在 `posts.ai_tags` 列中：

```json
{
  "personal_info": {
    "gender": "女",
    "age": 26,
    "height": 165,
    "education": "本科",
    "location": "深圳",
    "occupation": "产品经理"
  },
  "requirements": {
    "preferred_gender": "男",
    "age_range": {"min": 25, "max": 35},
    "min_height": 170,
    "education": "本科以上",
    "location": "深圳"
  },
  "dating_intent": {
    "seriousness_score": 85,
    "intent_type": "认真征婚",
    "urgency": "正常"
  },
  "extracted_tags": ["26岁女", "深圳", "本科", "产品经理", "认真找对象"],
  "confidence_score": 90
}
```

## 数据查询示例

### 查找已提取标签的帖子

```python
from findit.db import Database
import json

db = Database()

with db._conn() as conn:
    rows = conn.execute("""
        SELECT id, content, ai_tags
        FROM posts
        WHERE ai_tags IS NOT NULL
        LIMIT 10
    """).fetchall()

    for row in rows:
        tags = json.loads(row['ai_tags'])
        print(f"{row['id']}: {tags['personal_info']['gender']}, {tags['personal_info']['age']}岁")
```

### 按条件筛选

```python
# 查找认真度 > 80 的女性用户
with db._conn() as conn:
    rows = conn.execute("""
        SELECT id, content, ai_tags
        FROM posts
        WHERE ai_tags IS NOT NULL
        AND json_extract(ai_tags, '$.personal_info.gender') = '女'
        AND json_extract(ai_tags, '$.dating_intent.seriousness_score') > 80
    """).fetchall()
```

## 成本估算

- 每个 API 调用消耗约 500-1000 tokens
- Claude Sonnet 4.6 定价：$3/百万输入 tokens，$15/百万输出 tokens
- 估算：每个帖子标签提取成本约 $0.0002-0.0003
- 1000 个帖子成本约 $0.20-0.30

## 性能优化建议

1. **批量处理**：一次处理多个帖子，减少连接开销
2. **并发控制**：使用 `--limit` 控制批量大小
3. **增量处理**：默认只处理未标记的帖子
4. **错误处理**：失败的帖子会跳过，可以后续重试

## 故障排除

### API Key 未设置

```
Error: ANTHROPIC_API_KEY not set in .env file
```

解决：在 `.env` 文件中添加你的 API Key。

### 数据库权限问题

```
sqlite3.OperationalError: attempt to write a readonly database
```

解决：检查数据库文件权限，确保当前用户有写入权限。

### API 调用失败

```
✗ Post xxx: Extraction failed
```

可能原因：
- 网络连接问题
- API 配额超限
- 内容过短或格式异常

解决：检查网络连接和 API 配额，确认内容格式正确。

## 下一步开发

- [ ] 添加用户偏好匹配功能
- [ ] 实现 AI 破冰话术生成
- [ ] 支持更多社交平台
- [ ] 添加数据导出功能
- [ ] 实现用户反馈循环优化