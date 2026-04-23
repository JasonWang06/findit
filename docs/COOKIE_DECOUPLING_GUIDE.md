# 🚀 FindIt Cookie解耦完整指南

## 🎯 已解决的问题

### ✅ 问题1：链接打不开 - 已修复
**原因**：数据库中存储的是帖子链接，不是用户主页链接
**解决**：
- 添加了`homepage_url`字段到`authors`表
- 现在所有匹配都使用用户主页链接
- 格式：`https://www.xiaohongshu.com/user/profile/{user_id}`

### ✅ 问题2：Cookie与爬虫耦合 - 已解耦
**原因**：Cookie硬编码在MediaCrawler配置中
**解决**：
- 创建了独立的Cookie管理器
- 支持多种cookie来源（文件、环境变量、手动输入）
- 爬虫运行前自动检查和更新cookie

---

## 📋 使用方���

### 第1步：更新Cookie

#### 方法A：从文件加载（推荐）
```bash
# 保存cookie到FindIt
python3 scripts/setup_cookie_manager.py save --cookie "你的cookie字符串" --source "browser_export"

# 检查状态
python3 scripts/setup_cookie_manager.py status
```

#### 方法B：从环境变量加载
```bash
# 设置环境变量
export XHS_COOKIE="你的cookie字符串"

# 检查状态
python3 scripts/setup_cookie_manager.py status
```

#### 方法C：手动配置文件
```bash
# 直接编辑MediaCrawler配置
vim ~/Desktop/MediaCrawler/config/base_config.py
# 修改第24行的COOKIES变量
```

### 第2步：使用解耦版爬虫

#### 基本用法
```bash
# 快速模式（推荐）
python3 scripts/smart_crawler_decoupled.py --mode quick

# 完整模式
python3 scripts/smart_crawler_decoupled.py --mode full

# 测试模式
python3 scripts/smart_crawler_decoupled.py --mode test
```

#### 新加坡专属爬取
```bash
# 爬取新加坡相关数据
python3 scripts/smart_crawler_decoupled.py \
  --mode custom \
  --cities "新加坡" \
  --keywords "新加坡找对象" "新加坡相亲" "新加坡脱单" \
  --max-notes 20 \
  --max-comments 10
```

---

## 🎯 现在的完整工作流

### 1. 更新Cookie（首次或过期时）
```bash
python3 scripts/setup_cookie_manager.py save --cookie "你的新cookie"
```

### 2. 爬取数据
```bash
# 新加坡数据
python3 scripts/smart_crawler_decoupled.py \
  --mode custom \
  --cities "新加坡" \
  --keywords "新加坡找对象" "新加坡相亲" "新加坡脱单"
```

### 3. 导入数据到FindIt
```bash
python3 scripts/import_mediacrawler.py
```

### 4. 生成匹配报告
```bash
# 使用脚本自动匹配
python3 scripts/singapore_match.py
```

---

## 📊 Cookie管理器功能

### 检查状态
```bash
python3 scripts/setup_cookie_manager.py status
```

输出：
```
📊 Cookie状态检查
==================================================
FindIt cookie文件: ✅
环境变量 (XHS_COOKIE): ✅
MediaCrawler配置: ✅
最后更新: 2026-04-10T22:30:00
来源: browser_export
==================================================
```

### 保存Cookie
```bash
# 从字符串保存
python3 scripts/setup_cookie_manager.py save --cookie "gid=...;a1=..." --source "manual"

# 从环境变量保存
export XHS_COOKIE="gid=...;a1=..."
python3 scripts/setup_cookie_manager.py save
```

### 更新MediaCrawler配置
```bash
# 自动同步cookie到MediaCrawler
python3 scripts/setup_cookie_manager.py update
```

---

## 🔧 获取Cookie的方法

### 方法1：浏览器开发者工具（推荐）
1. 打开Chrome/Edge
2. 访问小红书并登录
3. F12 → Application → Cookies → https://www.xiaohongshu.com
4. 复制所有cookie值
5. 重点关注：`a1`, `webId`, `web_session`

### 方法2：浏览器插件
- 使用Cookie导出插件
- 格式：Netscape HTTP Cookie File
- 转换为字符串格式

### 方法3：MediaCrawler自动获取
```bash
cd ~/Desktop/MediaCrawler
python main.py --platform xhs --lt qrcode
# 扫码登录后，cookie会自动保存到browser_data
```

---

## ⚠️ 常见问题

### Q: Cookie多久过期一次？
A:
- **登录cookie** (`web_session`): 几小时到几天
- **设备cookie** (`a1`, `webId`): 几周到几个月
- **建议**: 每周检查一次，出现"登录已过期"时更新

### Q: 链接还是打不开怎么办？
A: 检查数据库迁移是否成功：
```bash
python3 -c "from findit.db import Database; db = Database(); print('✅ homepage_url字段存在' if 'homepage_url' in [c[1] for c in db._conn().__execute('PRAGMA table_info(authors)').fetchall()] else '❌ 需要运行迁移')"
```

### Q: 爬虫还是提示"登录已过期"？
A:
1. 检查cookie是否最新
2. 尝试重新获取cookie
3. 检查网络连接
4. 查看MediaCrawler日志

---

## 🎉 总结

现在你有两个独立的问题解决方案：

1. **链接问题**：数据库已迁移，所有匹配使用用户主页链接
2. **Cookie问题**：独立管理器，多种来源，自动更新

可以正常使用了！🚀
