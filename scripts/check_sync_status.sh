#!/bin/bash
# 检查同步状态和数据质量

FINDIT_DIR="$HOME/Desktop/findit"
LOG_FILE="$FINDIT_DIR/logs/sync.log"

echo "========================================"
echo "📊 FindIt 数据同步状态"
echo "========================================"

# 最新同步时间
if [ -f "$LOG_FILE" ]; then
    echo "🕐 最新同步: $(tail -5 "$LOG_FILE" | grep "同步完成" | tail -1 | cut -d']' -f1 | cut -d'[' -f2)"
else
    echo "⚠️  暂无同步日志"
fi

# 数据库统计
echo ""
echo "========================================"
echo "📈 数据库统计"
echo "========================================"
python3 -c "
from findit.db import Database
import sqlite3
from datetime import datetime, timedelta

db = Database()
with db._conn() as conn:
    # 总体统计
    total = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    authors = conn.execute('SELECT COUNT(*) FROM authors').fetchone()[0]
    comments = conn.execute('SELECT COUNT(*) FROM posts WHERE source_type=\"comment\"').fetchone()[0]
    with_tags = conn.execute('SELECT COUNT(*) FROM posts WHERE ai_tags IS NOT NULL').fetchone()[0]
    with_url = conn.execute('SELECT COUNT(*) FROM posts WHERE post_url IS NOT NULL').fetchone()[0]

    print(f'📝 总帖子: {total}')
    print(f'👥 总作者: {authors}')
    print(f'💬 评论数: {comments}')
    print(f'🏷️  已提取标签: {with_tags}')
    print(f'🔗 有链接: {with_url} ({with_url/total*100:.1f}%)' if total > 0 else '🔗 有链接: 0')

    # 最新数据
    print('')
    print('🕒 最新数据:')
    latest = conn.execute('''
        SELECT crawled_at, source_type
        FROM posts
        ORDER BY crawled_at DESC
        LIMIT 1
    ''').fetchone()
    if latest:
        print(f'   抓取时间: {latest[0]}')
        print(f'   数据类型: {latest[1]}')
    else:
        print('   暂无数据')

    # 地理分布
    print('')
    print('🌍 地理分布 (前5):')
    locations = conn.execute('''
        SELECT ip_location, COUNT(*) as count
        FROM authors
        WHERE ip_location IS NOT NULL AND ip_location != ''
        GROUP BY ip_location
        ORDER BY count DESC
        LIMIT 5
    ''').fetchall()

    for loc, count in locations:
        print(f'   {loc}: {count}个')

    # 最近7天的数据增长
    print('')
    print('📅 最近7天数据增长:')
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    recent = conn.execute('''
        SELECT COUNT(*) FROM posts WHERE crawled_at > ?
    ''', (week_ago,)).fetchone()[0]
    print(f'   新增帖子: {recent}')
"

# 磁盘使用
echo ""
echo "========================================"
echo "💾 磁盘使用"
echo "========================================"
if [ -d "$FINDIT_DIR/data" ]; then
    du -sh "$FINDIT_DIR/data/" 2>/dev/null
else
    echo "数据目录不存在"
fi

# 检查链接完整性
echo ""
echo "========================================"
echo "🔗 链接完整性检查"
echo "========================================"
python3 -c "
from findit.db import Database
db = Database()
with db._conn() as conn:
    total = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    with_url = conn.execute('SELECT COUNT(*) FROM posts WHERE post_url IS NOT NULL').fetchone()[0]

    if total > 0:
        percentage = (with_url/total)*100
        print(f'帖子总数: {total}')
        print(f'有链接: {with_url} ({percentage:.1f}%)')

        # 显示几个样本链接
        print('')
        print('📎 链接样本:')
        samples = conn.execute('''
            SELECT post_url, source_type
            FROM posts
            WHERE post_url IS NOT NULL
            ORDER BY crawled_at DESC
            LIMIT 3
        ''').fetchall()

        for i, (url, type_) in enumerate(samples, 1):
            print(f'   {i}. [{type_}] {url[:60]}...')
    else:
        print('暂无数据')
"

# 服务器状态检查
echo ""
echo "========================================"
echo "🖥️  服务器状态"
echo "========================================"

# 从同步脚本中提取服务器配置 (需要用户配置)
SYNC_SCRIPT="$FINDIT_DIR/scripts/sync_from_server.sh"
if [ -f "$SYNC_SCRIPT" ]; then
    SERVER_USER=$(grep "SERVER_USER=" "$SYNC_SCRIPT" | cut -d'=' -f2 | tr -d '"')
    SERVER_IP=$(grep "SERVER_IP=" "$SYNC_SCRIPT" | cut -d'=' -f2 | tr -d '"')

    if [ "$SERVER_USER" != "your_username" ] && [ "$SERVER_IP" != "your_japan_server_ip" ]; then
        echo "服务器配置: $SERVER_USER@$SERVER_IP"

        # 测试连接
        if ssh -o ConnectTimeout=5 -o BatchMode=yes "$SERVER_USER@$SERVER_IP" "echo '连接成功'" 2>/dev/null; then
            echo "✅ SSH 连接: 正常"

            # 检查服务器上的数据
            REMOTE_DIR=$(grep "REMOTE_DIR=" "$SYNC_SCRIPT" | cut -d'=' -f2 | tr -d '"')
            REMOTE_FILES=$(ssh "$SERVER_USER@$SERVER_IP" "ls -1 $REMOTE_DIR/*.jsonl 2>/dev/null | wc -l" 2>/dev/null || echo "0")
            echo "📁 服务器数据文件: $REMOTE_FILES"
        else
            echo "❌ SSH 连接: 失败 (请检查密钥配置)"
        fi
    else
        echo "⚠️  请先配置服务器信息: $SYNC_SCRIPT"
    fi
else
    echo "⚠️  同步脚本不存在: $SYNC_SCRIPT"
fi

echo ""
echo "========================================"
echo "💡 提示"
echo "========================================"
echo "手动同步: bash $FINDIT_DIR/scripts/sync_from_server.sh"
echo "查看日志: tail -f $LOG_FILE"
echo "========================================"