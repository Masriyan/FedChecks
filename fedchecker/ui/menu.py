"""
Interactive TUI menu system for FedChecker.
"""

import sys
import os
from dataclasses import dataclass, field
from typing import Callable, Optional, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED, DOUBLE

from .colors import Colors, StatusIcon


@dataclass
class MenuItem:
    """A single menu item."""
    key: str
    label: str
    icon: str
    action: Optional[Callable] = None
    description: str = ""
    enabled: bool = True
    submenu: Optional['Menu'] = None


@dataclass
class Menu:
    """Interactive menu with keyboard navigation."""
    title: str
    items: list[MenuItem] = field(default_factory=list)
    subtitle: str = ""
    selected_index: int = 0
    console: Console = field(default_factory=Console)

    def add_item(
        self,
        key: str,
        label: str,
        icon: str,
        action: Callable = None,
        description: str = "",
        enabled: bool = True,
    ) -> 'Menu':
        """Add a menu item and return self for chaining."""
        self.items.append(MenuItem(
            key=key,
            label=label,
            icon=icon,
            action=action,
            description=description,
            enabled=enabled,
        ))
        return self

    def render(self) -> Panel:
        """Render the menu as a panel."""
        # Create menu table
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
            collapse_padding=True,
            expand=True,
        )
        table.add_column("Key", justify="center", width=5)
        table.add_column("Icon", justify="center", width=4)
        table.add_column("Label", justify="left")
        table.add_column("Desc", justify="right", style="dim")

        for i, item in enumerate(self.items):
            is_selected = i == self.selected_index

            # Style based on selection and enabled state
            if not item.enabled:
                key_style = "dim"
                icon = "[dim]○[/]"
                label_style = "dim strikethrough"
                desc_style = "dim"
            elif is_selected:
                key_style = f"bold {Colors.FEDORA_LIGHT_BLUE} reverse"
                icon = item.icon
                label_style = f"bold {Colors.FEDORA_LIGHT_BLUE}"
                desc_style = Colors.FEDORA_LIGHT_BLUE
            else:
                key_style = f"bold {Colors.FEDORA_BLUE}"
                icon = item.icon
                label_style = "white"
                desc_style = "dim"

            # Selection indicator
            selector = "▸ " if is_selected else "  "

            table.add_row(
                Text(f"[{item.key}]", style=key_style),
                icon,
                Text(f"{selector}{item.label}", style=label_style),
                Text(item.description, style=desc_style),
            )

        # Create title
        title_text = Text()
        title_text.append(f"  {self.title}  ", style=f"bold {Colors.FEDORA_BLUE}")

        # Create subtitle if present
        content = table
        if self.subtitle:
            subtitle = Text(f"\n{self.subtitle}\n", style="dim italic")
            content = Text()
            content.append_text(subtitle)
            content.append("\n")

        return Panel(
            table,
            title=title_text,
            title_align="center",
            border_style=Colors.FEDORA_BLUE,
            box=ROUNDED,
            padding=(1, 2),
        )

    def move_up(self):
        """Move selection up."""
        self.selected_index = (self.selected_index - 1) % len(self.items)
        # Skip disabled items
        while not self.items[self.selected_index].enabled:
            self.selected_index = (self.selected_index - 1) % len(self.items)

    def move_down(self):
        """Move selection down."""
        self.selected_index = (self.selected_index + 1) % len(self.items)
        # Skip disabled items
        while not self.items[self.selected_index].enabled:
            self.selected_index = (self.selected_index + 1) % len(self.items)

    def select(self) -> Optional[Any]:
        """Execute the selected item's action."""
        item = self.items[self.selected_index]
        if item.enabled and item.action:
            return item.action()
        return None

    def get_key_action(self, key: str) -> Optional[MenuItem]:
        """Get menu item by key."""
        for item in self.items:
            if item.key.lower() == key.lower() and item.enabled:
                return item
        return None


def create_main_menu(console: Console = None) -> Menu:
    """Create the main FedChecker menu."""
    menu = Menu(
        title="FedChecker - Main Menu",
        subtitle="Use arrow keys to navigate, Enter to select, or press the key shortcut",
        console=console or Console(),
    )

    menu.add_item("1", "Health Check", StatusIcon.HEALTH,
                  description="System health analysis")
    menu.add_item("2", "Drivers Check", StatusIcon.DRIVER,
                  description="Hardware driver status")
    menu.add_item("3", "Security Check", StatusIcon.SECURITY,
                  description="Security audit")
    menu.add_item("4", "Desktop Check", StatusIcon.DESKTOP,
                  description="Desktop environment")
    menu.add_item("5", "Post-Install Setup", StatusIcon.ROCKET,
                  description="Configure new system")
    menu.add_item("6", "Auto-Fix Issues", StatusIcon.FIX,
                  description="Fix detected problems")
    menu.add_item("7", "Generate Report", StatusIcon.REPORT,
                  description="Create PDF report")
    menu.add_item("8", "Settings", StatusIcon.SETTINGS,
                  description="Configure FedChecker")
    menu.add_item("0", "Exit", StatusIcon.EXIT,
                  description="Quit FedChecker")

    return menu


def get_keypress() -> str:
    """Get a single keypress from the user."""
    if os.name == 'nt':
        import msvcrt
        key = msvcrt.getch()
        if key == b'\xe0':  # Arrow key prefix on Windows
            key = msvcrt.getch()
            if key == b'H':
                return 'up'
            elif key == b'P':
                return 'down'
            elif key == b'K':
                return 'left'
            elif key == b'M':
                return 'right'
        elif key == b'\r':
            return 'enter'
        elif key == b'\x1b':
            return 'escape'
        return key.decode('utf-8', errors='ignore')
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)

            if ch == '\x1b':  # Escape sequence
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':
                        return 'up'
                    elif ch3 == 'B':
                        return 'down'
                    elif ch3 == 'C':
                        return 'right'
                    elif ch3 == 'D':
                        return 'left'
                return 'escape'
            elif ch == '\r' or ch == '\n':
                return 'enter'
            elif ch == '\x03':  # Ctrl+C
                return 'ctrl+c'
            elif ch == 'q' or ch == 'Q':
                return 'q'

            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def run_menu(menu: Menu, header_func: Callable = None) -> Optional[str]:
    """Run an interactive menu and return the selected key."""
    console = menu.console

    def redraw():
        console.clear()
        if header_func:
            header_func()
        console.print(menu.render())

    # Initial draw
    redraw()

    while True:
        key = get_keypress()

        if key == 'up':
            menu.move_up()
            redraw()
        elif key == 'down':
            menu.move_down()
            redraw()
        elif key == 'enter':
            item = menu.items[menu.selected_index]
            return item.key
        elif key == 'escape' or key == 'q' or key == 'ctrl+c':
            return '0'  # Exit
        else:
            # Check for direct key press
            item = menu.get_key_action(key)
            if item:
                for i, m in enumerate(menu.items):
                    if m.key == item.key:
                        menu.selected_index = i
                        return item.key


def show_submenu(
    console: Console,
    title: str,
    options: list[tuple[str, str, str]],  # (key, label, description)
    header_func: Callable = None,
) -> Optional[str]:
    """Show a simple submenu and return selected key."""
    menu = Menu(title=title, console=console)

    for key, label, desc in options:
        menu.add_item(key, label, StatusIcon.BULLET, description=desc)

    menu.add_item("0", "Back", StatusIcon.EXIT, description="Return to main menu")

    return run_menu(menu, header_func=header_func)


if __name__ == "__main__":
    # Demo the menu
    console = Console()

    def demo_header():
        console.print("[bold cyan]FedChecker Demo[/]\n")

    menu = create_main_menu(console)
    selected = run_menu(menu, header_func=demo_header)
    console.clear()
    console.print(f"[bold green]Selected: {selected}[/]\n")
