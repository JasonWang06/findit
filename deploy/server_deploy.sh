#!/bin/bash
# 一键部署 MediaCrawler 到服务器
# 使用方法: ./deploy/server_deploy.sh user@server_ip

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SERVER=$1

if [ -z "$SERVER" ]; then
    echo -e "${RED}错误: 请提供服务器地址${NC}"
    echo "使用方法: $0 user@server_ip"
    exit 1
fi

echo -e "${GREEN}🚀 开始部署 MediaCrawler 到 $SERVER${NC}"

# 创建临时目录
TEMP_DIR=$(mktemp -d)
echo "📁 临时目录: $TEMP_DIR"

# 创建部署文件
cat > "$TEMP_DIR/deploy.sh" << 'DEPLOY_EOF'
#!/bin/bash
set -e

echo "🔧 系统更新中..."
sudo apt update && sudo apt upgrade -y

echo "📦 安装基础工具..."
sudo apt install -y git python3 python3-pip python3-venv chromium-browser

echo "📥 克隆 MediaCrawler..."
if [ -d "MediaCrawler" ]; then
    echo "MediaCrawler 已存在，更新中..."
    cd MediaCrawler
    git pull
else
    git clone https://github.com/NanmiCoder/MediaCrawler.git
    cd MediaCrawler
fi

echo "🐍 创建虚拟环境..."
python3 -m venv venv
source venv/bin/activate

echo "📚 安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt

echo "📁 创建工作目录..."
mkdir -p ~/mediacrawler/logs
mkdir -p ~/mediacrawler/output

echo "📝 创建爬虫脚本..."
cat > ~/mediacrawler/run_crawler.sh << 'EOF'
#!/bin/bash
LOG_DIR="~/mediacrawler/logs"
DATA_DIR="~/mediacrawler/output"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"

cd ~/MediaCrawler
source venv/bin/activate

echo "[$(date)] 开始爬取..." >> "$LOG_DIR/crawler_$TIMESTAMP.log"
python main.py --platform xhs --lt cookie --type search \
    --keywords "深圳找对象,深圳相亲,深圳搭子,北京找对象,上海相亲" \
    >> "$LOG_DIR/crawler_$TIMESTAMP.log" 2>&1

if [ $? -eq 0 ]; then
    echo "[$(date)] 爬取完成" >> "$LOG_DIR/crawler_$TIMESTAMP.log"
    cp -r data/xhs/jsonl/* "$DATA_DIR/" 2>/dev/null || true
    echo "数据文件:" $(ls -1 "$DATA_DIR" | wc -l) >> "$LOG_DIR/crawler_$TIMESTAMP.log"
else
    echo "[$(date)] 爬取失败" >> "$LOG_DIR/crawler_$TIMESTAMP.log"
fi

echo "[$(date)] 脚本执行完毕" >> "$LOG_DIR/crawler_$TIMESTAMP.log"
EOF

chmod +x ~/mediacrawler/run_crawler.sh

echo "📝 创建监控脚本..."
cat > ~/mediacrawler/monitor.sh << 'EOF'
#!/bin/bash
LOG_DIR="~/mediacrawler/logs"
LAST_LOG=$(ls -t "$LOG_DIR"/*.log 2>/dev/null | head -1)

if [ -n "$LAST_LOG" ]; then
    echo "=== 最新爬虫日志 ==="
    tail -10 "$LAST_LOG"
else
    echo "暂无日志文件"
fi

echo ""
echo "=== 数据统计 ==="
echo "JSONL 文件数: $(ls -1 ~/mediacrawler/output/*.jsonl 2>/dev/null | wc -l)"
echo "日志文件数: $(ls -1 "$LOG_DIR"/*.log 2>/dev/null | wc -l)"

echo ""
echo "=== 磁盘使用 ==="
du -sh ~/mediacrawler/ 2>/dev/null || echo "目录不存在"
EOF

chmod +x ~/mediacrawler/monitor.sh

echo "⏰ 设置定时任务..."
# 移除旧的定时任务
crontab -l 2>/dev/null | grep -v "mediacrawler" | crontab -

# 添加新的定时任务
(crontab -l 2>/dev/null; echo "# MediaCrawler 自动化任务") | crontab -
(crontab -l 2>/dev/null; echo "0 8,20 * * * /bin/bash ~/mediacrawler/run_crawler.sh") | crontab -

echo "✅ 部署完成！"
echo ""
echo "📝 下一步操作："
echo "   1. 配置 Cookie:"
echo "      nano ~/MediaCrawler/config/base_config.py"
echo "      修改 COOKIES 和 KEYWORDS 变量"
echo ""
echo "   2. 手动测试:"
echo "      bash ~/mediacrawler/run_crawler.sh"
echo ""
echo "   3. 查看日志:"
echo "      tail -f ~/mediacrawler/logs/*.log"
echo ""
echo "   4. 查看定时任务:"
echo "      crontab -l"
echo ""
echo "   5. 监控状态:"
echo "      bash ~/mediacrawler/monitor.sh"
DEPLOY_EOF

# 复制部署脚本到服务器
echo "📤 上传部署脚本到服务器..."
scp "$TEMP_DIR/deploy.sh" "$SERVER:~/deploy.sh"

# 在服务器上执行部署
echo "🔧 在服务器上执行部署..."
ssh "$SERVER" "bash ~/deploy.sh"

# 清理临时文件
rm -rf "$TEMP_DIR"

echo ""
echo -e "${GREEN}🎉 部署完成！${NC}"
echo ""
echo "📖 后续步骤:"
echo "   1. SSH 连接到服务器配置 Cookie:"
echo "      ssh $SERVER"
echo "      nano ~/MediaCrawler/config/base_config.py"
echo ""
echo "   2. 测试爬虫:"
echo "      ssh $SERVER 'bash ~/mediacrawler/run_crawler.sh'"
echo ""
echo "   3. 设置本地数据同步 (参见 deploy/LOCAL_SYNC.md)"