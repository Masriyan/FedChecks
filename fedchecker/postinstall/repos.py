"""
Repository Setup Module for FedChecker.
Configures RPM Fusion, Flathub, and other repositories.
"""

import subprocess
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from ..ui.progress import ProgressManager


@dataclass
class RepoResult:
    """Result of a repository operation."""
    success: bool
    message: str
    repos_added: list[str]


class RepoSetup:
    """Manages repository configuration for Fedora."""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.progress = ProgressManager(self.console)

    def _run_command(
        self,
        cmd: list[str],
        sudo: bool = False,
        timeout: int = 120,
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

    def get_fedora_version(self) -> str:
        """Get Fedora version number."""
        success, output = self._run_command(["rpm", "-E", "%fedora"])
        return output.strip() if success else "unknown"

    def check_repo_enabled(self, repo_name: str) -> bool:
        """Check if a repository is enabled."""
        success, output = self._run_command(["dnf", "repolist", "--enabled"])
        return repo_name.lower() in output.lower()

    def show_repo_status(self) -> None:
        """Display current repository status."""
        table = Table(title="Repository Status")
        table.add_column("Repository", style="cyan")
        table.add_column("Status")
        table.add_column("Description", style="dim")

        repos = [
            ("rpmfusion-free", "RPM Fusion Free", "Free/open-source packages"),
            ("rpmfusion-nonfree", "RPM Fusion Nonfree", "Proprietary drivers, codecs"),
            ("flathub", "Flathub", "Flatpak applications"),
            ("fedora-cisco-openh264", "Cisco OpenH264", "H.264 video codec"),
            ("google-chrome", "Google Chrome", "Chrome browser"),
        ]

        for repo_id, name, desc in repos:
            if self.check_repo_enabled(repo_id):
                status = "[green]✓ Enabled[/]"
            else:
                status = "[dim]○ Not enabled[/]"

            table.add_row(name, status, desc)

        self.console.print(table)

    def setup_rpmfusion(self) -> RepoResult:
        """Set up RPM Fusion repositories."""
        self.console.print("\n[bold cyan]Setting up RPM Fusion...[/]\n")

        fedora_ver = self.get_fedora_version()
        repos_added = []

        # Check if already installed
        if self.check_repo_enabled("rpmfusion-free"):
            return RepoResult(
                success=True,
                message="RPM Fusion already configured",
                repos_added=[],
            )

        # Install RPM Fusion Free
        with self.progress.status("Installing RPM Fusion Free..."):
            free_url = f"https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-{fedora_ver}.noarch.rpm"
            success, output = self._run_command(
                ["dnf", "install", "-y", free_url],
                sudo=True,
                timeout=120,
            )

        if success:
            repos_added.append("rpmfusion-free")
        else:
            return RepoResult(
                success=False,
                message="Failed to install RPM Fusion Free",
                repos_added=[],
            )

        # Install RPM Fusion Nonfree
        with self.progress.status("Installing RPM Fusion Nonfree..."):
            nonfree_url = f"https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-{fedora_ver}.noarch.rpm"
            success, output = self._run_command(
                ["dnf", "install", "-y", nonfree_url],
                sudo=True,
                timeout=120,
            )

        if success:
            repos_added.append("rpmfusion-nonfree")

        # Enable AppStream metadata
        with self.progress.status("Enabling AppStream metadata..."):
            self._run_command(
                ["dnf", "groupupdate", "core", "-y"],
                sudo=True,
                timeout=300,
            )

        return RepoResult(
            success=True,
            message=f"RPM Fusion configured ({', '.join(repos_added)})",
            repos_added=repos_added,
        )

    def setup_flathub(self) -> RepoResult:
        """Set up Flathub repository for Flatpak."""
        self.console.print("\n[bold cyan]Setting up Flathub...[/]\n")

        # Check if Flatpak is installed
        success, _ = self._run_command(["which", "flatpak"])

        if not success:
            # Install Flatpak
            with self.progress.status("Installing Flatpak..."):
                success, output = self._run_command(
                    ["dnf", "install", "-y", "flatpak"],
                    sudo=True,
                )

            if not success:
                return RepoResult(
                    success=False,
                    message="Failed to install Flatpak",
                    repos_added=[],
                )

        # Check if Flathub already added
        success, output = self._run_command(["flatpak", "remotes"])
        if "flathub" in output.lower():
            return RepoResult(
                success=True,
                message="Flathub already configured",
                repos_added=[],
            )

        # Add Flathub
        with self.progress.status("Adding Flathub repository..."):
            success, output = self._run_command([
                "flatpak", "remote-add", "--if-not-exists",
                "flathub", "https://flathub.org/repo/flathub.flatpakrepo"
            ])

        if success:
            return RepoResult(
                success=True,
                message="Flathub configured",
                repos_added=["flathub"],
            )

        return RepoResult(
            success=False,
            message="Failed to add Flathub",
            repos_added=[],
        )

    def setup_openh264(self) -> RepoResult:
        """Enable Cisco OpenH264 repository."""
        self.console.print("\n[bold cyan]Enabling OpenH264...[/]\n")

        if self.check_repo_enabled("fedora-cisco-openh264"):
            return RepoResult(
                success=True,
                message="OpenH264 already enabled",
                repos_added=[],
            )

        with self.progress.status("Enabling OpenH264 repository..."):
            success, output = self._run_command(
                ["dnf", "config-manager", "--enable", "fedora-cisco-openh264"],
                sudo=True,
            )

        if not success:
            return RepoResult(
                success=False,
                message="Failed to enable OpenH264",
                repos_added=[],
            )

        # Install the codec
        with self.progress.status("Installing OpenH264 codec..."):
            self._run_command(
                ["dnf", "install", "-y", "openh264", "mozilla-openh264"],
                sudo=True,
            )

        return RepoResult(
            success=True,
            message="OpenH264 enabled and installed",
            repos_added=["fedora-cisco-openh264"],
        )

    def setup_all(self) -> RepoResult:
        """Set up all recommended repositories."""
        self.console.print("\n[bold cyan]Setting up all recommended repositories...[/]\n")

        all_repos = []
        errors = []

        # RPM Fusion
        result = self.setup_rpmfusion()
        if result.success:
            all_repos.extend(result.repos_added)
        else:
            errors.append("RPM Fusion")

        # Flathub
        result = self.setup_flathub()
        if result.success:
            all_repos.extend(result.repos_added)
        else:
            errors.append("Flathub")

        # OpenH264
        result = self.setup_openh264()
        if result.success:
            all_repos.extend(result.repos_added)
        else:
            errors.append("OpenH264")

        if errors:
            return RepoResult(
                success=False,
                message=f"Some repos failed: {', '.join(errors)}",
                repos_added=all_repos,
            )

        return RepoResult(
            success=True,
            message=f"All repositories configured",
            repos_added=all_repos,
        )

    def run(self) -> RepoResult:
        """Run repository setup interactively."""
        self.show_repo_status()
        self.console.print()

        if Confirm.ask("Set up all recommended repositories?"):
            return self.setup_all()

        return RepoResult(
            success=True,
            message="Repository setup skipped",
            repos_added=[],
        )


if __name__ == "__main__":
    console = Console()
    setup = RepoSetup(console)
    result = setup.run()

    if result.success:
        console.print(f"\n[bold green]✓ {result.message}[/]")
    else:
        console.print(f"\n[bold red]✗ {result.message}[/]")
