"""
report.py
---------
Generates a professional PDF weekly report using ReportLab.
Includes:
  - Cover page with title + date range
  - Key statistics summary
  - All charts
  - Actionable recommendations
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    Table, TableStyle, HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "static", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

CHARTS_DIR = os.path.join(os.path.dirname(__file__), "static", "charts")

# ── Colour constants ─────────────────────────────────────────────────
C_DARK   = colors.HexColor("#0f1117")
C_CARD   = colors.HexColor("#1a1d2e")
C_ACCENT = colors.HexColor("#4f8ef7")
C_ORANGE = colors.HexColor("#f7934f")
C_GREEN  = colors.HexColor("#4ff7a0")
C_WHITE  = colors.white
C_GREY   = colors.HexColor("#8890a0")


class ReportGenerator:
    """Builds the full PDF report."""

    def __init__(self, stats: dict, insights: list, predictions: dict,
                 absence: dict, peak_hours):
        self.stats       = stats       # summary stats
        self.insights    = insights    # list of insight dicts
        self.predictions = predictions # {next_7_days, metrics}
        self.absence     = absence     # doctor absence impact
        self.peak_hours  = peak_hours  # DataFrame

        # Build custom styles
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()

    def _add_custom_styles(self):
        """Registers additional paragraph styles."""
        self.styles.add(ParagraphStyle(
            name="CoverTitle",
            fontSize=28, textColor=C_WHITE,
            spaceAfter=8, alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        ))
        self.styles.add(ParagraphStyle(
            name="CoverSub",
            fontSize=13, textColor=C_GREY,
            spaceAfter=4, alignment=TA_CENTER,
            fontName="Helvetica",
        ))
        self.styles.add(ParagraphStyle(
            name="SectionHeader",
            fontSize=15, textColor=C_ACCENT,
            spaceBefore=14, spaceAfter=6,
            fontName="Helvetica-Bold",
        ))
        self.styles.add(ParagraphStyle(
            name="BodyDark",
            fontSize=10, textColor=C_WHITE,
            spaceAfter=4, fontName="Helvetica",
            leading=16,
        ))
        self.styles.add(ParagraphStyle(
            name="InsightHigh",
            fontSize=10, textColor=colors.HexColor("#ff6b6b"),
            spaceAfter=4, fontName="Helvetica-BoldOblique",
        ))
        self.styles.add(ParagraphStyle(
            name="InsightMed",
            fontSize=10, textColor=C_ORANGE,
            spaceAfter=4, fontName="Helvetica-BoldOblique",
        ))
        self.styles.add(ParagraphStyle(
            name="InsightLow",
            fontSize=10, textColor=C_GREEN,
            spaceAfter=4, fontName="Helvetica-BoldOblique",
        ))

    def _chart_image(self, filename: str, width: float = 15 * cm):
        """Returns a ReportLab Image if the chart file exists."""
        path = os.path.join(CHARTS_DIR, filename)
        if os.path.exists(path):
            img = Image(path)
            # Scale proportionally
            scale  = width / img.imageWidth
            img._restrictSize(width, img.imageHeight * scale)
            return img
        return Paragraph(f"[Chart not available: {filename}]",
                          self.styles["BodyDark"])

    def _spacer(self, h: float = 0.4):
        return Spacer(1, h * cm)

    def _hr(self):
        return HRFlowable(width="100%", thickness=0.5,
                          color=C_ACCENT, spaceAfter=6)

    # ── Cover Page ───────────────────────────────────────────────────
    def _build_cover(self) -> list:
        items = []
        items.append(self._spacer(3))
        items.append(Paragraph("🏥 Hospital OPD Analyzer",
                               self.styles["CoverTitle"]))
        items.append(Paragraph("Weekly Performance & Overcrowding Report",
                               self.styles["CoverSub"]))
        items.append(self._spacer(0.5))

        date_range = (f"{self.stats.get('start_date','N/A')} "
                      f"→ {self.stats.get('end_date','N/A')}")
        items.append(Paragraph(f"Data Period: {date_range}",
                               self.styles["CoverSub"]))
        items.append(Paragraph(
            f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}",
            self.styles["CoverSub"]
        ))
        items.append(self._spacer(1))
        items.append(self._hr())

        # Summary stat table
        data = [
            ["Total Records", "Departments", "Date Range"],
            [
                str(self.stats.get("total_records", 0)),
                str(self.stats.get("departments", 0)),
                f"{self.stats.get('start_date','?')} – {self.stats.get('end_date','?')}",
            ]
        ]
        t = Table(data, colWidths=[5 * cm, 5 * cm, 7 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), C_ACCENT),
            ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND",  (0, 1), (-1, -1), C_CARD),
            ("TEXTCOLOR",   (0, 1), (-1, -1), C_WHITE),
            ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",    (0, 0), (-1, -1), 11),
            ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_CARD]),
            ("GRID",        (0, 0), (-1, -1), 0.5, C_ACCENT),
            ("TOPPADDING",  (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        items.append(t)
        items.append(PageBreak())
        return items

    # ── Section: Charts ──────────────────────────────────────────────
    def _build_charts_section(self) -> list:
        items = []
        items.append(Paragraph("📊 Visualizations", self.styles["SectionHeader"]))
        items.append(self._hr())

        chart_files = [
            ("heatmap_volume.png",   "Patient Volume Heatmap (Hour × Department)"),
            ("bar_dept_avg.png",     "Average Wait Time by Department"),
            ("stacked_bar_wait.png", "Wait Time Breakdown by Time Slot"),
            ("line_trend.png",       "Daily Wait Time Trend"),
            ("ridge_weekday.png",    "Weekday Wait Distribution (Ridge Plot)"),
            ("prediction_chart.png", "7-Day Wait Time Prediction"),
        ]
        for filename, caption in chart_files:
            items.append(Paragraph(caption, self.styles["BodyDark"]))
            items.append(self._chart_image(filename))
            items.append(self._spacer(0.5))

        items.append(PageBreak())
        return items

    # ── Section: Insights ────────────────────────────────────────────
    def _build_insights_section(self) -> list:
        items = []
        items.append(Paragraph("💡 Key Insights & Recommendations",
                               self.styles["SectionHeader"]))
        items.append(self._hr())

        style_map = {
            "high":   "InsightHigh",
            "medium": "InsightMed",
            "low":    "InsightLow",
        }
        for ins in self.insights:
            sty = style_map.get(ins.get("severity", "low"), "BodyDark")
            items.append(Paragraph(ins["title"], self.styles[sty]))
            items.append(Paragraph(f"  → {ins['detail']}",
                                   self.styles["BodyDark"]))
            items.append(self._spacer(0.3))

        items.append(PageBreak())
        return items

    # ── Section: Predictions ─────────────────────────────────────────
    def _build_predictions_section(self) -> list:
        items = []
        items.append(Paragraph("🔮 7-Day Wait Time Forecast",
                               self.styles["SectionHeader"]))
        items.append(self._hr())

        preds = self.predictions.get("next_7_days", [])
        if preds:
            header = ["Date", "Day", "Predicted Wait (min)"]
            rows   = [header]
            for p in preds:
                rows.append([
                    p.get("date", ""), p.get("day_of_week", ""),
                    str(p.get("predicted_wait", ""))
                ])
            t = Table(rows, colWidths=[5 * cm, 5 * cm, 7 * cm])
            t.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), C_ACCENT),
                ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND",  (0, 1), (-1, -1), C_CARD),
                ("TEXTCOLOR",   (0, 1), (-1, -1), C_WHITE),
                ("GRID",        (0, 0), (-1, -1), 0.5, C_ACCENT),
                ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING",  (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            items.append(t)

        metrics = self.predictions.get("metrics", {})
        items.append(self._spacer(0.5))
        items.append(Paragraph(
            f"Model Performance → MAE: {metrics.get('mae','N/A')} min | "
            f"R²: {metrics.get('r2','N/A')} | "
            f"Trend: {metrics.get('trend_direction','N/A')}",
            self.styles["BodyDark"]
        ))

        items.append(PageBreak())
        return items

    # ── Section: Doctor Absence ──────────────────────────────────────
    def _build_absence_section(self) -> list:
        items = []
        items.append(Paragraph("🏥 Doctor Absence Impact Analysis",
                               self.styles["SectionHeader"]))
        items.append(self._hr())
        items.append(Paragraph(
            f"Most impacted department: <b>{self.absence.get('worst_dept','N/A')}</b> "
            f"(+{self.absence.get('worst_impact','N/A')} min cascading delay)",
            self.styles["BodyDark"]
        ))
        items.append(self._spacer(0.4))

        table_data = self.absence.get("table", [])
        if table_data:
            header = ["Department", "Normal Avg", "Stressed Avg", "Cascading Delay", "Stressed Days"]
            rows = [header]
            for row in table_data:
                rows.append([
                    row.get("department", ""),
                    f"{row.get('normal_avg_wait', 0)} min",
                    f"{row.get('stressed_avg_wait', 0)} min",
                    f"+{row.get('cascading_delay', 0)} min",
                    str(row.get("stressed_days", 0)),
                ])
            t = Table(rows, colWidths=[4*cm, 3*cm, 3.5*cm, 3.5*cm, 3*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), C_ACCENT),
                ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND",  (0, 1), (-1, -1), C_CARD),
                ("TEXTCOLOR",   (0, 1), (-1, -1), C_WHITE),
                ("GRID",        (0, 0), (-1, -1), 0.5, C_ACCENT),
                ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE",    (0, 0), (-1, -1), 9),
                ("TOPPADDING",  (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            items.append(t)

        return items

    # ── MAIN BUILD ───────────────────────────────────────────────────
    def generate(self, filename: str = "weekly_report.pdf") -> str:
        """Builds the full PDF and saves it. Returns the web path."""
        output_path = os.path.join(REPORTS_DIR, filename)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )

        story = []
        story += self._build_cover()
        story += self._build_charts_section()
        story += self._build_insights_section()
        story += self._build_predictions_section()
        story += self._build_absence_section()

        # Custom page background
        def on_page(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(C_DARK)
            canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
            canvas.restoreState()

        doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
        return f"/static/reports/{filename}"
