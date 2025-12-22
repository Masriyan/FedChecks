"""
Report Templates Module for FedChecker.
Provides reusable template components for reports.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph, Table, TableStyle, Spacer, Image,
    HRFlowable, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


@dataclass
class ReportTheme:
    """Theme settings for report styling."""
    primary_color: colors.Color = colors.HexColor('#3C6EB4')
    secondary_color: colors.Color = colors.HexColor('#51A2DA')
    success_color: colors.Color = colors.HexColor('#2ECC71')
    warning_color: colors.Color = colors.HexColor('#F39C12')
    error_color: colors.Color = colors.HexColor('#E74C3C')
    text_color: colors.Color = colors.HexColor('#333333')
    muted_color: colors.Color = colors.HexColor('#7F8C8D')
    background_color: colors.Color = colors.HexColor('#F8F9FA')
    font_family: str = 'Helvetica'
    title_size: int = 24
    heading_size: int = 16
    body_size: int = 10


class ReportTemplates:
    """Provides reusable report components."""

    def __init__(self, theme: ReportTheme = None):
        self.theme = theme or ReportTheme()

    def create_title_block(
        self,
        title: str,
        subtitle: str = None,
        include_logo: bool = True,
    ) -> list:
        """Create a title block with optional logo."""
        elements = []

        # ASCII logo as text (simplified for PDF)
        if include_logo:
            logo_style = ParagraphStyle(
                name='Logo',
                fontName='Courier',
                fontSize=8,
                textColor=self.theme.primary_color,
                alignment=TA_CENTER,
                leading=9,
            )

            logo_text = """
╔═══════════════════════════════════════════╗
║  ███████╗███████╗██████╗ ██████╗██╗  ██╗  ║
║  ██╔════╝██╔════╝██╔══██╗██╔═══╝██║  ██║  ║
║  █████╗  █████╗  ██║  ██║██║    ███████║  ║
║  ██╔══╝  ██╔══╝  ██║  ██║██║    ██╔══██║  ║
║  ██║     ███████╗██████╔╝╚██████╗██║  ██║  ║
║  ╚═╝     ╚══════╝╚═════╝  ╚═════╝╚═╝  ╚═╝  ║
╚═══════════════════════════════════════════╝
""".strip()

            elements.append(Paragraph(
                logo_text.replace('\n', '<br/>'),
                logo_style
            ))
            elements.append(Spacer(1, 10))

        # Title
        title_style = ParagraphStyle(
            name='Title',
            fontName=f'{self.theme.font_family}-Bold',
            fontSize=self.theme.title_size,
            textColor=self.theme.primary_color,
            alignment=TA_CENTER,
            spaceAfter=10,
        )
        elements.append(Paragraph(title, title_style))

        # Subtitle
        if subtitle:
            subtitle_style = ParagraphStyle(
                name='Subtitle',
                fontName=self.theme.font_family,
                fontSize=12,
                textColor=self.theme.muted_color,
                alignment=TA_CENTER,
                spaceAfter=20,
            )
            elements.append(Paragraph(subtitle, subtitle_style))

        # Divider
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=self.theme.primary_color,
            spaceAfter=20,
        ))

        return elements

    def create_info_card(
        self,
        title: str,
        items: list[tuple[str, str]],
        width: float = 6*inch,
    ) -> list:
        """Create an information card with key-value pairs."""
        elements = []

        # Card title
        title_style = ParagraphStyle(
            name='CardTitle',
            fontName=f'{self.theme.font_family}-Bold',
            fontSize=14,
            textColor=self.theme.primary_color,
            spaceAfter=10,
        )
        elements.append(Paragraph(title, title_style))

        # Content table
        data = [[k, v] for k, v in items]

        table = Table(data, colWidths=[width * 0.35, width * 0.65])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.theme.secondary_color),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('FONTNAME', (0, 0), (0, -1), f'{self.theme.font_family}-Bold'),
            ('FONTNAME', (1, 0), (1, -1), self.theme.font_family),
            ('FONTSIZE', (0, 0), (-1, -1), self.theme.body_size),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, self.theme.muted_color),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (1, 0), (1, -1), [colors.white, self.theme.background_color]),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 15))

        return elements

    def create_score_badge(
        self,
        score: float,
        label: str = "Score",
        size: float = 1*inch,
    ) -> Table:
        """Create a score badge element."""
        # Determine color based on score
        if score >= 80:
            color = self.theme.success_color
        elif score >= 60:
            color = self.theme.warning_color
        else:
            color = self.theme.error_color

        # Create badge as a table cell
        data = [[f"{score:.0f}%\n{label}"]]

        badge = Table(data, colWidths=[size], rowHeights=[size])
        badge.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), color),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('FONTNAME', (0, 0), (0, 0), f'{self.theme.font_family}-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 16),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
            ('ROUNDEDCORNERS', [5, 5, 5, 5]),
        ]))

        return badge

    def create_status_table(
        self,
        headers: list[str],
        rows: list[list],
        status_column: int = 0,
        width: float = 6.5*inch,
    ) -> Table:
        """Create a table with status-colored rows."""
        # Prepare data
        data = [headers] + rows

        # Calculate column widths
        num_cols = len(headers)
        col_widths = [width / num_cols] * num_cols

        table = Table(data, colWidths=col_widths)

        # Base style
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), self.theme.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), f'{self.theme.font_family}-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), self.theme.font_family),
            ('FONTSIZE', (0, 0), (-1, -1), self.theme.body_size),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, self.theme.muted_color),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]

        # Alternate row colors
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(('BACKGROUND', (0, i), (-1, i), self.theme.background_color))

        table.setStyle(TableStyle(style))
        return table

    def create_section_header(
        self,
        title: str,
        icon: str = None,
    ) -> list:
        """Create a section header with optional icon."""
        elements = []

        header_style = ParagraphStyle(
            name='SectionHeader',
            fontName=f'{self.theme.font_family}-Bold',
            fontSize=self.theme.heading_size,
            textColor=self.theme.primary_color,
            spaceBefore=15,
            spaceAfter=10,
            borderColor=self.theme.primary_color,
            borderWidth=0,
            borderPadding=0,
            leftIndent=0,
        )

        text = f"{icon} {title}" if icon else title
        elements.append(Paragraph(text, header_style))

        # Underline
        elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=self.theme.secondary_color,
            spaceAfter=10,
        ))

        return elements

    def create_recommendation_box(
        self,
        title: str,
        description: str,
        severity: str = "info",
        fix_command: str = None,
    ) -> list:
        """Create a recommendation box."""
        elements = []

        # Determine color based on severity
        severity_colors = {
            'critical': self.theme.error_color,
            'high': self.theme.error_color,
            'warning': self.theme.warning_color,
            'medium': self.theme.warning_color,
            'info': self.theme.primary_color,
            'low': self.theme.primary_color,
        }
        color = severity_colors.get(severity.lower(), self.theme.primary_color)

        # Box content
        content = []

        # Title with severity badge
        title_text = f"<b>[{severity.upper()}]</b> {title}"
        content.append([Paragraph(title_text, ParagraphStyle(
            name='RecTitle',
            fontName=f'{self.theme.font_family}-Bold',
            fontSize=11,
            textColor=color,
        ))])

        # Description
        content.append([Paragraph(description, ParagraphStyle(
            name='RecDesc',
            fontName=self.theme.font_family,
            fontSize=self.theme.body_size,
            textColor=self.theme.text_color,
        ))])

        # Fix command
        if fix_command:
            content.append([Paragraph(
                f"<b>Fix:</b> <font face='Courier' size='9'>{fix_command}</font>",
                ParagraphStyle(
                    name='RecFix',
                    fontName=self.theme.font_family,
                    fontSize=self.theme.body_size - 1,
                    textColor=self.theme.primary_color,
                )
            )])

        # Create box table
        box = Table(content, colWidths=[6*inch])
        box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 1, color),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(KeepTogether([box]))
        elements.append(Spacer(1, 10))

        return elements

    def create_footer_text(self) -> str:
        """Create footer text."""
        return f"FedChecker Report | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | by sudo3rs"


# Default theme instances
FEDORA_THEME = ReportTheme(
    primary_color=colors.HexColor('#3C6EB4'),
    secondary_color=colors.HexColor('#51A2DA'),
)

DARK_THEME = ReportTheme(
    primary_color=colors.HexColor('#2C3E50'),
    secondary_color=colors.HexColor('#34495E'),
    text_color=colors.HexColor('#ECF0F1'),
    background_color=colors.HexColor('#1A1A2E'),
)
