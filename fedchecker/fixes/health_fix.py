"""
Health Fix Module for FedChecker.
Provides auto-fix capabilities for health issues.
"""

import subprocess
import os
from typing import Optional, Callable
from dataclasses import dataclass

from rich.console import Console
from rich.prompt import Confirm

from ..ui.colors import CheckResult, CheckStatus
from ..ui.progress import ProgressManager


@dataclass
class FixResult:
    """Result of a fix operation."""
    success: bool
    message: str
    details: str = ""
    requires_reboot: bool = False


class HealthFixer:
    """Provides fixes for health-related issues."""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.progress = ProgressManager(self.console)

    def _run_command(
        self,
        cmd: list[str],
        sudo: bool = False,
        timeout: int = 300,
    ) -> tuple[bool, str]:
        """Run a command and return (success, output)."""
        if sudo:
            cmd = ["sudo"] + cmd

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except FileNotFoundError as e:
            return False, str(e)

    def fix_disk_space(self) -> FixResult:
        """Clean up disk space."""
        self.console.print("\n[bold cyan]Cleaning up disk space...[/]\n")

        steps = [
            ("Cleaning DNF cache", ["dnf", "clean", "all"]),
            ("Removing orphaned packages", ["dnf", "autoremove", "-y"]),
            ("Cleaning old kernels", ["dnf", "remove", "--oldinstallonly", "-y"]),
            ("Cleaning journal logs", ["journalctl", "--vacuum-time=7d"]),
        ]

        cleaned = []
        failed = []

        with self.progress.get_progress() as progress:
            task = progress.add_task("Cleaning...", total=len(steps))

            for desc, cmd in steps:
                progress.update(task, description=desc)
                success, output = self._run_command(cmd, sudo=True)

                if success:
                    cleaned.append(desc)
                else:
                    failed.append(desc)

                progress.advance(task)

        if failed:
            return FixResult(
                success=False,
                message=f"Partial cleanup: {len(cleaned)}/{len(steps)} steps completed",
                details=f"Failed: {', '.join(failed)}",
            )

        return FixResult(
            success=True,
            message="Disk cleanup completed",
            details=f"Completed: {', '.join(cleaned)}",
        )

    def fix_failed_units(self) -> FixResult:
        """Reset failed systemd units."""
        self.console.print("\n[bold cyan]Resetting failed systemd units...[/]\n")

        success, output = self._run_command(["systemctl", "reset-failed"], sudo=True)

        if success:
            return FixResult(
                success=True,
                message="Failed units reset",
            )

        return FixResult(
            success=False,
            message="Failed to reset units",
            details=output,
        )

    def fix_dnf_issues(self) -> FixResult:
        """Fix DNF/package manager issues."""
        self.console.print("\n[bold cyan]Fixing package manager issues...[/]\n")

        steps = [
            ("Rebuilding RPM database", ["rpm", "--rebuilddb"]),
            ("Cleaning DNF cache", ["dnf", "clean", "all"]),
            ("Checking for problems", ["dnf", "check"]),
            ("Syncing distribution", ["dnf", "distro-sync", "-y"]),
        ]

        with self.progress.get_progress() as progress:
            task = progress.add_task("Fixing...", total=len(steps))

            for desc, cmd in steps:
                progress.update(task, description=desc)
                success, output = self._run_command(cmd, sudo=True, timeout=600)

                if not success:
                    return FixResult(
                        success=False,
                        message=f"Failed at: {desc}",
                        details=output[:500],
                    )

                progress.advance(task)

        return FixResult(
            success=True,
            message="Package manager issues fixed",
        )

    def fix_orphaned_packages(self) -> FixResult:
        """Remove orphaned packages."""
        self.console.print("\n[bold cyan]Removing orphaned packages...[/]\n")

        with self.progress.status("Running dnf autoremove..."):
            success, output = self._run_command(
                ["dnf", "autoremove", "-y"],
                sudo=True,
                timeout=300,
            )

        if success:
            # Count removed packages
            removed = output.count("Removing:")
            return FixResult(
                success=True,
                message=f"Removed orphaned packages",
                details=output[-500:] if len(output) > 500 else output,
            )

        return FixResult(
            success=False,
            message="Failed to remove orphaned packages",
            details=output,
        )

    def create_swap(self, size_gb: int = 4) -> FixResult:
        """Create a swap file."""
        self.console.print(f"\n[bold cyan]Creating {size_gb}GB swap file...[/]\n")

        swapfile = "/swapfile"

        # Check if swap already exists
        if os.path.exists(swapfile):
            return FixResult(
                success=False,
                message="Swap file already exists",
                details="Remove /swapfile first if you want to recreate it",
            )

        steps = [
            ("Allocating space", ["fallocate", "-l", f"{size_gb}G", swapfile]),
            ("Setting permissions", ["chmod", "600", swapfile]),
            ("Formatting swap", ["mkswap", swapfile]),
            ("Enabling swap", ["swapon", swapfile]),
        ]

        with self.progress.get_progress() as progress:
            task = progress.add_task("Creating swap...", total=len(steps))

            for desc, cmd in steps:
                progress.update(task, description=desc)
                success, output = self._run_command(cmd, sudo=True)

                if not success:
                    # Cleanup on failure
                    self._run_command(["rm", "-f", swapfile], sudo=True)
                    return FixResult(
                        success=False,
                        message=f"Failed at: {desc}",
                        details=output,
                    )

                progress.advance(task)

        # Add to fstab
        fstab_entry = f"{swapfile} none swap sw 0 0\n"
        self.console.print("[dim]Adding to /etc/fstab...[/]")

        try:
            with open("/etc/fstab", "a") as f:
                f.write(fstab_entry)
        except PermissionError:
            self._run_command(
                ["bash", "-c", f"echo '{swapfile} none swap sw 0 0' >> /etc/fstab"],
                sudo=True
            )

        return FixResult(
            success=True,
            message=f"Created {size_gb}GB swap file",
            details="Swap is now active and will persist across reboots",
        )

    def apply_fix(self, check_result: CheckResult) -> Optional[FixResult]:
        """Apply fix based on check result."""
        if not check_result.fix_available:
            return None

        fix_map = {
            "Disk Space": self.fix_disk_space,
            "Failed Systemd Units": self.fix_failed_units,
            "Package Manager": self.fix_dnf_issues,
            "Orphaned Packages": self.fix_orphaned_packages,
            "Swap Space": self.create_swap,
        }

        fix_func = fix_map.get(check_result.name)

        if fix_func:
            if Confirm.ask(f"Apply fix for [bold]{check_result.name}[/]?"):
                return fix_func()

        # Generic fix using the command
        if check_result.fix_command:
            if Confirm.ask(
                f"Run fix command for [bold]{check_result.name}[/]?\n"
                f"[dim]{check_result.fix_command}[/]"
            ):
                success, output = self._run_command(
                    ["bash", "-c", check_result.fix_command],
                    sudo=True,
                )
                return FixResult(
                    success=success,
                    message="Fix applied" if success else "Fix failed",
                    details=output,
                )

        return None
