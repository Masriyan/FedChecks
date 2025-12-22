"""
PDF Report Generator Module for FedChecker.
Generates comprehensive PDF reports with charts and styling.
"""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable, KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import HorizontalBarChart

import psutil
import distro

from ..ui.colors import CheckCategory, CheckStatus, CheckResult
from .charts import ChartGenerator


class ReportGenerator:
    """Generates PDF reports for FedChecker results."""

    # Colors
    FEDORA_BLUE = colors.HexColor('#3C6EB4')
    FEDORA_DARK = colors.HexColor('#294172')
    FEDORA_LIGHT = colors.HexColor('#51A2DA')
    SUCCESS_GREEN = colors.HexColor('#2ECC71')
    WARNING_YELLOW = colors.HexColor('#F39C12')
    ERROR_RED = colors.HexColor('#E74C3C')
    GRAY = colors.HexColor('#7F8C8D')

    def __init__(self, output_path: str = None):
        self.output_path = output_path or self._default_output_path()
        self.styles = getSampleStyleSheet()
        self.chart_gen = ChartGenerator()
        self._setup_styles()

    def _default_output_path(self) -> str:
        """Generate default output path."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        home = Path.home()
        return str(home / f"fedchecker_report_{timestamp}.pdf")

    def _setup_styles(self):
        """Set up custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.FEDORA_BLUE,
            alignment=TA_CENTER,
            spaceAfter=20,
        ))

        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.GRAY,
            alignment=TA_CENTER,
            spaceAfter=30,
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=self.FEDORA_DARK,
            spaceBefore=20,
            spaceAfter=10,
            borderColor=self.FEDORA_BLUE,
            borderWidth=1,
            borderPadding=5,
        ))

        self.styles.add(ParagraphStyle(
            name='CheckPass',
            parent=self.styles['Normal'],
            textColor=self.SUCCESS_GREEN,
        ))

        self.styles.add(ParagraphStyle(
            name='CheckFail',
            parent=self.styles['Normal'],
            textColor=self.ERROR_RED,
        ))

        self.styles.add(ParagraphStyle(
            name='CheckWarn',
            parent=self.styles['Normal'],
            textColor=self.WARNING_YELLOW,
        ))

    def _get_system_info(self) -> dict:
        """Gather system information."""
        return {
            'hostname': os.uname().nodename,
            'distro': f"{distro.name()} {distro.version()}",
            'kernel': os.uname().release,
            'arch': os.uname().machine,
            'cpu': self._get_cpu_info(),
            'memory': f"{psutil.virtual_memory().total / (1024**3):.1f} GB",
            'disk': f"{psutil.disk_usage('/').total / (1024**3):.1f} GB",
        }

    def _get_cpu_info(self) -> str:
        """Get CPU information."""
        try:
            with open('/proc/cpuinfo') as f:
                for line in f:
                    if 'model name' in line:
                        return line.split(':')[1].strip()
        except:
            pass
        return f"{psutil.cpu_count()} cores"

    def _status_color(self, status: CheckStatus) -> colors.Color:
        """Get color for check status."""
        return {
            CheckStatus.PASS: self.SUCCESS_GREEN,
            CheckStatus.FAIL: self.ERROR_RED,
            CheckStatus.WARN: self.WARNING_YELLOW,
            CheckStatus.SKIP: self.GRAY,
            CheckStatus.ERROR: self.ERROR_RED,
        }.get(status, self.GRAY)

    def _status_symbol(self, status: CheckStatus) -> str:
        """Get symbol for check status."""
        return {
            CheckStatus.PASS: "✓",
            CheckStatus.FAIL: "✗",
            CheckStatus.WARN: "⚠",
            CheckStatus.SKIP: "○",
            CheckStatus.ERROR: "✗",
        }.get(status, "?")

    def _create_header(self, story: list):
        """Create report header."""
        # Banner
        story.append(Paragraph(
            "FedChecker Report",
            self.styles['ReportTitle']
        ))

        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['ReportSubtitle']
        ))

        # Horizontal line
        story.append(HRFlowable(
            width="100%",
            thickness=2,
            color=self.FEDORA_BLUE,
            spaceAfter=20,
        ))

    def _create_system_info_section(self, story: list):
        """Create system information section."""
        story.append(Paragraph("System Information", self.styles['SectionHeader']))

        info = self._get_system_info()

        data = [
            ["Hostname", info['hostname']],
            ["Distribution", info['distro']],
            ["Kernel", info['kernel']],
            ["Architecture", info['arch']],
            ["CPU", info['cpu']],
            ["Memory", info['memory']],
            ["Disk", info['disk']],
        ]

        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.FEDORA_LIGHT),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, self.GRAY),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))

        story.append(table)
        story.append(Spacer(1, 20))

    def _create_summary_section(
        self,
        story: list,
        categories: list[CheckCategory],
    ):
        """Create executive summary section."""
        story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))

        # Calculate overall score
        if categories:
            overall_score = sum(cat.score for cat in categories) / len(categories)
        else:
            overall_score = 0

        # Score gauge chart
        gauge_buf = self.chart_gen.create_health_gauge(overall_score, size=(3, 2.5))
        gauge_img = Image(gauge_buf, width=3*inch, height=2.5*inch)
        story.append(gauge_img)
        story.append(Spacer(1, 10))

        # Summary text
        if overall_score >= 80:
            summary = "Your system is in excellent health. Keep up the good work!"
            color = self.SUCCESS_GREEN
        elif overall_score >= 60:
            summary = "Your system has some issues that should be addressed."
            color = self.WARNING_YELLOW
        else:
            summary = "Your system requires immediate attention. Please review the recommendations."
            color = self.ERROR_RED

        story.append(Paragraph(
            f"<font color='{color.hexval()}'><b>{summary}</b></font>",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 20))

        # Category score comparison chart
        if categories:
            score_chart = self.chart_gen.create_score_bars(categories, size=(6, 3))
            story.append(Image(score_chart, width=6*inch, height=3*inch))
            story.append(Spacer(1, 20))

    def _create_category_section(
        self,
        story: list,
        category: CheckCategory,
    ):
        """Create a section for a check category."""
        story.append(Paragraph(
            f"{category.name}",
            self.styles['SectionHeader']
        ))

        # Category summary
        summary_text = (
            f"<b>Passed:</b> {category.passed} | "
            f"<b>Failed:</b> {category.failed} | "
            f"<b>Warnings:</b> {category.warnings} | "
            f"<b>Score:</b> {category.score:.0f}%"
        )
        story.append(Paragraph(summary_text, self.styles['Normal']))
        story.append(Spacer(1, 10))

        # Results table
        data = [["Status", "Check", "Result"]]

        for result in category.results:
            status_color = self._status_color(result.status)
            symbol = self._status_symbol(result.status)

            data.append([
                symbol,
                result.name,
                result.message,
            ])

        table = Table(data, colWidths=[0.5*inch, 2.5*inch, 3.5*inch])

        # Table styling
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), self.FEDORA_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, self.GRAY),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]

        # Color-code status column
        for i, result in enumerate(category.results, start=1):
            color = self._status_color(result.status)
            style.append(('TEXTCOLOR', (0, i), (0, i), color))
            style.append(('FONTNAME', (0, i), (0, i), 'Helvetica-Bold'))

        table.setStyle(TableStyle(style))
        story.append(table)
        story.append(Spacer(1, 20))

    def _create_recommendations_section(
        self,
        story: list,
        categories: list[CheckCategory],
    ):
        """Create recommendations section."""
        story.append(PageBreak())
        story.append(Paragraph("Recommendations", self.styles['SectionHeader']))

        recommendations = []

        for category in categories:
            for result in category.results:
                if result.status in (CheckStatus.FAIL, CheckStatus.WARN):
                    recommendations.append({
                        'category': category.name,
                        'check': result.name,
                        'message': result.message,
                        'details': result.details,
                        'fix': result.fix_command if result.fix_available else None,
                        'severity': 'High' if result.status == CheckStatus.FAIL else 'Medium',
                    })

        if not recommendations:
            story.append(Paragraph(
                "<i>No recommendations - all checks passed!</i>",
                self.styles['Normal']
            ))
            return

        # Sort by severity
        recommendations.sort(key=lambda x: x['severity'] == 'High', reverse=True)

        for i, rec in enumerate(recommendations, 1):
            severity_color = self.ERROR_RED if rec['severity'] == 'High' else self.WARNING_YELLOW

            story.append(Paragraph(
                f"<font color='{severity_color.hexval()}'><b>{i}. [{rec['severity']}] "
                f"{rec['category']}: {rec['check']}</b></font>",
                self.styles['Normal']
            ))
            story.append(Paragraph(
                f"<i>{rec['message']}</i>",
                self.styles['Normal']
            ))

            if rec['details']:
                story.append(Paragraph(
                    f"Details: {rec['details']}",
                    self.styles['Normal']
                ))

            if rec['fix']:
                story.append(Paragraph(
                    f"<font color='#3C6EB4'><b>Fix command:</b></font> "
                    f"<font face='Courier'>{rec['fix']}</font>",
                    self.styles['Normal']
                ))

            story.append(Spacer(1, 10))

    def _create_footer(self, canvas, doc):
        """Create page footer."""
        canvas.saveState()

        # Footer line
        canvas.setStrokeColor(self.FEDORA_BLUE)
        canvas.setLineWidth(1)
        canvas.line(inch, 0.5*inch, doc.pagesize[0] - inch, 0.5*inch)

        # Footer text
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self.GRAY)
        canvas.drawString(
            inch, 0.3*inch,
            f"FedChecker Report - Generated {datetime.now().strftime('%Y-%m-%d')}"
        )
        canvas.drawRightString(
            doc.pagesize[0] - inch, 0.3*inch,
            f"Page {doc.page}"
        )

        # Branding
        canvas.setFillColor(self.FEDORA_BLUE)
        canvas.drawCentredString(
            doc.pagesize[0] / 2, 0.3*inch,
            "by sudo3rs"
        )

        canvas.restoreState()

    def generate(
        self,
        categories: list[CheckCategory],
        output_path: str = None,
    ) -> str:
        """Generate the PDF report."""
        output = output_path or self.output_path

        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
        )

        story = []

        # Build report sections
        self._create_header(story)
        self._create_system_info_section(story)
        self._create_summary_section(story, categories)

        story.append(PageBreak())

        # Category sections
        for category in categories:
            self._create_category_section(story, category)

        # Recommendations
        self._create_recommendations_section(story, categories)

        # Build PDF
        doc.build(story, onFirstPage=self._create_footer, onLaterPages=self._create_footer)

        return output


if __name__ == "__main__":
    from rich.console import Console

    console = Console()

    # Create test data
    health_results = [
        CheckResult("Disk Space", CheckStatus.PASS, "Root: 45% used"),
        CheckResult("Memory", CheckStatus.PASS, "8GB, 60% used"),
        CheckResult("CPU Temp", CheckStatus.WARN, "78°C - High"),
        CheckResult("Failed Units", CheckStatus.FAIL, "2 failed units"),
    ]

    security_results = [
        CheckResult("Firewall", CheckStatus.PASS, "Active"),
        CheckResult("SELinux", CheckStatus.PASS, "Enforcing"),
        CheckResult("SSH", CheckStatus.WARN, "Root login enabled", fix_available=True, fix_command="sed -i ..."),
    ]

    categories = [
        CheckCategory("Health", "", health_results),
        CheckCategory("Security", "", security_results),
    ]

    # Generate report
    gen = ReportGenerator()
    output = gen.generate(categories)

    console.print(f"[bold green]Report generated: {output}[/]")
