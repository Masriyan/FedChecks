"""
System Health Check Module for FedChecker.
Checks disk space, memory, CPU, services, and package integrity.
"""

import subprocess
import shutil
import os
from typing import Optional
from dataclasses import dataclass

import psutil

from ..ui.colors import CheckResult, CheckStatus, CheckCategory, StatusIcon


class HealthChecker:
    """Performs system health checks."""

    def __init__(self):
        self.results: list[CheckResult] = []

    def run_all_checks(self) -> CheckCategory:
        """Run all health checks and return results."""
        self.results = []

        checks = [
            ("Disk Space", self.check_disk_space),
            ("Memory Usage", self.check_memory),
            ("CPU Temperature", self.check_cpu_temperature),
            ("Swap Space", self.check_swap),
            ("Failed Systemd Units", self.check_failed_units),
            ("System Load", self.check_system_load),
            ("Zombie Processes", self.check_zombie_processes),
            ("Package Manager", self.check_dnf_status),
            ("Journal Errors", self.check_journal_errors),
            ("Orphaned Packages", self.check_orphaned_packages),
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
            name="Health Check",
            icon=StatusIcon.HEALTH,
            results=self.results,
        )

    def check_disk_space(self) -> CheckResult:
        """Check available disk space on all mounted partitions."""
        warnings = []
        critical = []

        for partition in psutil.disk_partitions():
            if partition.fstype and not partition.mountpoint.startswith('/snap'):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    percent_used = usage.percent

                    if percent_used >= 95:
                        critical.append(f"{partition.mountpoint}: {percent_used}% used")
                    elif percent_used >= 85:
                        warnings.append(f"{partition.mountpoint}: {percent_used}% used")
                except PermissionError:
                    continue

        if critical:
            return CheckResult(
                name="Disk Space",
                status=CheckStatus.FAIL,
                message=f"Critical: {len(critical)} partition(s) nearly full",
                details="\n".join(critical + warnings),
                fix_available=True,
                fix_command="dnf autoremove && dnf clean all",
            )
        elif warnings:
            return CheckResult(
                name="Disk Space",
                status=CheckStatus.WARN,
                message=f"Warning: {len(warnings)} partition(s) above 85%",
                details="\n".join(warnings),
                fix_available=True,
                fix_command="dnf autoremove && dnf clean all",
            )

        root_usage = psutil.disk_usage('/').percent
        return CheckResult(
            name="Disk Space",
            status=CheckStatus.PASS,
            message=f"Root partition: {root_usage}% used",
        )

    def check_memory(self) -> CheckResult:
        """Check RAM usage."""
        memory = psutil.virtual_memory()
        percent_used = memory.percent
        available_gb = memory.available / (1024 ** 3)

        if percent_used >= 95:
            return CheckResult(
                name="Memory Usage",
                status=CheckStatus.FAIL,
                message=f"Critical: {percent_used}% RAM used",
                details=f"Only {available_gb:.1f} GB available",
                fix_available=False,
            )
        elif percent_used >= 85:
            return CheckResult(
                name="Memory Usage",
                status=CheckStatus.WARN,
                message=f"Warning: {percent_used}% RAM used",
                details=f"{available_gb:.1f} GB available",
            )

        return CheckResult(
            name="Memory Usage",
            status=CheckStatus.PASS,
            message=f"{percent_used}% used ({available_gb:.1f} GB free)",
        )

    def check_cpu_temperature(self) -> CheckResult:
        """Check CPU temperature if available."""
        try:
            temps = psutil.sensors_temperatures()

            if not temps:
                return CheckResult(
                    name="CPU Temperature",
                    status=CheckStatus.SKIP,
                    message="Temperature sensors not available",
                )

            max_temp = 0
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current > max_temp:
                        max_temp = entry.current

            if max_temp >= 90:
                return CheckResult(
                    name="CPU Temperature",
                    status=CheckStatus.FAIL,
                    message=f"Critical: {max_temp}°C",
                    details="CPU is overheating!",
                    fix_available=False,
                )
            elif max_temp >= 75:
                return CheckResult(
                    name="CPU Temperature",
                    status=CheckStatus.WARN,
                    message=f"Warning: {max_temp}°C",
                    details="CPU temperature is high",
                )

            return CheckResult(
                name="CPU Temperature",
                status=CheckStatus.PASS,
                message=f"{max_temp}°C",
            )
        except Exception:
            return CheckResult(
                name="CPU Temperature",
                status=CheckStatus.SKIP,
                message="Unable to read temperature",
            )

    def check_swap(self) -> CheckResult:
        """Check swap space configuration and usage."""
        swap = psutil.swap_memory()

        if swap.total == 0:
            return CheckResult(
                name="Swap Space",
                status=CheckStatus.WARN,
                message="No swap configured",
                details="Consider adding swap for stability",
                fix_available=True,
                fix_command="fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile",
            )

        swap_gb = swap.total / (1024 ** 3)
        percent_used = swap.percent

        if percent_used >= 80:
            return CheckResult(
                name="Swap Space",
                status=CheckStatus.WARN,
                message=f"Swap {percent_used}% used",
                details=f"{swap_gb:.1f} GB total swap",
            )

        return CheckResult(
            name="Swap Space",
            status=CheckStatus.PASS,
            message=f"{swap_gb:.1f} GB configured, {percent_used}% used",
        )

    def check_failed_units(self) -> CheckResult:
        """Check for failed systemd units."""
        try:
            result = subprocess.run(
                ["systemctl", "--failed", "--no-legend", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            failed_units = [line.split()[0] for line in result.stdout.strip().split('\n') if line]

            if failed_units:
                return CheckResult(
                    name="Failed Systemd Units",
                    status=CheckStatus.FAIL,
                    message=f"{len(failed_units)} failed unit(s)",
                    details="\n".join(failed_units[:5]),
                    fix_available=True,
                    fix_command="systemctl reset-failed",
                )

            return CheckResult(
                name="Failed Systemd Units",
                status=CheckStatus.PASS,
                message="No failed units",
            )
        except subprocess.TimeoutExpired:
            return CheckResult(
                name="Failed Systemd Units",
                status=CheckStatus.SKIP,
                message="Check timed out",
            )

    def check_system_load(self) -> CheckResult:
        """Check system load average."""
        load1, load5, load15 = os.getloadavg()
        cpu_count = os.cpu_count() or 1

        # Load per CPU
        load_per_cpu = load1 / cpu_count

        if load_per_cpu >= 2.0:
            return CheckResult(
                name="System Load",
                status=CheckStatus.FAIL,
                message=f"High load: {load1:.2f}",
                details=f"Load avg: {load1:.2f}, {load5:.2f}, {load15:.2f} ({cpu_count} CPUs)",
            )
        elif load_per_cpu >= 1.0:
            return CheckResult(
                name="System Load",
                status=CheckStatus.WARN,
                message=f"Elevated load: {load1:.2f}",
                details=f"Load avg: {load1:.2f}, {load5:.2f}, {load15:.2f}",
            )

        return CheckResult(
            name="System Load",
            status=CheckStatus.PASS,
            message=f"Load: {load1:.2f} ({cpu_count} CPUs)",
        )

    def check_zombie_processes(self) -> CheckResult:
        """Check for zombie processes."""
        zombies = []

        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                if proc.info['status'] == psutil.STATUS_ZOMBIE:
                    zombies.append(f"PID {proc.info['pid']}: {proc.info['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if zombies:
            return CheckResult(
                name="Zombie Processes",
                status=CheckStatus.WARN,
                message=f"{len(zombies)} zombie process(es)",
                details="\n".join(zombies[:5]),
            )

        return CheckResult(
            name="Zombie Processes",
            status=CheckStatus.PASS,
            message="No zombie processes",
        )

    def check_dnf_status(self) -> CheckResult:
        """Check if DNF is working properly."""
        try:
            result = subprocess.run(
                ["dnf", "check", "--quiet"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return CheckResult(
                    name="Package Manager",
                    status=CheckStatus.FAIL,
                    message="DNF reports issues",
                    details=result.stderr[:200] if result.stderr else "Package database may be corrupted",
                    fix_available=True,
                    fix_command="dnf check && dnf distro-sync",
                )

            return CheckResult(
                name="Package Manager",
                status=CheckStatus.PASS,
                message="DNF is healthy",
            )
        except FileNotFoundError:
            return CheckResult(
                name="Package Manager",
                status=CheckStatus.ERROR,
                message="DNF not found",
            )
        except subprocess.TimeoutExpired:
            return CheckResult(
                name="Package Manager",
                status=CheckStatus.SKIP,
                message="Check timed out",
            )

    def check_journal_errors(self) -> CheckResult:
        """Check system journal for recent errors."""
        try:
            result = subprocess.run(
                ["journalctl", "-p", "err", "-b", "--no-pager", "-q"],
                capture_output=True,
                text=True,
                timeout=15,
            )

            errors = result.stdout.strip().split('\n')
            error_count = len([e for e in errors if e])

            if error_count > 100:
                return CheckResult(
                    name="Journal Errors",
                    status=CheckStatus.WARN,
                    message=f"{error_count} errors since boot",
                    details="Many errors in journal. Check 'journalctl -p err -b'",
                )
            elif error_count > 0:
                return CheckResult(
                    name="Journal Errors",
                    status=CheckStatus.PASS,
                    message=f"{error_count} error(s) since boot",
                )

            return CheckResult(
                name="Journal Errors",
                status=CheckStatus.PASS,
                message="No errors since boot",
            )
        except Exception:
            return CheckResult(
                name="Journal Errors",
                status=CheckStatus.SKIP,
                message="Unable to read journal",
            )

    def check_orphaned_packages(self) -> CheckResult:
        """Check for orphaned packages."""
        try:
            result = subprocess.run(
                ["dnf", "repoquery", "--extras", "--quiet"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            packages = [p for p in result.stdout.strip().split('\n') if p]

            if len(packages) > 10:
                return CheckResult(
                    name="Orphaned Packages",
                    status=CheckStatus.WARN,
                    message=f"{len(packages)} orphaned package(s)",
                    details="Run 'dnf autoremove' to clean up",
                    fix_available=True,
                    fix_command="dnf autoremove",
                )

            return CheckResult(
                name="Orphaned Packages",
                status=CheckStatus.PASS,
                message=f"{len(packages)} orphaned package(s)" if packages else "No orphaned packages",
            )
        except Exception:
            return CheckResult(
                name="Orphaned Packages",
                status=CheckStatus.SKIP,
                message="Unable to check",
            )


if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    checker = HealthChecker()
    category = checker.run_all_checks()

    table = Table(title="Health Check Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Message")

    for result in category.results:
        table.add_row(result.name, result.get_icon(), result.message)

    console.print(table)
    console.print(f"\n[bold]Score: {category.score:.1f}%[/]")
