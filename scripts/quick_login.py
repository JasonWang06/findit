#!/usr/bin/env python3
"""
快速设置MediaCrawler登录

使用二维码登录，一次性获取Cookie
"""

import subprocess
import sys
from pathlib import Path


def setup_mediacrawler_login():
    """设置MediaCrawler登录"""

    mediacrawler_path = Path.home() / "Desktop" / "MediaCrawler"

    print("🚀 开始设置MediaCrawler登录")
    print("="*60)
    print(f"📁 MediaCrawler路径: {mediacrawler_path}")

    # 检查是否存在
    if not mediacrawler_path.exists():
        print("❌ MediaCrawler不存在，请先克隆:")
        print("   git clone https://github.com/NanmiCoder/MediaCrawler ~/Desktop/MediaCrawler")
        return False

    # 检查配置文件
    config_file = mediacrawler_path / "config.yaml"
    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}")
        return False

    print(f"✅ 找到配置文件: {config_file}")

    # 显示说明
    print("\n" + "="*60)
    print("📱 二维码登录说明:")
    print("="*60)
    print("1. 程序会打开浏览器窗口")
    print("2. 页面会显示小红书登录二维码")
    print("3. 打开手机小红书APP → 扫一扫")
    print("4. 扫码确认登录")
    print("5. 登录成功后自动保存Cookie")
    print("6. 以后就不需要重复登录了")
    print("\n⏰ 整个过程约1-2分钟")
    print("="*60)

    input("\n按回车键继续...")

    # 运行MediaCrawler登录
    print("\n🚀 启动MediaCrawler...")

    cmd = [
        sys.executable, "main.py",
        "--platform", "xhs",
        "--lt", "qrcode",  # 二维码登录
        "--type", "search",
        "--keywords", "测试"
    ]

    print(f"📝 命令: {' '.join(cmd)}")
    print(f"📂 工作目录: {mediacrawler_path}")
    print("\n⚠️  注意：浏览器窗口会自动弹出，请等待...")

    try:
        subprocess.run(cmd, cwd=mediacrawler_path)
        return True

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


def verify_login():
    """验证登录是否成功"""
    print("\n" + "="*60)
    print("🔍 验证登录状态")
    print("="*60)

    mediacrawler_path = Path.home() / "Desktop" / "MediaCrawler"
    cookies_file = mediacrawler_path / "cookies" / "xhs_cookies.json"

    if cookies_file.exists():
        print(f"✅ Cookie文件存在: {cookies_file}")
        print("\n🎉 登录设置完成！")
        print("\n下次运行时，MediaCrawler会自动使用保存的Cookie：")
        print("  python3 main.py --platform xhs --lt cookie --type search --keywords '深圳找对象'")
        return True
    else:
        print(f"⚠️  Cookie文件不存在: {cookies_file}")
        print("\n可能的原因：")
        print("1. 登录未完成或被中断")
        print("2. MediaCrawler保存路径不同")
        print("\n建议：重新运行登录流程")
        return False


def main():
    print("🎯 MediaCrawler登录设置向导")
    print("="*60)

    success = setup_mediacrawler_login()

    if success:
        verify_login()
    else:
        print("\n❌ 登录设置未完成")
        print("\n你可以：")
        print("1. 重新运行此脚本")
        print("2. 手动运行MediaCrawler:")
        print("   cd ~/Desktop/MediaCrawler")
        print("   python3 main.py --platform xhs --lt qrcode")


if __name__ == "__main__":
    main()
