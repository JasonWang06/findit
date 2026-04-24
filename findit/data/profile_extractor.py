#!/usr/bin/env python3
"""
从帖子内容中提取用户画像信息
使用正则表达��和关键词匹配提取结构化数据
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path


class ProfileExtractor:
    """用户画像提取器"""

    def __init__(self):
        # 年龄模式
        self.age_patterns = [
            r'(\d{2})\s*岁',  # 28岁
            r'(\d{2})\s*年',  # 95年、02年
            r'0(\d)\s*后',    # 90后、00后
            r'(\d{4})\s*年(?:生|出生)',  # 1996年生
            r'步?入?(\d{2})',  # 步入28
        ]

        # 性别模式
        self.gender_patterns = {
            'male': ['男', '男生', '小哥', '小哥哥', '男朋友', '老公'],
            'female': ['女', '女生', '小姐姐', '女孩', '女朋友', '老婆']
        }

        # 地点模式（主要城市）
        self.location_patterns = [
            r'(北京|上海|广州|深圳|杭州|成都|重庆|武汉|西安|南京|苏州|天津|长沙|郑州)',
            r'(旧金山|纽约|洛杉矶|伦敦|新加坡|东京|悉尼)',
            r'(宝安|南山|福田|罗湖|龙岗|龙华)',  # 深圳区域
            r'(朝阳|海淀|西城|东城|丰台)',  # 北京区域
            r'(浦东|静安|黄浦|徐汇|长宁)',  # 上海区域
        ]

        # 职业模式
        self.occupation_patterns = {
            'tech': ['程序员', '开发', '工程师', '技术', '互联网', 'IT', '算法', '数据'],
            'finance': ['金融', '银行', '证券', '基金', '保险', '投资'],
            'education': ['教师', '老师', '教授', '教育', '讲师'],
            'medical': ['医生', '护士', '医疗', '医院'],
            'civil_servant': ['公务员', '体制内', 'gwy', '事业编', '国企'],
            'business': ['创业', '老板', '经商', '个体'],
            'student': ['学生', '在读', '本科', '硕士', '博士', '研究生'],
            'media': ['媒体', '记者', '编辑', '主播', '网红'],
        }

        # 身高模式
        self.height_patterns = [
            r'(\d{3})\s*cm',
            r'(\d{3})\s*厘米',
            r'身[高位]?\s*(\d{3})',
        ]

        # 学历模式
        self.education_patterns = {
            'phd': ['博士', 'PhD'],
            'master': ['硕士', '研究生'],
            'bachelor': ['本科', '学士'],
            'college': ['大专', '专科'],
            'high_school': ['高中', '中专']
        }

        # 收入/资产模式
        self.income_patterns = [
            r'(A\d[-+]?)',  # A8, A9等
            r'(\d+)w?\s*(?:年薪|年收|月收)',
            r'(年薪|月收)\s*(\d+)',
            r'(\d+)k?\s*(?:月薪|月入)',
        ]

        # 状态标记
        self.status_patterns = {
            'looking': ['找对象', '相亲', '交友', '脱单', '想谈恋爱', '单身'],
            'taken': ['有对象', '男朋友', '女朋友', '已婚', '结婚了'],
            'complicated': ['暧昧中', '不确定关系', '复杂']
        }

    def extract_age(self, text: str) -> Optional[int]:
        """提取年龄"""
        current_year = datetime.now().year

        for pattern in self.age_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    num = int(match)

                    # 处理年份格式（95年 -> 2026-95=31岁）
                    if num > 50 and num < 100:  # 50-99可能是年份缩写
                        age = current_year - (1900 + num)
                        if 18 <= age <= 50:  # 合理年龄范围
                            return age

                    # 处理完整年份（1996 -> 30岁）
                    elif num > 1900:
                        age = current_year - num
                        if 18 <= age <= 50:
                            return age

                    # 直接年龄
                    elif 18 <= num <= 50:
                        return num

                except (ValueError, TypeError):
                    continue

        return None

    def extract_gender(self, text: str) -> Optional[str]:
        """提取性别"""
        male_count = sum(1 for keyword in self.gender_patterns['male'] if keyword in text)
        female_count = sum(1 for keyword in self.gender_patterns['female'] if keyword in text)

        if male_count > female_count:
            return 'male'
        elif female_count > male_count:
            return 'female'
        else:
            return None

    def extract_location(self, text: str) -> List[str]:
        """提取地点信息"""
        locations = set()

        for pattern in self.location_patterns:
            matches = re.findall(pattern, text)
            locations.update(matches)

        return list(locations)

    def extract_occupation(self, text: str) -> List[str]:
        """提取职业信息"""
        occupations = set()

        for category, keywords in self.occupation_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    occupations.add(category)
                    break

        return list(occupations)

    def extract_height(self, text: str) -> Optional[int]:
        """提取身高（厘米）"""
        for pattern in self.height_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    height = int(match)
                    if 150 <= height <= 200:  # 合理身高范围
                        return height
                except (ValueError, TypeError):
                    continue

        return None

    def extract_education(self, text: str) -> List[str]:
        """提取学历信息"""
        education = set()

        for level, keywords in self.education_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    education.add(level)
                    break

        return list(education)

    def extract_status(self, text: str) -> Optional[str]:
        """提取感情状态"""
        for status, keywords in self.status_patterns.items():
            if any(keyword in text for keyword in keywords):
                return status
        return None

    def extract_requirements(self, text: str) -> Dict[str, any]:
        """提取对对方的要求"""
        requirements = {}

        # 年龄要求
        age_match = re.search(r'(?:找|想要?|希望|蹲)\s*(\d{2})\s*[岁年]', text)
        if age_match:
            requirements['target_age'] = int(age_match.group(1))

        # 身高要求
        height_match = re.search(r'(\d{3})\s*(?:cm|厘米)?\s*\+', text)
        if height_match:
            requirements['min_height'] = int(height_match.group(1))

        # 收入/资产要求
        if 'A8' in text or '千万' in text or '有房有车' in text:
            requirements['financial_preference'] = 'high'
        elif '稳定' in text or '工作' in text:
            requirements['financial_preference'] = 'stable'

        return requirements

    def extract_profile(self, text: str, post_id: str = None) -> Dict:
        """提取完整的用户画像"""
        profile = {
            'post_id': post_id,
            'age': self.extract_age(text),
            'gender': self.extract_gender(text),
            'locations': self.extract_location(text),
            'occupations': self.extract_occupation(text),
            'height': self.extract_height(text),
            'education': self.extract_education(text),
            'status': self.extract_status(text),
            'requirements': self.extract_requirements(text),
            'raw_text': text[:200],  # 保留原始文本摘要
        }

        return profile

    def calculate_confidence(self, profile: Dict) -> float:
        """计算画像可信度"""
        score = 0.0
        total_weight = 0.0

        # 年龄权重最高
        if profile['age']:
            score += 0.3
        total_weight += 0.3

        # 地点信息
        if profile['locations']:
            score += min(0.2, len(profile['locations']) * 0.1)
        total_weight += 0.2

        # 职业信息
        if profile['occupations']:
            score += min(0.15, len(profile['occupations']) * 0.08)
        total_weight += 0.15

        # 性别
        if profile['gender']:
            score += 0.15
        total_weight += 0.15

        # 状态
        if profile['status']:
            score += 0.1
        total_weight += 0.1

        # 身高
        if profile['height']:
            score += 0.05
        total_weight += 0.05

        # 学历
        if profile['education']:
            score += 0.05
        total_weight += 0.05

        return score / total_weight if total_weight > 0 else 0.0


def test_extractor():
    """测试提取器"""
    extractor = ProfileExtractor()

    test_cases = [
        "深圳 96女。护士 三观正。有点黏人。做饭超好吃，蹲一个成熟稳重的男朋友",
        "94广东潮汕人定居深圳，粤语/211本科毕业，INTJ，颜控，深圳有车有房",
        "步入28后老妈开始紧锣密鼓地张罗，见了几个相亲对象",
        "90后，公司在京和深圳，创一代，净资产A8-5，蹲一个00年以后的小姐姐",
        "只要性别男170+工作gwy或者tzn，不管长相怎么样",
    ]

    for i, text in enumerate(test_cases, 1):
        print(f"\n测试案例 {i}:")
        print(f"原文: {text}")
        profile = extractor.extract_profile(text, f"test_{i}")
        print(f"提取结果:")
        print(f"  年龄: {profile['age']}")
        print(f"  性别: {profile['gender']}")
        print(f"  地点: {profile['locations']}")
        print(f"  职业: {profile['occupations']}")
        print(f"  身高: {profile['height']}")
        print(f"  学历: {profile['education']}")
        print(f"  状态: {profile['status']}")
        print(f"  要求: {profile['requirements']}")
        print(f"  可信度: {extractor.calculate_confidence(profile):.2%}")


if __name__ == "__main__":
    test_extractor()
