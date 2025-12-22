"""
Chart Generator Module for FedChecker.
Creates matplotlib charts for PDF reports.
"""

import io
from typing import Optional

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure

from ..ui.colors import CheckCategory, CheckStatus, Colors


class ChartGenerator:
    """Generates charts for PDF reports."""

    # Color scheme
    COLORS = {
        'pass': '#2ECC71',    # Green
        'fail': '#E74C3C',    # Red
        'warn': '#F39C12',    # Yellow/Orange
        'skip': '#95A5A6',    # Gray
        'primary': '#3C6EB4', # Fedora Blue
        'secondary': '#51A2DA',
        'background': '#F8F9FA',
    }

    def __init__(self):
        # Set matplotlib style
        plt.style.use('seaborn-v0_8-whitegrid')
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.size'] = 10

    def create_health_gauge(
        self,
        score: float,
        title: str = "Overall Health Score",
        size: tuple = (4, 3),
    ) -> io.BytesIO:
        """Create a gauge chart for health score."""
        fig, ax = plt.subplots(figsize=size, subplot_kw={'projection': 'polar'})

        # Gauge parameters
        theta = score / 100 * 180  # Convert to degrees (half circle)
        theta_rad = theta * 3.14159 / 180

        # Draw gauge background
        ax.barh(0, 180 * 3.14159 / 180, height=0.5, left=0,
                color=self.COLORS['background'], edgecolor='none')

        # Draw gauge value
        color = self._score_to_color(score)
        ax.barh(0, theta_rad, height=0.5, left=0,
                color=color, edgecolor='none')

        # Configure axes
        ax.set_theta_zero_location('W')
        ax.set_theta_direction(-1)
        ax.set_thetamin(0)
        ax.set_thetamax(180)
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticklabels([])
        ax.set_xticklabels([])
        ax.spines['polar'].set_visible(False)
        ax.grid(False)

        # Add score text
        ax.text(0, -0.1, f'{score:.0f}%', ha='center', va='center',
                fontsize=24, fontweight='bold', color=color,
                transform=ax.transAxes)
        ax.text(0, -0.25, title, ha='center', va='center',
                fontsize=10, color='#333333',
                transform=ax.transAxes)

        # Save to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        return buf

    def create_category_pie(
        self,
        category: CheckCategory,
        size: tuple = (4, 3),
    ) -> io.BytesIO:
        """Create a pie chart for category results."""
        fig, ax = plt.subplots(figsize=size)

        # Data
        passed = category.passed
        failed = category.failed
        warnings = category.warnings
        skipped = category.total - passed - failed - warnings

        sizes = [passed, failed, warnings, skipped]
        labels = ['Passed', 'Failed', 'Warnings', 'Skipped']
        colors = [
            self.COLORS['pass'],
            self.COLORS['fail'],
            self.COLORS['warn'],
            self.COLORS['skip'],
        ]

        # Filter out zeros
        filtered = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]
        if not filtered:
            filtered = [(1, 'No Data', self.COLORS['skip'])]

        sizes, labels, colors = zip(*filtered)

        # Create pie
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,
            colors=colors,
            autopct='%1.0f%%',
            startangle=90,
            pctdistance=0.75,
        )

        # Style autopct text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')

        # Add legend
        ax.legend(
            wedges, labels,
            title=category.name,
            loc='center left',
            bbox_to_anchor=(1, 0, 0.5, 1),
        )

        ax.set_title(f'{category.name}', fontweight='bold', pad=10)

        # Save to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        return buf

    def create_score_bars(
        self,
        categories: list[CheckCategory],
        size: tuple = (6, 4),
    ) -> io.BytesIO:
        """Create a horizontal bar chart comparing category scores."""
        fig, ax = plt.subplots(figsize=size)

        # Data
        names = [cat.name.replace(" Check", "") for cat in categories]
        scores = [cat.score for cat in categories]
        colors = [self._score_to_color(s) for s in scores]

        # Create bars
        y_pos = range(len(names))
        bars = ax.barh(y_pos, scores, color=colors, height=0.6)

        # Add score labels
        for bar, score in zip(bars, scores):
            width = bar.get_width()
            ax.text(
                width + 2, bar.get_y() + bar.get_height() / 2,
                f'{score:.0f}%',
                va='center', ha='left',
                fontweight='bold', fontsize=10,
            )

        # Configure axes
        ax.set_yticks(y_pos)
        ax.set_yticklabels(names)
        ax.set_xlim(0, 110)
        ax.set_xlabel('Score (%)')
        ax.set_title('Category Scores', fontweight='bold', pad=15)

        # Add reference lines
        ax.axvline(x=70, color='#F39C12', linestyle='--', alpha=0.5, label='Warning')
        ax.axvline(x=50, color='#E74C3C', linestyle='--', alpha=0.5, label='Critical')

        ax.invert_yaxis()
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Save to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        return buf

    def create_disk_usage_pie(
        self,
        partitions: list[tuple[str, float, float]],  # (name, used, total)
        size: tuple = (5, 4),
    ) -> io.BytesIO:
        """Create a pie chart for disk usage."""
        fig, ax = plt.subplots(figsize=size)

        if not partitions:
            ax.text(0.5, 0.5, 'No disk data', ha='center', va='center')
            ax.axis('off')
        else:
            # Use the first/main partition
            name, used, total = partitions[0]
            free = total - used

            sizes = [used, free]
            labels = [f'Used\n{used:.1f} GB', f'Free\n{free:.1f} GB']

            usage_percent = (used / total) * 100 if total > 0 else 0
            used_color = self._score_to_color(100 - usage_percent)

            colors = [used_color, '#E8E8E8']

            wedges, texts = ax.pie(
                sizes,
                labels=labels,
                colors=colors,
                startangle=90,
                wedgeprops={'linewidth': 2, 'edgecolor': 'white'},
            )

            # Add center text
            ax.text(0, 0, f'{usage_percent:.0f}%\nUsed',
                    ha='center', va='center',
                    fontsize=14, fontweight='bold')

            ax.set_title(f'Disk Usage ({name})', fontweight='bold', pad=10)

        # Save to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        return buf

    def create_memory_bar(
        self,
        used_gb: float,
        total_gb: float,
        size: tuple = (5, 1.5),
    ) -> io.BytesIO:
        """Create a memory usage bar chart."""
        fig, ax = plt.subplots(figsize=size)

        usage_percent = (used_gb / total_gb) * 100 if total_gb > 0 else 0
        free_gb = total_gb - used_gb

        # Draw background bar
        ax.barh(0, 100, height=0.5, color='#E8E8E8')

        # Draw usage bar
        color = self._score_to_color(100 - usage_percent)
        ax.barh(0, usage_percent, height=0.5, color=color)

        # Add labels
        ax.text(usage_percent / 2, 0, f'{used_gb:.1f} GB used',
                ha='center', va='center', color='white', fontweight='bold')
        ax.text(usage_percent + (100 - usage_percent) / 2, 0,
                f'{free_gb:.1f} GB free',
                ha='center', va='center', color='#666666')

        # Configure axes
        ax.set_xlim(0, 100)
        ax.set_ylim(-0.5, 0.5)
        ax.axis('off')
        ax.set_title(f'Memory Usage ({usage_percent:.0f}% of {total_gb:.1f} GB)',
                     fontweight='bold', pad=10, loc='left')

        # Save to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        return buf

    def create_summary_table_image(
        self,
        categories: list[CheckCategory],
        size: tuple = (6, 3),
    ) -> io.BytesIO:
        """Create a summary table as an image."""
        fig, ax = plt.subplots(figsize=size)
        ax.axis('off')

        # Table data
        headers = ['Category', 'Passed', 'Failed', 'Warnings', 'Score']
        data = []

        for cat in categories:
            data.append([
                cat.name.replace(" Check", ""),
                str(cat.passed),
                str(cat.failed),
                str(cat.warnings),
                f'{cat.score:.0f}%',
            ])

        # Create table
        table = ax.table(
            cellText=data,
            colLabels=headers,
            loc='center',
            cellLoc='center',
        )

        # Style table
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)

        # Style header
        for j in range(len(headers)):
            table[(0, j)].set_facecolor(self.COLORS['primary'])
            table[(0, j)].set_text_props(color='white', fontweight='bold')

        # Style score cells based on value
        for i in range(len(data)):
            score = categories[i].score
            table[(i + 1, 4)].set_facecolor(self._score_to_color(score))
            table[(i + 1, 4)].set_text_props(color='white', fontweight='bold')

        # Save to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        buf.seek(0)
        plt.close(fig)

        return buf

    def _score_to_color(self, score: float) -> str:
        """Convert a score to a color."""
        if score >= 80:
            return self.COLORS['pass']
        elif score >= 60:
            return self.COLORS['warn']
        else:
            return self.COLORS['fail']


if __name__ == "__main__":
    # Test chart generation
    from ..ui.colors import CheckResult, CheckStatus, CheckCategory

    results = [
        CheckResult("Test 1", CheckStatus.PASS, "OK"),
        CheckResult("Test 2", CheckStatus.PASS, "OK"),
        CheckResult("Test 3", CheckStatus.WARN, "Warning"),
        CheckResult("Test 4", CheckStatus.FAIL, "Failed"),
    ]

    category = CheckCategory(
        name="Test Category",
        icon="",
        results=results,
    )

    gen = ChartGenerator()

    # Generate gauge
    gauge = gen.create_health_gauge(75)
    with open("/tmp/gauge.png", "wb") as f:
        f.write(gauge.read())
    print("Generated gauge.png")

    # Generate pie
    pie = gen.create_category_pie(category)
    with open("/tmp/pie.png", "wb") as f:
        f.write(pie.read())
    print("Generated pie.png")
