# 小红书爬虫服务器部署方案分析

## 现实情况

小红书**没有公开API**，所有数据获取都需要：
1. 破解签名算法（复杂，容易失效）
2. 使用浏览器模拟（稳定但资源消耗大）
3. 使用现成工具如MediaCrawler（需要维护Cookie）

## 方案对比

### 方案1：Playwright/Selenium（浏览器渲染）

**优点：**
- ✅ 最稳定，不容易被封
- ✅ 不需要破解签名
- ✅ 可以处理JavaScript渲染的页面
- ✅ MediaCrawler也是基于Playwright

**缺点：**
- ❌ 内存占用大（~200-500MB）
- ❌ 速度慢
- ❌ 服务器需要安装浏览器

**服务器部署：**
```bash
# 安装依赖
apt-get install chromium-browser
pip install playwright
playwright install chromium

# 运行（无头模式）
python3 crawler.py --headless
```

**适用场景：**
- 中小规模爬取（每天<1000条）
- 有足够内存的服务器（>=2GB）
- 需要稳定性

### 方案2：MediaCrawler（推荐）

**优点：**
- ✅ 已经实现了签名破解
- ✅ 有Cookie管理机制
- ✅ 支持并发爬取
- ✅ 社区维护，持续更新

**缺点：**
- ⚠️ 需要定期更新Cookie
- ⚠️ 可能因小红书更新而失效

**服务器部署：**
```bash
# 1. 克隆MediaCrawler
git clone https://github.com/NanmiCoder/MediaCrawler
cd MediaCrawler

# 2. 配置Cookie
# 方式A: 手动获取（浏览器F12）
# 方式B: 使用自动登录脚本

# 3. 运行
python3 main.py --platform xhs --lt cookie --type search --keywords "深圳找对象"
```

### 方案3：混合方案（最实用）

**本地开发：**
```bash
# 使用Playwright有头模式，方便调试
python3 crawler.py --headless=false
```

**服务器部署：**
```bash
# 使用MediaCrawler + 定时任务
# 或者用Playwright无头模式
python3 crawler.py --headless --concurrent=3
```

## 服务器资源需求

### 小规模（每天100-500条）
- CPU: 1核
- 内存: 1GB
- 方案: Playwright无头模式或MediaCrawler

### 中规模（每天500-2000条）
- CPU: 2核
- 内存: 2GB
- 方案: MediaCrawler + 并发控制

### 大规模（每天>2000条）
- CPU: 4核+
- 内存: 4GB+
- 方案: 分布式部署，代理IP池

## 我的建议

### 短期（MVP阶段）
**直接用MediaCrawler，不要重复造轮子**

```python
# scripts/crawl_with_mediacrawler.py
import subprocess

def crawl_keywords(keywords):
    for keyword in keywords:
        cmd = [
            "python3", "main.py",
            "--platform", "xhs",
            "--lt", "cookie",
            "--type", "search",
            "--keywords", keyword,
            "--max_notes", "20"
        ]
        subprocess.run(cmd, cwd="~/Desktop/MediaCrawler")
```

**优点：**
- 立即可用
- 有人维护
- 功能完善

**缺点：**
- 依赖外部项目
- Cookie需要手动更新

### 长期（稳定运行后）
**自己实现轻量级爬虫**

基于对MediaCrawler的研究，提取核心逻辑：
1. Playwright无头浏览器
2. Cookie自动管理
3. 简单的反爬策略

**优点：**
- 完全可控
- 可以针对需求优化
- 轻量级

## 反爬对策

无论哪个方案，都需要：

1. **限流**
   ```python
   await asyncio.sleep(random.uniform(2, 5))  # 随机延迟
   ```

2. **请求间隔**
   ```python
   # 每分钟最多20次请求
   rate_limit = 20/60
   ```

3. **User-Agent轮换**
   ```python
   user_agents = [
       "Mozilla/5.0 ...",
       "Mozilla/5.0 ...",
   ]
   ```

4. **代理IP**（大规模）
   ```python
   # 使用代理IP池
   browser = await p.chromium.launch(
       proxy={"server": "http://proxy.example.com:8080"}
   )
   ```

## 快速启动方案

**现在就开始爬取：**

1. 本地用MediaCrawler测试（今天）
2. 搞到Cookie，能成功爬取数据（今天）
3. 部署到服务器，用crontab定时（明天）

**Cookie获取方式：**
- 方式A: 浏览器登录，F12复制Cookie
- 方式B: 使用MediaCrawler的自动登录
- 方式C: 手机抓包（复杂，不推荐）

## 结论

**小红书确实没有简单可用的API，最实用的方案是：**

1. **开发阶段：** MediaCrawler（本地）
2. **生产阶段：** MediaCrawler + Playwright无头模式（服务器）

**不要尝试自己破解签名算法**，投入产出比太低，而且容易被反爬。
