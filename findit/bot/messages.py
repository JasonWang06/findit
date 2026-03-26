"""Message templates for the Telegram bot (Chinese UI)."""

WELCOME = (
    "👋 欢迎使用 FindIt！\n\n"
    "我会帮你在小红书上找到真实求偶的女生，并生成个性化的破冰话术。\n\n"
    "首先需要完善你的资料，这样我才能精准匹配。\n"
    "请发送 /setup 开始设置。"
)

SETUP_AGE = "📝 第1步/8：你的年龄是？（例：28）"
SETUP_HEIGHT = "📏 第2步/8：你的身高？（cm，例：178）"
SETUP_EDUCATION = (
    "🎓 第3步/8：你的学历？\n"
    "请选择：高中 / 大专 / 本科 / 硕士 / 博士"
)
SETUP_SCHOOL = "🏫 第4步/8：毕业院校？（例：北京大学，如不想填写发 跳过）"
SETUP_OCCUPATION = "💼 第5步/8：你的职业？（例：软件工程师）"
SETUP_INCOME = (
    "💰 第6步/8：月收入区间？\n"
    "请选择：1万以下 / 1-2万 / 2-3万 / 3-5万 / 5万以上"
)
SETUP_CITY = "📍 第7步/8：你所在的城市？（例：深圳）"
SETUP_HOBBIES = (
    "🎯 第8步/8：你的兴趣爱好？\n"
    "用逗号分隔（例：跑步,摄影,美食,旅行）"
)
SETUP_HIGHLIGHTS = (
    "✨ 最后一步（选填）：其他亮点？\n"
    "如海归经历、房车情况等，用逗号分隔。\n"
    "不想填写发 跳过"
)

SETUP_COMPLETE = (
    "✅ 资料设置完成！\n\n"
    "你的资料：\n"
    "• 年龄：{age}\n"
    "• 身高：{height}cm\n"
    "• 学历：{education} {school}\n"
    "• 职业：{occupation}\n"
    "• 收入：{income_range}\n"
    "• 城市：{city}\n"
    "• 爱好：{hobbies}\n"
    "• 亮点：{highlights}\n\n"
    "发送 /match 获取今日推荐！"
)

MATCH_HEADER = "💘 为你找到以下匹配（{index}/{total}）\n"

MATCH_CARD = (
    "━━━━━━━━━━━━━━━━━━━━\n"
    "👤 {nickname}\n"
    "📍 {location} · {age_tag}\n"
    "📝 {bio_short}\n\n"
    "📊 匹配度：{match_score}%\n"
    "💡 {match_analysis}\n\n"
    "💬 推荐话术：\n"
    "```\n{opener}\n```\n\n"
    "🔗 原帖：{post_url}\n"
    "━━━━━━━━━━━━━━━━━━━━"
)

NO_MATCHES = (
    "😅 今天暂时没有新的匹配结果。\n"
    "系统正在持续抓取新数据，明天再来看看吧！"
)

ACTION_LIKED = "👍 已记录你的偏好，后续推荐会更精准！"
ACTION_PASSED = "👎 已记录，后续不会推荐类似的了。"
ACTION_REGENERATE = "🔄 正在重新生成话术..."
ACTION_REGENERATED = "🔄 新话术：\n```\n{opener}\n```"

HELP_TEXT = (
    "📖 使用指南：\n\n"
    "/start - 开始使用\n"
    "/setup - 设置/更新个人资料\n"
    "/match - 获取今日匹配推荐\n"
    "/preferences - 设置筛选偏好\n"
    "/help - 查看帮助\n\n"
    "每条推荐下方有操作按钮：\n"
    "👍 感兴趣 | 👎 不感兴趣 | 🔄 换话术"
)

PREFERENCES_PROMPT = (
    "⚙️ 筛选偏好设置：\n\n"
    "请输入你的偏好（JSON格式或逐项输入）：\n"
    "• 目标年龄范围（例：22-28）\n"
    "• 是否接受异地（是/否）\n\n"
    "例：22-28 否"
)

PREFERENCES_SAVED = "✅ 偏好已保存！"

ERROR_NOT_SETUP = "⚠️ 请先完善资料！发送 /setup 开始。"
ERROR_GENERIC = "⚠️ 出了点问题，请稍后再试。"
