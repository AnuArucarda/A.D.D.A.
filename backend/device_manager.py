"""
Device Manager - Auto-detect and manage Android devices via ADB
"""
import asyncio
import json
import re
from typing import List, Dict, Optional
from pathlib import Path
import logging

from binary_manager import binary_manager

logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages Android device detection and information gathering"""
    
    def __init__(self):
        self.connected_devices: Dict[str, Dict] = {}
    
    async def get_connected_devices(self) -> List[Dict]:
        """Get list of all connected Android devices via ADB"""
        adb_path = binary_manager.get_binary_path("adb")
        if not adb_path:
            return []
        
        try:
            # Run adb devices
            proc = await asyncio.create_subprocess_exec(
                adb_path, "devices", "-l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"ADB devices failed: {stderr.decode()}")
                return []
            
            devices = []
            lines = stdout.decode().strip().split('\n')
            
            # Parse output
            for line in lines[1:]:  # Skip header
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) < 2:
                    continue
                
                serial = parts[0]
                status = parts[1]
                
                if status != "device":
                    continue
                
                # Get device info
                device_info = await self.get_device_info(serial)
                devices.append(device_info)
                self.connected_devices[serial] = device_info
            
            return devices
            
        except Exception as e:
            logger.error(f"Error getting devices: {e}")
            return []
    
    async def get_device_info(self, serial: str) -> Dict:
        """Get detailed information about a device"""
        adb_path = binary_manager.get_binary_path("adb")
        if not adb_path:
            return {"serial": serial, "error": "ADB not available"}
        
        info = {
            "serial": serial,
            "manufacturer": await self._get_prop(serial, "ro.product.manufacturer"),
            "model": await self._get_prop(serial, "ro.product.model"),
            "device": await self._get_prop(serial, "ro.product.device"),
            "codename": await self._get_prop(serial, "ro.build.product"),
            "android_version": await self._get_prop(serial, "ro.build.version.release"),
            "sdk_version": await self._get_prop(serial, "ro.build.version.sdk"),
            "build_id": await self._get_prop(serial, "ro.build.id"),
            "build_fingerprint": await self._get_prop(serial, "ro.build.fingerprint"),
            "cpu_abi": await self._get_prop(serial, "ro.product.cpu.abi"),
            "kernel_version": await self._get_kernel_version(serial),
            "bootloader": await self._get_prop(serial, "ro.bootloader"),
            "security_patch": await self._get_prop(serial, "ro.build.version.security_patch"),
            "is_rooted": await self._check_root(serial),
            "has_custom_recovery": await self._check_custom_recovery(serial)
        }
        
        return info
    
    async def _get_prop(self, serial: str, prop: str) -> str:
        """Get a device property"""
        adb_path = binary_manager.get_binary_path("adb")
        if not adb_path:
            return "unknown"
        
        try:
            proc = await asyncio.create_subprocess_exec(
                adb_path, "-s", serial, "shell", "getprop", prop,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                return stdout.decode().strip()
            return "unknown"
            
        except Exception as e:
            logger.error(f"Error getting prop {prop}: {e}")
            return "unknown"
    
    async def _get_kernel_version(self, serial: str) -> str:
        """Get kernel version"""
        adb_path = binary_manager.get_binary_path("adb")
        if not adb_path:
            return "unknown"
        
        try:
            proc = await asyncio.create_subprocess_exec(
                adb_path, "-s", serial, "shell", "uname", "-r",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                return stdout.decode().strip()
            return "unknown"
            
        except Exception as e:
            return "unknown"
    
    async def _check_root(self, serial: str) -> bool:
        """Check if device is rooted"""
        adb_path = binary_manager.get_binary_path("adb")
        if not adb_path:
            return False
        
        try:
            # Try to run su
            proc = await asyncio.create_subprocess_exec(
                adb_path, "-s", serial, "shell", "su", "-c", "id",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            return "uid=0" in stdout.decode()
            
        except Exception:
            return False
    
    async def _check_custom_recovery(self, serial: str) -> bool:
        """Check if device has custom recovery (TWRP, etc.)"""
        # This is tricky to detect from normal boot
        # We check for common indicators
        adb_path = binary_manager.get_binary_path("adb")
        if not adb_path:
            return False
        
        try:
            # Check for TWRP directory
            proc = await asyncio.create_subprocess_exec(
                adb_path, "-s", serial, "shell", "ls", "/sdcard/TWRP",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            return proc.returncode == 0
            
        except Exception:
            return False
    
    async def reboot_device(self, serial: str, mode: str = "system") -> bool:
        """
        Reboot device to different modes
        mode: system, recovery, bootloader, fastboot
        """
        adb_path = binary_manager.get_binary_path("adb")
        if not adb_path:
            return False
        
        try:
            if mode == "system":
                cmd = [adb_path, "-s", serial, "reboot"]
            elif mode == "recovery":
                cmd = [adb_path, "-s", serial, "reboot", "recovery"]
            elif mode in ["bootloader", "fastboot"]:
                cmd = [adb_path, "-s", serial, "reboot", "bootloader"]
            else:
                return False
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            
            return proc.returncode == 0
            
        except Exception as e:
            logger.error(f"Error rebooting device: {e}")
            return False
    
    async def flash_image(self, serial: str, partition: str, image_path: str) -> tuple[bool, str]:
        """Flash an image to a partition using fastboot"""
        fastboot_path = binary_manager.get_binary_path("fastboot")
        if not fastboot_path:
            return False, "Fastboot not available"
        
        if not Path(image_path).exists():
            return False, f"Image file not found: {image_path}"
        
        try:
            proc = await asyncio.create_subprocess_exec(
                fastboot_path, "-s", serial, "flash", partition, image_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            output = stdout.decode() + stderr.decode()
            
            if proc.returncode == 0:
                return True, f"Successfully flashed {partition}"
            else:
                return False, f"Flash failed: {output}"
                
        except Exception as e:
            logger.error(f"Error flashing image: {e}")
            return False, str(e)
    
    async def install_apk(self, serial: str, apk_path: str) -> tuple[bool, str]:
        """Install an APK on the device"""
        adb_path = binary_manager.get_binary_path("adb")
        if not adb_path:
            return False, "ADB not available"
        
        if not Path(apk_path).exists():
            return False, f"APK file not found: {apk_path}"
        
        try:
            proc = await asyncio.create_subprocess_exec(
                adb_path, "-s", serial, "install", "-r", apk_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            output = stdout.decode() + stderr.decode()
            
            if "Success" in output:
                return True, "APK installed successfully"
            else:
                return False, f"Installation failed: {output}"
                
        except Exception as e:
            logger.error(f"Error installing APK: {e}")
            return False, str(e)


# Global instance
device_manager = DeviceManager()
