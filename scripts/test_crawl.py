#!/usr/bin/env python3
"""本地快速验证脚本：测试小红书爬虫能不能跑通。

用法:
    python scripts/test_crawl.py --cookie "你从Chrome复制的cookie"

这个脚本会依次测试爬虫的三个步骤：
  Step 1: 搜索关键词 → 能不能拿到帖子
  Step 2: 抓取评论 → 能不能拿到评论
  Step 3: 抓取主页 → 能不能拿到用户信息

每步都会打印结果，失败时打印详细错误信息帮你判断问题。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import hashlib
import random
from typing import Any

import httpx


# ── 请求配置 ───────────────────────────────────────────────────────────

BASE_URL = "https://edith.xiaohongshu.com"
WEB_URL = "https://www.xiaohongshu.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Origin": "https://www.xiaohongshu.com",
    "Referer": "https://www.xiaohongshu.com/",
}


def _sign(api_path: str, params: dict | None = None) -> dict[str, str]:
    """简化签名（可能不被XHS接受，脚本会自动测试有签名和无签名两种方式）。"""
    ts = str(int(time.time() * 1000))
    payload = f"{api_path}{ts}{json.dumps(params or {}, separators=(',', ':'))}"
    sign = hashlib.md5(payload.encode()).hexdigest()
    return {"X-t": ts, "X-s": sign}


# ── HTTP 请求 ──────────────────────────────────────────────────────────


async def _request(
    method: str,
    path: str,
    cookie: str,
    params: dict | None = None,
    payload: dict | None = None,
    use_sign: bool = True,
) -> tuple[int, dict[str, Any]]:
    """发送请求并返回 (status_code, response_json)。"""
    headers = {**HEADERS, "Cookie": cookie}
    if use_sign:
        headers.update(_sign(path, payload or params))

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        if method == "GET":
            resp = await client.get(f"{BASE_URL}{path}", params=params, headers=headers)
        else:
            resp = await client.post(f"{BASE_URL}{path}", json=payload, headers=headers)

        try:
            data = resp.json()
        except Exception:
            data = {"_raw": resp.text[:500]}

        return resp.status_code, data


# ── 测试步骤 ──────────────────────────────────────────────────────────


async def test_step1_search(cookie: str) -> dict | None:
    """Step 1: 搜索关键词，看能不能拿到帖子。"""
    print("\n" + "=" * 50)
    print("[Step 1] 搜索关键词'找对象'...")
    print("=" * 50)

    path = "/api/sns/web/v1/search/notes"
    payload = {
        "keyword": "找对象",
        "page": 1,
        "page_size": 5,
        "sort": "time_descending",
        "note_type": 0,
    }

    # 先尝试带签名
    status, data = await _request("POST", path, cookie, payload=payload, use_sign=True)

    if status != 200 or data.get("success") is False:
        print(f"  带签名请求: HTTP {status}")
        if data.get("msg"):
            print(f"  错误信息: {data['msg']}")

        # 再试不带签名
        print("  尝试不带签名...")
        status, data = await _request("POST", path, cookie, payload=payload, use_sign=False)

    if status != 200:
        print(f"  ❌ 失败 — HTTP {status}")
        print(f"  响应: {json.dumps(data, ensure_ascii=False)[:300]}")
        print()
        print("  可能原因:")
        print("  1. Cookie 已过期 → 重新从浏览器复制")
        print("  2. 签名校验不通过 → 需要接入真实签名方案")
        print("  3. IP 被限流 → 等一会再试")
        return None

    if data.get("success") is False:
        print(f"  ❌ API返回失败: {data.get('msg', '未知错误')}")
        print(f"  完整响应: {json.dumps(data, ensure_ascii=False)[:500]}")
        return None

    items = data.get("data", {}).get("items", [])
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

        if i == 0:
            first_note = {
                "note_id": note_id,
                "user_id": user_id,
                "title": title,
                "nickname": nickname,
            }

    return first_note


async def test_step2_comments(cookie: str, note_id: str) -> None:
    """Step 2: 抓取帖子评论。"""
    print("\n" + "=" * 50)
    print(f"[Step 2] 抓取帖子 {note_id} 的评论...")
    print("=" * 50)

    path = "/api/sns/web/v2/comment/page"
    params = {
        "note_id": note_id,
        "cursor": "",
        "top_comment_id": "",
        "image_formats": "jpg,webp",
    }

    # 先带签名
    status, data = await _request("GET", path, cookie, params=params, use_sign=True)

    if status != 200 or data.get("success") is False:
        # 不带签名重试
        status, data = await _request("GET", path, cookie, params=params, use_sign=False)

    if status != 200:
        print(f"  ❌ 失败 — HTTP {status}")
        print(f"  响应: {json.dumps(data, ensure_ascii=False)[:300]}")
        return

    if data.get("success") is False:
        print(f"  ❌ API返回失败: {data.get('msg', '未知错误')}")
        return

    comments = data.get("data", {}).get("comments", [])
    print(f"  ✅ 找到 {len(comments)} 条评论")

    # 检查有没有求偶意图的评论
    dating_keywords = [
        "蹲一个", "蹲男友", "蹲对象", "找对象", "找男友",
        "单身", "脱单", "交友", "坐标", "私聊", "dd", "cpdd",
    ]

    dating_comments = []
    for c in comments:
        content = c.get("content", "")
        if any(kw in content.lower() for kw in dating_keywords):
            dating_comments.append(c)

    for i, c in enumerate(comments[:3]):
        user = c.get("user_info", {})
        content = c.get("content", "")[:60]
        nickname = user.get("nickname", "")
        is_dating = "🎯" if c in dating_comments else "  "
        print(f"  {is_dating} [{i+1}] {nickname}: {content}")

    if dating_comments:
        print(f"\n  🎯 其中 {len(dating_comments)} 条有求偶意图")
    else:
        print(f"\n  ℹ️  没有检测到明确求偶意图的评论（正常，不是每个帖子都有）")


async def test_step3_profile(cookie: str, user_id: str, nickname: str) -> None:
    """Step 3: 抓取用户主页。"""
    print("\n" + "=" * 50)
    print(f"[Step 3] 抓取用户 {nickname} 的主页...")
    print("=" * 50)

    path = "/api/sns/web/v1/user/otherinfo"
    params = {"target_user_id": user_id}

    status, data = await _request("GET", path, cookie, params=params, use_sign=True)

    if status != 200 or data.get("success") is False:
        status, data = await _request("GET", path, cookie, params=params, use_sign=False)

    if status != 200:
        print(f"  ❌ 失败 — HTTP {status}")
        print(f"  响应: {json.dumps(data, ensure_ascii=False)[:300]}")
        return

    if data.get("success") is False:
        print(f"  ❌ API返回失败: {data.get('msg', '未知错误')}")
        return

    user_data = data.get("data", {})
    basic = user_data.get("basic_info", {})
    interactions = user_data.get("interactions", [])

    print(f"  ✅ 获取成功")
    print(f"  昵称: {basic.get('nickname', '未知')}")
    print(f"  简介: {basic.get('desc', '无')[:50]}")
    print(f"  IP属地: {basic.get('ip_location', '未知')}")

    if interactions:
        labels = ["粉丝", "关注", "获赞与收藏"]
        for i, item in enumerate(interactions[:3]):
            count = item.get("count", "0")
            label = labels[i] if i < len(labels) else f"指标{i}"
            print(f"  {label}: {count}")

    # 也抓一下用户的笔记列表
    print(f"\n  抓取最近笔记...")
    notes_path = "/api/sns/web/v1/user_posted"
    notes_params = {"user_id": user_id, "cursor": "", "num": 5, "image_formats": "jpg,webp"}

    status, notes_data = await _request("GET", notes_path, cookie, params=notes_params, use_sign=True)
    if status != 200 or notes_data.get("success") is False:
        status, notes_data = await _request("GET", notes_path, cookie, params=notes_params, use_sign=False)

    if status == 200 and notes_data.get("success") is not False:
        notes = notes_data.get("data", {}).get("notes", [])
        print(f"  ✅ 找到 {len(notes)} 条笔记")
        for i, n in enumerate(notes[:3]):
            title = n.get("display_title", "无标题")
            likes = n.get("interact_info", {}).get("liked_count", "0")
            print(f"  [{i+1}] {title} (👍 {likes})")
    else:
        print(f"  ❌ 笔记列表获取失败")


# ── 主流程 ──────────────────────────────────────────────────────────


async def main(cookie: str) -> None:
    print("🔍 FindIt 爬虫验证工具")
    print(f"Cookie长度: {len(cookie)} 字符")

    if len(cookie) < 50:
        print("⚠️  Cookie 看起来太短了，请确认复制完整")
        return

    # Step 1: 搜索
    first_note = await test_step1_search(cookie)
    if not first_note:
        print("\n💡 Step 1 失败，后续步骤跳过。请先解决搜索接口的问题。")
        return

    await asyncio.sleep(random.uniform(2, 4))  # 间隔

    # Step 2: 评论
    await test_step2_comments(cookie, first_note["note_id"])

    await asyncio.sleep(random.uniform(2, 4))

    # Step 3: 主页
    await test_step3_profile(cookie, first_note["user_id"], first_note["nickname"])

    # 总结
    print("\n" + "=" * 50)
    print("✅ 验证完成！")
    print("=" * 50)
    print()
    print("如果三步都成功了，恭喜！爬虫可以正常工作。")
    print("接下来：")
    print("  1. 把 Cookie 填到 .env 文件")
    print("  2. 运行 findit-crawler-service 开始抓数据")
    print()
    print("如果有步骤失败了：")
    print("  - HTTP 403 → Cookie过期或签名被拦，重新复制Cookie试试")
    print("  - success=false → 看错误信息，可能是接口变了")
    print("  - 连接超时 → 检查网络/VPN")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FindIt 爬虫本地验证")
    parser.add_argument("--cookie", required=True, help="小红书Cookie（从Chrome DevTools复制）")
    args = parser.parse_args()

    asyncio.run(main(args.cookie))
