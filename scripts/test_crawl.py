#!/usr/bin/env python3
"""本地快速验证脚本：测试小红书爬虫能不能跑通。

使用 xhs 库（带真实签名）替代之前的 MD5 占位签名。

用法:
    python scripts/test_crawl.py --cookie "你从Chrome Network标签复制的完整cookie"

获取 Cookie 的方法：
    1. Chrome 打开 xiaohongshu.com 并登录
    2. F12 → Network 标签 → 刷新页面
    3. 点一个请求（选 data 或 homefeed 等，避免 OPTIONS 请求）
    4. 在 Request Headers 里找 Cookie，右键 Copy value
    注意：不要用 Console 的 document.cookie，那个拿不到 httpOnly cookie！
"""

from __future__ import annotations

import argparse
import json
import random
import time

from xhs import XhsClient
from xhs.exception import DataFetchError, SignError, NeedVerifyError, IPBlockError
from xhs.help import sign as xhs_sign


def _sign(uri, data=None, a1="", web_session=""):
    """Sign function for XhsClient."""
    return xhs_sign(uri, data, a1=a1)


def test_step1_search(client: XhsClient) -> dict | None:
    """Step 1: 搜索关键词，看能不能拿到帖子。"""
    print("\n" + "=" * 50)
    print("[Step 1] 搜索关键词'找对象'...")
    print("=" * 50)

    try:
        data = client.get_note_by_keyword("找对象", page=1, page_size=5)
        items = data.get("items", [])
        print(f"  ✅ 找到 {len(items)} 条帖子")

        first_note = None
        for i, item in enumerate(items[:3]):
            note = item.get("note_card", {})
            user = note.get("user", {})
            title = note.get("title", "无标题")
            nickname = user.get("nickname", "未知")
            likes = note.get("interact_info", {}).get("liked_count", "0")
            note_id = item.get("id", "")
            user_id = user.get("user_id", "")

            print(f"  [{i+1}] {title}")
            print(f"      作者: {nickname} | 点赞: {likes} | ID: {note_id}")

            if i == 0 and note_id:
                first_note = {
                    "note_id": note_id,
                    "user_id": user_id,
                    "title": title,
                    "nickname": nickname,
                }

        return first_note

    except SignError:
        print("  ❌ 签名错误 — xhs 库的内置签名可能需要更新")
        print("  建议：检查 xhs 库版本是否最新 (pip install --upgrade xhs)")
        return None
    except NeedVerifyError as e:
        print(f"  ❌ 触发验证码 — {e}")
        print("  建议：等几分钟再试，或换个 IP")
        return None
    except IPBlockError:
        print("  ❌ IP 被封 — 请使用代理或换 IP")
        return None
    except DataFetchError as e:
        print(f"  ❌ 数据获取失败: {e}")
        return None
    except Exception as e:
        print(f"  ❌ 未知错误: {type(e).__name__}: {e}")
        return None


def test_step2_comments(client: XhsClient, note_id: str) -> None:
    """Step 2: 抓取帖子评论。"""
    print("\n" + "=" * 50)
    print(f"[Step 2] 抓取帖子 {note_id} 的评论...")
    print("=" * 50)

    try:
        data = client.get_note_comments(note_id, cursor="")
        comments = data.get("comments", [])
        print(f"  ✅ 找到 {len(comments)} 条评论")

        dating_keywords = [
            "蹲一个", "蹲男友", "蹲对象", "找对象", "找男友",
            "单身", "脱单", "交友", "坐标", "私聊", "dd", "cpdd",
        ]

        dating_count = 0
        for i, c in enumerate(comments[:5]):
            user = c.get("user_info", {})
            content = c.get("content", "")[:60]
            nickname = user.get("nickname", "")
            is_dating = any(kw in content.lower() for kw in dating_keywords)
            marker = "🎯" if is_dating else "  "
            if is_dating:
                dating_count += 1
            print(f"  {marker} [{i+1}] {nickname}: {content}")

        if dating_count:
            print(f"\n  🎯 其中 {dating_count} 条有求偶意图")
        else:
            print(f"\n  ℹ️  没有检测到明确求偶意图的评论（正常，不是每个帖子都有）")

    except Exception as e:
        print(f"  ❌ 失败: {type(e).__name__}: {e}")


def test_step3_profile(client: XhsClient, user_id: str, nickname: str) -> None:
    """Step 3: 抓取用户主页。"""
    print("\n" + "=" * 50)
    print(f"[Step 3] 抓取用户 {nickname} 的主页...")
    print("=" * 50)

    try:
        user_data = client.get_user_info(user_id)
        basic = user_data.get("basic_info", {})
        interactions = user_data.get("interactions", [])

        print(f"  ✅ 获取成功")
        print(f"  昵称: {basic.get('nickname', '未知')}")
        print(f"  简介: {(basic.get('desc') or '无')[:50]}")
        print(f"  IP属地: {basic.get('ip_location', '未知')}")

        labels = ["粉丝", "关注", "获赞与收藏"]
        for i, item in enumerate(interactions[:3]):
            count = item.get("count", "0")
            label = labels[i] if i < len(labels) else f"指标{i}"
            print(f"  {label}: {count}")

    except Exception as e:
        print(f"  ❌ 失败: {type(e).__name__}: {e}")
        return

    # 抓笔记列表
    print(f"\n  抓取最近笔记...")
    try:
        time.sleep(random.uniform(1, 2))
        notes_data = client.get_user_notes(user_id, cursor="")
        notes = notes_data.get("notes", [])
        print(f"  ✅ 找到 {len(notes)} 条笔记")
        for i, n in enumerate(notes[:3]):
            title = n.get("display_title", "无标题")
            likes = n.get("interact_info", {}).get("liked_count", "0")
            print(f"  [{i+1}] {title} (👍 {likes})")
    except Exception as e:
        print(f"  ❌ 笔记列表获取失败: {type(e).__name__}: {e}")


def main(cookie: str) -> None:
    print("🔍 FindIt 爬虫验证工具 (xhs 库版)")
    print(f"Cookie长度: {len(cookie)} 字符")

    if len(cookie) < 50:
        print("⚠️  Cookie 看起来太短了，请确认从 Network 标签复制了完整 Cookie")
        return

    if "web_session" not in cookie:
        print("⚠️  Cookie 中没有 web_session 字段")
        print("   请从 Network 标签复制（不要用 Console 的 document.cookie）")
        print("   继续尝试...\n")

    client = XhsClient(cookie=cookie, sign=_sign)

    # Step 1: 搜索
    first_note = test_step1_search(client)
    if not first_note:
        print("\n💡 Step 1 失败，后续步骤跳过。")
        print("   常见原因：")
        print("   1. Cookie 不完整 → 从 Network 标签重新复制")
        print("   2. Cookie 过期 → 重新登录小红书")
        print("   3. 签名被拦 → 检查 xhs 库版本")
        return

    time.sleep(random.uniform(2, 4))

    # Step 2: 评论
    test_step2_comments(client, first_note["note_id"])

    time.sleep(random.uniform(2, 4))

    # Step 3: 主页
    test_step3_profile(client, first_note["user_id"], first_note["nickname"])

    # 总结
    print("\n" + "=" * 50)
    print("✅ 验证完成！")
    print("=" * 50)
    print()
    print("如果三步都成功了，恭喜！爬虫可以正常工作。")
    print("接下来：")
    print("  1. 把 Cookie 填到 .env 文件的 XHS_COOKIE")
    print("  2. 运行 findit-crawler-service 开始抓数据")
    print()
    print("如果有步骤失败了：")
    print("  - 签名错误 → pip install --upgrade xhs")
    print("  - 验证码 → 等几分钟或换 IP")
    print("  - Cookie 问题 → 重新从 Network 标签复制")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FindIt 爬虫本地验证（xhs 库版）")
    parser.add_argument(
        "--cookie",
        required=True,
        help="小红书Cookie（从Chrome DevTools Network标签复制）",
    )
    args = parser.parse_args()
    main(args.cookie)
