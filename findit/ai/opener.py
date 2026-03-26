"""Personalized icebreaker / opener generation using Claude API.

Generates 1-2 natural, non-cringe conversation starters based on:
- The target's post content and profile
- The user's profile and strengths
- Common interests as hooks
"""

from __future__ import annotations

import json
import logging

import anthropic

from findit.config import settings

logger = logging.getLogger(__name__)

_OPENER_SYSTEM_PROMPT = """\
你是一个社交话术专家，擅长帮助男性用户在小红书上写出自然、有吸引力的破冰消息。

核心原则：
1. 对方明确要求的硬性条件（年龄、身高、收入等），在话术中直接覆盖
2. 对方没有提及的条件，不主动暴露（特别是年龄，除非对方问了）
3. 从对方主页内容中找共同话题作为钩子
4. 结尾带一个开放性话题或轻松的线下邀约暗示
5. 语气自然、不油腻、不堆砌条件
6. 长度控制在50-80字
7. 不要用"小姐姐"等过时称呼
8. 不要开头就自报家门式地列条件

请严格按照JSON格式输出，不要输出任何其他内容。"""

_OPENER_USER_PROMPT = """\
## 对方信息

**帖子/评论内容：**
{post_content}

**对方主页：**
- 昵称：{nickname}
- 简介：{bio}
- 城市：{ip_location}
- 年龄标签：{age_tag}
- 最近笔记：{recent_notes}

**对方提出的要求：**
{her_requirements}

**AI分析的共同话题：**
{common_topics}

**对方沟通风格：** {communication_style}

**建议的切入点：**
{opener_hooks}

## 我的资料

- 年龄：{user_age}
- 身高：{user_height}cm
- 学历：{user_education}（{user_school}）
- 职业：{user_occupation}
- 收入区间：{user_income}
- 城市：{user_city}
- 兴趣爱好：{user_hobbies}
- 亮点：{user_highlights}

## 请生成2条备选破冰话术

输出JSON格式：
{{
    "opener_1": "<第一条话术，50-80字>",
    "opener_2": "<第二条话术，50-80字，不同切入角度>",
    "strategy": "<简短说明话术策略>"
}}"""


class OpenerGenerator:
    """Generates personalized icebreaker messages using Claude API."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def generate(
        self,
        post: dict,
        author: dict,
        user: dict,
        scoring_result: dict | None = None,
    ) -> tuple[str, str, str]:
        """Generate two opener options and a strategy note.

        Returns (opener_1, opener_2, strategy).
        """
        scoring = scoring_result or {}
        notes_summary = author.get("notes_summary", "[]")
        if isinstance(notes_summary, str):
            try:
                notes = json.loads(notes_summary)
            except (json.JSONDecodeError, TypeError):
                notes = []
        else:
            notes = notes_summary

        recent_titles = ", ".join(
            n.get("title", "无标题") for n in (notes[:5] if notes else [])
        ) or "无"

        hobbies = user.get("hobbies", "[]")
        if isinstance(hobbies, str):
            try:
                hobbies = json.loads(hobbies)
            except (json.JSONDecodeError, TypeError):
                hobbies = []

        highlights = user.get("highlights", "[]")
        if isinstance(highlights, str):
            try:
                highlights = json.loads(highlights)
            except (json.JSONDecodeError, TypeError):
                highlights = []

        common_topics = scoring.get("common_topics", [])
        opener_hooks = scoring.get("opener_hooks", [])

        prompt = _OPENER_USER_PROMPT.format(
            post_content=post.get("content", "")[:800],
            nickname=author.get("nickname", ""),
            bio=author.get("bio", "无"),
            ip_location=author.get("ip_location", "未知"),
            age_tag=author.get("age_tag", "未知"),
            recent_notes=recent_titles,
            her_requirements=scoring.get("her_requirements", "未明确提出"),
            common_topics=", ".join(common_topics) if common_topics else "待发现",
            communication_style=scoring.get("communication_style", "未知"),
            opener_hooks=", ".join(opener_hooks) if opener_hooks else "无特定建议",
            user_age=user.get("age", "未填"),
            user_height=user.get("height", "未填"),
            user_education=user.get("education", "未填"),
            user_school=user.get("school", "未填"),
            user_occupation=user.get("occupation", "未填"),
            user_income=user.get("income_range", "未填"),
            user_city=user.get("city", "未填"),
            user_hobbies=", ".join(hobbies) if hobbies else "未填",
            user_highlights=", ".join(highlights) if highlights else "无",
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                system=_OPENER_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)
            return (
                data.get("opener_1", ""),
                data.get("opener_2", ""),
                data.get("strategy", ""),
            )
        except Exception:
            logger.exception("Opener generation failed")
            return ("", "", "")

    def regenerate_single(
        self,
        post: dict,
        author: dict,
        user: dict,
        previous_opener: str,
    ) -> str:
        """Generate a fresh opener that's different from the previous one."""
        prompt = f"""请为以下场景生成一条全新的破冰话术（与之前不同的角度）。

之前的话术（请避免相似内容）：{previous_opener}

对方帖子内容：{post.get('content', '')[:500]}
对方昵称：{author.get('nickname', '')}
对方城市：{author.get('ip_location', '')}
我的城市：{user.get('city', '')}
我的职业：{user.get('occupation', '')}

要求：50-80字，自然不油腻，以共同话题切入。
只输出话术文本，不要JSON格式。"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception:
            logger.exception("Opener regeneration failed")
            return ""
