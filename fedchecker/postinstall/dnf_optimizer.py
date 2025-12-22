"""
DNF Optimizer Module for FedChecker.
Optimizes DNF configuration for faster package management.
"""

import subprocess
from pathlib import Path
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

from ..ui.progress import ProgressManager


@dataclass
class OptimizationResult:
    """Result of an optimization operation."""
    success: bool
    message: str
    changes: list[str]


class DNFOptimizer:
    """Optimizes DNF package manager configuration."""

    DNF_CONF = Path("/etc/dnf/dnf.conf")

    OPTIMIZATIONS = {
        "fastestmirror": "True",
        "max_parallel_downloads": "10",
        "deltarpm": "True",
        "defaultyes": "True",
        "keepcache": "False",
        "install_weak_deps": "False",
    }

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.progress = ProgressManager(self.console)

    def _run_command(self, cmd: list[str], sudo: bool = False) -> tuple[bool, str]:
        """Run a command and return (success, output)."""
        if sudo:
            cmd = ["sudo"] + cmd

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def get_current_config(self) -> dict[str, str]:
        """Read current DNF configuration."""
        config = {}

        if not self.DNF_CONF.exists():
            return config

        try:
            content = self.DNF_CONF.read_text()
            for line in content.split('\n'):
                line = line.strip()
                if '=' in line and not line.startswith('#') and not line.startswith('['):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        except Exception:
            pass

        return config

    def show_current_status(self) -> None:
        """Display current DNF configuration status."""
        current = self.get_current_config()

        table = Table(title="Current DNF Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Current Value", style="yellow")
        table.add_column("Recommended", style="green")
        table.add_column("Status")

        for key, recommended in self.OPTIMIZATIONS.items():
            current_val = current.get(key, "Not set")
            if current_val.lower() == recommended.lower():
                status = "[green]✓[/]"
            else:
                status = "[yellow]○[/]"

            table.add_row(key, current_val, recommended, status)

        self.console.print(table)

    def apply_optimizations(self) -> OptimizationResult:
        """Apply DNF optimizations."""
        self.console.print("\n[bold cyan]Optimizing DNF configuration...[/]\n")

        changes = []
        current = self.get_current_config()

        # Read current config
        try:
            if self.DNF_CONF.exists():
                content = self.DNF_CONF.read_text()
            else:
                content = "[main]\n"
        except Exception as e:
            return OptimizationResult(
                success=False,
                message=f"Cannot read DNF config: {e}",
                changes=[],
            )

        # Prepare new content
        lines = content.split('\n')
        new_lines = []
        applied_keys = set()

        for line in lines:
            stripped = line.strip()

            # Check if this line has a key we want to modify
            modified = False
            for key, value in self.OPTIMIZATIONS.items():
                if stripped.startswith(f"{key}=") or stripped.startswith(f"#{key}="):
                    if current.get(key, "").lower() != value.lower():
                        new_lines.append(f"{key}={value}")
                        changes.append(f"{key}: {current.get(key, 'Not set')} -> {value}")
                    else:
                        new_lines.append(line)
                    applied_keys.add(key)
                    modified = True
                    break

            if not modified:
                new_lines.append(line)

        # Add missing settings after [main]
        for i, line in enumerate(new_lines):
            if line.strip() == "[main]":
                insert_pos = i + 1
                for key, value in self.OPTIMIZATIONS.items():
                    if key not in applied_keys:
                        new_lines.insert(insert_pos, f"{key}={value}")
                        changes.append(f"{key}: Not set -> {value}")
                        insert_pos += 1
                break

        # Write new config
        new_content = '\n'.join(new_lines)

        # Use sudo to write
        with self.progress.status("Writing DNF configuration..."):
            success, output = self._run_command(
                ["bash", "-c", f"echo '{new_content}' > {self.DNF_CONF}"],
                sudo=True,
            )

        if not success:
            # Try alternative method
            try:
                temp_file = Path("/tmp/dnf.conf.tmp")
                temp_file.write_text(new_content)
                success, output = self._run_command(
                    ["cp", str(temp_file), str(self.DNF_CONF)],
                    sudo=True,
                )
                temp_file.unlink()
            except Exception as e:
                return OptimizationResult(
                    success=False,
                    message=f"Failed to write config: {e}",
                    changes=[],
                )

        if changes:
            return OptimizationResult(
                success=True,
                message=f"Applied {len(changes)} optimization(s)",
                changes=changes,
            )

        return OptimizationResult(
            success=True,
            message="DNF already optimized",
            changes=[],
        )

    def clean_cache(self) -> bool:
        """Clean DNF cache."""
        self.console.print("\n[dim]Cleaning DNF cache...[/]")

        success, _ = self._run_command(["dnf", "clean", "all"], sudo=True)
        return success

    def update_cache(self) -> bool:
        """Update DNF cache."""
        self.console.print("[dim]Updating DNF cache...[/]")

        with self.progress.status("Refreshing package metadata..."):
            success, _ = self._run_command(
                ["dnf", "makecache", "--refresh"],
                sudo=True,
            )
        return success

    def run(self) -> OptimizationResult:
        """Run full DNF optimization."""
        self.show_current_status()
        self.console.print()

        result = self.apply_optimizations()

        if result.success and result.changes:
            self.console.print("\n[bold green]Changes applied:[/]")
            for change in result.changes:
                self.console.print(f"  [dim]•[/] {change}")

            # Clean and refresh cache
            self.clean_cache()
            self.update_cache()

        return result


if __name__ == "__main__":
    console = Console()
    optimizer = DNFOptimizer(console)
    result = optimizer.run()

    if result.success:
        console.print(f"\n[bold green]✓ {result.message}[/]")
    else:
        console.print(f"\n[bold red]✗ {result.message}[/]")
