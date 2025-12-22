"""
Driver Fix Module for FedChecker.
Provides auto-fix capabilities for driver issues.
"""

import subprocess
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


class DriverFixer:
    """Provides fixes for driver-related issues."""

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

    def install_nvidia_driver(self) -> FixResult:
        """Install NVIDIA proprietary drivers."""
        self.console.print("\n[bold cyan]Installing NVIDIA drivers...[/]\n")

        # First, enable RPM Fusion if not already
        steps = [
            ("Enabling RPM Fusion", [
                "dnf", "install", "-y",
                "https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm",
                "https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm",
            ]),
            ("Installing NVIDIA driver", ["dnf", "install", "-y", "akmod-nvidia"]),
            ("Installing CUDA support", ["dnf", "install", "-y", "xorg-x11-drv-nvidia-cuda"]),
        ]

        with self.progress.get_progress() as progress:
            task = progress.add_task("Installing...", total=len(steps))

            for desc, cmd in steps:
                progress.update(task, description=desc)

                # Handle shell expansion
                if "$" in " ".join(cmd):
                    success, output = self._run_command(
                        ["bash", "-c", " ".join(cmd)],
                        sudo=True,
                        timeout=600,
                    )
                else:
                    success, output = self._run_command(cmd, sudo=True, timeout=600)

                if not success and "RPM Fusion" not in desc:
                    return FixResult(
                        success=False,
                        message=f"Failed at: {desc}",
                        details=output[:500],
                    )

                progress.advance(task)

        return FixResult(
            success=True,
            message="NVIDIA driver installed",
            details="Reboot required to load the new driver",
            requires_reboot=True,
        )

    def install_wifi_firmware(self) -> FixResult:
        """Install common WiFi firmware packages."""
        self.console.print("\n[bold cyan]Installing WiFi firmware...[/]\n")

        packages = [
            "linux-firmware",
            "iwl*-firmware",
            "atheros-firmware",
            "b43-openfwwf",
            "brcmfmac-firmware",
        ]

        with self.progress.status("Installing firmware packages..."):
            success, output = self._run_command(
                ["dnf", "install", "-y"] + packages,
                sudo=True,
                timeout=300,
            )

        if success:
            return FixResult(
                success=True,
                message="WiFi firmware installed",
                details="You may need to reboot or reload the WiFi module",
                requires_reboot=True,
            )

        return FixResult(
            success=False,
            message="Failed to install firmware",
            details=output,
        )

    def unblock_wifi(self) -> FixResult:
        """Unblock WiFi using rfkill."""
        self.console.print("\n[bold cyan]Unblocking WiFi...[/]\n")

        success, output = self._run_command(["rfkill", "unblock", "wifi"], sudo=True)

        if success:
            return FixResult(
                success=True,
                message="WiFi unblocked",
            )

        return FixResult(
            success=False,
            message="Failed to unblock WiFi",
            details=output,
        )

    def install_audio_drivers(self) -> FixResult:
        """Install audio-related packages."""
        self.console.print("\n[bold cyan]Installing audio packages...[/]\n")

        packages = [
            "alsa-firmware",
            "alsa-plugins-pulseaudio",
            "pipewire-alsa",
            "sof-firmware",
        ]

        with self.progress.status("Installing audio packages..."):
            success, output = self._run_command(
                ["dnf", "install", "-y"] + packages,
                sudo=True,
                timeout=300,
            )

        if success:
            return FixResult(
                success=True,
                message="Audio packages installed",
                requires_reboot=True,
            )

        return FixResult(
            success=False,
            message="Failed to install audio packages",
            details=output,
        )

    def enable_bluetooth(self) -> FixResult:
        """Enable and start Bluetooth service."""
        self.console.print("\n[bold cyan]Enabling Bluetooth...[/]\n")

        steps = [
            ("Unblocking Bluetooth", ["rfkill", "unblock", "bluetooth"]),
            ("Enabling service", ["systemctl", "enable", "--now", "bluetooth"]),
        ]

        for desc, cmd in steps:
            self.console.print(f"[dim]{desc}...[/]")
            success, output = self._run_command(cmd, sudo=True)

            if not success:
                return FixResult(
                    success=False,
                    message=f"Failed at: {desc}",
                    details=output,
                )

        return FixResult(
            success=True,
            message="Bluetooth enabled",
        )

    def install_fwupd(self) -> FixResult:
        """Install fwupd for firmware updates."""
        self.console.print("\n[bold cyan]Installing fwupd...[/]\n")

        with self.progress.status("Installing fwupd..."):
            success, output = self._run_command(
                ["dnf", "install", "-y", "fwupd"],
                sudo=True,
            )

        if success:
            # Enable the service
            self._run_command(
                ["systemctl", "enable", "--now", "fwupd"],
                sudo=True,
            )
            return FixResult(
                success=True,
                message="fwupd installed and enabled",
            )

        return FixResult(
            success=False,
            message="Failed to install fwupd",
            details=output,
        )

    def install_hw_acceleration(self) -> FixResult:
        """Install hardware acceleration packages."""
        self.console.print("\n[bold cyan]Installing hardware acceleration...[/]\n")

        packages = [
            "libva-utils",
            "vdpauinfo",
            "mesa-va-drivers",
            "mesa-vdpau-drivers",
            "libva-intel-driver",
            "intel-media-driver",
        ]

        with self.progress.status("Installing VA-API/VDPAU..."):
            success, output = self._run_command(
                ["dnf", "install", "-y"] + packages,
                sudo=True,
                timeout=300,
            )

        if success:
            return FixResult(
                success=True,
                message="Hardware acceleration installed",
            )

        return FixResult(
            success=False,
            message="Failed to install packages",
            details=output,
        )

    def update_firmware(self) -> FixResult:
        """Update firmware using fwupdmgr."""
        self.console.print("\n[bold cyan]Updating firmware...[/]\n")

        # Refresh metadata
        self.console.print("[dim]Refreshing firmware metadata...[/]")
        self._run_command(["fwupdmgr", "refresh", "--force"], sudo=True, timeout=60)

        # Apply updates
        with self.progress.status("Applying firmware updates..."):
            success, output = self._run_command(
                ["fwupdmgr", "update", "-y"],
                sudo=True,
                timeout=600,
            )

        if success or "No upgrades" in output:
            return FixResult(
                success=True,
                message="Firmware updated",
                requires_reboot="reboot" in output.lower(),
            )

        return FixResult(
            success=False,
            message="Failed to update firmware",
            details=output,
        )

    def apply_fix(self, check_result: CheckResult) -> FixResult | None:
        """Apply fix based on check result."""
        if not check_result.fix_available:
            return None

        fix_map = {
            "GPU Driver": self.install_nvidia_driver,
            "WiFi Driver": self.install_wifi_firmware,
            "Audio Driver": self.install_audio_drivers,
            "Bluetooth": self.enable_bluetooth,
            "Firmware Updates": self.update_firmware,
            "Hardware Acceleration": self.install_hw_acceleration,
        }

        # Handle specific fixes
        if "blocked" in check_result.message.lower():
            if "wifi" in check_result.name.lower():
                return self.unblock_wifi()
            elif "bluetooth" in check_result.name.lower():
                return self.enable_bluetooth()

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
