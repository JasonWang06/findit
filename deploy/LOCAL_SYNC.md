# 🔄 本地数据同步自动化配置

## 📋 概述

自动从日本服务器同步爬虫数据到本地，并导入到 FindIt 数据库。

## 🔧 第一步：配置 SSH 免密登录

```bash
# 1. 在本地生成 SSH 密钥对 (如果还没有)
ssh-keygen -t rsa -b 4096

# 2. 复制公钥到服务器
ssh-copy-id user@your_japan_server_ip

# 3. 测试免密登录
ssh user@your_japan_server_ip
```

## 📤 第二步：创建数据同步脚本

创建 `scripts/sync_from_server.sh`:

```bash
#!/bin/bash
# 从服务器同步 MediaCrawler 数据并导入到 FindIt

# 服务器配置
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

echo "[$(date)] 开始数据同步..." | tee -a "$LOG_FILE"

# 1. 从服务器拉取最新数据
echo "[$(date)] 从服务器拉取数据..." | tee -a "$LOG_FILE"
scp -r "$SERVER_USER@$SERVER_IP:$REMOTE_DIR"/* "$LOCAL_MEDIA_DIR/" 2>&1 | tee -a "$LOG_FILE"

# 检查是否成功
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "[$(date)] 数据拉取成功" | tee -a "$LOG_FILE"
    
    # 2. 统计新文件数量
    FILE_COUNT=$(ls -1 "$LOCAL_MEDIA_DIR"/*.jsonl 2>/dev/null | wc -l)
    echo "[$(date)] 当前有 $FILE_COUNT 个 JSONL 文件" | tee -a "$LOG_FILE"
    
    # 3. 导入到 FindIt 数据库
    echo "[$(date)] 开始导入数据到 FindIt..." | tee -a "$LOG_FILE"
    cd "$FINDIT_DIR"
    
    # 检查 API key
    if [ -f ".env" ] && grep -q "ANTHROPIC_API_KEY" .env; then
        echo "[$(date)] 配置了 API Key，将同时运行标签提取" | tee -a "$LOG_FILE"
        
        # 导入数据 + AI 标签提取
        python3 scripts/import_mediacrawler.py "$LOCAL_MEDIA_DIR" 2>&1 | tee -a "$LOG_FILE"
        python3 scripts/extract_tags.py --limit 10 2>&1 | tee -a "$LOG_FILE"
    else
        echo "[$(date)] 未配置 API Key，仅导入数据" | tee -a "$LOG_FILE"
        python3 scripts/import_mediacrawler.py "$LOCAL_MEDIA_DIR" 2>&1 | tee -a "$LOG_FILE"
    fi
    
    # 4. 显示数据统计
    echo "[$(date)] 数据库统计:" | tee -a "$LOG_FILE"
    python3 -c "
from findit.db import Database
db = Database()
with db._conn() as conn:
    total = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    comments = conn.execute('SELECT COUNT(*) FROM posts WHERE source_type=\"comment\"').fetchone()[0]
    print(f'总帖子: {total}, 评论: {comments}')
" 2>&1 | tee -a "$LOG_FILE"
    
    echo "[$(date)] 同步完成！" | tee -a "$LOG_FILE"
else
    echo "[$(date)] 数据拉取失败" | tee -a "$LOG_FILE"
    exit 1
fi
```

## ⏰ 第三步：设置本地定时任务

```bash
# 编辑本地 crontab
crontab -e

# 添加定时任务 (每天早上9点和晚上9点同步)
0 9,21 * * * /bin/bash /Users/json/Desktop/findit/scripts/sync_from_server.sh

# 或者每小时同步一次 (测试用)
0 * * * * /bin/bash /Users/json/Desktop/findit/scripts/sync_from_server.sh
```

## 🔍 第四步：创建监控脚本

创建 `scripts/check_sync_status.sh`:

```bash
#!/bin/bash
# 检查同步状态和数据质量

FINDIT_DIR="$HOME/Desktop/findit"
LOG_FILE="$FINDIT_DIR/logs/sync.log"

echo "=== 数据同步状态 ==="

# 最新同步时间
if [ -f "$LOG_FILE" ]; then
    echo "最新同步: $(tail -1 "$LOG_FILE" | cut -d']' -f1 | cut -d'[' -f2)"
else
    echo "暂无同步日志"
fi

# 数据库统计
echo ""
echo "=== 数据库统计 ==="
python3 -c "
from findit.db import Database
import sqlite3

db = Database()
with db._conn() as conn:
    # 总体统计
    total = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    authors = conn.execute('SELECT COUNT(*) FROM authors').fetchone()[0]
    comments = conn.execute('SELECT COUNT(*) FROM posts WHERE source_type=\"comment\"').fetchone()[0]
    with_tags = conn.execute('SELECT COUNT(*) FROM posts WHERE ai_tags IS NOT NULL').fetchone()[0]
    
    print(f'总帖子: {total}')
    print(f'总作者: {authors}')
    print(f'评论数: {comments}')
    print(f'已提取标签: {with_tags}')
    
    # 最新数据
    print('')
    print('=== 最新数据 ===')
    latest = conn.execute('''
        SELECT crawled_at, source_type 
        FROM posts 
        ORDER BY crawled_at DESC 
        LIMIT 1
    ''').fetchone()
    print(f'最新抓取: {latest[0]} ({latest[1]})')
    
    # 地理分布
    print('')
    print('=== 地理分布 (前5) ===')
    locations = conn.execute('''
        SELECT ip_location, COUNT(*) as count 
        FROM authors 
        WHERE ip_location IS NOT NULL AND ip_location != ''
        GROUP BY ip_location 
        ORDER BY count DESC 
        LIMIT 5
    ''').fetchall()
    
    for loc, count in locations:
        print(f'{loc}: {count}个')
"

# 磁盘使用
echo ""
echo "=== 磁盘使用 ==="
du -sh "$FINDIT_DIR/data/" 2>/dev/null

# 检查链接完整性
echo ""
echo "=== 链接完整性检查 ==="
python3 -c "
from findit.db import Database
db = Database()
with db._conn() as conn:
    total = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    with_url = conn.execute('SELECT COUNT(*) FROM posts WHERE post_url IS NOT NULL').fetchone()[0]
    print(f'帖子总数: {total}')
    print(f'有链接: {with_url} ({with_url/total*100:.1f}%)')
"
```

## 🚀 第五步：手动触发同步

```bash
# 立即执行一次同步
bash /Users/json/Desktop/findit/scripts/sync_from_server.sh

# 检查同步状态
bash /Users/json/Desktop/findit/scripts/check_sync_status.sh
```

## 📱 第六步：可选的自动通知

创建 `scripts/notify_sync_result.sh`:

```bash
#!/bin/bash
# 同步完成后发送通知 (需要安装 terminal-notifier)

# 安装 terminal-notifier
# brew install terminal-notifier

FINDIT_DIR="$HOME/Desktop/findit"
LOG_FILE="$FINDIT_DIR/logs/sync.log"

# 检查最新同步是否成功
if tail -1 "$LOG_FILE" | grep -q "同步完成"; then
    # 提取数据统计
    STATS=$(tail -20 "$LOG_FILE" | grep "总帖子\|总作者" | tr '\n' ' ')
    
    # 发送通知
    terminal-notifier -title "FindIt 数据同步" \
                      -message "✅ 同步成功\n$STATS" \
                      -sound default
else
    terminal-notifier -title "FindIt 数据同步" \
                      -message "❌ 同步失败，请检查日志" \
                      -sound Basso
fi
```

## 📊 数据验证示例

```bash
# 验证链接是否可访问
python3 << 'EOF'
from findit.db import Database

db = Database()
with db._conn() as conn:
    # 获取几个样本帖子的链接
    rows = conn.execute('''
        SELECT id, content, post_url, source_type 
        FROM posts 
        WHERE post_url IS NOT NULL 
        ORDER BY crawled_at DESC 
        LIMIT 5
    ''').fetchall()
    
    print("=== 帖子链接样本 ===")
    for i, row in enumerate(rows, 1):
        print(f"\n{i}. [{row['source_type']}] {row['id']}")
        print(f"   内容: {row['content'][:50]}...")
        print(f"   链接: {row['post_url']}")
        print(f"   可访问: {'✅' if row['post_url'].startswith('http') else '❌'}")
EOF
```

## 🎯 完整工作流

### 服务器端 (自动化)
1. 每天 8:00 和 20:00 自动运行爬虫
2. 数据保存到 `~/mediacrawler/output/`
3. 日志记录到 `~/mediacrawler/logs/`

### 本地端 (自动化)
1. 每天 9:00 和 21:00 自动同步服务器数据
2. 自动导入到 FindIt 数据库
3. (可选) 自动运行 AI 标签提取
4. 发送完成通知

### 手动操作
- 随时可以手动触发同步: `bash scripts/sync_from_server.sh`
- 检查同步状态: `bash scripts/check_sync_status.sh`
- 查看同步日志: `tail -f logs/sync.log`

## 🔧 故障排除

### SSH 连接问题
```bash
# 测试连接
ssh user@server_ip "echo '连接成功'"

# 检查密钥
ls -la ~/.ssh/id_rsa*

# 重新复制密钥
ssh-copy-id user@server_ip
```

### 路径问题
```bash
# 确认服务器上的路径
ssh user@server_ip "ls -la ~/mediacrawler/output/"

# 确认本地路径
ls -la ~/Desktop/MediaCrawler/data/xhs/jsonl/
```

### 权限问题
```bash
# 确保脚本可执行
chmod +x scripts/*.sh

# 确保数据库可写
chmod +w data/findit.db
```

---

**预期效果**: 设置完成后，整个流程完全自动化，服务器定期爬取，本地自动同步和处理，无需人工干预。