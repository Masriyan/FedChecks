"""
FedChecker - Main Application
Fedora Linux Health & Setup Tool by sudo3rs
"""

import sys
import os
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from . import __version__, __app_name__, __author__
from .banner import print_banner, get_header
from .ui.menu import Menu, create_main_menu, run_menu, get_keypress
from .ui.colors import Colors, StatusIcon, CheckCategory, CheckStatus
from .ui.progress import ProgressManager, AnimatedCheckRunner

from .checks.health import HealthChecker
from .checks.drivers import DriverChecker
from .checks.security import SecurityChecker
from .checks.desktop import DesktopChecker

from .fixes.health_fix import HealthFixer
from .fixes.driver_fix import DriverFixer
from .fixes.security_fix import SecurityFixer
from .fixes.desktop_fix import DesktopFixer

from .postinstall.dnf_optimizer import DNFOptimizer
from .postinstall.repos import RepoSetup
from .postinstall.codecs import CodecInstaller
from .postinstall.devtools import DevToolsInstaller

from .reports.generator import ReportGenerator


class FedChecker:
    """Main FedChecker application."""

    def __init__(self):
        self.console = Console()
        self.progress = ProgressManager(self.console)
        self.check_results: dict[str, CheckCategory] = {}

    def run(self):
        """Run the main application loop."""
        def show_banner():
            print_banner(self.console)

        while True:
            menu = create_main_menu(self.console)
            choice = run_menu(menu, header_func=show_banner)

            self.console.clear()
            print_banner(self.console, small=True)

            if choice == '0':
                self._exit()
                break
            elif choice == '1':
                self._run_health_check()
            elif choice == '2':
                self._run_driver_check()
            elif choice == '3':
                self._run_security_check()
            elif choice == '4':
                self._run_desktop_check()
            elif choice == '5':
                self._run_post_install()
            elif choice == '6':
                self._run_auto_fix()
            elif choice == '7':
                self._generate_report()
            elif choice == '8':
                self._show_settings()

            self._wait_for_key()

    def _wait_for_key(self):
        """Wait for user to press a key."""
        self.console.print("\n[dim]Press any key to continue...[/]")
        get_keypress()

    def _display_category_results(self, category: CheckCategory):
        """Display results for a check category."""
        # Store results for report
        self.check_results[category.name] = category

        # Create results table
        table = Table(
            title=f"{category.icon} {category.name} Results",
            show_header=True,
            header_style=f"bold {Colors.FEDORA_BLUE}",
        )
        table.add_column("Status", width=6, justify="center")
        table.add_column("Check", style="cyan")
        table.add_column("Result")
        table.add_column("Fix", width=4, justify="center")

        for result in category.results:
            fix_icon = "[green]✓[/]" if result.fix_available else "[dim]-[/]"
            table.add_row(
                result.get_icon(),
                result.name,
                result.message,
                fix_icon,
            )

        self.console.print(table)

        # Summary
        summary = Text()
        summary.append(f"\nScore: ", style="bold")
        score_color = "green" if category.score >= 80 else "yellow" if category.score >= 60 else "red"
        summary.append(f"{category.score:.0f}%", style=f"bold {score_color}")
        summary.append(f" | Passed: {category.passed} | Failed: {category.failed} | Warnings: {category.warnings}")

        self.console.print(Panel(summary, border_style=Colors.FEDORA_BLUE))

    def _run_health_check(self):
        """Run health checks."""
        self.console.print(get_header("Health Check"))
        self.console.print()

        checker = HealthChecker()

        with self.progress.status("Running health checks..."):
            category = checker.run_all_checks()

        self._display_category_results(category)

    def _run_driver_check(self):
        """Run driver checks."""
        self.console.print(get_header("Driver Check"))
        self.console.print()

        checker = DriverChecker()

        with self.progress.status("Checking hardware drivers..."):
            category = checker.run_all_checks()

        self._display_category_results(category)

    def _run_security_check(self):
        """Run security checks."""
        self.console.print(get_header("Security Check"))
        self.console.print()

        checker = SecurityChecker()

        with self.progress.status("Running security audit..."):
            category = checker.run_all_checks()

        self._display_category_results(category)

    def _run_desktop_check(self):
        """Run desktop environment checks."""
        self.console.print(get_header("Desktop Environment Check"))
        self.console.print()

        checker = DesktopChecker()

        with self.progress.status("Checking desktop environment..."):
            category = checker.run_all_checks()

        self._display_category_results(category)

    def _run_post_install(self):
        """Run post-installation setup."""
        def show_header():
            print_banner(self.console, small=True)
            self.console.print(get_header("Post-Install Setup"))
            self.console.print()

        # Sub-menu for post-install options
        menu = Menu(
            title="Post-Install Options",
            console=self.console,
        )

        menu.add_item("1", "DNF Optimization", StatusIcon.ROCKET,
                      description="Configure fastest mirrors")
        menu.add_item("2", "Repository Setup", StatusIcon.FIX,
                      description="RPM Fusion, Flathub")
        menu.add_item("3", "Multimedia Codecs", StatusIcon.DESKTOP,
                      description="Video/audio codecs")
        menu.add_item("4", "Development Tools", StatusIcon.SETTINGS,
                      description="Git, compilers, etc.")
        menu.add_item("5", "Full Setup", StatusIcon.ROCKET,
                      description="All of the above")
        menu.add_item("0", "Back", StatusIcon.EXIT)

        choice = run_menu(menu, header_func=show_header)

        self.console.clear()
        print_banner(self.console, small=True)

        if choice == '1':
            optimizer = DNFOptimizer(self.console)
            optimizer.run()
        elif choice == '2':
            setup = RepoSetup(self.console)
            setup.run()
        elif choice == '3':
            installer = CodecInstaller(self.console)
            installer.run()
        elif choice == '4':
            installer = DevToolsInstaller(self.console)
            installer.run()
        elif choice == '5':
            self._run_full_post_install()

    def _run_full_post_install(self):
        """Run complete post-installation setup."""
        self.console.print("\n[bold cyan]Running full post-install setup...[/]\n")

        if not Confirm.ask("This will configure DNF, add repositories, install codecs, and dev tools. Continue?"):
            return

        steps = [
            ("DNF Optimization", DNFOptimizer),
            ("Repository Setup", RepoSetup),
            ("Multimedia Codecs", CodecInstaller),
            ("Development Tools", DevToolsInstaller),
        ]

        for name, installer_class in steps:
            self.console.print(f"\n[bold]{name}[/]")
            self.console.print("-" * 40)

            installer = installer_class(self.console)
            if hasattr(installer, 'run'):
                installer.run()

        self.console.print("\n[bold green]✓ Post-installation setup complete![/]")

    def _run_auto_fix(self):
        """Run auto-fix for detected issues."""
        self.console.print(get_header("Auto-Fix Issues"))
        self.console.print()

        if not self.check_results:
            self.console.print("[yellow]No checks have been run yet.[/]")
            self.console.print("Please run checks first to detect issues.")
            return

        # Collect all fixable issues
        fixable = []
        for category in self.check_results.values():
            for result in category.results:
                if result.fix_available and result.status in (CheckStatus.FAIL, CheckStatus.WARN):
                    fixable.append((category.name, result))

        if not fixable:
            self.console.print("[green]✓ No issues require fixing![/]")
            return

        self.console.print(f"[yellow]Found {len(fixable)} issue(s) that can be fixed:[/]\n")

        # Display fixable issues
        table = Table(show_header=True)
        table.add_column("#", width=3)
        table.add_column("Category", style="cyan")
        table.add_column("Issue")
        table.add_column("Status")

        for i, (cat_name, result) in enumerate(fixable, 1):
            table.add_row(
                str(i),
                cat_name.replace(" Check", ""),
                result.name,
                result.get_icon(),
            )

        self.console.print(table)

        if not Confirm.ask("\nAttempt to fix all issues?"):
            return

        # Map categories to fixers
        fixer_map = {
            "Health Check": HealthFixer,
            "Driver Check": DriverFixer,
            "Security Check": SecurityFixer,
            "Desktop Check": DesktopFixer,
        }

        fixed = 0
        failed = 0

        for cat_name, result in fixable:
            fixer_class = fixer_map.get(cat_name)
            if fixer_class:
                fixer = fixer_class(self.console)
                fix_result = fixer.apply_fix(result)

                if fix_result and fix_result.success:
                    fixed += 1
                    self.console.print(f"[green]✓[/] Fixed: {result.name}")
                else:
                    failed += 1
                    self.console.print(f"[red]✗[/] Failed: {result.name}")

        self.console.print(f"\n[bold]Results: {fixed} fixed, {failed} failed[/]")

    def _generate_report(self):
        """Generate PDF report."""
        self.console.print(get_header("Generate Report"))
        self.console.print()

        # Run all checks if not already done
        if not self.check_results or len(self.check_results) < 4:
            if Confirm.ask("Run all checks to generate complete report?"):
                self.console.print("\n[dim]Running all checks...[/]\n")

                with self.progress.get_check_progress() as progress:
                    task = progress.add_task("Running checks...", total=4)

                    progress.update(task, description="Health Check")
                    checker = HealthChecker()
                    self.check_results["Health Check"] = checker.run_all_checks()
                    progress.advance(task)

                    progress.update(task, description="Driver Check")
                    checker = DriverChecker()
                    self.check_results["Driver Check"] = checker.run_all_checks()
                    progress.advance(task)

                    progress.update(task, description="Security Check")
                    checker = SecurityChecker()
                    self.check_results["Security Check"] = checker.run_all_checks()
                    progress.advance(task)

                    progress.update(task, description="Desktop Check")
                    checker = DesktopChecker()
                    self.check_results["Desktop Check"] = checker.run_all_checks()
                    progress.advance(task)

        categories = list(self.check_results.values())

        if not categories:
            self.console.print("[yellow]No check data available for report.[/]")
            return

        # Generate report
        self.console.print("\n[dim]Generating PDF report...[/]")

        with self.progress.status("Creating report..."):
            generator = ReportGenerator()
            output_path = generator.generate(categories)

        self.console.print(f"\n[bold green]✓ Report generated:[/] {output_path}")

        # Try to open the report
        if Confirm.ask("Open the report now?"):
            import subprocess
            try:
                subprocess.run(["xdg-open", output_path], check=True)
            except:
                self.console.print(f"[dim]Could not open automatically. Report saved at: {output_path}[/]")

    def _show_settings(self):
        """Show settings menu."""
        self.console.print(get_header("Settings"))
        self.console.print()

        info = [
            ("Application", f"{__app_name__} v{__version__}"),
            ("Author", __author__),
            ("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
            ("Working Dir", os.getcwd()),
        ]

        for label, value in info:
            self.console.print(f"[cyan]{label}:[/] {value}")

        self.console.print("\n[dim]Settings configuration coming soon![/]")

    def _exit(self):
        """Exit the application."""
        self.console.print("\n[bold cyan]Thank you for using FedChecker![/]")
        self.console.print("[dim]by sudo3rs[/]\n")


def main():
    """Entry point for FedChecker."""
    try:
        app = FedChecker()
        app.run()
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[yellow]Interrupted by user[/]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"\n[red]Error: {e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
