"""
Desktop Fix Module for FedChecker.
Provides auto-fix capabilities for desktop environment issues.
"""

import subprocess
import os
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


class DesktopFixer:
    """Provides fixes for desktop-related issues."""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.progress = ProgressManager(self.console)

    def _run_command(
        self,
        cmd: list[str],
        sudo: bool = False,
        timeout: int = 120,
        user: bool = False,
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
                env=os.environ if user else None,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except FileNotFoundError as e:
            return False, str(e)

    def install_fonts(self) -> FixResult:
        """Install common font packages."""
        self.console.print("\n[bold cyan]Installing fonts...[/]\n")

        packages = [
            "google-noto-fonts-common",
            "google-noto-sans-fonts",
            "google-noto-serif-fonts",
            "liberation-fonts",
            "dejavu-fonts-all",
            "fira-code-fonts",
            "mozilla-fira-sans-fonts",
            "adobe-source-code-pro-fonts",
        ]

        with self.progress.status("Installing font packages..."):
            success, output = self._run_command(
                ["dnf", "install", "-y"] + packages,
                sudo=True,
                timeout=180,
            )

        if success:
            # Refresh font cache
            self._run_command(["fc-cache", "-fv"], timeout=60)
            return FixResult(
                success=True,
                message="Fonts installed successfully",
            )

        return FixResult(
            success=False,
            message="Failed to install fonts",
            details=output,
        )

    def install_flatpak(self) -> FixResult:
        """Install Flatpak and configure Flathub."""
        self.console.print("\n[bold cyan]Setting up Flatpak...[/]\n")

        steps = [
            ("Installing Flatpak", ["dnf", "install", "-y", "flatpak"]),
            ("Adding Flathub", [
                "flatpak", "remote-add", "--if-not-exists",
                "flathub", "https://flathub.org/repo/flathub.flatpakrepo"
            ]),
        ]

        for desc, cmd in steps:
            self.console.print(f"[dim]{desc}...[/]")
            sudo = "dnf" in cmd
            success, output = self._run_command(cmd, sudo=sudo, timeout=120)

            if not success:
                return FixResult(
                    success=False,
                    message=f"Failed at: {desc}",
                    details=output,
                )

        return FixResult(
            success=True,
            message="Flatpak configured with Flathub",
            details="You may need to log out and back in for apps to appear",
        )

    def install_portals(self) -> FixResult:
        """Install XDG desktop portals."""
        self.console.print("\n[bold cyan]Installing desktop portals...[/]\n")

        # Detect DE and install appropriate portal
        de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

        packages = ["xdg-desktop-portal"]

        if "gnome" in de:
            packages.append("xdg-desktop-portal-gnome")
        elif "kde" in de or "plasma" in de:
            packages.append("xdg-desktop-portal-kde")
        else:
            packages.append("xdg-desktop-portal-gtk")

        with self.progress.status("Installing portals..."):
            success, output = self._run_command(
                ["dnf", "install", "-y"] + packages,
                sudo=True,
                timeout=120,
            )

        if not success:
            return FixResult(
                success=False,
                message="Failed to install portals",
                details=output,
            )

        # Enable portal service
        self._run_command(
            ["systemctl", "--user", "enable", "--now", "xdg-desktop-portal"],
            user=True,
        )

        return FixResult(
            success=True,
            message="Desktop portals installed",
        )

    def fix_gnome_extensions(self) -> FixResult:
        """Reset problematic GNOME extensions."""
        self.console.print("\n[bold cyan]Managing GNOME extensions...[/]\n")

        # Get list of enabled extensions
        success, output = self._run_command(
            ["gnome-extensions", "list", "--enabled"],
            user=True,
        )

        if not success:
            return FixResult(
                success=False,
                message="Cannot access GNOME extensions",
                details=output,
            )

        extensions = [e.strip() for e in output.split('\n') if e.strip()]

        if not extensions:
            return FixResult(
                success=True,
                message="No extensions to manage",
            )

        # Disable all extensions temporarily
        for ext in extensions:
            self._run_command(
                ["gnome-extensions", "disable", ext],
                user=True,
            )

        # Re-enable them
        enabled = 0
        for ext in extensions:
            success, _ = self._run_command(
                ["gnome-extensions", "enable", ext],
                user=True,
            )
            if success:
                enabled += 1

        return FixResult(
            success=True,
            message=f"Reset {enabled} extensions",
            details="Extensions have been reloaded",
        )

    def configure_display_manager(self) -> FixResult:
        """Configure the display manager."""
        self.console.print("\n[bold cyan]Configuring display manager...[/]\n")

        # Detect current DE
        de = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

        dm = "gdm"  # Default
        if "kde" in de or "plasma" in de:
            dm = "sddm"

        # Install if needed
        success, _ = self._run_command(
            ["dnf", "install", "-y", dm],
            sudo=True,
        )

        # Enable the display manager
        success, output = self._run_command(
            ["systemctl", "enable", dm],
            sudo=True,
        )

        # Set graphical target
        self._run_command(
            ["systemctl", "set-default", "graphical.target"],
            sudo=True,
        )

        if success:
            return FixResult(
                success=True,
                message=f"{dm.upper()} enabled",
            )

        return FixResult(
            success=False,
            message="Failed to configure display manager",
            details=output,
        )

    def install_codecs_gui(self) -> FixResult:
        """Install multimedia codecs for desktop use."""
        self.console.print("\n[bold cyan]Installing multimedia support...[/]\n")

        packages = [
            "gstreamer1-plugins-bad-free",
            "gstreamer1-plugins-good",
            "gstreamer1-plugins-ugly-free",
            "gstreamer1-plugin-openh264",
            "mozilla-openh264",
        ]

        with self.progress.status("Installing codecs..."):
            success, output = self._run_command(
                ["dnf", "install", "-y"] + packages,
                sudo=True,
                timeout=180,
            )

        if success:
            return FixResult(
                success=True,
                message="Multimedia codecs installed",
            )

        return FixResult(
            success=False,
            message="Failed to install codecs",
            details=output,
        )

    def reset_gnome_settings(self) -> FixResult:
        """Reset GNOME settings to defaults."""
        self.console.print("\n[bold cyan]Resetting GNOME settings...[/]\n")

        if not Confirm.ask(
            "[yellow]This will reset all GNOME settings to defaults. Continue?[/]"
        ):
            return FixResult(
                success=False,
                message="Reset cancelled by user",
            )

        success, output = self._run_command(
            ["dconf", "reset", "-f", "/"],
            user=True,
        )

        if success:
            return FixResult(
                success=True,
                message="GNOME settings reset",
                details="Log out and back in for full effect",
            )

        return FixResult(
            success=False,
            message="Failed to reset settings",
            details=output,
        )

    def apply_fix(self, check_result: CheckResult) -> FixResult | None:
        """Apply fix based on check result."""
        if not check_result.fix_available:
            return None

        fix_map = {
            "Fonts": self.install_fonts,
            "Flatpak Apps": self.install_flatpak,
            "Desktop Portals": self.install_portals,
            "GNOME Extensions": self.fix_gnome_extensions,
            "Display Manager": self.configure_display_manager,
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
