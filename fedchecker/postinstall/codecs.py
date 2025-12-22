"""
Codec Installer Module for FedChecker.
Installs multimedia codecs and hardware acceleration support.
"""

import subprocess
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from ..ui.progress import ProgressManager


@dataclass
class CodecResult:
    """Result of codec installation."""
    success: bool
    message: str
    packages_installed: list[str]


class CodecInstaller:
    """Manages multimedia codec installation."""

    # Codec packages organized by category
    CODEC_GROUPS = {
        "gstreamer": {
            "name": "GStreamer Plugins",
            "packages": [
                "gstreamer1-plugins-bad-free",
                "gstreamer1-plugins-bad-freeworld",
                "gstreamer1-plugins-good",
                "gstreamer1-plugins-ugly",
                "gstreamer1-plugins-ugly-free",
                "gstreamer1-plugin-openh264",
                "gstreamer1-libav",
            ],
        },
        "ffmpeg": {
            "name": "FFmpeg & Libraries",
            "packages": [
                "ffmpeg",
                "ffmpeg-libs",
                "libavcodec-freeworld",
            ],
        },
        "vaapi": {
            "name": "Hardware Acceleration (VA-API)",
            "packages": [
                "libva",
                "libva-utils",
                "mesa-va-drivers",
                "libva-intel-driver",
                "intel-media-driver",
            ],
        },
        "vdpau": {
            "name": "Hardware Acceleration (VDPAU)",
            "packages": [
                "libvdpau",
                "vdpauinfo",
                "mesa-vdpau-drivers",
            ],
        },
        "audio": {
            "name": "Audio Codecs",
            "packages": [
                "lame",
                "lame-libs",
                "opus",
                "flac",
                "wavpack",
            ],
        },
    }

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
        except Exception as e:
            return False, str(e)

    def is_package_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        success, _ = self._run_command(["rpm", "-q", package])
        return success

    def check_rpmfusion(self) -> bool:
        """Check if RPM Fusion is enabled."""
        success, output = self._run_command(["dnf", "repolist", "--enabled"])
        return "rpmfusion" in output.lower()

    def show_codec_status(self) -> None:
        """Display current codec installation status."""
        table = Table(title="Multimedia Codec Status")
        table.add_column("Category", style="cyan")
        table.add_column("Installed", justify="center")
        table.add_column("Missing", justify="center")

        for group_id, group in self.CODEC_GROUPS.items():
            installed = 0
            missing = 0

            for pkg in group["packages"]:
                if self.is_package_installed(pkg):
                    installed += 1
                else:
                    missing += 1

            inst_style = "green" if installed > 0 else "dim"
            miss_style = "yellow" if missing > 0 else "dim"

            table.add_row(
                group["name"],
                f"[{inst_style}]{installed}[/]",
                f"[{miss_style}]{missing}[/]",
            )

        self.console.print(table)

    def install_group(self, group_id: str) -> CodecResult:
        """Install a specific codec group."""
        if group_id not in self.CODEC_GROUPS:
            return CodecResult(
                success=False,
                message=f"Unknown codec group: {group_id}",
                packages_installed=[],
            )

        group = self.CODEC_GROUPS[group_id]
        self.console.print(f"\n[bold cyan]Installing {group['name']}...[/]\n")

        # Filter out already installed packages
        to_install = [
            pkg for pkg in group["packages"]
            if not self.is_package_installed(pkg)
        ]

        if not to_install:
            return CodecResult(
                success=True,
                message=f"{group['name']} already installed",
                packages_installed=[],
            )

        with self.progress.status(f"Installing {len(to_install)} package(s)..."):
            success, output = self._run_command(
                ["dnf", "install", "-y", "--skip-broken"] + to_install,
                sudo=True,
                timeout=600,
            )

        if success:
            # Check what was actually installed
            installed = [pkg for pkg in to_install if self.is_package_installed(pkg)]
            return CodecResult(
                success=True,
                message=f"Installed {len(installed)} package(s)",
                packages_installed=installed,
            )

        return CodecResult(
            success=False,
            message=f"Failed to install {group['name']}",
            packages_installed=[],
        )

    def install_all(self) -> CodecResult:
        """Install all multimedia codecs."""
        self.console.print("\n[bold cyan]Installing all multimedia codecs...[/]\n")

        # Check RPM Fusion first
        if not self.check_rpmfusion():
            self.console.print(
                "[yellow]⚠ RPM Fusion not enabled. Some codecs may not be available.[/]\n"
            )

        all_packages = []
        for group in self.CODEC_GROUPS.values():
            all_packages.extend(group["packages"])

        # Filter out installed
        to_install = [
            pkg for pkg in all_packages
            if not self.is_package_installed(pkg)
        ]

        if not to_install:
            return CodecResult(
                success=True,
                message="All codecs already installed",
                packages_installed=[],
            )

        self.console.print(f"[dim]Installing {len(to_install)} package(s)...[/]\n")

        with self.progress.get_progress() as progress:
            task = progress.add_task("Installing codecs...", total=100)

            success, output = self._run_command(
                ["dnf", "install", "-y", "--skip-broken"] + to_install,
                sudo=True,
                timeout=900,
            )

            progress.update(task, completed=100)

        if success:
            installed = [pkg for pkg in to_install if self.is_package_installed(pkg)]
            return CodecResult(
                success=True,
                message=f"Installed {len(installed)}/{len(to_install)} package(s)",
                packages_installed=installed,
            )

        return CodecResult(
            success=False,
            message="Some packages failed to install",
            packages_installed=[],
        )

    def install_essential(self) -> CodecResult:
        """Install essential codecs only (smaller set)."""
        essential = [
            "gstreamer1-plugins-good",
            "gstreamer1-plugins-bad-free",
            "gstreamer1-plugin-openh264",
            "ffmpeg",
            "libva",
            "libva-utils",
        ]

        self.console.print("\n[bold cyan]Installing essential codecs...[/]\n")

        to_install = [pkg for pkg in essential if not self.is_package_installed(pkg)]

        if not to_install:
            return CodecResult(
                success=True,
                message="Essential codecs already installed",
                packages_installed=[],
            )

        with self.progress.status(f"Installing {len(to_install)} package(s)..."):
            success, output = self._run_command(
                ["dnf", "install", "-y", "--skip-broken"] + to_install,
                sudo=True,
                timeout=300,
            )

        if success:
            installed = [pkg for pkg in to_install if self.is_package_installed(pkg)]
            return CodecResult(
                success=True,
                message=f"Essential codecs installed",
                packages_installed=installed,
            )

        return CodecResult(
            success=False,
            message="Failed to install essential codecs",
            packages_installed=[],
        )

    def swap_mesa_freeworld(self) -> CodecResult:
        """Swap Mesa drivers with freeworld versions for better codec support."""
        self.console.print("\n[bold cyan]Swapping to Mesa Freeworld...[/]\n")

        if not self.check_rpmfusion():
            return CodecResult(
                success=False,
                message="RPM Fusion required for Mesa Freeworld",
                packages_installed=[],
            )

        with self.progress.status("Swapping Mesa drivers..."):
            success, output = self._run_command(
                ["dnf", "swap", "mesa-va-drivers", "mesa-va-drivers-freeworld", "-y"],
                sudo=True,
                timeout=120,
            )

            if success:
                self._run_command(
                    ["dnf", "swap", "mesa-vdpau-drivers", "mesa-vdpau-drivers-freeworld", "-y"],
                    sudo=True,
                    timeout=120,
                )

        return CodecResult(
            success=success,
            message="Mesa Freeworld installed" if success else "Failed to swap Mesa",
            packages_installed=["mesa-va-drivers-freeworld"] if success else [],
        )

    def run(self) -> CodecResult:
        """Run codec installation interactively."""
        self.show_codec_status()
        self.console.print()

        if Confirm.ask("Install all multimedia codecs?"):
            return self.install_all()
        elif Confirm.ask("Install essential codecs only?"):
            return self.install_essential()

        return CodecResult(
            success=True,
            message="Codec installation skipped",
            packages_installed=[],
        )


if __name__ == "__main__":
    console = Console()
    installer = CodecInstaller(console)
    result = installer.run()

    if result.success:
        console.print(f"\n[bold green]✓ {result.message}[/]")
        if result.packages_installed:
            console.print(f"[dim]Installed: {', '.join(result.packages_installed[:5])}...[/]")
    else:
        console.print(f"\n[bold red]✗ {result.message}[/]")
