"""
保持原文模式长文本分页测试（Phase 3 P1 - 长文本理解优化）

覆盖边界情况：
- 空输入 → 调用方兜底标题页，_fill_keep_original 本身返回 []
- 单段超过单页行数 → 多页分页，无内容丢失
- 超长无标点段落 → 硬切不丢字
- 标题行 + 内容流混合
- 纯内容流（无标题行）→ 多页时首行提升为页标题
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.api.routes.generation import GenerationService


@pytest.fixture
def svc():
    return GenerationService()


class TestSplitParaToLines:
    """_split_para_to_lines：句子边界拆分"""

    def test_short_para_unchanged(self, svc):
        lines = svc._split_para_to_lines("这是短段落。")
        assert lines == ["这是短段落。"]

    def test_sents_split_at_boundaries(self, svc):
        # 301+ 字符会触发拆分，每句独立成行
        text = "第一句。" * 100  # 600 字符，200 句（每句 3 字符）
        lines = svc._split_para_to_lines(text)
        # 每行都应以句号结尾（最后一个可能也是）
        assert all(ln.endswith("。") for ln in lines)
        assert len(lines) == 100
        # 无内容丢失
        assert "".join(lines) == text

    def test_no_punctuation_hard_cut(self, svc):
        # 400 个无标点字符 → 按 300 上限硬切
        text = "字" * 400
        lines = svc._split_para_to_lines(text)
        assert lines == ["字" * 300, "字" * 100]
        assert len(lines[0]) == 300


class TestPaginateKeepOriginal:
    """_paginate_keep_original：分页主逻辑"""

    def test_empty_input_returns_empty(self, svc):
        assert svc._paginate_keep_original([]) == []

    def test_single_line_no_title(self, svc):
        slides = svc._paginate_keep_original(["一段普通内容，长度超过标题行阈值但未到分页上限。"])
        assert len(slides) == 1
        assert slides[0]["title"] == "要点"
        assert slides[0]["content"] == ["一段普通内容，长度超过标题行阈值但未到分页上限。"]

    def test_title_line_grouped_with_content(self, svc):
        paras = [
            "第一章 背景",  # 短标题行（<40 字，无句号结尾）
            "背景说明第一行。",
            "背景说明第二行。",
        ]
        slides = svc._paginate_keep_original(paras)
        assert len(slides) == 1
        assert slides[0]["title"] == "第一章 背景"
        assert len(slides[0]["content"]) == 2

    def test_long_content_paginates_no_loss(self, svc):
        # 25 个内容行（每个 < 300 字符、< 40 字符且以句号结尾 → 均非标题行）
        paras = [f"第{i}行内容。" for i in range(25)]
        slides = svc._paginate_keep_original(paras)
        # 无内容丢失：标题+内容行合计等于原文总行数（标题行也计数）
        total_lines = sum(len(s["content"]) + (1 if s["title"] != "要点" else 0) for s in slides)
        assert total_lines == 25, f"无内容丢失，实际 {total_lines} != 25"
        # 多页时不允许出现无标题页
        for s in slides:
            assert s["title"], "不应有无标题页"

    def test_multi_page_first_line_promoted_to_title(self, svc):
        # 10 行内容（无标题行）→ 2 页，各页首行提升为页标题
        paras = [f"内容行{i}。" for i in range(10)]
        slides = svc._paginate_keep_original(paras)
        assert len(slides) == 2
        # 第 1 页：标题=内容行0，内容=内容行1~7（共 7 行）
        assert slides[0]["title"] == "内容行0。"
        assert len(slides[0]["content"]) == 7
        # 第 2 页：标题=内容行8，内容=内容行9（共 1 行）
        assert slides[1]["title"] == "内容行8。"
        assert slides[1]["content"] == ["内容行9。"]

    def test_title_group_overflow_paginates(self, svc):
        # 标题 + 20 行内容（超单页 8 行）→ 标题页继续分页
        paras = ["章节标题", *[f"内容{i}。" for i in range(20)]]
        slides = svc._paginate_keep_original(paras)
        assert all(s["title"] == "章节标题" for s in slides)
        total = sum(len(s["content"]) for s in slides)
        assert total == 20
        assert len(slides) == 3  # 8 + 8 + 4

    def test_mixed_title_and_content_flow(self, svc):
        paras = [
            "标题A",
            "A 的内容 1。",
            "A 的内容 2。",
            "标题B",
            "B 的内容 1。",
        ]
        slides = svc._paginate_keep_original(paras)
        titles = [s["title"] for s in slides]
        assert "标题A" in titles
        assert "标题B" in titles

    def test_long_unpunctuated_para_no_char_loss(self, svc):
        # 1000 字无标点 → 拆 4 行（300+300+300+100），进同一页（< 8 行）
        # 该页非标题行 → 第 1 行提升为标题，其余 3 行进内容
        text = "甲" * 1000
        slides = svc._paginate_keep_original([text])
        assert len(slides) == 1
        # 标题（前 300 字）+ 内容（后 700 字）合计 = 原文 1000 字，无丢失
        title_chars = len(slides[0]["title"])
        content_chars = sum(len(c) for c in slides[0]["content"])
        assert title_chars + content_chars == 1000, "无字符丢失"
        assert title_chars == 300
        assert content_chars == 700


class TestFillKeepOriginal:
    """_fill_keep_original：对外入口 + 空输入契约"""

    def test_empty_returns_empty_list(self, svc):
        assert svc._fill_keep_original("") == []
        # 全空白段落（split('\n') 后每段 strip() 为空 → 过滤为空）
        assert svc._fill_keep_original("   \n\n  ") == []

    def test_non_empty_returns_titled_slides(self, svc):
        slides = svc._fill_keep_original("某章节\n内容一行。")
        assert len(slides) >= 1
        assert all(s["title"] for s in slides), "不允许出现空标题页"

    def test_publishes_progress_when_session_id_given(self, svc):
        from app.api.routes.generation import collab_publish
        calls = []
        import app.api.routes.generation as g
        orig = g.collab_publish

        def spy(sid, event, payload):
            calls.append((sid, event, payload))
            return orig(sid, event, payload)

        g.collab_publish = spy
        try:
            svc._fill_keep_original("短输入。", "sess-test-1")
        finally:
            g.collab_publish = orig
        assert any(c[1] == "generation_progress" for c in calls), "应广播进度事件"


class TestPipelineFallback:
    """_quick_mode_pipeline keep_original 分支：空输入兜底标题页"""

    @staticmethod
    def _run(coro):
        import asyncio as _aio
        import contextlib
        with contextlib.suppress(RuntimeError):
            return _aio.get_event_loop().run_until_complete(coro)
        loop = _aio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_quick_mode_empty_input_produces_fallback_title_slide(self, svc):
        # user_input 全空白 → _fill_keep_original 返回 []
        # → _quick_mode_pipeline 兜底插入标题页
        result = self._run(svc._quick_mode_pipeline("sess-fb", "   ", {}, True))
        assert result["slides"], "空输入应产出兜底标题页"
        assert result["slides"][0]["title"], "兜底页必须有标题"
        assert result["keep_original"] is True

    def test_quick_mode_normal_input_titled(self, svc):
        result = self._run(svc._quick_mode_pipeline("sess-norm", "背景\n正文第一行。\n\n正文第二行。", {}, True))
        assert all(s["title"] for s in result["slides"]), "每页必须有标题"
