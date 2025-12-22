"""
Driver Check Module for FedChecker.
Checks GPU, WiFi, audio, Bluetooth, and other hardware drivers.
"""

import subprocess
import os
import re
from pathlib import Path
from typing import Optional

from ..ui.colors import CheckResult, CheckStatus, CheckCategory, StatusIcon


class DriverChecker:
    """Performs hardware driver checks."""

    def __init__(self):
        self.results: list[CheckResult] = []

    def run_all_checks(self) -> CheckCategory:
        """Run all driver checks and return results."""
        self.results = []

        checks = [
            ("GPU Driver", self.check_gpu_driver),
            ("WiFi Driver", self.check_wifi_driver),
            ("Audio Driver", self.check_audio_driver),
            ("Bluetooth", self.check_bluetooth),
            ("USB Controllers", self.check_usb),
            ("Network (Ethernet)", self.check_ethernet),
            ("Webcam", self.check_webcam),
            ("Firmware Updates", self.check_firmware),
            ("Kernel Modules", self.check_kernel_modules),
            ("Hardware Acceleration", self.check_hw_acceleration),
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
            name="Driver Check",
            icon=StatusIcon.DRIVER,
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

    def check_gpu_driver(self) -> CheckResult:
        """Check GPU driver status."""
        gpu_info = {"vendor": "Unknown", "driver": "Unknown", "status": "unknown"}

        # Check for GPU using lspci
        success, output = self._run_command(["lspci", "-nnk"])

        if not success:
            return CheckResult(
                name="GPU Driver",
                status=CheckStatus.SKIP,
                message="Unable to detect GPU",
            )

        # Parse GPU information
        lines = output.split('\n')
        vga_lines = []
        capturing = False

        for line in lines:
            if 'VGA' in line or '3D controller' in line or 'Display controller' in line:
                vga_lines.append(line)
                capturing = True
            elif capturing:
                if line.startswith('\t'):
                    vga_lines.append(line)
                else:
                    capturing = False

        if not vga_lines:
            return CheckResult(
                name="GPU Driver",
                status=CheckStatus.WARN,
                message="No GPU detected",
            )

        # Detect GPU vendor and driver
        gpu_text = '\n'.join(vga_lines)

        if 'NVIDIA' in gpu_text.upper():
            gpu_info['vendor'] = "NVIDIA"
            if 'nvidia' in gpu_text.lower() and 'Kernel driver in use: nvidia' in gpu_text:
                gpu_info['driver'] = "nvidia (proprietary)"
                gpu_info['status'] = "optimal"
            elif 'nouveau' in gpu_text.lower():
                gpu_info['driver'] = "nouveau (open-source)"
                gpu_info['status'] = "working"
                return CheckResult(
                    name="GPU Driver",
                    status=CheckStatus.WARN,
                    message=f"NVIDIA using nouveau driver",
                    details="Consider installing nvidia-driver for better performance",
                    fix_available=True,
                    fix_command="dnf install akmod-nvidia xorg-x11-drv-nvidia-cuda",
                )
            else:
                return CheckResult(
                    name="GPU Driver",
                    status=CheckStatus.FAIL,
                    message="NVIDIA GPU without proper driver",
                    fix_available=True,
                    fix_command="dnf install akmod-nvidia",
                )

        elif 'AMD' in gpu_text.upper() or 'ATI' in gpu_text.upper() or 'Radeon' in gpu_text:
            gpu_info['vendor'] = "AMD"
            if 'amdgpu' in gpu_text.lower():
                gpu_info['driver'] = "amdgpu"
                gpu_info['status'] = "optimal"
            elif 'radeon' in gpu_text.lower():
                gpu_info['driver'] = "radeon"
                gpu_info['status'] = "working"

        elif 'Intel' in gpu_text:
            gpu_info['vendor'] = "Intel"
            if 'i915' in gpu_text.lower():
                gpu_info['driver'] = "i915"
                gpu_info['status'] = "optimal"

        # Get driver in use
        kernel_driver_match = re.search(r'Kernel driver in use: (\w+)', gpu_text)
        if kernel_driver_match:
            gpu_info['driver'] = kernel_driver_match.group(1)

        return CheckResult(
            name="GPU Driver",
            status=CheckStatus.PASS,
            message=f"{gpu_info['vendor']}: {gpu_info['driver']}",
            details=vga_lines[0] if vga_lines else "",
        )

    def check_wifi_driver(self) -> CheckResult:
        """Check WiFi driver and connectivity."""
        # Check for wireless interfaces
        success, output = self._run_command(["ip", "link", "show"])

        wireless_interfaces = []
        if success:
            for line in output.split('\n'):
                if 'wl' in line.lower() or 'wlan' in line.lower():
                    match = re.match(r'\d+: (\w+):', line)
                    if match:
                        wireless_interfaces.append(match.group(1))

        if not wireless_interfaces:
            # Check if there's WiFi hardware
            success, lspci = self._run_command(["lspci", "-nnk"])
            if 'Wireless' in lspci or 'Wi-Fi' in lspci or 'WLAN' in lspci:
                return CheckResult(
                    name="WiFi Driver",
                    status=CheckStatus.FAIL,
                    message="WiFi hardware found but no driver loaded",
                    fix_available=True,
                    fix_command="dnf install linux-firmware iwlwifi-firmware",
                )
            return CheckResult(
                name="WiFi Driver",
                status=CheckStatus.SKIP,
                message="No WiFi hardware detected",
            )

        # Get driver for the interface
        interface = wireless_interfaces[0]
        driver_path = f"/sys/class/net/{interface}/device/driver"

        driver = "unknown"
        if os.path.exists(driver_path):
            driver = os.path.basename(os.readlink(driver_path))

        # Check connection status
        success, rfkill = self._run_command(["rfkill", "list", "wifi"])
        if 'Soft blocked: yes' in rfkill or 'Hard blocked: yes' in rfkill:
            return CheckResult(
                name="WiFi Driver",
                status=CheckStatus.WARN,
                message=f"{driver} driver loaded, WiFi blocked",
                details=f"Interface: {interface}",
                fix_available=True,
                fix_command="rfkill unblock wifi",
            )

        return CheckResult(
            name="WiFi Driver",
            status=CheckStatus.PASS,
            message=f"{driver} ({interface})",
        )

    def check_audio_driver(self) -> CheckResult:
        """Check audio driver and sound devices."""
        # Check for sound cards
        sound_cards_path = Path("/proc/asound/cards")

        if not sound_cards_path.exists():
            return CheckResult(
                name="Audio Driver",
                status=CheckStatus.FAIL,
                message="No sound subsystem detected",
                fix_available=True,
                fix_command="dnf install alsa-plugins-pulseaudio pipewire-alsa",
            )

        cards = sound_cards_path.read_text()

        if "no soundcards" in cards.lower() or not cards.strip():
            return CheckResult(
                name="Audio Driver",
                status=CheckStatus.FAIL,
                message="No sound cards found",
                fix_available=True,
                fix_command="dnf install alsa-firmware sof-firmware",
            )

        # Check PipeWire/PulseAudio status
        success, pw = self._run_command(["systemctl", "--user", "is-active", "pipewire"])
        if success and "active" in pw:
            audio_server = "PipeWire"
        else:
            success, pa = self._run_command(["systemctl", "--user", "is-active", "pulseaudio"])
            if success and "active" in pa:
                audio_server = "PulseAudio"
            else:
                audio_server = "Unknown"

        # Count sound cards
        card_count = len(re.findall(r'^\s*\d+\s+\[', cards, re.MULTILINE))

        return CheckResult(
            name="Audio Driver",
            status=CheckStatus.PASS,
            message=f"{card_count} card(s), {audio_server}",
        )

    def check_bluetooth(self) -> CheckResult:
        """Check Bluetooth driver and service."""
        # Check if Bluetooth hardware exists
        success, lsusb = self._run_command(["lsusb"])
        success2, lspci = self._run_command(["lspci"])

        has_bt_hardware = 'Bluetooth' in lsusb or 'Bluetooth' in lspci

        if not has_bt_hardware:
            # Check hci devices
            hci_path = Path("/sys/class/bluetooth")
            if not hci_path.exists() or not list(hci_path.iterdir()):
                return CheckResult(
                    name="Bluetooth",
                    status=CheckStatus.SKIP,
                    message="No Bluetooth hardware detected",
                )

        # Check Bluetooth service
        success, bt_status = self._run_command(["systemctl", "is-active", "bluetooth"])

        if not success or "inactive" in bt_status:
            return CheckResult(
                name="Bluetooth",
                status=CheckStatus.WARN,
                message="Bluetooth service not running",
                fix_available=True,
                fix_command="systemctl enable --now bluetooth",
            )

        # Check if blocked
        success, rfkill = self._run_command(["rfkill", "list", "bluetooth"])
        if 'Soft blocked: yes' in rfkill or 'Hard blocked: yes' in rfkill:
            return CheckResult(
                name="Bluetooth",
                status=CheckStatus.WARN,
                message="Bluetooth is blocked",
                fix_available=True,
                fix_command="rfkill unblock bluetooth",
            )

        return CheckResult(
            name="Bluetooth",
            status=CheckStatus.PASS,
            message="Bluetooth active",
        )

    def check_usb(self) -> CheckResult:
        """Check USB controllers."""
        success, output = self._run_command(["lsusb"])

        if not success:
            return CheckResult(
                name="USB Controllers",
                status=CheckStatus.SKIP,
                message="Unable to query USB devices",
            )

        device_count = len([l for l in output.split('\n') if l.strip()])

        # Check for USB 3.0 support
        success, lspci = self._run_command(["lspci", "-v"])
        has_usb3 = 'xHCI' in lspci or 'USB 3' in lspci

        return CheckResult(
            name="USB Controllers",
            status=CheckStatus.PASS,
            message=f"{device_count} device(s)" + (", USB 3.0" if has_usb3 else ""),
        )

    def check_ethernet(self) -> CheckResult:
        """Check ethernet driver."""
        success, output = self._run_command(["ip", "link", "show"])

        eth_interfaces = []
        if success:
            for line in output.split('\n'):
                if 'eth' in line.lower() or 'enp' in line.lower() or 'eno' in line.lower():
                    match = re.match(r'\d+: (\w+):', line)
                    if match:
                        eth_interfaces.append(match.group(1))

        if not eth_interfaces:
            return CheckResult(
                name="Network (Ethernet)",
                status=CheckStatus.SKIP,
                message="No ethernet interface detected",
            )

        # Get driver info
        interface = eth_interfaces[0]
        driver_path = f"/sys/class/net/{interface}/device/driver"

        driver = "unknown"
        if os.path.exists(driver_path):
            driver = os.path.basename(os.readlink(driver_path))

        # Check link status
        success, carrier = self._run_command(["cat", f"/sys/class/net/{interface}/carrier"])
        is_connected = success and carrier.strip() == "1"

        status_msg = "connected" if is_connected else "no link"

        return CheckResult(
            name="Network (Ethernet)",
            status=CheckStatus.PASS,
            message=f"{driver} ({interface}): {status_msg}",
        )

    def check_webcam(self) -> CheckResult:
        """Check webcam/video devices."""
        video_devices = list(Path("/dev").glob("video*"))

        if not video_devices:
            return CheckResult(
                name="Webcam",
                status=CheckStatus.SKIP,
                message="No video devices found",
            )

        # Try to get more info
        success, output = self._run_command(["v4l2-ctl", "--list-devices"])

        if success and output.strip():
            # Count actual cameras (not metadata devices)
            cameras = len(re.findall(r'/dev/video\d+', output))
            return CheckResult(
                name="Webcam",
                status=CheckStatus.PASS,
                message=f"{cameras} video device(s) found",
            )

        return CheckResult(
            name="Webcam",
            status=CheckStatus.PASS,
            message=f"{len(video_devices)} video device(s)",
        )

    def check_firmware(self) -> CheckResult:
        """Check for firmware updates using fwupd."""
        # Check if fwupd is available
        success, _ = self._run_command(["which", "fwupdmgr"])

        if not success:
            return CheckResult(
                name="Firmware Updates",
                status=CheckStatus.WARN,
                message="fwupd not installed",
                fix_available=True,
                fix_command="dnf install fwupd",
            )

        # Check for updates
        success, output = self._run_command(["fwupdmgr", "get-updates", "--json"], timeout=30)

        if "No upgrades" in output or "No updates" in output:
            return CheckResult(
                name="Firmware Updates",
                status=CheckStatus.PASS,
                message="Firmware up to date",
            )
        elif success:
            return CheckResult(
                name="Firmware Updates",
                status=CheckStatus.WARN,
                message="Firmware updates available",
                fix_available=True,
                fix_command="fwupdmgr update",
            )

        return CheckResult(
            name="Firmware Updates",
            status=CheckStatus.PASS,
            message="Unable to check updates",
        )

    def check_kernel_modules(self) -> CheckResult:
        """Check for missing or problematic kernel modules."""
        success, output = self._run_command(["dmesg"])

        if not success:
            return CheckResult(
                name="Kernel Modules",
                status=CheckStatus.SKIP,
                message="Unable to read dmesg",
            )

        # Look for firmware/module errors
        missing_firmware = re.findall(r'firmware: failed to load (\S+)', output)
        failed_modules = re.findall(r'(\w+): probe of .* failed', output)

        issues = len(set(missing_firmware)) + len(set(failed_modules))

        if issues > 5:
            return CheckResult(
                name="Kernel Modules",
                status=CheckStatus.WARN,
                message=f"{issues} firmware/module issue(s)",
                details="Check dmesg for details",
                fix_available=True,
                fix_command="dnf install linux-firmware",
            )
        elif issues > 0:
            return CheckResult(
                name="Kernel Modules",
                status=CheckStatus.PASS,
                message=f"{issues} minor issue(s)",
            )

        return CheckResult(
            name="Kernel Modules",
            status=CheckStatus.PASS,
            message="No module issues detected",
        )

    def check_hw_acceleration(self) -> CheckResult:
        """Check hardware video acceleration."""
        # Check VA-API
        success, vainfo = self._run_command(["vainfo"])
        has_vaapi = success and "VAProfile" in vainfo

        # Check VDPAU
        success, vdpau = self._run_command(["vdpauinfo"])
        has_vdpau = success and "VDPAU" in vdpau

        if has_vaapi and has_vdpau:
            return CheckResult(
                name="Hardware Acceleration",
                status=CheckStatus.PASS,
                message="VA-API and VDPAU available",
            )
        elif has_vaapi:
            return CheckResult(
                name="Hardware Acceleration",
                status=CheckStatus.PASS,
                message="VA-API available",
            )
        elif has_vdpau:
            return CheckResult(
                name="Hardware Acceleration",
                status=CheckStatus.PASS,
                message="VDPAU available",
            )

        return CheckResult(
            name="Hardware Acceleration",
            status=CheckStatus.WARN,
            message="No hardware acceleration detected",
            fix_available=True,
            fix_command="dnf install libva-utils vdpauinfo mesa-va-drivers",
        )


if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    checker = DriverChecker()
    category = checker.run_all_checks()

    table = Table(title="Driver Check Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Message")

    for result in category.results:
        table.add_row(result.name, result.get_icon(), result.message)

    console.print(table)
    console.print(f"\n[bold]Score: {category.score:.1f}%[/]")
