"""PPTX export service for GRC reports"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE
import io
from datetime import datetime
from typing import List, Dict, Any, Optional


class PPTXExportService:
    """
    Generates branded PPTX presentations for GRC reports.

    Slide types:
    - Title slide: Full-bleed brand color background with company name
    - Section slide: Dark background section divider
    - Table slide: Data table with alternating row colors
    - Chart slide: Bar, pie, or line chart (native PPTX chart objects)
    - Summary slide: Large-number KPI cards
    """

    # Brand palette — Indigo-500 / Slate-800 / Slate-100
    BRAND_COLOR = RGBColor(99, 102, 241)
    DARK_COLOR = RGBColor(30, 41, 59)
    LIGHT_COLOR = RGBColor(241, 245, 249)
    ACCENT_RED = RGBColor(239, 68, 68)
    ACCENT_AMBER = RGBColor(245, 158, 11)
    ACCENT_GREEN = RGBColor(34, 197, 94)
    WHITE = RGBColor(255, 255, 255)
    TEXT_MUTED = RGBColor(100, 116, 139)

    # Severity colour map
    SEVERITY_COLORS = {
        "critical": RGBColor(239, 68, 68),
        "high": RGBColor(249, 115, 22),
        "medium": RGBColor(245, 158, 11),
        "low": RGBColor(34, 197, 94),
    }

    def __init__(self, tenant_name: str = "Governex+"):
        self.tenant_name = tenant_name
        self.prs = Presentation()
        # 16:9 widescreen
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _blank_layout(self):
        """Return the blank slide layout (index 6)."""
        return self.prs.slide_layouts[6]

    def _add_rect(self, slide, left, top, width, height, fill_color: RGBColor, line_color: Optional[RGBColor] = None):
        """Add a filled rectangle shape."""
        from pptx.util import Emu
        shape = slide.shapes.add_shape(
            1,  # MSO_SHAPE_TYPE.RECTANGLE
            left, top, width, height,
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
        if line_color:
            shape.line.color.rgb = line_color
            shape.line.width = Pt(0.75)
        else:
            shape.line.fill.background()
        return shape

    def _add_text_box(self, slide, text: str, left, top, width, height,
                      font_size: int = 18, bold: bool = False,
                      color: RGBColor = None, align=PP_ALIGN.LEFT,
                      word_wrap: bool = True):
        """Add a text box with consistent styling."""
        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.word_wrap = word_wrap
        p = tf.paragraphs[0]
        p.alignment = align
        run = p.add_run()
        run.text = text
        run.font.size = Pt(font_size)
        run.font.bold = bold
        if color:
            run.font.color.rgb = color
        return txBox

    def _set_cell_fill(self, cell, color: RGBColor):
        """Set background color of a table cell."""
        from pptx.oxml.ns import qn
        from lxml import etree
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        # Remove existing solidFill
        for existing in tcPr.findall(qn('a:solidFill')):
            tcPr.remove(existing)
        solidFill = etree.SubElement(tcPr, qn('a:solidFill'))
        srgbClr = etree.SubElement(solidFill, qn('a:srgbClr'))
        srgbClr.set('val', f'{color.rgb:06X}')

    def _style_header_row(self, table, header_color: RGBColor = None):
        """Apply brand header styling to the first row of a table."""
        color = header_color or self.BRAND_COLOR
        for cell in table.rows[0].cells:
            self._set_cell_fill(cell, color)
            for para in cell.text_frame.paragraphs:
                for run in para.runs:
                    run.font.color.rgb = self.WHITE
                    run.font.bold = True
                    run.font.size = Pt(11)

    def _style_data_rows(self, table):
        """Apply alternating row colors to data rows (rows 1+)."""
        for i, row in enumerate(table.rows[1:], start=1):
            bg = self.LIGHT_COLOR if i % 2 == 0 else self.WHITE
            for cell in row.cells:
                self._set_cell_fill(cell, bg)
                for para in cell.text_frame.paragraphs:
                    for run in para.runs:
                        run.font.size = Pt(10)
                        run.font.color.rgb = self.DARK_COLOR

    # -------------------------------------------------------------------------
    # Slide factories
    # -------------------------------------------------------------------------

    def add_title_slide(self, title: str, subtitle: str = "") -> None:
        """Full branded title slide with tenant name and generation timestamp."""
        slide = self.prs.slides.add_slide(self._blank_layout())
        W = self.prs.slide_width
        H = self.prs.slide_height

        # Full-bleed brand background
        self._add_rect(slide, 0, 0, W, H, self.BRAND_COLOR)

        # Decorative bottom stripe
        self._add_rect(slide, 0, H - Inches(1.2), W, Inches(1.2), self.DARK_COLOR)

        # Decorative left accent bar
        self._add_rect(slide, 0, 0, Inches(0.15), H, self.WHITE)

        # Company / product name (top-right)
        self._add_text_box(
            slide, self.tenant_name,
            W - Inches(4), Inches(0.35), Inches(3.8), Inches(0.5),
            font_size=13, bold=True, color=self.WHITE, align=PP_ALIGN.RIGHT,
        )

        # Main title
        self._add_text_box(
            slide, title,
            Inches(0.6), Inches(2.2), W - Inches(1.2), Inches(2.0),
            font_size=40, bold=True, color=self.WHITE, align=PP_ALIGN.LEFT,
        )

        # Subtitle
        if subtitle:
            self._add_text_box(
                slide, subtitle,
                Inches(0.6), Inches(4.4), W - Inches(1.2), Inches(0.7),
                font_size=18, bold=False, color=self.WHITE, align=PP_ALIGN.LEFT,
            )

        # Bottom: generated timestamp
        ts = datetime.utcnow().strftime("Generated %B %d, %Y at %H:%M UTC")
        self._add_text_box(
            slide, ts,
            Inches(0.6), H - Inches(1.0), W - Inches(1.2), Inches(0.5),
            font_size=11, color=self.TEXT_MUTED, align=PP_ALIGN.LEFT,
        )

    def add_section_slide(self, title: str) -> None:
        """Dark section divider slide."""
        slide = self.prs.slides.add_slide(self._blank_layout())
        W = self.prs.slide_width
        H = self.prs.slide_height

        # Dark background
        self._add_rect(slide, 0, 0, W, H, self.DARK_COLOR)

        # Brand accent bar (left)
        self._add_rect(slide, 0, 0, Inches(0.5), H, self.BRAND_COLOR)

        # Section title
        self._add_text_box(
            slide, title,
            Inches(1.0), Inches(2.8), W - Inches(1.5), Inches(1.5),
            font_size=36, bold=True, color=self.WHITE, align=PP_ALIGN.LEFT,
        )

        # Tenant name watermark bottom-right
        self._add_text_box(
            slide, self.tenant_name,
            W - Inches(3.5), H - Inches(0.6), Inches(3.3), Inches(0.5),
            font_size=12, color=self.TEXT_MUTED, align=PP_ALIGN.RIGHT,
        )

    def add_table_slide(self, title: str, headers: List[str], rows: List[List[str]],
                        subtitle: str = "") -> None:
        """Slide with a formatted data table."""
        slide = self.prs.slides.add_slide(self._blank_layout())
        W = self.prs.slide_width
        H = self.prs.slide_height

        # White background
        self._add_rect(slide, 0, 0, W, H, self.WHITE)

        # Header stripe
        self._add_rect(slide, 0, 0, W, Inches(1.4), self.DARK_COLOR)

        # Title
        self._add_text_box(
            slide, title,
            Inches(0.4), Inches(0.2), W - Inches(0.8), Inches(0.8),
            font_size=24, bold=True, color=self.WHITE,
        )

        # Subtitle
        if subtitle:
            self._add_text_box(
                slide, subtitle,
                Inches(0.4), Inches(0.9), W - Inches(0.8), Inches(0.4),
                font_size=12, color=self.LIGHT_COLOR,
            )

        # Page indicator
        self._add_text_box(
            slide, self.tenant_name,
            W - Inches(2.5), H - Inches(0.4), Inches(2.3), Inches(0.35),
            font_size=10, color=self.TEXT_MUTED, align=PP_ALIGN.RIGHT,
        )

        if not headers or not rows:
            self._add_text_box(
                slide, "No data available.",
                Inches(0.4), Inches(1.8), W - Inches(0.8), Inches(1.0),
                font_size=14, color=self.TEXT_MUTED,
            )
            return

        # Clamp rows to what fits on slide (max 20 for readability)
        display_rows = rows[:20]

        cols = len(headers)
        table_rows = len(display_rows) + 1  # +1 for header
        col_width = (W - Inches(0.8)) // cols
        table_height = min(Inches(5.6), Pt(22) * table_rows)

        table = slide.shapes.add_table(
            table_rows, cols,
            Inches(0.4), Inches(1.55),
            W - Inches(0.8), table_height,
        ).table

        # Set column widths
        for ci in range(cols):
            table.columns[ci].width = col_width

        # Header row
        for ci, header in enumerate(headers):
            cell = table.cell(0, ci)
            cell.text = str(header)

        # Data rows
        for ri, row in enumerate(display_rows, start=1):
            for ci, val in enumerate(row[:cols]):
                cell = table.cell(ri, ci)
                cell.text = str(val) if val is not None else ""

        self._style_header_row(table)
        self._style_data_rows(table)

        # Overflow note
        if len(rows) > 20:
            self._add_text_box(
                slide,
                f"Showing 20 of {len(rows)} records. See full report for complete data.",
                Inches(0.4), H - Inches(0.55), W - Inches(0.8), Inches(0.4),
                font_size=9, color=self.TEXT_MUTED,
            )

    def add_chart_slide(self, title: str, chart_data: dict, chart_type: str = "bar") -> None:
        """
        Slide with a native PPTX chart.

        chart_data format:
          {
            "categories": ["Q1", "Q2", "Q3"],
            "series": [
              {"name": "Violations", "values": [12, 8, 15]},
              {"name": "Mitigated", "values": [4, 3, 6]},
            ]
          }
        """
        slide = self.prs.slides.add_slide(self._blank_layout())
        W = self.prs.slide_width
        H = self.prs.slide_height

        # Background
        self._add_rect(slide, 0, 0, W, H, self.WHITE)
        self._add_rect(slide, 0, 0, W, Inches(1.2), self.DARK_COLOR)

        self._add_text_box(
            slide, title,
            Inches(0.4), Inches(0.2), W - Inches(0.8), Inches(0.8),
            font_size=24, bold=True, color=self.WHITE,
        )
        self._add_text_box(
            slide, self.tenant_name,
            W - Inches(2.5), H - Inches(0.4), Inches(2.3), Inches(0.35),
            font_size=10, color=self.TEXT_MUTED, align=PP_ALIGN.RIGHT,
        )

        categories = chart_data.get("categories", [])
        series_list = chart_data.get("series", [])

        if not categories or not series_list:
            self._add_text_box(
                slide, "No chart data available.",
                Inches(0.4), Inches(2.0), W - Inches(0.8), Inches(1.0),
                font_size=14, color=self.TEXT_MUTED,
            )
            return

        cd = ChartData()
        cd.categories = categories
        for s in series_list:
            cd.add_series(s["name"], tuple(s["values"]))

        xl_type_map = {
            "bar": XL_CHART_TYPE.COLUMN_CLUSTERED,
            "column": XL_CHART_TYPE.COLUMN_CLUSTERED,
            "line": XL_CHART_TYPE.LINE,
            "pie": XL_CHART_TYPE.PIE,
            "area": XL_CHART_TYPE.AREA,
        }
        xl_type = xl_type_map.get(chart_type, XL_CHART_TYPE.COLUMN_CLUSTERED)

        chart_left = Inches(0.5)
        chart_top = Inches(1.4)
        chart_width = W - Inches(1.0)
        chart_height = H - Inches(2.0)

        slide.shapes.add_chart(xl_type, chart_left, chart_top, chart_width, chart_height, cd)

    def add_summary_slide(self, title: str, metrics: List[Dict[str, Any]]) -> None:
        """
        KPI summary slide with large-number metric cards.

        metrics: [{"label": "Total Violations", "value": "142", "delta": "+12", "severity": "high"}]
        """
        slide = self.prs.slides.add_slide(self._blank_layout())
        W = self.prs.slide_width
        H = self.prs.slide_height

        self._add_rect(slide, 0, 0, W, H, self.WHITE)
        self._add_rect(slide, 0, 0, W, Inches(1.3), self.DARK_COLOR)

        self._add_text_box(
            slide, title,
            Inches(0.4), Inches(0.22), W - Inches(0.8), Inches(0.8),
            font_size=26, bold=True, color=self.WHITE,
        )
        self._add_text_box(
            slide, self.tenant_name,
            W - Inches(2.5), H - Inches(0.4), Inches(2.3), Inches(0.35),
            font_size=10, color=self.TEXT_MUTED, align=PP_ALIGN.RIGHT,
        )

        max_per_row = 4
        card_w = Inches(2.9)
        card_h = Inches(1.7)
        card_gap = Inches(0.25)
        start_top = Inches(1.6)
        total_cards_w = min(len(metrics), max_per_row) * (card_w + card_gap) - card_gap
        start_left = (W - total_cards_w) / 2

        for i, metric in enumerate(metrics[:8]):  # max 8 cards (2 rows)
            row = i // max_per_row
            col = i % max_per_row
            left = start_left + col * (card_w + card_gap)
            top = start_top + row * (card_h + Inches(0.2))

            severity = metric.get("severity", "").lower()
            accent = self.SEVERITY_COLORS.get(severity, self.BRAND_COLOR)

            # Card background
            self._add_rect(slide, left, top, card_w, card_h, self.LIGHT_COLOR)
            # Top accent bar
            self._add_rect(slide, left, top, card_w, Inches(0.08), accent)

            # Value (large)
            self._add_text_box(
                slide, str(metric.get("value", "—")),
                left + Inches(0.15), top + Inches(0.18), card_w - Inches(0.3), Inches(0.9),
                font_size=34, bold=True, color=self.DARK_COLOR, align=PP_ALIGN.CENTER,
            )
            # Label
            self._add_text_box(
                slide, str(metric.get("label", "")),
                left + Inches(0.1), top + Inches(1.05), card_w - Inches(0.2), Inches(0.45),
                font_size=11, color=self.TEXT_MUTED, align=PP_ALIGN.CENTER,
            )
            # Delta (optional)
            delta = metric.get("delta", "")
            if delta:
                delta_color = self.ACCENT_GREEN if str(delta).startswith("-") else self.ACCENT_RED
                self._add_text_box(
                    slide, str(delta),
                    left + Inches(0.1), top + Inches(1.42), card_w - Inches(0.2), Inches(0.25),
                    font_size=10, color=delta_color, align=PP_ALIGN.CENTER,
                )

    # -------------------------------------------------------------------------
    # Report builders
    # -------------------------------------------------------------------------

    def export_risk_report(self, risks: List[Dict], heatmap: Dict, top_risks: List[Dict]) -> bytes:
        """
        Full risk management PPTX report.

        Args:
            risks: List of violation dicts with keys: user_id, username, rule_id, rule_name,
                   severity, risk_category, status, detected_at
            heatmap: Dict mapping severity -> count, e.g. {"critical": 5, "high": 12, ...}
            top_risks: Top N violations sorted by severity_score desc
        """
        self.__init__(self.tenant_name)  # Reset presentation

        # 1. Title slide
        self.add_title_slide(
            "Enterprise Risk Report",
            f"Generated {datetime.now().strftime('%B %d, %Y')}",
        )

        # 2. Executive summary KPIs
        total = len(risks)
        critical_count = heatmap.get("critical", 0)
        high_count = heatmap.get("high", 0)
        medium_count = heatmap.get("medium", 0)
        low_count = heatmap.get("low", 0)
        open_count = sum(1 for r in risks if r.get("status", "open") in ("open", "new", "active"))

        self.add_summary_slide("Risk Executive Summary", [
            {"label": "Total Violations", "value": str(total), "severity": ""},
            {"label": "Critical", "value": str(critical_count), "severity": "critical"},
            {"label": "High", "value": str(high_count), "severity": "high"},
            {"label": "Medium", "value": str(medium_count), "severity": "medium"},
            {"label": "Low", "value": str(low_count), "severity": "low"},
            {"label": "Open / Unresolved", "value": str(open_count), "severity": "high"},
        ])

        # 3. Section: Violation Heatmap
        self.add_section_slide("Violation Severity Distribution")

        # Heatmap as a 2-column table
        heatmap_rows = [
            [sev.capitalize(), str(cnt),
             f"{(cnt / total * 100):.1f}%" if total > 0 else "0%"]
            for sev, cnt in [
                ("critical", critical_count),
                ("high", high_count),
                ("medium", medium_count),
                ("low", low_count),
            ]
        ]
        self.add_table_slide(
            "Severity Heatmap",
            ["Severity Level", "Violation Count", "Percentage"],
            heatmap_rows,
            subtitle=f"Total violations analysed: {total}",
        )

        # 4. Bar chart of severity distribution
        if total > 0:
            self.add_chart_slide(
                "Violations by Severity",
                {
                    "categories": ["Critical", "High", "Medium", "Low"],
                    "series": [
                        {"name": "Count", "values": [critical_count, high_count, medium_count, low_count]},
                    ],
                },
                chart_type="bar",
            )

        # 5. Section: Top Risks
        self.add_section_slide("Top Risk Violations")

        top_rows = [
            [
                r.get("rule_id", ""),
                r.get("rule_name", ""),
                r.get("severity", "").capitalize(),
                r.get("risk_category", ""),
                r.get("username", r.get("user_id", "")),
                str(r.get("severity_score", "")),
            ]
            for r in (top_risks or risks[:20])
        ]
        self.add_table_slide(
            "Top Risk Violations",
            ["Rule ID", "Rule Name", "Severity", "Category", "User", "Score"],
            top_rows,
            subtitle="Ranked by severity score descending",
        )

        # 6. Section: Full Violation Detail
        self.add_section_slide("Full Violation Detail")

        detail_rows = [
            [
                r.get("user_id", ""),
                r.get("username", ""),
                r.get("rule_id", ""),
                r.get("severity", "").capitalize(),
                r.get("risk_category", ""),
                r.get("status", "open"),
                str(r.get("detected_at", ""))[:10],
            ]
            for r in risks
        ]
        self.add_table_slide(
            "All Violations",
            ["User ID", "Name", "Rule ID", "Severity", "Category", "Status", "Detected"],
            detail_rows,
        )

        return self._to_bytes()

    def export_audit_report(self, engagement: Dict, findings: List[Dict], actions: List[Dict]) -> bytes:
        """
        Audit engagement PPTX report.

        Args:
            engagement: Dict with engagement metadata (id, title, type, status, period, owner)
            findings: List of finding dicts (id, title, severity, status, description, owner)
            actions: List of remediation action dicts (id, description, owner, due_date, status)
        """
        self.__init__(self.tenant_name)

        eng_title = engagement.get("title", "Audit Engagement")
        eng_period = engagement.get("period", "")
        eng_owner = engagement.get("owner", "")

        # 1. Title
        self.add_title_slide(
            eng_title,
            f"Audit Report  |  {eng_period}  |  {eng_owner}",
        )

        # 2. Engagement overview KPIs
        total_findings = len(findings)
        critical_f = sum(1 for f in findings if f.get("severity", "").lower() == "critical")
        high_f = sum(1 for f in findings if f.get("severity", "").lower() == "high")
        open_actions = sum(1 for a in actions if a.get("status", "").lower() not in ("completed", "closed"))
        past_due = sum(
            1 for a in actions
            if a.get("due_date") and a.get("status", "").lower() not in ("completed", "closed")
            and str(a.get("due_date", "")) < datetime.utcnow().strftime("%Y-%m-%d")
        )

        self.add_summary_slide("Engagement Overview", [
            {"label": "Total Findings", "value": str(total_findings), "severity": ""},
            {"label": "Critical Findings", "value": str(critical_f), "severity": "critical"},
            {"label": "High Findings", "value": str(high_f), "severity": "high"},
            {"label": "Open Actions", "value": str(open_actions), "severity": "medium"},
            {"label": "Past Due Actions", "value": str(past_due), "severity": "critical"},
        ])

        # 3. Section: Findings
        self.add_section_slide("Audit Findings")

        finding_rows = [
            [
                f.get("id", ""),
                f.get("title", ""),
                f.get("severity", "").capitalize(),
                f.get("status", "").capitalize(),
                f.get("owner", ""),
                str(f.get("due_date", ""))[:10],
            ]
            for f in findings
        ]
        self.add_table_slide(
            "Audit Findings",
            ["Finding ID", "Title", "Severity", "Status", "Owner", "Due Date"],
            finding_rows,
            subtitle=f"Engagement: {eng_title}",
        )

        # 4. Findings by severity chart
        sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for f in findings:
            sev = f.get("severity", "low").capitalize()
            if sev in sev_counts:
                sev_counts[sev] += 1
        self.add_chart_slide(
            "Findings Distribution",
            {
                "categories": list(sev_counts.keys()),
                "series": [{"name": "Findings", "values": list(sev_counts.values())}],
            },
            chart_type="bar",
        )

        # 5. Section: Remediation Actions
        self.add_section_slide("Remediation Actions")

        action_rows = [
            [
                a.get("id", ""),
                a.get("description", "")[:80],
                a.get("owner", ""),
                str(a.get("due_date", ""))[:10],
                a.get("status", "").capitalize(),
            ]
            for a in actions
        ]
        self.add_table_slide(
            "Remediation Actions",
            ["Action ID", "Description", "Owner", "Due Date", "Status"],
            action_rows,
        )

        return self._to_bytes()

    def export_control_report(self, controls: List[Dict], deficiencies: List[Dict], dashboard: Dict) -> bytes:
        """
        Process control status PPTX report.

        Args:
            controls: List of control dicts (id, name, type, status, owner, last_tested, effectiveness)
            deficiencies: List of deficiency dicts (control_id, description, severity, remediation_due)
            dashboard: Summary dict (total_controls, effective, ineffective, not_tested, coverage_pct)
        """
        self.__init__(self.tenant_name)

        # 1. Title
        self.add_title_slide(
            "Process Control Status Report",
            f"Generated {datetime.now().strftime('%B %d, %Y')}",
        )

        # 2. Control dashboard KPIs
        total = dashboard.get("total_controls", len(controls))
        effective = dashboard.get("effective", 0)
        ineffective = dashboard.get("ineffective", 0)
        not_tested = dashboard.get("not_tested", 0)
        coverage = dashboard.get("coverage_pct", 0)

        self.add_summary_slide("Control Dashboard", [
            {"label": "Total Controls", "value": str(total), "severity": ""},
            {"label": "Effective", "value": str(effective), "severity": "low"},
            {"label": "Ineffective", "value": str(ineffective), "severity": "critical"},
            {"label": "Not Tested", "value": str(not_tested), "severity": "medium"},
            {"label": "Deficiencies", "value": str(len(deficiencies)), "severity": "high"},
            {"label": "Coverage %", "value": f"{coverage:.0f}%", "severity": ""},
        ])

        # 3. Control effectiveness chart
        self.add_chart_slide(
            "Control Effectiveness Distribution",
            {
                "categories": ["Effective", "Ineffective", "Not Tested"],
                "series": [{"name": "Controls", "values": [effective, ineffective, not_tested]}],
            },
            chart_type="pie",
        )

        # 4. Section: Controls
        self.add_section_slide("Control Details")

        control_rows = [
            [
                c.get("id", ""),
                c.get("name", ""),
                c.get("type", ""),
                c.get("status", "").capitalize(),
                c.get("owner", ""),
                str(c.get("last_tested", ""))[:10],
                c.get("effectiveness", ""),
            ]
            for c in controls
        ]
        self.add_table_slide(
            "All Controls",
            ["Control ID", "Name", "Type", "Status", "Owner", "Last Tested", "Effectiveness"],
            control_rows,
        )

        # 5. Section: Deficiencies
        if deficiencies:
            self.add_section_slide("Control Deficiencies")

            def_rows = [
                [
                    d.get("control_id", ""),
                    d.get("description", "")[:80],
                    d.get("severity", "").capitalize(),
                    str(d.get("remediation_due", ""))[:10],
                    d.get("status", "open").capitalize(),
                ]
                for d in deficiencies
            ]
            self.add_table_slide(
                "Control Deficiencies",
                ["Control ID", "Description", "Severity", "Remediation Due", "Status"],
                def_rows,
            )

        return self._to_bytes()

    def export_grc_executive(self, grc_dashboard: Dict) -> bytes:
        """
        Unified GRC executive summary PPTX.

        Args:
            grc_dashboard: Dict with keys:
              - risk: {total_violations, critical, high, medium, low, risk_score}
              - audit: {total_findings, open_findings, past_due}
              - compliance: {frameworks, compliant, non_compliant, coverage_pct}
              - controls: {total, effective, deficiencies}
              - period: str
        """
        self.__init__(self.tenant_name)

        period = grc_dashboard.get("period", datetime.now().strftime("%B %Y"))

        # 1. Title
        self.add_title_slide(
            "GRC Executive Summary",
            f"{self.tenant_name}  |  {period}",
        )

        # 2. Risk section
        risk = grc_dashboard.get("risk", {})
        self.add_section_slide("Risk Management")
        self.add_summary_slide("Risk Overview", [
            {"label": "Total Violations", "value": str(risk.get("total_violations", 0)), "severity": ""},
            {"label": "Critical", "value": str(risk.get("critical", 0)), "severity": "critical"},
            {"label": "High", "value": str(risk.get("high", 0)), "severity": "high"},
            {"label": "Risk Score", "value": f"{risk.get('risk_score', 0):.1f}", "severity": "high"},
        ])

        # Trend chart (if data available)
        risk_trend = risk.get("trend", {})
        if risk_trend:
            self.add_chart_slide(
                "Violation Trend",
                {
                    "categories": list(risk_trend.get("labels", [])),
                    "series": [{"name": "Violations", "values": list(risk_trend.get("values", []))}],
                },
                chart_type="line",
            )

        # 3. Audit section
        audit = grc_dashboard.get("audit", {})
        self.add_section_slide("Audit Management")
        self.add_summary_slide("Audit Overview", [
            {"label": "Total Findings", "value": str(audit.get("total_findings", 0)), "severity": ""},
            {"label": "Open Findings", "value": str(audit.get("open_findings", 0)), "severity": "high"},
            {"label": "Past Due Actions", "value": str(audit.get("past_due", 0)), "severity": "critical"},
        ])

        # 4. Compliance section
        compliance = grc_dashboard.get("compliance", {})
        self.add_section_slide("Compliance")
        self.add_summary_slide("Compliance Overview", [
            {"label": "Frameworks", "value": str(compliance.get("frameworks", 0)), "severity": ""},
            {"label": "Compliant", "value": str(compliance.get("compliant", 0)), "severity": "low"},
            {"label": "Non-Compliant", "value": str(compliance.get("non_compliant", 0)), "severity": "critical"},
            {"label": "Coverage", "value": f"{compliance.get('coverage_pct', 0):.0f}%", "severity": ""},
        ])

        # 5. Controls section
        controls = grc_dashboard.get("controls", {})
        self.add_section_slide("Process Controls")
        self.add_summary_slide("Controls Overview", [
            {"label": "Total Controls", "value": str(controls.get("total", 0)), "severity": ""},
            {"label": "Effective", "value": str(controls.get("effective", 0)), "severity": "low"},
            {"label": "Deficiencies", "value": str(controls.get("deficiencies", 0)), "severity": "critical"},
        ])

        return self._to_bytes()

    # -------------------------------------------------------------------------
    # Serialisation
    # -------------------------------------------------------------------------

    def _to_bytes(self) -> bytes:
        """Serialise the presentation to bytes."""
        buf = io.BytesIO()
        self.prs.save(buf)
        buf.seek(0)
        return buf.read()
