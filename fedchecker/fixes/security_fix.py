"""
Security Fix Module for FedChecker.
Provides auto-fix capabilities for security issues.
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


class SecurityFixer:
    """Provides fixes for security-related issues."""

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
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except FileNotFoundError as e:
            return False, str(e)

    def enable_firewall(self) -> FixResult:
        """Enable and configure firewalld."""
        self.console.print("\n[bold cyan]Enabling firewall...[/]\n")

        steps = [
            ("Installing firewalld", ["dnf", "install", "-y", "firewalld"]),
            ("Enabling service", ["systemctl", "enable", "--now", "firewalld"]),
            ("Setting default zone", ["firewall-cmd", "--set-default-zone=FedoraWorkstation"]),
        ]

        for desc, cmd in steps:
            self.console.print(f"[dim]{desc}...[/]")
            success, output = self._run_command(cmd, sudo=True)

            if not success and "already installed" not in output.lower():
                return FixResult(
                    success=False,
                    message=f"Failed at: {desc}",
                    details=output,
                )

        return FixResult(
            success=True,
            message="Firewall enabled and configured",
        )

    def enforce_selinux(self) -> FixResult:
        """Set SELinux to enforcing mode."""
        self.console.print("\n[bold cyan]Enabling SELinux enforcing mode...[/]\n")

        # Set runtime mode
        success, output = self._run_command(["setenforce", "1"], sudo=True)

        if not success:
            return FixResult(
                success=False,
                message="Failed to enable SELinux",
                details=output,
            )

        # Update config for persistence
        success, _ = self._run_command(
            ["sed", "-i", "s/SELINUX=permissive/SELINUX=enforcing/",
             "/etc/selinux/config"],
            sudo=True,
        )

        success, _ = self._run_command(
            ["sed", "-i", "s/SELINUX=disabled/SELINUX=enforcing/",
             "/etc/selinux/config"],
            sudo=True,
        )

        return FixResult(
            success=True,
            message="SELinux set to enforcing",
            details="Configuration updated for persistence",
        )

    def harden_ssh(self) -> FixResult:
        """Harden SSH configuration."""
        self.console.print("\n[bold cyan]Hardening SSH configuration...[/]\n")

        ssh_config = "/etc/ssh/sshd_config"

        settings = [
            ("PermitRootLogin", "no"),
            ("PermitEmptyPasswords", "no"),
            ("MaxAuthTries", "3"),
            ("ClientAliveInterval", "300"),
            ("ClientAliveCountMax", "2"),
        ]

        for key, value in settings:
            # Check if setting exists and update, or append
            self._run_command(
                ["sed", "-i", f"s/^#*{key}.*/{key} {value}/", ssh_config],
                sudo=True,
            )

        # Restart SSH
        success, output = self._run_command(
            ["systemctl", "restart", "sshd"],
            sudo=True,
        )

        if success:
            return FixResult(
                success=True,
                message="SSH hardened",
                details="Root login disabled, auth limits set",
            )

        return FixResult(
            success=False,
            message="Failed to restart SSH",
            details=output,
        )

    def install_fail2ban(self) -> FixResult:
        """Install and configure fail2ban."""
        self.console.print("\n[bold cyan]Installing fail2ban...[/]\n")

        with self.progress.status("Installing fail2ban..."):
            success, output = self._run_command(
                ["dnf", "install", "-y", "fail2ban"],
                sudo=True,
                timeout=120,
            )

        if not success:
            return FixResult(
                success=False,
                message="Failed to install fail2ban",
                details=output,
            )

        # Create basic jail configuration
        jail_config = """[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
"""

        # Write config
        self._run_command(
            ["bash", "-c", f"echo '{jail_config}' > /etc/fail2ban/jail.local"],
            sudo=True,
        )

        # Enable service
        success, output = self._run_command(
            ["systemctl", "enable", "--now", "fail2ban"],
            sudo=True,
        )

        if success:
            return FixResult(
                success=True,
                message="fail2ban installed and configured",
            )

        return FixResult(
            success=False,
            message="Failed to enable fail2ban",
            details=output,
        )

    def enable_auto_updates(self) -> FixResult:
        """Enable automatic security updates."""
        self.console.print("\n[bold cyan]Enabling automatic updates...[/]\n")

        # Install dnf-automatic
        with self.progress.status("Installing dnf-automatic..."):
            success, output = self._run_command(
                ["dnf", "install", "-y", "dnf-automatic"],
                sudo=True,
            )

        if not success:
            return FixResult(
                success=False,
                message="Failed to install dnf-automatic",
                details=output,
            )

        # Configure for security updates only
        config_cmd = """sed -i 's/apply_updates = no/apply_updates = yes/' /etc/dnf/automatic.conf && \
sed -i 's/upgrade_type = default/upgrade_type = security/' /etc/dnf/automatic.conf"""

        self._run_command(["bash", "-c", config_cmd], sudo=True)

        # Enable timer
        success, output = self._run_command(
            ["systemctl", "enable", "--now", "dnf-automatic.timer"],
            sudo=True,
        )

        if success:
            return FixResult(
                success=True,
                message="Automatic security updates enabled",
            )

        return FixResult(
            success=False,
            message="Failed to enable auto-updates",
            details=output,
        )

    def install_clamav(self) -> FixResult:
        """Install and configure ClamAV."""
        self.console.print("\n[bold cyan]Installing ClamAV...[/]\n")

        packages = ["clamav", "clamav-update", "clamd"]

        with self.progress.status("Installing ClamAV..."):
            success, output = self._run_command(
                ["dnf", "install", "-y"] + packages,
                sudo=True,
                timeout=120,
            )

        if not success:
            return FixResult(
                success=False,
                message="Failed to install ClamAV",
                details=output,
            )

        # Update virus definitions
        self.console.print("[dim]Updating virus definitions...[/]")
        self._run_command(["freshclam"], sudo=True, timeout=300)

        # Enable freshclam service
        self._run_command(
            ["systemctl", "enable", "--now", "clamav-freshclam"],
            sudo=True,
        )

        return FixResult(
            success=True,
            message="ClamAV installed and updating",
        )

    def fix_file_permissions(self) -> FixResult:
        """Fix permissions on sensitive files."""
        self.console.print("\n[bold cyan]Fixing file permissions...[/]\n")

        files = [
            ("/etc/passwd", "644"),
            ("/etc/shadow", "000"),
            ("/etc/gshadow", "000"),
            ("/etc/sudoers", "440"),
        ]

        fixed = []
        for filepath, mode in files:
            success, _ = self._run_command(
                ["chmod", mode, filepath],
                sudo=True,
            )
            if success:
                fixed.append(filepath)

        return FixResult(
            success=len(fixed) == len(files),
            message=f"Fixed {len(fixed)}/{len(files)} file permissions",
        )

    def apply_fix(self, check_result: CheckResult) -> FixResult | None:
        """Apply fix based on check result."""
        if not check_result.fix_available:
            return None

        fix_map = {
            "Firewall (firewalld)": self.enable_firewall,
            "SELinux Status": self.enforce_selinux,
            "SSH Configuration": self.harden_ssh,
            "Failed Login Attempts": self.install_fail2ban,
            "Automatic Updates": self.enable_auto_updates,
            "Antivirus (ClamAV)": self.install_clamav,
            "File Permissions": self.fix_file_permissions,
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
