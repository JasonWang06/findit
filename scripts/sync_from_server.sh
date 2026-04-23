#!/bin/bash
# 从服务器同步 MediaCrawler 数据并导入到 FindIt

# 服务器配置 - 请修改为您的实际服务器信息
SERVER_USER="your_username"
SERVER_IP="your_japan_server_ip"
REMOTE_DIR="~/mediacrawler/output"

# 本地配置
LOCAL_MEDIA_DIR="$HOME/Desktop/MediaCrawler/data/xhs/jsonl"
FINDIT_DIR="$HOME/Desktop/findit"

# 日志
LOG_FILE="$FINDIT_DIR/logs/sync.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 创建目录
mkdir -p "$LOCAL_MEDIA_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

echo "========================================" | tee -a "$LOG_FILE"
echo "[$(date)] 开始数据同步..." | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# 1. 从服务器拉取最新数据
echo "[$(date)] 从服务器 $SERVER_USER@$SERVER_IP 拉取数据..." | tee -a "$LOG_FILE"
scp -r "$SERVER_USER@$SERVER_IP:$REMOTE_DIR"/* "$LOCAL_MEDIA_DIR/" 2>&1 | tee -a "$LOG_FILE"

# 检查是否成功
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "[$(date)] ✅ 数据拉取成功" | tee -a "$LOG_FILE"

    # 2. 统计文件数量
    FILE_COUNT=$(ls -1 "$LOCAL_MEDIA_DIR"/*.jsonl 2>/dev/null | wc -l | tr -d ' ')
    echo "[$(date)] 当前有 $FILE_COUNT 个 JSONL 文件" | tee -a "$LOG_FILE"

    # 3. 导入到 FindIt 数据库
    echo "[$(date)] 开始导入数据到 FindIT..." | tee -a "$LOG_FILE"
    cd "$FINDIT_DIR"

    # 导入数据
    python3 scripts/import_mediacrawler.py "$LOCAL_MEDIA_DIR" 2>&1 | tee -a "$LOG_FILE"

    # 4. 显示数据统计
    echo "[$(date)] 📊 数据库统计:" | tee -a "$LOG_FILE"
    python3 -c "
from findit.db import Database
db = Database()
with db._conn() as conn:
    total = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    authors = conn.execute('SELECT COUNT(*) FROM authors').fetchone()[0]
    comments = conn.execute('SELECT COUNT(*) FROM posts WHERE source_type=\"comment\"').fetchone()[0]
    with_url = conn.execute('SELECT COUNT(*) FROM posts WHERE post_url IS NOT NULL').fetchone()[0]
    print(f'总帖子: {total}')
    print(f'总作者: {authors}')
    print(f'评论数: {comments}')
    print(f'有链接: {with_url} ({with_url/total*100:.1f}%)')
" 2>&1 | tee -a "$LOG_FILE"

    # 5. 检查是否配置了 API Key，如果有则运行标签提取
    if [ -f ".env" ] && grep -q "ANTHROPIC_API_KEY=" .env && ! grep -q "ANTHROPIC_API_KEY=$" .env; then
        echo "[$(date)] 🤖 检测到 API Key，开始 AI 标签提取..." | tee -a "$LOG_FILE"
        python3 scripts/extract_tags.py --limit 5 2>&1 | tee -a "$LOG_FILE"
    else
        echo "[$(date)] ℹ️  未配置 API Key，跳过 AI 标签提取" | tee -a "$LOG_FILE"
    fi

    echo "[$(date)] 🎉 同步完成！" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
else
    echo "[$(date)] ❌ 数据拉取失败" | tee -a "$LOG_FILE"
    echo "[$(date)] 请检查:" | tee -a "$LOG_FILE"
    echo "   1. 服务器是否在线: ssh $SERVER_USER@$SERVER_IP" | tee -a "$LOG_FILE"
    echo "   2. 服务器路径是否存在: ssh $SERVER_USER@$SERVER_IP 'ls -la $REMOTE_DIR'" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"
    exit 1
fi