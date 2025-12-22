"""
Animated progress bars and spinners for FedChecker.
"""

import time
from typing import Callable, Any, Optional
from contextlib import contextmanager

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner

from .colors import Colors, CheckStatus, CheckResult


class ProgressManager:
    """Manager for animated progress displays."""

    def __init__(self, console: Console = None):
        self.console = console or Console()

    def get_progress(self, description: str = "Processing...") -> Progress:
        """Create a styled progress bar."""
        return Progress(
            SpinnerColumn("dots", style=f"bold {Colors.FEDORA_BLUE}"),
            TextColumn("[bold]{task.description}"),
            BarColumn(
                bar_width=40,
                style=Colors.DIM,
                complete_style=Colors.FEDORA_BLUE,
                finished_style=Colors.SUCCESS,
            ),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            transient=False,
        )

    def get_check_progress(self) -> Progress:
        """Create a progress bar for running checks."""
        return Progress(
            SpinnerColumn("dots12", style=f"bold {Colors.FEDORA_LIGHT_BLUE}"),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(
                bar_width=30,
                style=Colors.DIM,
                complete_style=Colors.FEDORA_BLUE,
                finished_style=Colors.SUCCESS,
            ),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
        )

    def get_download_progress(self) -> Progress:
        """Create a progress bar for downloads/installations."""
        return Progress(
            SpinnerColumn("arc", style="bold green"),
            TextColumn("[bold green]{task.description}"),
            BarColumn(
                bar_width=40,
                style=Colors.DIM,
                complete_style=Colors.SUCCESS,
                finished_style=Colors.SUCCESS,
            ),
            TaskProgressColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=self.console,
        )

    @contextmanager
    def status(self, message: str):
        """Context manager for showing a spinner with status message."""
        with self.console.status(
            f"[bold {Colors.FEDORA_BLUE}]{message}",
            spinner="dots",
            spinner_style=f"bold {Colors.FEDORA_LIGHT_BLUE}",
        ):
            yield

    def run_with_progress(
        self,
        tasks: list[tuple[str, Callable]],
        title: str = "Running checks...",
    ) -> list[Any]:
        """Run tasks with a progress bar and return results."""
        results = []

        with self.get_check_progress() as progress:
            task_id = progress.add_task(title, total=len(tasks))

            for description, task_func in tasks:
                progress.update(task_id, description=description)
                try:
                    result = task_func()
                    results.append(result)
                except Exception as e:
                    results.append(CheckResult(
                        name=description,
                        status=CheckStatus.ERROR,
                        message=f"Error: {str(e)}",
                    ))
                progress.advance(task_id)

        return results


class TaskProgress:
    """Track progress of individual tasks with visual feedback."""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.tasks: list[dict] = []

    def add_task(self, name: str, status: str = "pending") -> int:
        """Add a task and return its index."""
        self.tasks.append({
            "name": name,
            "status": status,
            "result": None,
        })
        return len(self.tasks) - 1

    def update_task(self, index: int, status: str, result: str = None):
        """Update task status."""
        if 0 <= index < len(self.tasks):
            self.tasks[index]["status"] = status
            self.tasks[index]["result"] = result

    def _get_status_icon(self, status: str) -> str:
        """Get icon for status."""
        icons = {
            "pending": "[dim]○[/]",
            "running": "[bold cyan]⟳[/]",
            "success": "[bold green]✓[/]",
            "warning": "[bold yellow]⚠[/]",
            "failed": "[bold red]✗[/]",
            "skipped": "[dim]○[/]",
        }
        return icons.get(status, "[dim]?[/]")

    def render(self) -> Table:
        """Render current task list as a table."""
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 1),
            collapse_padding=True,
        )
        table.add_column("Status", width=3)
        table.add_column("Task")
        table.add_column("Result", style="dim")

        for task in self.tasks:
            icon = self._get_status_icon(task["status"])
            name = task["name"]
            result = task.get("result") or ""

            if task["status"] == "running":
                name = f"[bold cyan]{name}[/]"
            elif task["status"] == "success":
                name = f"[green]{name}[/]"
            elif task["status"] == "failed":
                name = f"[red]{name}[/]"
            elif task["status"] == "warning":
                name = f"[yellow]{name}[/]"

            table.add_row(icon, name, result)

        return table


class AnimatedCheckRunner:
    """Run checks with animated progress display."""

    def __init__(self, console: Console = None):
        self.console = console or Console()

    def run_checks(
        self,
        checks: list[tuple[str, Callable[[], CheckResult]]],
        category_name: str = "System Checks",
    ) -> list[CheckResult]:
        """Run a list of checks with animated progress."""
        results = []
        task_progress = TaskProgress(self.console)

        # Add all tasks
        for name, _ in checks:
            task_progress.add_task(name)

        with Live(
            task_progress.render(),
            console=self.console,
            refresh_per_second=10,
            transient=False,
        ) as live:
            for i, (name, check_func) in enumerate(checks):
                # Mark as running
                task_progress.update_task(i, "running")
                live.update(task_progress.render())

                # Run the check
                try:
                    result = check_func()
                    results.append(result)

                    # Update status based on result
                    if result.status == CheckStatus.PASS:
                        task_progress.update_task(i, "success", result.message)
                    elif result.status == CheckStatus.WARN:
                        task_progress.update_task(i, "warning", result.message)
                    elif result.status == CheckStatus.SKIP:
                        task_progress.update_task(i, "skipped", result.message)
                    else:
                        task_progress.update_task(i, "failed", result.message)

                except Exception as e:
                    results.append(CheckResult(
                        name=name,
                        status=CheckStatus.ERROR,
                        message=str(e),
                    ))
                    task_progress.update_task(i, "failed", str(e))

                live.update(task_progress.render())
                time.sleep(0.1)  # Small delay for visual effect

        return results


def simulate_progress(
    console: Console,
    description: str,
    steps: int = 100,
    delay: float = 0.02,
):
    """Simulate progress for demonstration purposes."""
    pm = ProgressManager(console)

    with pm.get_progress() as progress:
        task = progress.add_task(description, total=steps)

        for _ in range(steps):
            time.sleep(delay)
            progress.advance(task)


if __name__ == "__main__":
    # Demo the progress bars
    console = Console()

    console.print("\n[bold cyan]Progress Bar Demo[/]\n")

    simulate_progress(console, "Scanning system...", steps=50, delay=0.05)

    console.print("\n[bold green]✓ Demo complete![/]\n")
