"""
序号样式解析引擎测试
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from app.parsers.numbering_parser import (
    detect_numbering_style,
    parse_numbering_styles,
    enhance_confidence,
    detect_and_enhance,
    is_numeric_numbering,
    is_chinese_numbering,
    is_level_numbering,
    NUMBERING_PATTERNS,
)


class TestDetectNumberingStyle:
    """检测序号样式的单元测试"""

    def test_numeric_dot(self):
        assert detect_numbering_style("1. 第一项\n2. 第二项\n3. 第三项") == "numeric-dot"

    def test_numeric_paren(self):
        assert detect_numbering_style("(1) 第一项\n(2) 第二项") == "numeric-paren"

    def test_numeric_bracket(self):
        assert detect_numbering_style("[1] 第一项\n[2] 第二项") == "numeric-bracket"

    def test_chinese_clause(self):
        assert detect_numbering_style("一、第一项\n二、第二项\n三、第三项") == "chinese-clause"

    def test_chinese_paren(self):
        assert detect_numbering_style("（一）第一项\n（二）第二项") == "chinese-paren"

    def test_level_nested(self):
        assert detect_numbering_style("1.1 二级标题\n1.1.1 三级标题") == "level-nested"

    def test_english_alpha(self):
        assert detect_numbering_style("A. First\nB. Second\nC. Third") == "english-alpha"

    def test_graphic_bullet(self):
        result = detect_numbering_style("• 第一项\n• 第二项")
        assert result is not None  # 至少匹配到某个 graphic 类型

    def test_empty_text(self):
        assert detect_numbering_style("") is None

    def test_no_numbering(self):
        assert detect_numbering_style("普通文本\n没有序号") is None

    def test_mixed_content(self):
        # 混合内容，应以多数匹配为准
        text = "1. 第一项\n2. 第二项\n普通段落\n4. 第四项"
        result = detect_numbering_style(text)
        assert result == "numeric-dot"


class TestParseNumberingStyles:
    """解析序号样式的单元测试"""

    def test_single_line(self):
        lines = ["1. 第一项"]
        results = parse_numbering_styles(lines)
        assert len(results) == 1
        assert results[0].style_id == "numeric-dot"
        assert results[0].line_number == 1

    def test_multiple_lines(self):
        lines = ["1. 第一项", "2. 第二项", "3. 第三项"]
        results = parse_numbering_styles(lines)
        assert len(results) == 3
        assert all(r.style_id == "numeric-dot" for r in results)

    def test_empty_lines_skipped(self):
        lines = ["", "1. 第一项", "", "2. 第二项"]
        results = parse_numbering_styles(lines)
        assert len(results) == 2

    def test_confidence_sorted(self):
        lines = ["1. 第一项", "2. 第二项"]
        results = parse_numbering_styles(lines)
        # 结果应按置信度降序排列
        for i in range(len(results) - 1):
            assert results[i].confidence >= results[i + 1].confidence


class TestEnhanceConfidence:
    """置信度增强测试"""

    def test_three_or_more_matches(self):
        from app.parsers.numbering_parser import NumberingMatch
        matches = [
            NumberingMatch("numeric-dot", 0.8, "1.", 1),
            NumberingMatch("numeric-dot", 0.8, "2.", 2),
            NumberingMatch("numeric-dot", 0.8, "3.", 3),
        ]
        enhanced = enhance_confidence(matches)
        assert all(m.confidence == 1.0 for m in enhanced)

    def test_two_matches(self):
        from app.parsers.numbering_parser import NumberingMatch
        matches = [
            NumberingMatch("numeric-dot", 0.8, "1.", 1),
            NumberingMatch("numeric-dot", 0.8, "2.", 2),
        ]
        enhanced = enhance_confidence(matches)
        assert all(m.confidence == 0.9 for m in enhanced)

    def test_single_match(self):
        from app.parsers.numbering_parser import NumberingMatch
        matches = [NumberingMatch("numeric-dot", 0.8, "1.", 1)]
        enhanced = enhance_confidence(matches)
        assert enhanced[0].confidence == 0.8  # 单条不增强


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_is_numeric_numbering(self):
        assert is_numeric_numbering("1. 第一项")
        assert is_numeric_numbering("① 圆圈数字")
        assert not is_numeric_numbering("一、中文序号")

    def test_is_chinese_numbering(self):
        assert is_chinese_numbering("一、第一项")
        assert is_chinese_numbering("二、第二项")
        assert not is_chinese_numbering("1. 数字序号")

    def test_is_level_numbering(self):
        assert is_level_numbering("1.1 二级标题")
        assert is_level_numbering("1.1.1 三级标题")
        assert not is_level_numbering("1. 一级标题")


class TestPatternCoverage:
    """模式覆盖率测试"""

    def test_all_styles_have_pattern(self):
        """确认所有 30 种样式都有对应的正则模式"""
        expected_ids = {
            "numeric-dot", "numeric-paren", "numeric-bracket", "numeric-bracket-n", "numeric-period-n",
            "chinese-clause", "chinese-paren", "chinese-bracket", "chinese-ten",
            "level-nested", "level-decimal", "level-bracket",
            "graphic-circle", "graphic-diamond", "graphic-square", "graphic-triangle", "graphic-check", "graphic-bullet",
            "icon-check", "icon-arrow", "icon-star", "icon-badge", "icon-alert",
            "english-alpha", "english-roman", "english-alpha-lower", "english-roman-lower",
            "special-enclosed", "special-enclosed-caps", "special-enclosed-small",
        }
        actual_ids = set(NUMBERING_PATTERNS.keys())
        missing = expected_ids - actual_ids
        assert not missing, f"以下样式缺少正则模式: {missing}"
