# FindIt 用户标签体系设计

## 📋 标签分类架构

```
用户画像
├── 基础信息 (必填)
├── 个人特质 (可选项)
├── 偏好设置 (想找什么样的)
└── 系统标签 (自动生成)
```

---

## 1️⃣ 基础信息标签

### 基本信息
- **gender**: `male | female | other`
- **age**: `18-99` (整数)
- **location**: `城市+区域` (如: 深圳-南山)
- **height**: `cm` (整数, 可选)
- **education**: `学历等级`

### 学历选项
```
phd        # 博士及以上
master     # 硕士/研究生
bachelor   # 本科
college    # 大专/专科
high_school # 高中及以下
other      # 其他
```

### 职业类别
```
tech          # 互联网/技术 (程序员、开发、工程师)
finance       # 金融/银行 (证券、基金、保险)
education     # 教育/科研 (教师、教授)
medical       # 医疗健康 (医生、护士)
civil_servant # 公务员/体制内
business      # 创业/经商
student       # 学生
media         # 媒体/娱乐 (记者、主播)
art           # 艺术/设计 (设计师、画家)
law           # 法律 (律师、法务)
manufacturing # 制造业/工程师
service       # 服务业 (餐饮、零售)
other         # 其他职业
```

### 收入水平
```
A9_plus   # 亿万+ (A9+)
A9        # 千万级 (1000万+)
A8_plus   # 500万-1000万
A8        # 百万级 (100万-500万)
A7_plus   # 50万-100万
A7        # 20万-50万
A6_plus   # 10万-20万
A6        # 5万-10万
below_A6  # 5万以下
unspecified # 未说明
```

---

## 2️⃣ 个人特质标签 (可选项)

### 性格标签
```
introvert      # 内向
extrovert      # 外向
humorous       # 幽默
serious        # 成熟稳重
romantic       # 浪漫
rational       # 理性
emotional      # 感性
independent    # 独立
dependent      # 依赖型
clingy         # 黏人
easy_going     # 随和
 perfectionist # 完美主义
adventurous    # 爱冒险
homebody       # 宅家型
```

### 兴趣爱好
```
sports         # 运动
fitness        # 健身
travel         # 旅游
cooking        # 烹饪
reading        # 阅读
gaming         # 游戏
music          # 音乐
movies         # 电影
photography    # 摄影
pets           # 宠物
outdoor        # 户外
foodie         # 美食
art            # 艺术
tech           # 科技
diy            # 手作
```

### 生活习惯
```
non_smoker     # 不抽烟
smoker         # 抽烟
non_drinker    # 不喝酒
social_drinker # 社交饮酒
heavy_drinker  # 经常喝酒
early_bird     # 早起型
night_owl      # 熬夜型
neat           # 爱干净
messy          # 随意
home_cook      # 经常做饭
takeout        # 经常外卖
```

### 外观特征
```
slim       # 苗条
average    # 匀称
athletic   # 健硕
chubby     # 微胖
glasses    # 戴眼镜
tattoo     # 有纹身
fashion    # 时尚
casual     # 休闲风
```

---

## 3️⃣ 偏好设置标签 (想找什么样的)

### 年龄偏好
```
age_younger: ±3年  # 希望对方比自己小
age_same: ±2年     # 希望同龄
age_older: ±5年    # 希望对方比自己大
age_any: # 不限
```

### 身高偏好
```
min_height: 170  # 最低身高要求
max_height: 185  # 最高身高要求 (可选)
```

### 外貌偏好
```
looks_important    # 颜控
looks_moderate     # 看眼缘
looks_not_important # 不在乎外貌
```

### 性格偏好
```
personality_similar    # 性格相似
personality_complement # 性格互补
personality_any        # 不限
```

### 地点偏好
```
location_same_city    # 同城
location_nearby       # 附近城市
location_any          # 不限
location_accept_remote # 接受异地
```

### 经济偏好
```
financial_high      # 经济条件好
financial_stable    # 收入稳定
financial_any       # 不限
```

### 婚姻观
```
marriage_want_kids  # 想要孩子
marriage_no_kids    # 不想要孩子
marriage_soon       # 近期结婚
marriage_take_time  # 慢慢来
```

---

## 4️⃣ 系统标签 (自动生成)

### 感情状态
```
single      # 单身
dating      # 恋爱中
complicated # 关系复杂
married     # 已婚
divorced    # 离异
widowed     # 丧偶
```

### 活跃度
```
active_daily     # 每日活跃
active_weekly    # 每周活跃
active_monthly   # 每月活跃
inactive         # 不活跃
```

### 认证状态
```
verified_basic   # 基础认证 (手机)
verified_profile # 资料认证
verified_premium # 高级认证 (身份+收入)
```

### 账号类型
```
real_user     # 真实用户
bot           # 机器人/可疑账号
scammer       # 骗子账号
verified      # 已认证用户
```

### 数据来源
```
self_reported    # 用户自己填写
crawler_inferred # 爬虫推断
mixed           # 混合来源
```

### 推荐标签
```
high_quality     # 高质量用户
popular          # 热门用户
new_user         # 新用户
complete_profile # 资料完整
active_seeker    # 积极找对象中
```

---

## 🎯 标签优先级

### 第一优先级 (必须有)
- gender
- age
- location
- status (感情状态)

### 第二优先级 (重要)
- education
- occupation
- height
- income_level

### 第三优先级 (加分项)
- personality
- interests
- requirements

### 第四优先级 (可选)
- lifestyle
- looks
- detailed_preferences

---

## 📊 标签存储结构

### 用户表 (users)
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,

    -- 基础信息
    gender TEXT,
    age INTEGER,
    location TEXT,
    height INTEGER,
    education TEXT,
    occupation TEXT,
    income_level TEXT,

    -- 感情状态
    relationship_status TEXT,

    -- 来源信息
    data_source TEXT,  -- 'self_reported' | 'crawler_inferred'
    source_post_id TEXT,

    -- 元数据
    profile_complete REAL,  -- 0.0-1.0 资料完整度
    confidence_score REAL,  -- 0.0-1.0 数据可信度
    created_at TEXT,
    updated_at TEXT
);
```

### 用户标签表 (user_tags)
```sql
CREATE TABLE user_tags (
    user_id TEXT,
    tag_category TEXT,  -- 'personality' | 'interest' | 'lifestyle' etc.
    tag_name TEXT,
    tag_value TEXT,
    confidence REAL,
    created_at TEXT,
    PRIMARY KEY (user_id, tag_category, tag_name),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 用户偏好表 (user_preferences)
```sql
CREATE TABLE user_preferences (
    user_id TEXT PRIMARY KEY,
    age_range_min INTEGER,
    age_range_max INTEGER,
    min_height INTEGER,
    preferred_locations TEXT,  -- JSON array
    preferred_occupations TEXT, -- JSON array
    gender_preference TEXT,
    location_preference TEXT,
    financial_preference TEXT,
    marriage_preference TEXT,
    updated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## 🏷️ 标签示例

### 示例1: "深圳 96女。护士 三观正。有点黏人。做饭超好吃"

```json
{
  "user_id": "xhs_user_123",
  "basic_info": {
    "gender": "female",
    "age": 28,  // 1996年生
    "location": "深圳",
    "education": "bachelor",  // 护士通常本科
    "occupation": "medical"
  },
  "personality": [
    "clingy",      // 有点黏人
    "easy_going"   // 三观正 (推断)
  ],
  "interests": [
    "cooking"      // 做饭超好吃
  ],
  "status": "single",
  "data_source": "crawler_inferred",
  "confidence_score": 0.75
}
```

### 示例2: "94广东潮汕人定居深圳，粤语/211本科毕业，INTJ，颜控，深圳有车有房"

```json
{
  "user_id": "xhs_user_456",
  "basic_info": {
    "gender": "male",  // 推断
    "age": 30,  // 1994年生
    "location": "深圳",
    "hometown": "广东潮汕",
    "education": "bachelor",  // 211本科
    "occupation": "unspecified",
    "income_level": "A7_plus"  // 有车有房
  },
  "personality": [
    "rational",    // INTJ
    "perfectionist"  // 颜控
  ],
  "preferences": {
    "looks": "looks_important",  // 颜控
    "language": "粤语"
  },
  "assets": {
    "car": true,
    "house": true
  },
  "status": "single",
  "data_source": "crawler_inferred",
  "confidence_score": 0.85
}
```

### 示例3: "只要性别男170+工作gwy或者tzn"

```json
{
  "user_id": "xhs_user_789",
  "basic_info": {
    "gender": "female"  // 推断
  },
  "preferences": {
    "target_gender": "male",
    "min_height": 170,
    "preferred_occupations": [
      "civil_servant",  // gwy
      "education"       // tzn (推测:教师)
    ]
  },
  "status": "single",
  "data_source": "crawler_inferred",
  "confidence_score": 0.65
}
```

---

## 🔄 标签更新策略

### 用户主动填写
- 优先级最高
- 覆盖推断标签
- confidence_score = 1.0

### 爬虫推断
- 作为初始数据
- 用户确认后更新
- confidence_score = 0.5-0.8

### 行为推断
- 浏览/点赞/评论行为
- 逐步优化标签
- confidence_score = 0.3-0.5

---

## 📈 标签质量评估

### 完整度评分
```python
def calculate_completeness(user_tags):
    score = 0
    total = 0

    # 必填项 40%
    if user_tags.get('gender'): score += 10
    if user_tags.get('age'): score += 10
    if user_tags.get('location'): score += 10
    if user_tags.get('status'): score += 10
    total += 40

    # 重要项 40%
    if user_tags.get('education'): score += 10
    if user_tags.get('occupation'): score += 10
    if user_tags.get('height'): score += 5
    if user_tags.get('personality'): score += 15
    total += 40

    # 可选项 20%
    if user_tags.get('interests'): score += 10
    if user_tags.get('preferences'): score += 10
    total += 20

    return score / total
```

---

*版本: v1.0*
*最后更新: 2026-04-24*
