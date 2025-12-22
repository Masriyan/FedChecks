"""
Development Tools Installer Module for FedChecker.
Installs common development tools and packages.
"""

import subprocess
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from ..ui.progress import ProgressManager


@dataclass
class DevToolsResult:
    """Result of dev tools installation."""
    success: bool
    message: str
    packages_installed: list[str]


class DevToolsInstaller:
    """Manages development tools installation."""

    # Development tool groups
    DEV_GROUPS = {
        "essential": {
            "name": "Essential Build Tools",
            "packages": [
                "git",
                "make",
                "gcc",
                "gcc-c++",
                "kernel-devel",
                "kernel-headers",
            ],
        },
        "python": {
            "name": "Python Development",
            "packages": [
                "python3-devel",
                "python3-pip",
                "python3-virtualenv",
                "python3-wheel",
                "python3-setuptools",
            ],
        },
        "web": {
            "name": "Web Development",
            "packages": [
                "nodejs",
                "npm",
            ],
        },
        "rust": {
            "name": "Rust Development",
            "packages": [
                "rust",
                "cargo",
            ],
        },
        "go": {
            "name": "Go Development",
            "packages": [
                "golang",
            ],
        },
        "containers": {
            "name": "Container Tools",
            "packages": [
                "podman",
                "podman-compose",
                "buildah",
                "skopeo",
            ],
        },
        "editors": {
            "name": "Code Editors",
            "packages": [
                "vim-enhanced",
                "neovim",
            ],
        },
        "tools": {
            "name": "Development Utilities",
            "packages": [
                "curl",
                "wget",
                "jq",
                "htop",
                "tmux",
                "tree",
                "ripgrep",
                "fd-find",
                "bat",
            ],
        },
    }

    # DNF groups for development
    DNF_GROUPS = [
        "@development-tools",
        "@c-development",
    ]

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
        # Handle group packages
        if package.startswith("@"):
            success, output = self._run_command(
                ["dnf", "group", "info", package.lstrip("@")]
            )
            return success and "Installed" in output

        success, _ = self._run_command(["rpm", "-q", package])
        return success

    def show_devtools_status(self) -> None:
        """Display current development tools status."""
        table = Table(title="Development Tools Status")
        table.add_column("Category", style="cyan")
        table.add_column("Installed", justify="center")
        table.add_column("Missing", justify="center")

        for group_id, group in self.DEV_GROUPS.items():
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

    def install_group(self, group_id: str) -> DevToolsResult:
        """Install a specific development tool group."""
        if group_id not in self.DEV_GROUPS:
            return DevToolsResult(
                success=False,
                message=f"Unknown group: {group_id}",
                packages_installed=[],
            )

        group = self.DEV_GROUPS[group_id]
        self.console.print(f"\n[bold cyan]Installing {group['name']}...[/]\n")

        to_install = [
            pkg for pkg in group["packages"]
            if not self.is_package_installed(pkg)
        ]

        if not to_install:
            return DevToolsResult(
                success=True,
                message=f"{group['name']} already installed",
                packages_installed=[],
            )

        with self.progress.status(f"Installing {len(to_install)} package(s)..."):
            success, output = self._run_command(
                ["dnf", "install", "-y"] + to_install,
                sudo=True,
                timeout=300,
            )

        if success:
            installed = [pkg for pkg in to_install if self.is_package_installed(pkg)]
            return DevToolsResult(
                success=True,
                message=f"Installed {len(installed)} package(s)",
                packages_installed=installed,
            )

        return DevToolsResult(
            success=False,
            message=f"Failed to install {group['name']}",
            packages_installed=[],
        )

    def install_dnf_groups(self) -> DevToolsResult:
        """Install DNF development groups."""
        self.console.print("\n[bold cyan]Installing development groups...[/]\n")

        installed = []

        for group in self.DNF_GROUPS:
            group_name = group.lstrip("@")

            if self.is_package_installed(group):
                self.console.print(f"[dim]{group_name} already installed[/]")
                continue

            self.console.print(f"[dim]Installing {group_name}...[/]")

            success, _ = self._run_command(
                ["dnf", "group", "install", "-y", group_name],
                sudo=True,
                timeout=600,
            )

            if success:
                installed.append(group_name)

        return DevToolsResult(
            success=True,
            message=f"Installed {len(installed)} group(s)",
            packages_installed=installed,
        )

    def install_all(self) -> DevToolsResult:
        """Install all development tools."""
        self.console.print("\n[bold cyan]Installing all development tools...[/]\n")

        all_packages = []
        for group in self.DEV_GROUPS.values():
            all_packages.extend(group["packages"])

        to_install = [
            pkg for pkg in all_packages
            if not self.is_package_installed(pkg)
        ]

        if not to_install:
            return DevToolsResult(
                success=True,
                message="All development tools already installed",
                packages_installed=[],
            )

        # Install DNF groups first
        self.install_dnf_groups()

        # Then individual packages
        self.console.print(f"\n[dim]Installing {len(to_install)} package(s)...[/]\n")

        with self.progress.get_progress() as progress:
            task = progress.add_task("Installing dev tools...", total=100)

            success, output = self._run_command(
                ["dnf", "install", "-y", "--skip-broken"] + to_install,
                sudo=True,
                timeout=900,
            )

            progress.update(task, completed=100)

        if success:
            installed = [pkg for pkg in to_install if self.is_package_installed(pkg)]
            return DevToolsResult(
                success=True,
                message=f"Installed {len(installed)}/{len(to_install)} package(s)",
                packages_installed=installed,
            )

        return DevToolsResult(
            success=False,
            message="Some packages failed to install",
            packages_installed=[],
        )

    def install_essential(self) -> DevToolsResult:
        """Install essential development tools only."""
        essential_groups = ["essential", "python", "tools"]

        self.console.print("\n[bold cyan]Installing essential development tools...[/]\n")

        all_installed = []

        for group_id in essential_groups:
            result = self.install_group(group_id)
            all_installed.extend(result.packages_installed)

        return DevToolsResult(
            success=True,
            message=f"Essential tools installed ({len(all_installed)} packages)",
            packages_installed=all_installed,
        )

    def setup_git_config(self) -> bool:
        """Interactive Git configuration setup."""
        self.console.print("\n[bold cyan]Git Configuration[/]\n")

        # Check current config
        success, name = self._run_command(["git", "config", "--global", "user.name"])
        success2, email = self._run_command(["git", "config", "--global", "user.email"])

        if success and success2 and name.strip() and email.strip():
            self.console.print(f"[dim]Git already configured:[/]")
            self.console.print(f"  Name:  {name.strip()}")
            self.console.print(f"  Email: {email.strip()}")
            return True

        self.console.print("[yellow]Git user configuration not set.[/]")
        self.console.print("[dim]You can configure it later with:[/]")
        self.console.print("  git config --global user.name 'Your Name'")
        self.console.print("  git config --global user.email 'your@email.com'")

        return True

    def run(self) -> DevToolsResult:
        """Run development tools installation interactively."""
        self.show_devtools_status()
        self.console.print()

        if Confirm.ask("Install all development tools?"):
            result = self.install_all()
            self.setup_git_config()
            return result
        elif Confirm.ask("Install essential tools only?"):
            result = self.install_essential()
            self.setup_git_config()
            return result

        return DevToolsResult(
            success=True,
            message="Development tools installation skipped",
            packages_installed=[],
        )


if __name__ == "__main__":
    console = Console()
    installer = DevToolsInstaller(console)
    result = installer.run()

    if result.success:
        console.print(f"\n[bold green]✓ {result.message}[/]")
    else:
        console.print(f"\n[bold red]✗ {result.message}[/]")
