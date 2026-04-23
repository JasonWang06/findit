#!/usr/bin/env python3
"""
Cookie管理器 - 将cookie与爬虫解耦

功能：
1. 从环境变量或配置文件读取cookie
2. 自动更新MediaCrawler的cookie配置
3. 提供cookie状态检查
4. 支持多种cookie来源（文件、环境变量、手动输入）
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json

# MediaCrawler配置路径
MEDIACRAWLER_CONFIG = Path.home() / "Desktop/MediaCrawler/config/base_config.py"
FINDIT_COOKIE_FILE = Path(__file__).parent.parent / "data/xhs_cookies.json"


class CookieManager:
    """Cookie管理器 - 解耦cookie与爬虫逻辑"""

    def __init__(self):
        self.findit_dir = Path(__file__).parent.parent
        self.cookie_file = self.findit_dir / "data/xhs_cookies.json"
        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)

    def load_cookie_from_file(self) -> dict | None:
        """从文件加载cookie"""
        if not self.cookie_file.exists():
            return None

        try:
            with open(self.cookie_file, 'r') as f:
                data = json.load(f)
                return data.get('cookie')
        except Exception as e:
            print(f"❌ 加载cookie文件失败: {e}")
            return None

    def load_cookie_from_env(self) -> str | None:
        """从环境变量加载cookie"""
        return os.environ.get('XHS_COOKIE')

    def save_cookie_to_file(self, cookie_string: str, source: str = "manual"):
        """保存cookie到文件"""
        try:
            data = {
                'cookie': cookie_string,
                'source': source,
                'updated_at': datetime.now().isoformat(),
                'version': '1.0'
            }

            with open(self.cookie_file, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"✅ Cookie已保存到: {self.cookie_file}")
            return True
        except Exception as e:
            print(f"❌ 保存cookie失败: {e}")
            return False

    def update_mediacrawler_config(self, cookie_string: str) -> bool:
        """更新MediaCrawler配置文件中的cookie"""
        try:
            if not MEDIACRAWLER_CONFIG.exists():
                print(f"❌ MediaCrawler配置文件不存在: {MEDIACRAWLER_CONFIG}")
                return False

            # 读取原配置
            with open(MEDIACRAWLER_CONFIG, 'r') as f:
                content = f.read()

            # 替换cookie行
            import re
            new_content = re.sub(
                r'COOKIES = ".*"',
                f'COOKIES = "{cookie_string}"',
                content
            )

            # 写回配置文件
            with open(MEDIACRAWLER_CONFIG, 'w') as f:
                f.write(new_content)

            print(f"✅ MediaCrawler配置已更新")
            return True
        except Exception as e:
            print(f"❌ 更新MediaCrawler配置失败: {e}")
            return False

    def get_cookie(self) -> str | None:
        """获取cookie（按优先级：文件 > 环境变量）"""
        # 优先从文件加载
        cookie_data = self.load_cookie_from_file()
        if cookie_data:
            print(f"📋 从文件加载cookie (来源: {cookie_data.get('source', 'unknown')})")
            return cookie_data

        # 其次从环境变量加载
        env_cookie = self.load_cookie_from_env()
        if env_cookie:
            print(f"📋 从环境变量加载cookie")
            return env_cookie

        return None

    def check_cookie_status(self) -> dict:
        """检查cookie状态"""
        status = {
            'file_exists': self.cookie_file.exists(),
            'env_exists': os.environ.get('XHS_COOKIE') is not None,
            'mediacrawler_config_exists': MEDIACRAWLER_CONFIG.exists(),
            'last_updated': None
        }

        if status['file_exists']:
            try:
                with open(self.cookie_file, 'r') as f:
                    data = json.load(f)
                    status['last_updated'] = data.get('updated_at')
                    status['source'] = data.get('source', 'unknown')
            except:
                pass

        return status

    def print_status(self):
        """打印cookie状态"""
        status = self.check_cookie_status()

        print("📊 Cookie状态检查")
        print("=" * 50)
        print(f"FindIt cookie文件: {'✅' if status['file_exists'] else '❌'}")
        print(f"环境变量 (XHS_COOKIE): {'✅' if status['env_exists'] else '❌'}")
        print(f"MediaCrawler配置: {'✅' if status['mediacrawler_config_exists'] else '❌'}")

        if status['last_updated']:
            print(f"最后更新: {status['last_updated']}")
            print(f"来源: {status.get('source', 'unknown')}")

        print("=" * 50)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Cookie管理器")
    parser.add_argument("action", choices=["status", "update", "save"],
                       help="操作: status(检查状态), update(更新MediaCrawler), save(保存新cookie)")
    parser.add_argument("--cookie", help="Cookie字符串")
    parser.add_argument("--source", default="manual", help="Cookie来源")

    args = parser.parse_args()

    manager = CookieManager()

    if args.action == "status":
        manager.print_status()

    elif args.action == "save":
        if not args.cookie:
            # 从环境变量读取
            cookie = os.environ.get('XHS_COOKIE')
            if not cookie:
                print("❌ 请提供 --cookie 参数或设置 XHS_COOKIE 环境变量")
                return
        else:
            cookie = args.cookie

        manager.save_cookie_to_file(cookie, args.source)

    elif args.action == "update":
        cookie = manager.get_cookie()
        if not cookie:
            print("❌ 未找到cookie，请先使用 'save' 命令保存cookie")
            return

        manager.update_mediacrawler_config(cookie if isinstance(cookie, str) else cookie.get('cookie'))


if __name__ == "__main__":
    main()
