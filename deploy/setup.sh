#!/bin/bash
# FindIt 一键部署脚本（Ubuntu/Debian）
# 用法: bash deploy/setup.sh
set -e

echo "========================================="
echo "  FindIt 部署脚本"
echo "========================================="

# 1. 安装系统依赖
echo ""
echo "[1/5] 安装系统依赖..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv git

# 2. 创建项目目录和用户
echo "[2/5] 设置项目目录..."
PROJECT_DIR="/opt/findit"
sudo mkdir -p "$PROJECT_DIR"
sudo chown "$USER:$USER" "$PROJECT_DIR"

# 3. 克隆代码（如果还没有的话）
if [ ! -f "$PROJECT_DIR/pyproject.toml" ]; then
    echo "[3/5] 克隆代码..."
    # 如果当前目录就是项目，直接复制
    if [ -f "pyproject.toml" ]; then
        cp -r . "$PROJECT_DIR/"
    else
        echo "请先把代码放到 $PROJECT_DIR 目录下"
        exit 1
    fi
else
    echo "[3/5] 代码已存在，跳过克隆"
fi

cd "$PROJECT_DIR"

# 4. 创建虚拟环境并安装
echo "[4/5] 安装 Python 依赖..."
python3 -m venv venv
source venv/bin/activate
pip install -e . --quiet

# 5. 创建 .env 配置文件（如果不存在）
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "[5/5] 创建配置文件..."
    cp .env.example .env
    echo ""
    echo "========================================="
    echo "  请编辑配置文件！"
    echo "========================================="
    echo ""
    echo "运行以下命令编辑配置："
    echo "  nano /opt/findit/.env"
    echo ""
    echo "必填项："
    echo "  TELEGRAM_BOT_TOKEN=你的Bot Token"
    echo "  XHS_COOKIE=你的小红书Cookie"
    echo ""
    echo "可选项（暂时不填也能跑）："
    echo "  ANTHROPIC_API_KEY=你的Claude API Key"
    echo ""
else
    echo "[5/5] 配置文件已存在，跳过"
fi

# 6. 创建数据目录
mkdir -p "$PROJECT_DIR/data"

# 7. 安装 systemd 服务
echo ""
echo "安装系统服务..."
sudo cp deploy/findit-crawler.service /etc/systemd/system/
sudo cp deploy/findit-bot.service /etc/systemd/system/

# 替换服务文件中的用户名
sudo sed -i "s/User=ubuntu/User=$USER/" /etc/systemd/system/findit-crawler.service
sudo sed -i "s/User=ubuntu/User=$USER/" /etc/systemd/system/findit-bot.service

sudo systemctl daemon-reload

echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
echo ""
echo "接下来的步骤："
echo ""
echo "1. 编辑配置文件（如果还没填）："
echo "   nano /opt/findit/.env"
echo ""
echo "2. 启动服务："
echo "   sudo systemctl start findit-crawler"
echo "   sudo systemctl start findit-bot"
echo ""
echo "3. 设置开机自启："
echo "   sudo systemctl enable findit-crawler"
echo "   sudo systemctl enable findit-bot"
echo ""
echo "4. 查看日志："
echo "   sudo journalctl -u findit-crawler -f"
echo "   sudo journalctl -u findit-bot -f"
echo ""
echo "5. 停止服务："
echo "   sudo systemctl stop findit-crawler"
echo "   sudo systemctl stop findit-bot"
echo ""
