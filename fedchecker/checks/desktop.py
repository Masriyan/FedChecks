"""
Desktop Environment Check Module for FedChecker.
Checks DE type, display server, compositor, themes, and extensions.
"""

import subprocess
import os
import re
from pathlib import Path
from typing import Optional

from ..ui.colors import CheckResult, CheckStatus, CheckCategory, StatusIcon


class DesktopChecker:
    """Performs desktop environment checks."""

    def __init__(self):
        self.results: list[CheckResult] = []
        self.desktop_session = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        self.session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()

    def run_all_checks(self) -> CheckCategory:
        """Run all desktop checks and return results."""
        self.results = []

        checks = [
            ("Desktop Environment", self.check_desktop_environment),
            ("Display Server", self.check_display_server),
            ("Compositor", self.check_compositor),
            ("Display Manager", self.check_display_manager),
            ("Screen Resolution", self.check_resolution),
            ("Theme & Icons", self.check_themes),
            ("Fonts", self.check_fonts),
            ("GNOME Extensions", self.check_gnome_extensions),
            ("Flatpak Apps", self.check_flatpak),
            ("Desktop Portals", self.check_portals),
        ]

        for name, check_func in checks:
            try:
                result = check_func()
                self.results.append(result)
            except Exception as e:
                self.results.append(CheckResult(
                    name=name,
                    status=CheckStatus.ERROR,
                    message=f"Check failed: {str(e)}",
                ))

        return CheckCategory(
            name="Desktop Check",
            icon=StatusIcon.DESKTOP,
            results=self.results,
        )

    def _run_command(self, cmd: list[str], timeout: int = 10) -> tuple[bool, str]:
        """Run a command and return (success, output)."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "LC_ALL": "C"},
            )
            return result.returncode == 0, result.stdout + result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return False, str(e)

    def check_desktop_environment(self) -> CheckResult:
        """Detect and check the desktop environment."""
        de_map = {
            "gnome": "GNOME",
            "kde": "KDE Plasma",
            "plasma": "KDE Plasma",
            "xfce": "XFCE",
            "cinnamon": "Cinnamon",
            "mate": "MATE",
            "lxde": "LXDE",
            "lxqt": "LXQt",
            "budgie": "Budgie",
            "pantheon": "Pantheon",
            "sway": "Sway",
            "i3": "i3",
            "hyprland": "Hyprland",
        }

        desktop = self.desktop_session
        de_name = "Unknown"

        for key, name in de_map.items():
            if key in desktop:
                de_name = name
                break

        if de_name == "Unknown":
            # Try alternative detection
            if os.environ.get("GNOME_DESKTOP_SESSION_ID"):
                de_name = "GNOME"
            elif os.environ.get("KDE_FULL_SESSION"):
                de_name = "KDE Plasma"

        if de_name == "Unknown":
            return CheckResult(
                name="Desktop Environment",
                status=CheckStatus.WARN,
                message="Unable to detect DE",
                details="Running in TTY or unknown DE",
            )

        # Get version if possible
        version = ""
        if "gnome" in de_name.lower():
            success, output = self._run_command(["gnome-shell", "--version"])
            if success:
                version = output.strip().replace("GNOME Shell ", "")
        elif "kde" in de_name.lower() or "plasma" in de_name.lower():
            success, output = self._run_command(["plasmashell", "--version"])
            if success:
                match = re.search(r'(\d+\.\d+)', output)
                if match:
                    version = match.group(1)

        message = f"{de_name}" + (f" {version}" if version else "")

        return CheckResult(
            name="Desktop Environment",
            status=CheckStatus.PASS,
            message=message,
        )

    def check_display_server(self) -> CheckResult:
        """Check display server (X11 or Wayland)."""
        session_type = self.session_type

        if session_type == "wayland":
            # Check Wayland compositor
            wayland_display = os.environ.get("WAYLAND_DISPLAY", "")
            return CheckResult(
                name="Display Server",
                status=CheckStatus.PASS,
                message=f"Wayland ({wayland_display})",
            )
        elif session_type == "x11":
            display = os.environ.get("DISPLAY", ":0")
            return CheckResult(
                name="Display Server",
                status=CheckStatus.PASS,
                message=f"X11 ({display})",
            )
        elif session_type == "tty":
            return CheckResult(
                name="Display Server",
                status=CheckStatus.SKIP,
                message="TTY session (no GUI)",
            )
        else:
            return CheckResult(
                name="Display Server",
                status=CheckStatus.WARN,
                message="Unknown display server",
            )

    def check_compositor(self) -> CheckResult:
        """Check compositor status."""
        if self.session_type == "wayland":
            # On Wayland, compositor is always active
            compositor = os.environ.get("XDG_CURRENT_DESKTOP", "Unknown")
            return CheckResult(
                name="Compositor",
                status=CheckStatus.PASS,
                message=f"Wayland compositor ({compositor})",
            )

        # X11 compositor check
        success, output = self._run_command(["xdpyinfo"])

        if not success:
            return CheckResult(
                name="Compositor",
                status=CheckStatus.SKIP,
                message="Cannot check compositor",
            )

        # Check for composite extension
        if "Composite" in output:
            # Try to detect specific compositor
            compositors = [
                ("picom", ["pgrep", "picom"]),
                ("compton", ["pgrep", "compton"]),
                ("compiz", ["pgrep", "compiz"]),
                ("kwin", ["pgrep", "kwin"]),
                ("mutter", ["pgrep", "mutter"]),
            ]

            for name, cmd in compositors:
                success, _ = self._run_command(cmd)
                if success:
                    return CheckResult(
                        name="Compositor",
                        status=CheckStatus.PASS,
                        message=f"{name} compositor active",
                    )

            return CheckResult(
                name="Compositor",
                status=CheckStatus.PASS,
                message="Composite extension enabled",
            )

        return CheckResult(
            name="Compositor",
            status=CheckStatus.WARN,
            message="No compositor detected",
            details="Desktop effects may not work properly",
        )

    def check_display_manager(self) -> CheckResult:
        """Check which display manager is active."""
        display_managers = [
            ("gdm", "GDM (GNOME)"),
            ("sddm", "SDDM (KDE)"),
            ("lightdm", "LightDM"),
            ("lxdm", "LXDM"),
            ("xdm", "XDM"),
        ]

        for service, name in display_managers:
            success, output = self._run_command(["systemctl", "is-active", service])
            if success and "active" in output:
                return CheckResult(
                    name="Display Manager",
                    status=CheckStatus.PASS,
                    message=name,
                )

        return CheckResult(
            name="Display Manager",
            status=CheckStatus.WARN,
            message="No display manager detected",
            details="Using TTY login or startx",
        )

    def check_resolution(self) -> CheckResult:
        """Check screen resolution."""
        if self.session_type == "wayland":
            # Use wlr-randr or gnome settings
            success, output = self._run_command(["wlr-randr"])
            if not success:
                success, output = self._run_command(
                    ["gsettings", "get", "org.gnome.desktop.interface", "scaling-factor"]
                )

        # Try xrandr for X11 or as fallback
        success, output = self._run_command(["xrandr", "--current"])

        if not success:
            return CheckResult(
                name="Screen Resolution",
                status=CheckStatus.SKIP,
                message="Cannot detect resolution",
            )

        # Parse resolutions
        resolutions = re.findall(r'(\d{3,4}x\d{3,4})\s+\d+\.\d+\*', output)

        if resolutions:
            return CheckResult(
                name="Screen Resolution",
                status=CheckStatus.PASS,
                message=f"{', '.join(resolutions)}",
            )

        # Try to find connected monitors
        connected = re.findall(r'(\w+) connected', output)
        if connected:
            return CheckResult(
                name="Screen Resolution",
                status=CheckStatus.PASS,
                message=f"{len(connected)} display(s) connected",
            )

        return CheckResult(
            name="Screen Resolution",
            status=CheckStatus.WARN,
            message="No displays detected",
        )

    def check_themes(self) -> CheckResult:
        """Check GTK/Qt themes and icons."""
        themes = {}

        # GTK theme
        success, output = self._run_command(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"]
        )
        if success:
            themes["GTK"] = output.strip().strip("'")

        # Icon theme
        success, output = self._run_command(
            ["gsettings", "get", "org.gnome.desktop.interface", "icon-theme"]
        )
        if success:
            themes["Icons"] = output.strip().strip("'")

        # Cursor theme
        success, output = self._run_command(
            ["gsettings", "get", "org.gnome.desktop.interface", "cursor-theme"]
        )
        if success:
            themes["Cursor"] = output.strip().strip("'")

        if themes:
            theme_str = ", ".join([f"{k}: {v}" for k, v in list(themes.items())[:2]])
            return CheckResult(
                name="Theme & Icons",
                status=CheckStatus.PASS,
                message=theme_str[:50] + ("..." if len(theme_str) > 50 else ""),
            )

        return CheckResult(
            name="Theme & Icons",
            status=CheckStatus.SKIP,
            message="Unable to detect themes",
        )

    def check_fonts(self) -> CheckResult:
        """Check font configuration."""
        success, output = self._run_command(["fc-list"])

        if not success:
            return CheckResult(
                name="Fonts",
                status=CheckStatus.SKIP,
                message="fontconfig not available",
            )

        font_count = len(output.strip().split('\n'))

        # Check for common font packages
        common_fonts = ["DejaVu", "Liberation", "Noto", "Roboto", "Fira"]
        found_fonts = [f for f in common_fonts if f.lower() in output.lower()]

        if font_count < 50:
            return CheckResult(
                name="Fonts",
                status=CheckStatus.WARN,
                message=f"Only {font_count} fonts installed",
                details="Consider installing more font packages",
                fix_available=True,
                fix_command="dnf install google-noto-fonts-common liberation-fonts dejavu-fonts-all",
            )

        return CheckResult(
            name="Fonts",
            status=CheckStatus.PASS,
            message=f"{font_count} fonts ({', '.join(found_fonts[:3])})",
        )

    def check_gnome_extensions(self) -> CheckResult:
        """Check GNOME extensions status."""
        if "gnome" not in self.desktop_session:
            return CheckResult(
                name="GNOME Extensions",
                status=CheckStatus.SKIP,
                message="Not using GNOME",
            )

        success, output = self._run_command(["gnome-extensions", "list", "--enabled"])

        if not success:
            return CheckResult(
                name="GNOME Extensions",
                status=CheckStatus.SKIP,
                message="gnome-extensions not available",
            )

        extensions = [e for e in output.strip().split('\n') if e]

        if not extensions:
            return CheckResult(
                name="GNOME Extensions",
                status=CheckStatus.PASS,
                message="No extensions enabled",
            )

        # Check for problematic extensions
        success, disabled = self._run_command(["gnome-extensions", "list", "--disabled"])
        disabled_count = len([e for e in disabled.strip().split('\n') if e])

        return CheckResult(
            name="GNOME Extensions",
            status=CheckStatus.PASS,
            message=f"{len(extensions)} enabled, {disabled_count} disabled",
        )

    def check_flatpak(self) -> CheckResult:
        """Check Flatpak installation and apps."""
        success, _ = self._run_command(["which", "flatpak"])

        if not success:
            return CheckResult(
                name="Flatpak Apps",
                status=CheckStatus.WARN,
                message="Flatpak not installed",
                fix_available=True,
                fix_command="dnf install flatpak && flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo",
            )

        # Count installed apps
        success, output = self._run_command(["flatpak", "list", "--app"])

        if success:
            apps = [a for a in output.strip().split('\n') if a]
            app_count = len(apps)

            # Check remotes
            success, remotes = self._run_command(["flatpak", "remotes"])
            has_flathub = "flathub" in remotes.lower()

            if not has_flathub:
                return CheckResult(
                    name="Flatpak Apps",
                    status=CheckStatus.WARN,
                    message=f"{app_count} app(s), Flathub not configured",
                    fix_available=True,
                    fix_command="flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo",
                )

            return CheckResult(
                name="Flatpak Apps",
                status=CheckStatus.PASS,
                message=f"{app_count} app(s) installed",
            )

        return CheckResult(
            name="Flatpak Apps",
            status=CheckStatus.PASS,
            message="Flatpak configured",
        )

    def check_portals(self) -> CheckResult:
        """Check XDG desktop portals."""
        portal_packages = [
            "xdg-desktop-portal",
            "xdg-desktop-portal-gtk",
            "xdg-desktop-portal-gnome",
            "xdg-desktop-portal-kde",
        ]

        installed = []
        for pkg in portal_packages:
            success, _ = self._run_command(["rpm", "-q", pkg])
            if success:
                installed.append(pkg.replace("xdg-desktop-portal-", "").replace("xdg-desktop-portal", "core"))

        if not installed:
            return CheckResult(
                name="Desktop Portals",
                status=CheckStatus.WARN,
                message="XDG portals not installed",
                details="Flatpak apps may not work correctly",
                fix_available=True,
                fix_command="dnf install xdg-desktop-portal xdg-desktop-portal-gtk",
            )

        # Check portal service
        success, output = self._run_command(
            ["systemctl", "--user", "is-active", "xdg-desktop-portal"]
        )

        if success and "active" in output:
            return CheckResult(
                name="Desktop Portals",
                status=CheckStatus.PASS,
                message=f"Active ({', '.join(installed[:3])})",
            )

        return CheckResult(
            name="Desktop Portals",
            status=CheckStatus.WARN,
            message="Portal service not running",
            fix_available=True,
            fix_command="systemctl --user enable --now xdg-desktop-portal",
        )


if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    checker = DesktopChecker()
    category = checker.run_all_checks()

    table = Table(title="Desktop Check Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Message")

    for result in category.results:
        table.add_row(result.name, result.get_icon(), result.message)

    console.print(table)
    console.print(f"\n[bold]Score: {category.score:.1f}%[/]")
