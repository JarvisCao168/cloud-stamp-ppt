"""
PPT 序号解析引擎（Phase 1 规则匹配）
用于从 PPT 内容中识别已使用的序号样式
"""
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class NumberingMatch:
    """序号匹配结果"""
    style_id: str
    confidence: float  # 0.0 ~ 1.0
    matched_text: str  # 匹配到的序号文本
    line_number: int


# ========== 正则模式定义 ==========

NUMBERING_PATTERNS = {
    # 数字型 (numeric)
    "numeric-dot": re.compile(r"^(\d+\.)\s"),          # 1. 2. 3.
    "numeric-paren": re.compile(r"^(\(\d+\))\s"),      # (1) (2) (3)
    "numeric-bracket": re.compile(r"^(\[\d+\])\s"),    # [1] [2] [3]
    "numeric-bracket-n": re.compile(r"^(\d+\))\s"),    # 1) 2) 3)
    "numeric-period-n": re.compile(r"^([①-⑩])\s"),    # ① ② ③

    # 中文型 (chinese)
    "chinese-clause": re.compile(r"([一二三四五六七八九十]+、)"),  # 一、二、
    "chinese-paren": re.compile(r"（[一二三四五六七八九十]+）"),  # （一）（二）
    "chinese-bracket": re.compile(r"^\((\d+)\)\s"),        # (1) (2) - 复用数字括号模式
    "chinese-ten": re.compile(r"^([甲乙丙丁戊己庚辛壬癸])\s"),  # 甲乙丙丁

    # 层级型 (level)
    "level-nested": re.compile(r"^(\d+\.\d+(?:\.\d+)?)\s"),  # 1.1 1.1.1
    "level-decimal": re.compile(r"^(0\.\d+(?:\.\d+)?)\s"),   # 0.1 0.1.1
    "level-bracket": re.compile(r"^(\(\d+\.\d+\))\s"),       # (1.1) (1.1.1)

    # 图形型 (graphic) - 匹配特定符号开头
    "graphic-circle": re.compile(r"^[●○■□★☆]"),
    "graphic-diamond": re.compile(r"^[◆◇▸◂▹◃]"),
    "graphic-square": re.compile(r"^[▣▤▥▦▧▨]"),
    "graphic-triangle": re.compile(r"^[▲△▼▽⬆⬇]"),
    "graphic-check": re.compile(r"^[✓✗]"),
    "graphic-bullet": re.compile(r"^[•‣⁃·▪▫]"),

    # 图标型 (icon)
    "icon-check": re.compile(r"^[→✓✗⚠★]"),
    "icon-arrow": re.compile(r"^[▶]"),
    "icon-star": re.compile(r"^[⭐☆★]"),
    "icon-badge": re.compile(r"^[🏆🥈🥉🎖🏅]"),
    "icon-alert": re.compile(r"^[⚠❗❓ℹ✅]"),

    # 英文型 (english)
    "english-alpha": re.compile(r"^[A-Z]\."),
    "english-roman": re.compile(r"^[IVXLCDM]+\."),
    "english-alpha-lower": re.compile(r"^[a-z]\."),
    "english-roman-lower": re.compile(r"^[ivxlcdm]+\."),

    # 特殊型 (special)
    "special-enclosed": re.compile(r"^[①-⑳]"),
    "special-enclosed-caps": re.compile(r"^[ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ]"),
    "special-enclosed-small": re.compile(r"^[ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ]"),
}

# 备选模式：检测连续多个匹配（增强置信度）
MULTI_MATCH_PATTERNS = {
    "numeric-dot": re.compile(r"^(\d+\.)\s"),
    "chinese-clause": re.compile(r"^([一二三四五六七八九十]+、)\s"),
    "level-nested": re.compile(r"^(\d+\.\d+(?:\.\d+)?)\s"),
    "english-alpha": re.compile(r"^[A-Z]\."),
}


def detect_numbering_style(text: str, min_confidence: float = 0.6) -> Optional[str]:
    """
    检测文本中使用的序号样式

    Args:
        text: 待检测的文本（可以是单行或多行）
        min_confidence: 最低置信度阈值

    Returns:
        匹配的 style_id，如果未匹配则返回 None
    """
    lines = text.strip().split("\n")
    if not lines:
        return None

    # 统计每种模式在文本中的匹配次数
    match_counts: dict[str, int] = {}
    for line in lines:
        for style_id, pattern in NUMBERING_PATTERNS.items():
            if pattern.search(line):
                match_counts[style_id] = match_counts.get(style_id, 0) + 1

    if not match_counts:
        return None

    # 按匹配次数排序，返回最高分
    best_style = max(match_counts, key=match_counts.get)
    total_lines = len(lines)
    confidence = match_counts[best_style] / total_lines

    if confidence >= min_confidence:
        return best_style

    return None


def parse_numbering_styles(lines: List[str]) -> List[NumberingMatch]:
    """
    解析多行文本，返回所有匹配的序号样式

    Returns:
        匹配结果列表
    """
    results: List[NumberingMatch] = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        for style_id, pattern in NUMBERING_PATTERNS.items():
            match = pattern.search(line)
            if match:
                results.append(NumberingMatch(
                    style_id=style_id,
                    confidence=0.8,  # 单行匹配置信度固定 0.8
                    matched_text=match.group(0).strip(),
                    line_number=i + 1
                ))
                break  # 每行只匹配一种样式

    # 按置信度排序
    results.sort(key=lambda x: x.confidence, reverse=True)
    return results


def enhance_confidence(matches: List[NumberingMatch]) -> List[NumberingMatch]:
    """
    增强置信度：检测连续匹配，提升整体置信度

    例如：连续出现 3+ 条同一模式的序号，置信度从 0.8 提升到 1.0
    """
    if len(matches) < 2:
        return matches

    # 按 style_id 分组统计
    style_groups: dict[str, List[NumberingMatch]] = {}
    for m in matches:
        style_groups.setdefault(m.style_id, []).append(m)

    # 提升连续匹配多的样式置信度
    for style_id, group in style_groups.items():
        if len(group) >= 3:
            for m in group:
                m.confidence = 1.0
        elif len(group) >= 2:
            for m in group:
                m.confidence = 0.9

    return matches


def detect_and_enhance(text: str) -> List[NumberingMatch]:
    """
    完整的序号检测流程：检测 + 置信度增强

    Returns:
        增强后的匹配结果列表
    """
    lines = text.strip().split("\n")
    matches = parse_numbering_styles(lines)
    return enhance_confidence(matches)


# ========== 便捷函数 ==========

def is_numeric_numbering(text: str) -> bool:
    """检测是否为数字序号"""
    return bool(detect_numbering_style(text)) and any(
        text.startswith(s) for s in ["1", "2", "3", "4", "5", "①", "(1)", "[1]"]
    )


def is_chinese_numbering(text: str) -> bool:
    """检测是否为中文序号"""
    return bool(re.search(r"^[一二三四五六七八九十]+、", text, re.MULTILINE))


def is_level_numbering(text: str) -> bool:
    """检测是否为层级序号"""
    return bool(re.search(r"^\d+\.\d+", text, re.MULTILINE))
