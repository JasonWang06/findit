# 🚀 FindIt 服务器自动化部署指南

## 📋 部署概览

**目标**: 在日本服务器上部署自动化爬虫，定期抓取小红书交友数据
**优势**: 低延迟、稳定运行、自动化维护
**技术栈**: Docker + systemd + crontab + MediaCrawler

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────┐
│              日本服务器 (Ubuntu/Debian)               │
├─────────────��───────────────────────────────────────┤
│  Docker Container                                    │
│  ├── MediaCrawler (爬虫)                             │
│  ├── Python 3.12 + 依赖                              │
│  └── Chrome/Chromium (浏览器)                         │
├─────────────────────────────────────────────────────┤
│  自动化调度                                           │
│  ├── systemd (服务管理)                              │
│  ├── crontab (定时任务)                              │
│  └── logrotate (日志管理)                            │
├─────────────────────────────────────────────────────┤
│  数据同步                                             │
│  ├── SSH/SCP (文件传输)                              │
│  ├── rsync (增量同步)                                │
│  └── SQLite + GitHub (备份)                          │
└─────────────────────────────────────────────────────┘
           ↓ 定期同步
┌─────────────────────────────────────────────────────┐
│         本地机器 (开发 + AI 分析)                    │
│  ├── FindIt 数据库                                   │
│  ├── AI 标签提取                                     │
│  └── 匹配推荐系统                                     │
└─────────────────────────────────────────────────────┘
```

## 📦 部署步骤

### 第一步：服务器环境准备

```bash
# 1. SSH 连接到日本服务器
ssh your_user@your_japan_server_ip

# 2. 更新系统
sudo apt update && sudo apt upgrade -y

# 3. 安装基础工具
sudo apt install -y git python3 python3-pip docker.io docker-compose

# 4. 安装 Chrome (MediaCrawler 需要)
sudo apt install -y chromium-browser

# 5. 创建工作目录
mkdir -p ~/mediacrawler
cd ~/mediacrawler
```

### 第二步：部署 MediaCrawler

```bash
# 1. 克隆 MediaCrawler
git clone https://github.com/NanmiCoder/MediaCrawler.git
cd MediaCrawler

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 Cookie (只需要配置一次)
# 编辑 config/base_config.py 或使用环境变量
nano config/base_config.py

# 设置搜索关键词
KEYWORDS = "深圳找对象,深圳相亲,深圳搭子,北京找对象,上海相亲"
```

### 第三步：创建自动化脚本

创建 `~/mediacrawler/run_crawler.sh`:

```bash
#!/bin/bash
# 自动化爬虫脚本

LOG_DIR="~/mediacrawler/logs"
DATA_DIR="~/mediacrawler/output"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 创建目录
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"

# 进入项目目录
cd ~/mediacrawler/MediaCrawler
source venv/bin/activate

# 运行爬虫 (搜索模式)
echo "[$(date)] 开始爬取..." >> "$LOG_DIR/crawler_$TIMESTAMP.log"
python main.py --platform xhs --lt cookie --type search \
    --keywords "深圳找对象,深圳相亲,深圳搭子" \
    >> "$LOG_DIR/crawler_$TIMESTAMP.log" 2>&1

# 检查是否成功
if [ $? -eq 0 ]; then
    echo "[$(date)] 爬取完成" >> "$LOG_DIR/crawler_$TIMESTAMP.log"
    
    # 复制最新数据到输出目录
    cp -r data/xhs/jsonl/* "$DATA_DIR/"
    
    # 记录统计信息
    echo "数据文件:" $(ls -1 "$DATA_DIR" | wc -l) >> "$LOG_DIR/crawler_$TIMESTAMP.log"
else
    echo "[$(date)] 爬取失败" >> "$LOG_DIR/crawler_$TIMESTAMP.log"
fi

echo "[$(date)] 脚本执行完毕" >> "$LOG_DIR/crawler_$TIMESTAMP.log"
```

### 第四步：设置定时任务

```bash
# 编辑 crontab
crontab -e

# 添加定时任务 (每天早上8点和晚上8点执行)
0 8 * * * /bin/bash ~/mediacrawler/run_crawler.sh
0 20 * * * /bin/bash ~/mediacrawler/run_crawler.sh

# 每小时执行一次 (测试用)
0 * * * * /bin/bash ~/mediacrawler/run_crawler.sh
```

### 第五步：创建 systemd 服务 (可选)

```bash
# 创建服务文件
sudo nano /etc/systemd/system/mediacrawler.service
```

```ini
[Unit]
Description=MediaCrawler Automated Service
After=network.target

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/home/your_username/mediacrawler/MediaCrawler
ExecStart=/home/your_username/mediacrawler/MediaCrawler/venv/bin/python main.py --platform xhs --lt cookie --type search --keywords "深圳找对象,深圳相亲,深圳搭子"
Environment="PATH=/home/your_username/mediacrawler/MediaCrawler/venv/bin"

[Install]
WantedBy=multi-user.target
```

```bash
# 创建定时器
sudo nano /etc/systemd/system/mediacrawler.timer
```

```ini
[Unit]
Description=MediaCrawler Timer
Requires=mediacrawler.service

[Timer]
OnCalendar=daily
OnCalendar=08:00
OnCalendar=20:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
# 启用服务
sudo systemctl enable mediacrawler.timer
sudo systemctl start mediacrawler.timer

# 查看状态
sudo systemctl status mediacrawler.timer
sudo systemctl list-timers
```

## 🔄 第六步：数据同步回本地

### 方案A: SSH/SCP 定期拉取

在本地机器创建 `~/sync_crawler_data.sh`:

```bash
#!/bin/bash
# 从服务器同步数据到本地

SERVER_USER="your_username"
SERVER_IP="your_japan_server_ip"
REMOTE_DIR="~/mediacrawler/output"
LOCAL_DIR="~/Desktop/MediaCrawler/data/xhs/jsonl"

# 创建本地目录
mkdir -p "$LOCAL_DIR"

# 同步数据
scp -r "$SERVER_USER@$SERVER_IP:$REMOTE_DIR/*" "$LOCAL_DIR/"

# 导入到 FindIt 数据库
cd ~/Desktop/findit
python3 scripts/import_mediacrawler.py ~/Desktop/MediaCrawler/data/xhs/jsonl

echo "数据同步完成: $(date)"
```

### 方案B: rsync 增量同步

```bash
#!/bin/bash
# 使用 rsync 增量同步 (更高效)

rsync -avz --progress \
    "$SERVER_USER@$SERVER_IP:~/mediacrawler/output/" \
    "~/Desktop/MediaCrawler/data/xhs/jsonl/"
```

### 方案C: 服务器自动推送

在服务器上创建 `~/mediacrawler/sync_to_local.sh`:

```bash
#!/bin/bash
# 爬取完成后自动推送到本地

LOCAL_USER="your_local_username"
LOCAL_IP="your_local_machine_ip"
LOCAL_DIR="~/Desktop/MediaCrawler/data/xhs/jsonl"

# 推送数据到本地机器
scp -r ~/mediacrawler/output/* \
    "$LOCAL_USER@$LOCAL_IP:$LOCAL_DIR/"
```

## 📊 第七步：监控和日志

### 日志轮转配置

```bash
# 在服务器上配置 logrotate
sudo nano /etc/logrotate.d/mediacrawler
```

```
/home/your_username/mediacrawler/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### 监控脚本

创建 `~/mediacrawler/monitor.sh`:

```bash
#!/bin/bash
# 监控爬虫状态

LOG_DIR="~/mediacrawler/logs"
LAST_LOG=$(ls -t "$LOG_DIR"/*.log | head -1)

echo "=== 最新爬虫日志 ==="
tail -20 "$LAST_LOG"

echo ""
echo "=== 数据统计 ==="
echo "JSONL 文件数: $(ls -1 ~/mediacrawler/output/*.jsonl 2>/dev/null | wc -l)"
echo "日志文件数: $(ls -1 "$LOG_DIR"/*.log 2>/dev/null | wc -l)"

echo ""
echo "=== 磁盘使用 ==="
du -sh ~/mediacrawler/
```

## 🔧 第八步：故障恢复

### Cookie 自动更新

创建 `~/mediacrawler/check_cookie.sh`:

```bash
#!/bin/bash
# 检查 Cookie 是否有效，如果无效则发送通知

cd ~/mediacrawler/MediaCrawler
source venv/bin/activate

# 测试爬虫
timeout 30 python main.py --platform xhs --lt cookie --type search --keywords "测试" > /tmp/test_crawl.log 2>&1

# 检查是否成功
if grep -q "error\|Error\|ERROR" /tmp/test_crawl.log; then
    echo "Cookie 可能失效，需要更新"
    # 发送通知 (可以集成 Telegram/邮件)
else
    echo "Cookie 正常"
fi
```

### 自动重启机制

```bash
# 在 crontab 中添加监控任务
*/30 * * * * /bin/bash ~/mediacrawler/check_cookie.sh
```

## 🚀 快速部署命令

```bash
# 一键部署脚本
cat > deploy.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 开始部署 MediaCrawler 到服务器..."

# 1. 环境准备
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-pip chromium-browser

# 2. 克隆项目
git clone https://github.com/NanmiCoder/MediaCrawler.git
cd MediaCrawler
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 创建脚本
cat > ~/mediacrawler/run_crawler.sh << 'SCRIPT'
#!/bin/bash
cd ~/mediacrawler/MediaCrawler
source venv/bin/activate
python main.py --platform xhs --lt cookie --type search --keywords "深圳找对象,深圳相亲,深圳搭子"
SCRIPT

chmod +x ~/mediacrawler/run_crawler.sh

# 4. 设置定时任务
(crontab -l 2>/dev/null; echo "0 8,20 * * * /bin/bash ~/mediacrawler/run_crawler.sh") | crontab -

echo "✅ 部署完成！"
echo "📝 下一步："
echo "   1. 配置 Cookie: nano ~/mediacrawler/MediaCrawler/config/base_config.py"
echo "   2. 手动测试: bash ~/mediacrawler/run_crawler.sh"
echo "   3. 查看日志: tail -f ~/mediacrawler/logs/*.log"
EOF

chmod +x deploy.sh
```

## 📱 本地自动化 (可选)

### 创建本地自动同步和导入服务

在本地创建 `~/Desktop/findit/scripts/auto_sync_import.sh`:

```bash
#!/bin/bash
# 自动同步服务器数据并导入到 FindIt

SERVER="your_user@your_japan_server"
REMOTE_DIR="~/mediacrawler/output"
LOCAL_DIR="~/Desktop/MediaCrawler/data/xhs/jsonl"
FINDIT_DIR="~/Desktop/findit"

echo "[$(date)] 开始同步数据..."

# 1. 从服务器拉取最新数据
scp -r "$SERVER:$REMOTE_DIR/*" "$LOCAL_DIR/"

# 2. 导入到 FindIt 数据库
cd "$FINDIT_DIR"
python3 scripts/import_mediacrawler.py "$LOCAL_DIR"

# 3. 运行 AI 标签提取
# python3 scripts/extract_tags.py --limit 20

echo "[$(date)] 同步和导入完成"
```

设置本地定时任务：
```bash
# 编辑本地 crontab
crontab -e

# 每天早上9点和晚上9点自动同步
0 9,21 * * * /bin/bash ~/Desktop/findit/scripts/auto_sync_import.sh
```

## 🎯 部署检查清单

### 服务器端
- [ ] 基础环境安装 (Python, Chrome, Git)
- [ ] MediaCrawler 部署
- [ ] Cookie 配置
- [ ] 自动化脚本创建
- [ ] 定时任务设置
- [ ] 日志目录创建
- [ ] 权限设置正确

### 本地端
- [ ] 数据同步脚本
- [ ] 自动导入脚本
- [ ] 定时同步设置
- [ ] 数据库备份策略

### 监控
- [ ] 日志轮转配置
- [ ] Cookie 健康检查
- [ ] 磁盘空间监控
- [ ] 异常通知机制

---

**预期效果**：部署完成后，服务器将自动每天2次抓取最新数据，您只需要在本地运行数据同步和AI分析即可。