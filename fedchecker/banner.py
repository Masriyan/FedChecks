"""
ASCII Banner for FedChecker
by sudo3rs
"""

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

BANNER = r"""
███████╗███████╗██████╗  ██████╗██╗  ██╗███████╗ ██████╗██╗  ██╗███████╗██████╗
██╔════╝██╔════╝██╔══██╗██╔════╝██║  ██║██╔════╝██╔════╝██║ ██╔╝██╔════╝██╔══██╗
█████╗  █████╗  ██║  ██║██║     ███████║█████╗  ██║     █████╔╝ █████╗  ██████╔╝
██╔══╝  ██╔══╝  ██║  ██║██║     ██╔══██║██╔══╝  ██║     ██╔═██╗ ██╔══╝  ██╔══██╗
██║     ███████╗██████╔╝╚██████╗██║  ██║███████╗╚██████╗██║  ██╗███████╗██║  ██║
╚═╝     ╚══════╝╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
"""

BANNER_SMALL = r"""
 ___        _  ___ _           _
| __|__ _ _| |/ __| |_  ___ __| |_____ _ _
| _/ -_) _` | (__| ' \/ -_) _| / / -_) '_|
|_|\___\__,_|\___|_||_\___\__|_\_\___|_|
"""

TAGLINE = "Fedora Linux Health & Setup Tool"
AUTHOR = "by sudo3rs"
VERSION = "v1.0.0"


def get_gradient_banner() -> Text:
    """Create a gradient-colored banner."""
    text = Text()
    lines = BANNER.strip().split('\n')

    # Fedora blue gradient colors
    colors = [
        "#3C6EB4",  # Fedora blue
        "#294172",  # Dark blue
        "#51A2DA",  # Light blue
        "#3C6EB4",  # Fedora blue
        "#294172",  # Dark blue
        "#51A2DA",  # Light blue
    ]

    for i, line in enumerate(lines):
        color = colors[i % len(colors)]
        text.append(line + "\n", style=f"bold {color}")

    return text


def print_banner(console: Console = None, small: bool = False, clear: bool = False) -> None:
    """Print the FedChecker banner with styling."""
    if console is None:
        console = Console()

    if clear:
        console.clear()

    # Choose banner size
    banner_text = BANNER_SMALL if small else BANNER

    # Create gradient banner
    if small:
        banner = Text(banner_text.strip(), style="bold #3C6EB4")
    else:
        banner = get_gradient_banner()

    # Create info line
    info = Text()
    info.append(f"\n{TAGLINE}\n", style="bold white")
    info.append(f"{AUTHOR} ", style="dim cyan")
    info.append(f"| {VERSION}", style="dim yellow")

    # Combine banner and info
    full_banner = Text()
    full_banner.append_text(banner)
    full_banner.append_text(info)

    # Create panel
    panel = Panel(
        Align.center(full_banner),
        border_style="#3C6EB4",
        padding=(1, 2),
    )

    console.print(panel)
    console.print()


def get_header(title: str) -> Panel:
    """Create a styled header panel for sections."""
    return Panel(
        Align.center(Text(title, style="bold white")),
        border_style="#3C6EB4",
        padding=(0, 2),
    )


if __name__ == "__main__":
    # Test banner display
    console = Console()
    print_banner(console, clear=True)
    print_banner(console, small=True)
