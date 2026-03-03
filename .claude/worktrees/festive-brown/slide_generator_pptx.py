"""
slide_generator_pptx.py - PowerPoint生成エンジン

slides.md から Python-PPTX を使用して PPTX ファイルを生成します。
"""

import argparse
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

try:
    from pptx.chart.data import BarChartData, PieChartData, CategoryChartData
    from pptx.enum.chart import XL_LEGEND_POSITION, XL_CHART_TYPE
    CHART_SUPPORT = True
except ImportError:
    CHART_SUPPORT = False

from slides_markdown import parse_markdown_file, count_characters, truncate_text


class PowerPointGenerator:
    """PowerPointプレゼンテーション生成クラス"""

    # スライドサイズ（16:9）
    SLIDE_WIDTH = Inches(10)
    SLIDE_HEIGHT = Inches(5.625)

    # マージン
    MARGIN_LEFT = Inches(0.5)
    MARGIN_RIGHT = Inches(0.5)
    MARGIN_TOP = Inches(0.4)
    MARGIN_BOTTOM = Inches(0.4)

    def __init__(self, config: Dict[str, Any]):
        """
        初期化

        :param config: config.json の内容
        """
        self.prs = Presentation()
        self.prs.slide_width = self.SLIDE_WIDTH
        self.prs.slide_height = self.SLIDE_HEIGHT

        self.config = config
        self.palette = config.get('palette', {})
        self.font_family = config.get('font', {}).get('family', 'Meiryo UI')

    def generate(self, slides: List[Dict[str, Any]]) -> Presentation:
        """
        スライド情報から Presentation を生成

        :param slides: スライド情報のリスト
        :return: Presentation オブジェクト
        """
        for slide_info in slides:
            layout_type = slide_info.get('layout', 'bullet_points')

            # レイアウト別の処理を呼び出し
            if layout_type == 'title':
                self._add_title_slide(slide_info)
            elif layout_type == 'section':
                self._add_section_slide(slide_info)
            elif layout_type == 'toc':
                self._add_toc_slide(slide_info)
            elif layout_type == 'bullet_points':
                self._add_bullet_points_slide(slide_info)
            elif layout_type == 'numbered_list':
                self._add_numbered_list_slide(slide_info)
            elif layout_type == 'two_column':
                self._add_two_column_slide(slide_info)
            elif layout_type == 'three_column':
                self._add_three_column_slide(slide_info)
            elif layout_type == 'four_column':
                self._add_four_column_slide(slide_info)
            elif layout_type == 'metrics':
                self._add_metrics_slide(slide_info)
            elif layout_type == 'quote':
                self._add_quote_slide(slide_info)
            elif layout_type == 'faq':
                self._add_faq_slide(slide_info)
            elif layout_type == 'comparison_table':
                self._add_comparison_table_slide(slide_info)
            elif layout_type == 'image_with_text':
                self._add_image_with_text_slide(slide_info)
            elif layout_type == 'chart':
                self._add_chart_slide(slide_info)
            elif layout_type == 'cta':
                self._add_cta_slide(slide_info)
            else:
                # デフォルト: bullet_points
                self._add_bullet_points_slide(slide_info)

        return self.prs

    # ========== レイアウト別の追加処理 ==========

    def _add_title_slide(self, slide_info: Dict[str, Any]):
        """表紙スライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])  # 空白レイアウト
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('primary', '#1E3A5F'))

        # タイトル
        title_box = slide.shapes.add_textbox(
            self.MARGIN_LEFT, Inches(1.8), self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT, Inches(1.5)
        )
        title_frame = title_box.text_frame
        title_frame.word_wrap = True
        title_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

        p = title_frame.paragraphs[0]
        p.text = slide_info.get('title', '')
        p.font.size = Pt(44)
        p.font.bold = True
        p.font.color.rgb = self._hex_to_rgb(self.palette.get('text.light', '#FFFFFF'))
        p.alignment = PP_ALIGN.CENTER

        # サブタイトル
        if slide_info.get('key_message'):
            subtitle_box = slide.shapes.add_textbox(
                self.MARGIN_LEFT, Inches(3.2), self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT, Inches(1.5)
            )
            subtitle_frame = subtitle_box.text_frame
            subtitle_frame.word_wrap = True
            p = subtitle_frame.paragraphs[0]
            p.text = slide_info.get('key_message', '')
            p.font.size = Pt(24)
            p.font.color.rgb = self._hex_to_rgb(self.palette.get('text.light', '#FFFFFF'))
            p.alignment = PP_ALIGN.CENTER

    def _add_section_slide(self, slide_info: Dict[str, Any]):
        """セクション区切りスライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])  # 空白レイアウト
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.secondary', '#F5F5F5'))

        # タイトル
        title_box = slide.shapes.add_textbox(
            self.MARGIN_LEFT, Inches(2.2), self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT, Inches(1.5)
        )
        title_frame = title_box.text_frame
        title_frame.word_wrap = True

        p = title_frame.paragraphs[0]
        p.text = slide_info.get('title', '')
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = self._hex_to_rgb(self.palette.get('text.primary', '#333333'))
        p.alignment = PP_ALIGN.LEFT

    def _add_toc_slide(self, slide_info: Dict[str, Any]):
        """目次スライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.primary', '#FFFFFF'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # キーメッセージ
        if slide_info.get('key_message'):
            self._add_key_message_to_slide(slide, slide_info.get('key_message', ''))

        # 目次アイテム
        bullet_items = self._extract_bullet_items(slide_info)
        self._add_bullet_points_to_slide(slide, bullet_items, top_offset=Inches(1.2))

    def _add_bullet_points_slide(self, slide_info: Dict[str, Any]):
        """箇条書きスライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.primary', '#FFFFFF'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # キーメッセージ
        if slide_info.get('key_message'):
            self._add_key_message_to_slide(slide, slide_info.get('key_message', ''))

        # 箇条書きアイテム
        bullet_items = self._extract_bullet_items(slide_info)
        self._add_bullet_points_to_slide(slide, bullet_items, top_offset=Inches(1.2))

    def _add_numbered_list_slide(self, slide_info: Dict[str, Any]):
        """番号付きリストスライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.primary', '#FFFFFF'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # キーメッセージ
        if slide_info.get('key_message'):
            self._add_key_message_to_slide(slide, slide_info.get('key_message', ''))

        # 番号付きリストアイテム
        numbered_items = self._extract_numbered_items(slide_info)
        self._add_numbered_list_to_slide(slide, numbered_items, top_offset=Inches(1.2))

    def _add_two_column_slide(self, slide_info: Dict[str, Any]):
        """2列スライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.primary', '#FFFFFF'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # キーメッセージ
        if slide_info.get('key_message'):
            self._add_key_message_to_slide(slide, slide_info.get('key_message', ''))

        # 2列コンテンツ
        content_blocks = self._extract_column_blocks(slide_info)
        if len(content_blocks) >= 2:
            col_width = (self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT) / 2 - Inches(0.1)

            for idx, block in enumerate(content_blocks[:2]):
                left = self.MARGIN_LEFT + idx * (col_width + Inches(0.2))
                self._add_column_content(slide, block, left, Inches(1.3), col_width, Inches(3.5))

    def _add_three_column_slide(self, slide_info: Dict[str, Any]):
        """3列スライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.primary', '#FFFFFF'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # キーメッセージ
        if slide_info.get('key_message'):
            self._add_key_message_to_slide(slide, slide_info.get('key_message', ''))

        # 3列コンテンツ
        content_blocks = self._extract_column_blocks(slide_info)
        col_width = (self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT) / 3 - Inches(0.1)

        for idx, block in enumerate(content_blocks[:3]):
            left = self.MARGIN_LEFT + idx * (col_width + Inches(0.15))
            self._add_column_content(slide, block, left, Inches(1.3), col_width, Inches(3.5))

    def _add_four_column_slide(self, slide_info: Dict[str, Any]):
        """4列スライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.primary', '#FFFFFF'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # キーメッセージ
        if slide_info.get('key_message'):
            self._add_key_message_to_slide(slide, slide_info.get('key_message', ''))

        # 4列コンテンツ
        content_blocks = self._extract_column_blocks(slide_info)
        col_width = (self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT) / 4 - Inches(0.1)

        for idx, block in enumerate(content_blocks[:4]):
            left = self.MARGIN_LEFT + idx * (col_width + Inches(0.1))
            self._add_column_content(slide, block, left, Inches(1.3), col_width, Inches(3.5))

    def _add_metrics_slide(self, slide_info: Dict[str, Any]):
        """メトリクススライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.primary', '#FFFFFF'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # キーメッセージ
        if slide_info.get('key_message'):
            self._add_key_message_to_slide(slide, slide_info.get('key_message', ''))

        # メトリクスアイテム
        metrics = self._extract_metrics(slide_info)
        self._add_metrics_to_slide(slide, metrics, top_offset=Inches(1.3))

    def _add_quote_slide(self, slide_info: Dict[str, Any]):
        """引用スライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.secondary', '#F5F5F5'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # 引用テキスト
        quote_text = self._extract_quote_text(slide_info)
        quote_box = slide.shapes.add_textbox(
            self.MARGIN_LEFT, Inches(1.5), self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT, Inches(3.5)
        )
        text_frame = quote_box.text_frame
        text_frame.word_wrap = True
        text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE

        p = text_frame.paragraphs[0]
        p.text = quote_text
        p.font.size = Pt(24)
        p.font.italic = True
        p.font.color.rgb = self._hex_to_rgb(self.palette.get('text.primary', '#333333'))
        p.alignment = PP_ALIGN.CENTER

    def _add_faq_slide(self, slide_info: Dict[str, Any]):
        """FAQスライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.primary', '#FFFFFF'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # FAQ アイテム
        faq_items = self._extract_faq_items(slide_info)
        self._add_faq_to_slide(slide, faq_items, top_offset=Inches(1.0))

    def _add_comparison_table_slide(self, slide_info: Dict[str, Any]):
        """比較表スライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.primary', '#FFFFFF'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # キーメッセージ
        if slide_info.get('key_message'):
            self._add_key_message_to_slide(slide, slide_info.get('key_message', ''))

        # テーブル
        table_data = self._extract_table_data(slide_info)
        if table_data:
            self._add_table_to_slide(slide, table_data, Inches(0.8), Inches(1.2))

    def _add_image_with_text_slide(self, slide_info: Dict[str, Any]):
        """画像＋テキストスライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.primary', '#FFFFFF'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # キーメッセージ
        if slide_info.get('key_message'):
            self._add_key_message_to_slide(slide, slide_info.get('key_message', ''))

        # 画像と説明文
        image_path = self._extract_image_path(slide_info)
        text_content = self._extract_text_content(slide_info)

        if image_path and os.path.exists(image_path):
            # 画像を左側に配置
            slide.shapes.add_picture(image_path, self.MARGIN_LEFT, Inches(1.2), width=Inches(3.5))

            # テキストを右側に配置
            text_box = slide.shapes.add_textbox(
                Inches(4.3), Inches(1.2), Inches(5.2), Inches(3.5)
            )
            text_frame = text_box.text_frame
            text_frame.word_wrap = True

            p = text_frame.paragraphs[0]
            p.text = text_content
            p.font.size = Pt(12)
            p.font.color.rgb = self._hex_to_rgb(self.palette.get('text.primary', '#333333'))

    def _add_chart_slide(self, slide_info: Dict[str, Any]):
        """グラフスライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.primary', '#FFFFFF'))

        # タイトル
        self._add_title_to_slide(slide, slide_info.get('title', ''))

        # キーメッセージ
        if slide_info.get('key_message'):
            self._add_key_message_to_slide(slide, slide_info.get('key_message', ''))

        # チャート
        table_data = self._extract_table_data(slide_info)
        if table_data:
            self._add_chart_to_slide(slide, table_data, Inches(1), Inches(1.2), Inches(8), Inches(3.5))

    def _add_cta_slide(self, slide_info: Dict[str, Any]):
        """行動喚起スライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('background.secondary', '#F5F5F5'))

        # メッセージ
        message_box = slide.shapes.add_textbox(
            self.MARGIN_LEFT, Inches(1.5), self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT, Inches(1)
        )
        message_frame = message_box.text_frame
        message_frame.word_wrap = True

        p = message_frame.paragraphs[0]
        p.text = slide_info.get('title', '')
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = self._hex_to_rgb(self.palette.get('text.primary', '#333333'))
        p.alignment = PP_ALIGN.CENTER

        # 説明文
        if slide_info.get('key_message'):
            desc_box = slide.shapes.add_textbox(
                self.MARGIN_LEFT, Inches(2.5), self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT, Inches(1)
            )
            desc_frame = desc_box.text_frame
            desc_frame.word_wrap = True

            p = desc_frame.paragraphs[0]
            p.text = slide_info.get('key_message', '')
            p.font.size = Pt(14)
            p.font.color.rgb = self._hex_to_rgb(self.palette.get('text.primary', '#333333'))
            p.alignment = PP_ALIGN.CENTER

    # ========== ヘルパーメソッド ==========

    def _add_title_to_slide(self, slide, title: str, top: Pt = Inches(0.3)):
        """スライドにタイトルを追加"""
        title = truncate_text(title, 25)
        title_box = slide.shapes.add_textbox(
            self.MARGIN_LEFT, top, self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT, Inches(0.6)
        )
        text_frame = title_box.text_frame
        p = text_frame.paragraphs[0]
        p.text = title
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = self._hex_to_rgb(self.palette.get('primary', '#1E3A5F'))

    def _add_key_message_to_slide(self, slide, message: str, top: Pt = Inches(0.95)):
        """キーメッセージを追加"""
        message = truncate_text(message, 40)
        message_box = slide.shapes.add_textbox(
            self.MARGIN_LEFT, top, self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT, Inches(0.5)
        )
        text_frame = message_box.text_frame
        text_frame.word_wrap = True
        p = text_frame.paragraphs[0]
        p.text = message
        p.font.size = Pt(16)
        p.font.color.rgb = self._hex_to_rgb(self.palette.get('text.secondary', '#666666'))

    def _add_bullet_points_to_slide(self, slide, items: List[str], top_offset: Pt = Inches(1.2)):
        """箇条書きを追加"""
        bullet_box = slide.shapes.add_textbox(
            self.MARGIN_LEFT, top_offset, self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT, Inches(3.5)
        )
        text_frame = bullet_box.text_frame
        text_frame.word_wrap = True

        for idx, item in enumerate(items):
            if idx == 0:
                p = text_frame.paragraphs[0]
            else:
                p = text_frame.add_paragraph()

            p.text = truncate_text(item, 50)
            p.font.size = Pt(14)
            p.font.color.rgb = self._hex_to_rgb(self.palette.get('text.primary', '#333333'))
            p.level = 0
            p.space_before = Pt(6)
            p.space_after = Pt(6)

    def _add_numbered_list_to_slide(self, slide, items: List[Dict], top_offset: Pt = Inches(1.2)):
        """番号付きリストを追加"""
        list_box = slide.shapes.add_textbox(
            self.MARGIN_LEFT, top_offset, self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT, Inches(3.5)
        )
        text_frame = list_box.text_frame
        text_frame.word_wrap = True

        for idx, item in enumerate(items):
            if idx == 0:
                p = text_frame.paragraphs[0]
            else:
                p = text_frame.add_paragraph()

            item_title = truncate_text(item.get('item', ''), 15)
            p.text = f"{idx + 1}. {item_title}"
            p.font.size = Pt(13)
            p.font.bold = True
            p.font.color.rgb = self._hex_to_rgb(self.palette.get('accent', '#3AA899'))
            p.level = 0

            # 説明文
            if item.get('description'):
                p_desc = text_frame.add_paragraph()
                p_desc.text = truncate_text(item.get('description'), 50)
                p_desc.font.size = Pt(11)
                p_desc.font.color.rgb = self._hex_to_rgb(self.palette.get('text.primary', '#333333'))
                p_desc.level = 1

    def _add_metrics_to_slide(self, slide, metrics: List[Dict], top_offset: Pt = Inches(1.3)):
        """メトリクスを追加"""
        for idx, metric in enumerate(metrics[:4]):
            top = top_offset + Inches(idx * 0.8)

            value = metric.get('value', '')
            label = truncate_text(metric.get('label', ''), 15)

            # 値（大きく表示）
            value_box = slide.shapes.add_textbox(
                self.MARGIN_LEFT, top, Inches(2), Inches(0.6)
            )
            value_frame = value_box.text_frame
            p = value_frame.paragraphs[0]
            p.text = value
            p.font.size = Pt(36)
            p.font.bold = True
            p.font.color.rgb = self._hex_to_rgb(self.palette.get('accent', '#3AA899'))

            # ラベル
            label_box = slide.shapes.add_textbox(
                Inches(2.2), top + Inches(0.15), Inches(7), Inches(0.5)
            )
            label_frame = label_box.text_frame
            p = label_frame.paragraphs[0]
            p.text = label
            p.font.size = Pt(12)
            p.font.color.rgb = self._hex_to_rgb(self.palette.get('text.primary', '#333333'))

    def _add_faq_to_slide(self, slide, items: List[Dict], top_offset: Pt = Inches(1.0)):
        """FAQアイテムを追加"""
        faq_box = slide.shapes.add_textbox(
            self.MARGIN_LEFT, top_offset, self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT, Inches(4.2)
        )
        text_frame = faq_box.text_frame
        text_frame.word_wrap = True

        for idx, item in enumerate(items[:3]):
            if idx > 0:
                p = text_frame.add_paragraph()
                p.text = ''
                p.space_after = Pt(6)

            # 質問
            p = text_frame.add_paragraph() if idx > 0 else text_frame.paragraphs[0]
            p.text = truncate_text(item.get('question', ''), 30)
            p.font.size = Pt(12)
            p.font.bold = True
            p.font.color.rgb = self._hex_to_rgb(self.palette.get('accent', '#3AA899'))
            p.space_before = Pt(6)

            # 回答
            p_answer = text_frame.add_paragraph()
            p_answer.text = truncate_text(item.get('answer', ''), 80)
            p_answer.font.size = Pt(11)
            p_answer.font.color.rgb = self._hex_to_rgb(self.palette.get('text.primary', '#333333'))
            p_answer.level = 1
            p_answer.space_after = Pt(6)

    def _add_column_content(self, slide, block: Dict, left: Pt, top: Pt, width: Pt, height: Pt):
        """カラムコンテンツを追加"""
        # ヘッダー
        header = block.get('header', '')
        if header:
            header_box = slide.shapes.add_textbox(left, top, width, Inches(0.4))
            header_frame = header_box.text_frame
            p = header_frame.paragraphs[0]
            p.text = truncate_text(header, 10)
            p.font.size = Pt(12)
            p.font.bold = True
            p.font.color.rgb = self._hex_to_rgb(self.palette.get('primary', '#1E3A5F'))

        # コンテンツ
        content = block.get('content', '')
        content_box = slide.shapes.add_textbox(left, top + Inches(0.45), width, height - Inches(0.45))
        content_frame = content_box.text_frame
        content_frame.word_wrap = True
        p = content_frame.paragraphs[0]
        p.text = truncate_text(content, 80)
        p.font.size = Pt(11)
        p.font.color.rgb = self._hex_to_rgb(self.palette.get('text.primary', '#333333'))

    def _add_table_to_slide(self, slide, table_data: Dict, left: Pt, top: Pt):
        """テーブルを追加"""
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])

        rows_count = len(rows) + 1
        cols_count = len(headers)

        # テーブルの幅と高さを計算
        table_width = self.SLIDE_WIDTH - self.MARGIN_LEFT - self.MARGIN_RIGHT - Inches(0.5)
        table_height = Inches(3.5)

        # テーブルを追加
        table_shape = slide.shapes.add_table(rows_count, cols_count, left, top, table_width, table_height).table

        # ヘッダー行
        for col_idx, header in enumerate(headers):
            cell = table_shape.cell(0, col_idx)
            cell.text = truncate_text(header, 10)
            cell.fill.solid()
            cell.fill.fore_color.rgb = self._hex_to_rgb(self.palette.get('secondary', '#4A6FA5'))

            text_frame = cell.text_frame
            for paragraph in text_frame.paragraphs:
                paragraph.font.size = Pt(11)
                paragraph.font.bold = True
                paragraph.font.color.rgb = self._hex_to_rgb(self.palette.get('text.light', '#FFFFFF'))

        # データ行
        for row_idx, row in enumerate(rows):
            for col_idx, cell_data in enumerate(row):
                cell = table_shape.cell(row_idx + 1, col_idx)
                cell.text = truncate_text(str(cell_data), 15)

                text_frame = cell.text_frame
                for paragraph in text_frame.paragraphs:
                    paragraph.font.size = Pt(10)
                    paragraph.font.color.rgb = self._hex_to_rgb(self.palette.get('text.primary', '#333333'))

    def _add_chart_to_slide(self, slide, table_data: Dict, left: Pt, top: Pt, width: Pt, height: Pt):
        """グラフを追加"""
        headers = table_data.get('headers', [])
        rows = table_data.get('rows', [])

        if not headers or not rows:
            return

        # グラフ種別を判定
        chart_type = self._detect_chart_type(headers, rows)

        if chart_type == 'pie':
            self._add_pie_chart(slide, headers, rows, left, top, width, height)
        elif chart_type == 'line':
            self._add_line_chart(slide, headers, rows, left, top, width, height)
        else:
            # デフォルト: 横棒グラフ
            self._add_bar_chart(slide, headers, rows, left, top, width, height)

    def _add_bar_chart(self, slide, headers: List[str], rows: List[List],
                       left: Pt, top: Pt, width: Pt, height: Pt):
        """横棒グラフを追加（テーブルで代替）"""
        if CHART_SUPPORT:
            chart_data = BarChartData()
            chart_data.categories = [row[0] for row in rows]
            if len(headers) > 1:
                for col_idx in range(1, len(headers)):
                    values = []
                    for row in rows:
                        try:
                            values.append(float(row[col_idx]) if col_idx < len(row) else 0)
                        except (ValueError, IndexError):
                            values.append(0)
                    chart_data.add_series(headers[col_idx], values)
            x, y, cx, cy = left, top, width, height
            chart = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, x, y, cx, cy, chart_data).chart
        else:
            # テーブルで代替
            self._add_table_to_slide(slide, {'headers': headers, 'rows': rows}, left, top)

    def _add_pie_chart(self, slide, headers: List[str], rows: List[List],
                       left: Pt, top: Pt, width: Pt, height: Pt):
        """円グラフを追加（テーブルで代替）"""
        if CHART_SUPPORT:
            chart_data = PieChartData()
            chart_data.categories = [row[0] for row in rows]
            values = []
            for row in rows:
                try:
                    values.append(float(row[1]) if len(row) > 1 else 0)
                except (ValueError, IndexError):
                    values.append(0)
            chart_data.add_series('', values)
            x, y, cx, cy = left, top, width, height
            chart = slide.shapes.add_chart(XL_CHART_TYPE.PIE, x, y, cx, cy, chart_data).chart
        else:
            # テーブルで代替
            self._add_table_to_slide(slide, {'headers': headers, 'rows': rows}, left, top)

    def _add_line_chart(self, slide, headers: List[str], rows: List[List],
                        left: Pt, top: Pt, width: Pt, height: Pt):
        """折れ線グラフを追加（テーブルで代替）"""
        if CHART_SUPPORT:
            from pptx.chart.data import CategoryChartData
            chart_data = CategoryChartData()
            chart_data.categories = [row[0] for row in rows]
            if len(headers) > 1:
                for col_idx in range(1, len(headers)):
                    values = []
                    for row in rows:
                        try:
                            values.append(float(row[col_idx]) if col_idx < len(row) else 0)
                        except (ValueError, IndexError):
                            values.append(0)
                    chart_data.add_series(headers[col_idx], values)
            x, y, cx, cy = left, top, width, height
            chart = slide.shapes.add_chart(XL_CHART_TYPE.LINE, x, y, cx, cy, chart_data).chart
        else:
            # テーブルで代替
            self._add_table_to_slide(slide, {'headers': headers, 'rows': rows}, left, top)

    def _detect_chart_type(self, headers: List[str], rows: List[List]) -> str:
        """グラフ種別を自動判定"""
        # シンプルな実装：1列のデータなら pie、複数なら bar
        if len(headers) <= 2 and all('%' in str(row[1]) if len(row) > 1 else False for row in rows):
            return 'pie'
        return 'bar'

    def _extract_bullet_items(self, slide_info: Dict[str, Any]) -> List[str]:
        """箇条書きアイテムを抽出"""
        items = []
        for content in slide_info.get('content', []):
            if content.get('type') == 'bullet_points':
                items.extend(content.get('items', []))
        return items

    def _extract_numbered_items(self, slide_info: Dict[str, Any]) -> List[Dict]:
        """番号付きリストアイテムを抽出"""
        items = []
        for content in slide_info.get('content', []):
            if content.get('type') == 'numbered_list':
                items.extend(content.get('items', []))
        return items

    def _extract_column_blocks(self, slide_info: Dict[str, Any]) -> List[Dict]:
        """カラムブロックを抽出"""
        blocks = []
        current_header = ''

        for content in slide_info.get('content', []):
            if content.get('type') == 'column_header':
                current_header = content.get('text', '')
            elif content.get('type') == 'text':
                blocks.append({
                    'header': current_header,
                    'content': content.get('text', '')
                })

        return blocks

    def _extract_metrics(self, slide_info: Dict[str, Any]) -> List[Dict]:
        """メトリクスを抽出"""
        metrics = []
        for content in slide_info.get('content', []):
            if content.get('type') == 'bullet_points':
                for item in content.get('items', []):
                    # "**120%** 売上成長率" のような形式を解析
                    match = re.match(r'\*\*([^*]+)\*\*\s+(.*)', item)
                    if match:
                        metrics.append({
                            'value': match.group(1),
                            'label': match.group(2)
                        })
                    else:
                        metrics.append({'value': item, 'label': ''})
        return metrics

    def _extract_quote_text(self, slide_info: Dict[str, Any]) -> str:
        """引用テキストを抽出"""
        for content in slide_info.get('content', []):
            if content.get('type') == 'quote':
                return content.get('text', '')
        return ''

    def _extract_faq_items(self, slide_info: Dict[str, Any]) -> List[Dict]:
        """FAQアイテムを抽出"""
        for content in slide_info.get('content', []):
            if content.get('type') == 'faq':
                return content.get('items', [])
        return []

    def _extract_table_data(self, slide_info: Dict[str, Any]) -> Optional[Dict]:
        """テーブルデータを抽出"""
        for content in slide_info.get('content', []):
            if content.get('type') == 'table':
                return content.get('data', None)
        return None

    def _extract_image_path(self, slide_info: Dict[str, Any]) -> Optional[str]:
        """画像パスを抽出"""
        for content in slide_info.get('content', []):
            if content.get('type') == 'image':
                return content.get('src', None)
        return None

    def _extract_text_content(self, slide_info: Dict[str, Any]) -> str:
        """テキストコンテンツを抽出"""
        texts = []
        for content in slide_info.get('content', []):
            if content.get('type') == 'text':
                texts.append(content.get('text', ''))
        return '\n'.join(texts)

    def _hex_to_rgb(self, hex_color: str) -> RGBColor:
        """HEX色をRGBColorに変換"""
        hex_color = hex_color.lstrip('#')
        return RGBColor(int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))

    def save(self, output_path: str):
        """PowerPointファイルを保存"""
        self.prs.save(output_path)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='PowerPoint生成スクリプト')
    parser.add_argument('--markdown-file', required=True, help='slides.md のパス')
    parser.add_argument('--config', help='config.json のパス')
    parser.add_argument('--title', help='プレゼンテーションタイトル')
    parser.add_argument('--output-dir', default='output', help='出力ディレクトリ')
    parser.add_argument('--template', help='テンプレート.pptx のパス')

    args = parser.parse_args()

    # config を読み込み
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)

    # slides.md を解析
    slides = parse_markdown_file(args.markdown_file)

    # PowerPoint を生成
    generator = PowerPointGenerator(config)
    presentation = generator.generate(slides)

    # 出力ファイル名
    title = args.title or 'presentation'
    output_path = os.path.join(args.output_dir, f'{title}.pptx')

    # 出力ディレクトリを作成
    os.makedirs(args.output_dir, exist_ok=True)

    # ファイルを保存
    generator.save(output_path)
    print(f'✓ PowerPoint生成完了: {output_path}')


if __name__ == '__main__':
    main()
