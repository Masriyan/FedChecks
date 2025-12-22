"""
Color definitions and status icons for FedChecker UI.
"""

from enum import Enum
from dataclasses import dataclass


class Colors:
    """Color palette for FedChecker - Fedora inspired."""

    # Primary colors
    FEDORA_BLUE = "#3C6EB4"
    FEDORA_DARK_BLUE = "#294172"
    FEDORA_LIGHT_BLUE = "#51A2DA"

    # Status colors
    SUCCESS = "#2ECC71"
    WARNING = "#F39C12"
    ERROR = "#E74C3C"
    INFO = "#3498DB"

    # UI colors
    HEADER = "#3C6EB4"
    BORDER = "#3C6EB4"
    TEXT = "#FFFFFF"
    DIM = "#7F8C8D"
    HIGHLIGHT = "#51A2DA"

    # Check result colors
    PASS = "#2ECC71"
    FAIL = "#E74C3C"
    WARN = "#F39C12"
    SKIP = "#95A5A6"


class StatusIcon:
    """Unicode icons for status display."""

    # Status indicators
    PASS = "[bold green]✓[/]"
    FAIL = "[bold red]✗[/]"
    WARN = "[bold yellow]⚠[/]"
    INFO = "[bold blue]ℹ[/]"
    SKIP = "[dim]○[/]"
    RUNNING = "[bold cyan]⟳[/]"
    PENDING = "[dim]◌[/]"

    # Menu icons
    HEALTH = "[bold green]🏥[/]"
    DRIVER = "[bold yellow]🔧[/]"
    SECURITY = "[bold red]🛡️[/]"
    DESKTOP = "[bold blue]🖥️[/]"
    ROCKET = "[bold magenta]🚀[/]"
    FIX = "[bold cyan]🔄[/]"
    REPORT = "[bold white]📊[/]"
    SETTINGS = "[dim]⚙️[/]"
    EXIT = "[dim]🚪[/]"

    # Progress icons
    ARROW_RIGHT = "➜"
    BULLET = "●"
    STAR = "★"
    CHECK = "✔"
    CROSS = "✖"


class CheckStatus(Enum):
    """Status for check results."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class CheckResult:
    """Result of a single check."""
    name: str
    status: CheckStatus
    message: str
    details: str = ""
    fix_available: bool = False
    fix_command: str = ""

    def get_icon(self) -> str:
        """Get the status icon for this result."""
        icons = {
            CheckStatus.PASS: StatusIcon.PASS,
            CheckStatus.FAIL: StatusIcon.FAIL,
            CheckStatus.WARN: StatusIcon.WARN,
            CheckStatus.SKIP: StatusIcon.SKIP,
            CheckStatus.ERROR: StatusIcon.FAIL,
        }
        return icons.get(self.status, StatusIcon.INFO)

    def get_color(self) -> str:
        """Get the color for this result."""
        colors = {
            CheckStatus.PASS: Colors.PASS,
            CheckStatus.FAIL: Colors.FAIL,
            CheckStatus.WARN: Colors.WARN,
            CheckStatus.SKIP: Colors.SKIP,
            CheckStatus.ERROR: Colors.ERROR,
        }
        return colors.get(self.status, Colors.INFO)


@dataclass
class CheckCategory:
    """A category of checks with results."""
    name: str
    icon: str
    results: list[CheckResult]

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.FAIL)

    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.WARN)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def score(self) -> float:
        """Calculate health score (0-100)."""
        if self.total == 0:
            return 100.0
        passed_weight = self.passed * 1.0
        warn_weight = self.warnings * 0.5
        return ((passed_weight + warn_weight) / self.total) * 100

    @property
    def overall_status(self) -> CheckStatus:
        """Get overall status for the category."""
        if self.failed > 0:
            return CheckStatus.FAIL
        elif self.warnings > 0:
            return CheckStatus.WARN
        return CheckStatus.PASS
