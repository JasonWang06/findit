"""AI-powered scoring of author profiles using Claude API.

Second-pass filter that uses an LLM to assess:
- Authenticity (real person vs fake/agency)
- Seriousness of dating intent
- Match compatibility with the user
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import anthropic

from findit.config import settings

logger = logging.getLogger(__name__)

_SCORING_SYSTEM_PROMPT = """\
你是一个约会匹配分析专家。你的任务是分析小红书上的女性用户资料，判断其是否为真实求偶用户，并评估与男方用户的匹配度。

请严格按照JSON格式输出，不要输出任何其他内容。"""

_SCORING_USER_PROMPT = """\
## 待分析的女方信息

**帖子/评论内容：**
{post_content}

**作者主页信息：**
- 昵称：{nickname}
- 简介：{bio}
- IP属地：{ip_location}
- 年龄标签：{age_tag}
- 粉丝数：{followers}
- 关注数：{following}
- 获赞与收藏：{likes_collected}
- 最近笔记标题：{recent_notes}

## 男方用户资料

- 年龄：{user_age}
- 身高：{user_height}cm
- 学历：{user_education}（{user_school}）
- 职业：{user_occupation}
- 收入区间：{user_income}
- 所在城市：{user_city}
- 兴趣爱好：{user_hobbies}
- 其他亮点：{user_highlights}

## 请输出以下JSON

{{
    "authenticity_score": <0-100整数, 真人置信度>,
    "seriousness_score": <0-100整数, 求偶认真度>,
    "match_score": <0-100整数, 与男方匹配度>,
    "match_analysis": "<1-2句话的匹配分析，说明为什么匹配或不匹配>",
    "her_requirements": "<她提出的硬性条件概要>",
    "common_topics": ["<共同话题1>", "<共同话题2>"],
    "communication_style": "<理性条件型 或 感性氛围型>",
    "red_flags": ["<可疑信号，如有>"],
    "opener_hooks": ["<可用于破冰的切入点1>", "<切入点2>"]
}}"""


@dataclass
class ScoringResult:
    authenticity_score: float
    seriousness_score: float
    match_score: float
    match_analysis: str
    her_requirements: str
    common_topics: list[str]
    communication_style: str
    red_flags: list[str]
    opener_hooks: list[str]


class AIScorer:
    """Uses Claude API to score and analyze author profiles."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def score(
        self,
        post: dict,
        author: dict,
        user: dict,
    ) -> ScoringResult | None:
        """Score a single post+author against a user profile.

        Returns ScoringResult or None if the API call fails.
        """
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

        prompt = _SCORING_USER_PROMPT.format(
            post_content=post.get("content", "")[:1000],
            nickname=author.get("nickname", "未知"),
            bio=author.get("bio", "无"),
            ip_location=author.get("ip_location", "未知"),
            age_tag=author.get("age_tag", "未知"),
            followers=author.get("followers", 0),
            following=author.get("following", 0),
            likes_collected=author.get("likes_collected", 0),
            recent_notes=recent_titles,
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
                max_tokens=800,
                system=_SCORING_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)
            return ScoringResult(
                authenticity_score=float(data.get("authenticity_score", 0)),
                seriousness_score=float(data.get("seriousness_score", 0)),
                match_score=float(data.get("match_score", 0)),
                match_analysis=data.get("match_analysis", ""),
                her_requirements=data.get("her_requirements", ""),
                common_topics=data.get("common_topics", []),
                communication_style=data.get("communication_style", ""),
                red_flags=data.get("red_flags", []),
                opener_hooks=data.get("opener_hooks", []),
            )
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI scoring response as JSON")
            return None
        except Exception:
            logger.exception("AI scoring API call failed")
            return None
