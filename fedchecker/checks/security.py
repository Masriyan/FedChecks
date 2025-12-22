"""
Security Check Module for FedChecker.
Checks firewall, SELinux, SSH, ports, and other security settings.
"""

import subprocess
import os
import re
from pathlib import Path
from typing import Optional

from ..ui.colors import CheckResult, CheckStatus, CheckCategory, StatusIcon


class SecurityChecker:
    """Performs security audit checks."""

    def __init__(self):
        self.results: list[CheckResult] = []

    def run_all_checks(self) -> CheckCategory:
        """Run all security checks and return results."""
        self.results = []

        checks = [
            ("Firewall (firewalld)", self.check_firewall),
            ("SELinux Status", self.check_selinux),
            ("SSH Configuration", self.check_ssh_config),
            ("Open Ports", self.check_open_ports),
            ("Failed Login Attempts", self.check_failed_logins),
            ("Root Account", self.check_root_account),
            ("Sudo Configuration", self.check_sudo),
            ("Automatic Updates", self.check_auto_updates),
            ("Password Policy", self.check_password_policy),
            ("File Permissions", self.check_sensitive_files),
            ("Kernel Security", self.check_kernel_security),
            ("Antivirus (ClamAV)", self.check_antivirus),
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
            name="Security Check",
            icon=StatusIcon.SECURITY,
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
            )
            return result.returncode == 0, result.stdout + result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return False, str(e)

    def check_firewall(self) -> CheckResult:
        """Check firewalld status and configuration."""
        # Check if firewalld is installed and running
        success, output = self._run_command(["systemctl", "is-active", "firewalld"])

        if not success or "inactive" in output:
            return CheckResult(
                name="Firewall (firewalld)",
                status=CheckStatus.FAIL,
                message="Firewall is not running",
                details="Your system is not protected by a firewall",
                fix_available=True,
                fix_command="systemctl enable --now firewalld",
            )

        # Get active zone
        success, zone = self._run_command(["firewall-cmd", "--get-default-zone"])
        zone = zone.strip() if success else "unknown"

        # Check for open services
        success, services = self._run_command(["firewall-cmd", "--list-services"])
        service_count = len(services.split()) if success else 0

        return CheckResult(
            name="Firewall (firewalld)",
            status=CheckStatus.PASS,
            message=f"Active (zone: {zone})",
            details=f"{service_count} allowed services",
        )

    def check_selinux(self) -> CheckResult:
        """Check SELinux status and mode."""
        success, output = self._run_command(["getenforce"])

        if not success:
            return CheckResult(
                name="SELinux Status",
                status=CheckStatus.WARN,
                message="Unable to check SELinux",
            )

        mode = output.strip().lower()

        if mode == "enforcing":
            return CheckResult(
                name="SELinux Status",
                status=CheckStatus.PASS,
                message="SELinux is enforcing",
            )
        elif mode == "permissive":
            return CheckResult(
                name="SELinux Status",
                status=CheckStatus.WARN,
                message="SELinux is permissive",
                details="Consider setting to enforcing mode",
                fix_available=True,
                fix_command="setenforce 1 && sed -i 's/SELINUX=permissive/SELINUX=enforcing/' /etc/selinux/config",
            )
        else:
            return CheckResult(
                name="SELinux Status",
                status=CheckStatus.FAIL,
                message="SELinux is disabled",
                details="Highly recommended to enable SELinux",
                fix_available=True,
                fix_command="sed -i 's/SELINUX=disabled/SELINUX=enforcing/' /etc/selinux/config && reboot",
            )

    def check_ssh_config(self) -> CheckResult:
        """Check SSH server configuration."""
        sshd_config = Path("/etc/ssh/sshd_config")

        if not sshd_config.exists():
            return CheckResult(
                name="SSH Configuration",
                status=CheckStatus.SKIP,
                message="SSH server not installed",
            )

        config = sshd_config.read_text()
        issues = []

        # Check for root login
        if re.search(r'^\s*PermitRootLogin\s+yes', config, re.MULTILINE | re.IGNORECASE):
            issues.append("Root login enabled")

        # Check for password authentication (may want key-only)
        if re.search(r'^\s*PasswordAuthentication\s+yes', config, re.MULTILINE | re.IGNORECASE):
            # This is a warning, not critical
            pass

        # Check for empty passwords
        if re.search(r'^\s*PermitEmptyPasswords\s+yes', config, re.MULTILINE | re.IGNORECASE):
            issues.append("Empty passwords allowed")

        # Check X11 forwarding
        if re.search(r'^\s*X11Forwarding\s+yes', config, re.MULTILINE | re.IGNORECASE):
            # Minor issue
            pass

        # Check SSH service
        success, _ = self._run_command(["systemctl", "is-active", "sshd"])

        if issues:
            return CheckResult(
                name="SSH Configuration",
                status=CheckStatus.WARN,
                message=f"{len(issues)} security issue(s)",
                details="\n".join(issues),
                fix_available=True,
                fix_command="sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config && systemctl restart sshd",
            )

        if success:
            return CheckResult(
                name="SSH Configuration",
                status=CheckStatus.PASS,
                message="SSH configured securely",
            )
        else:
            return CheckResult(
                name="SSH Configuration",
                status=CheckStatus.PASS,
                message="SSH not running (secure)",
            )

    def check_open_ports(self) -> CheckResult:
        """Check for open listening ports."""
        success, output = self._run_command(["ss", "-tuln"])

        if not success:
            return CheckResult(
                name="Open Ports",
                status=CheckStatus.SKIP,
                message="Unable to check ports",
            )

        # Parse listening ports
        listening = []
        for line in output.split('\n'):
            if 'LISTEN' in line:
                parts = line.split()
                if len(parts) >= 5:
                    addr = parts[4]
                    # Extract port
                    if ':' in addr:
                        port = addr.rsplit(':', 1)[-1]
                        listening.append(port)

        # Common safe ports
        safe_ports = {'22', '631', '5353'}  # SSH, CUPS, mDNS
        external_ports = [p for p in listening if p not in safe_ports]

        if len(external_ports) > 5:
            return CheckResult(
                name="Open Ports",
                status=CheckStatus.WARN,
                message=f"{len(listening)} ports listening",
                details=f"External: {', '.join(external_ports[:5])}...",
            )

        return CheckResult(
            name="Open Ports",
            status=CheckStatus.PASS,
            message=f"{len(listening)} ports listening",
        )

    def check_failed_logins(self) -> CheckResult:
        """Check for failed login attempts."""
        success, output = self._run_command(
            ["journalctl", "-u", "sshd", "--since", "24 hours ago", "--no-pager", "-q"],
            timeout=15
        )

        if not success:
            # Try alternative method
            success, output = self._run_command(
                ["lastb", "-n", "100"],
                timeout=10
            )

        if not success:
            return CheckResult(
                name="Failed Login Attempts",
                status=CheckStatus.SKIP,
                message="Unable to check login attempts",
            )

        # Count failed attempts
        failed_count = output.lower().count("failed") + output.lower().count("authentication failure")

        if failed_count > 50:
            return CheckResult(
                name="Failed Login Attempts",
                status=CheckStatus.WARN,
                message=f"{failed_count}+ failed attempts (24h)",
                details="Consider installing fail2ban",
                fix_available=True,
                fix_command="dnf install fail2ban && systemctl enable --now fail2ban",
            )
        elif failed_count > 0:
            return CheckResult(
                name="Failed Login Attempts",
                status=CheckStatus.PASS,
                message=f"{failed_count} failed attempt(s) (24h)",
            )

        return CheckResult(
            name="Failed Login Attempts",
            status=CheckStatus.PASS,
            message="No failed attempts (24h)",
        )

    def check_root_account(self) -> CheckResult:
        """Check root account security."""
        # Check if root has a password set
        shadow = Path("/etc/shadow")

        if not shadow.exists() or not os.access(shadow, os.R_OK):
            return CheckResult(
                name="Root Account",
                status=CheckStatus.SKIP,
                message="Cannot read shadow file",
            )

        try:
            with open(shadow) as f:
                for line in f:
                    if line.startswith("root:"):
                        parts = line.split(":")
                        password_hash = parts[1] if len(parts) > 1 else ""

                        if password_hash in ("", "*", "!!", "!"):
                            return CheckResult(
                                name="Root Account",
                                status=CheckStatus.PASS,
                                message="Root login disabled",
                            )
                        else:
                            return CheckResult(
                                name="Root Account",
                                status=CheckStatus.WARN,
                                message="Root has password set",
                                details="Consider using sudo instead of root login",
                            )
        except PermissionError:
            return CheckResult(
                name="Root Account",
                status=CheckStatus.SKIP,
                message="Cannot check root account",
            )

        return CheckResult(
            name="Root Account",
            status=CheckStatus.PASS,
            message="Root account secure",
        )

    def check_sudo(self) -> CheckResult:
        """Check sudo configuration."""
        # Check if user is in wheel group
        success, groups = self._run_command(["groups"])

        if "wheel" not in groups:
            return CheckResult(
                name="Sudo Configuration",
                status=CheckStatus.WARN,
                message="Current user not in wheel group",
                details="May not have sudo access",
            )

        # Check sudoers for NOPASSWD
        sudoers = Path("/etc/sudoers")
        sudoers_d = Path("/etc/sudoers.d")

        has_nopasswd = False

        if sudoers.exists() and os.access(sudoers, os.R_OK):
            content = sudoers.read_text()
            if "NOPASSWD" in content:
                has_nopasswd = True

        if sudoers_d.exists():
            for f in sudoers_d.iterdir():
                if f.is_file() and os.access(f, os.R_OK):
                    try:
                        if "NOPASSWD" in f.read_text():
                            has_nopasswd = True
                    except:
                        pass

        if has_nopasswd:
            return CheckResult(
                name="Sudo Configuration",
                status=CheckStatus.WARN,
                message="NOPASSWD entries found",
                details="Some commands don't require password",
            )

        return CheckResult(
            name="Sudo Configuration",
            status=CheckStatus.PASS,
            message="Sudo configured properly",
        )

    def check_auto_updates(self) -> CheckResult:
        """Check if automatic updates are configured."""
        # Check for dnf-automatic
        success, output = self._run_command(["systemctl", "is-enabled", "dnf-automatic.timer"])

        if success and "enabled" in output:
            return CheckResult(
                name="Automatic Updates",
                status=CheckStatus.PASS,
                message="dnf-automatic enabled",
            )

        # Check for packagekit offline updates
        success, output = self._run_command(["systemctl", "is-enabled", "packagekit-offline-update"])

        if success and "enabled" in output:
            return CheckResult(
                name="Automatic Updates",
                status=CheckStatus.PASS,
                message="PackageKit updates enabled",
            )

        return CheckResult(
            name="Automatic Updates",
            status=CheckStatus.WARN,
            message="Auto-updates not configured",
            details="Consider enabling automatic security updates",
            fix_available=True,
            fix_command="dnf install dnf-automatic && systemctl enable --now dnf-automatic.timer",
        )

    def check_password_policy(self) -> CheckResult:
        """Check password policy configuration."""
        pwquality = Path("/etc/security/pwquality.conf")

        if not pwquality.exists():
            return CheckResult(
                name="Password Policy",
                status=CheckStatus.WARN,
                message="pwquality not configured",
                fix_available=True,
                fix_command="dnf install libpwquality",
            )

        config = pwquality.read_text()

        # Check minimum length
        minlen_match = re.search(r'^\s*minlen\s*=\s*(\d+)', config, re.MULTILINE)
        minlen = int(minlen_match.group(1)) if minlen_match else 8

        if minlen < 8:
            return CheckResult(
                name="Password Policy",
                status=CheckStatus.WARN,
                message=f"Minimum password length: {minlen}",
                details="Recommended: at least 12 characters",
            )

        return CheckResult(
            name="Password Policy",
            status=CheckStatus.PASS,
            message=f"Password policy OK (min: {minlen})",
        )

    def check_sensitive_files(self) -> CheckResult:
        """Check permissions on sensitive files."""
        files_to_check = [
            ("/etc/passwd", 0o644),
            ("/etc/shadow", 0o000),
            ("/etc/gshadow", 0o000),
            ("/etc/sudoers", 0o440),
        ]

        issues = []

        for filepath, expected_mode in files_to_check:
            path = Path(filepath)
            if path.exists():
                mode = path.stat().st_mode & 0o777
                if mode > expected_mode:
                    issues.append(f"{filepath}: {oct(mode)}")

        if issues:
            return CheckResult(
                name="File Permissions",
                status=CheckStatus.WARN,
                message=f"{len(issues)} permission issue(s)",
                details="\n".join(issues),
            )

        return CheckResult(
            name="File Permissions",
            status=CheckStatus.PASS,
            message="Sensitive files secured",
        )

    def check_kernel_security(self) -> CheckResult:
        """Check kernel security parameters."""
        issues = []

        sysctl_checks = {
            "/proc/sys/net/ipv4/ip_forward": ("0", "IP forwarding enabled"),
            "/proc/sys/net/ipv4/conf/all/rp_filter": ("1", "Reverse path filtering disabled"),
            "/proc/sys/kernel/randomize_va_space": ("2", "ASLR not fully enabled"),
        }

        for path, (expected, issue_msg) in sysctl_checks.items():
            p = Path(path)
            if p.exists():
                try:
                    value = p.read_text().strip()
                    if value != expected:
                        issues.append(issue_msg)
                except:
                    pass

        if issues:
            return CheckResult(
                name="Kernel Security",
                status=CheckStatus.WARN,
                message=f"{len(issues)} setting(s) suboptimal",
                details="\n".join(issues),
            )

        return CheckResult(
            name="Kernel Security",
            status=CheckStatus.PASS,
            message="Kernel security OK",
        )

    def check_antivirus(self) -> CheckResult:
        """Check if ClamAV is installed and updated."""
        # Check if clamscan is available
        success, _ = self._run_command(["which", "clamscan"])

        if not success:
            return CheckResult(
                name="Antivirus (ClamAV)",
                status=CheckStatus.SKIP,
                message="ClamAV not installed",
                details="Optional: install for malware scanning",
                fix_available=True,
                fix_command="dnf install clamav clamav-update",
            )

        # Check freshclam service
        success, output = self._run_command(["systemctl", "is-active", "clamav-freshclam"])

        if success and "active" in output:
            return CheckResult(
                name="Antivirus (ClamAV)",
                status=CheckStatus.PASS,
                message="ClamAV installed and updating",
            )

        return CheckResult(
            name="Antivirus (ClamAV)",
            status=CheckStatus.WARN,
            message="ClamAV installed, updates disabled",
            fix_available=True,
            fix_command="systemctl enable --now clamav-freshclam",
        )


if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    checker = SecurityChecker()
    category = checker.run_all_checks()

    table = Table(title="Security Check Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Message")

    for result in category.results:
        table.add_row(result.name, result.get_icon(), result.message)

    console.print(table)
    console.print(f"\n[bold]Score: {category.score:.1f}%[/]")
