"""
Binary Manager - Handles detection, configuration, and installation of required build tools
"""
import os
import shutil
import asyncio
import platform
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiofiles
import httpx
import logging

logger = logging.getLogger(__name__)

WORK_DIR = Path("/tmp/linux_forge")
BINARIES_DIR = WORK_DIR / "binaries"
BINARIES_DIR.mkdir(parents=True, exist_ok=True)

# Binary download sources
BINARY_SOURCES = {
    "adb": {
        "linux": "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
        "darwin": "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
        "windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
    },
    "repo": {
        "url": "https://storage.googleapis.com/git-repo-downloads/repo",
        "install_path": "/usr/local/bin/repo"
    },
    "dtc": {
        "package": "device-tree-compiler"
    },
    "mkbootimg": {
        "git": "https://github.com/osm0sis/mkbootimg.git"
    }
}

class BinaryManager:
    def __init__(self):
        self.binary_paths: Dict[str, str] = {}
        self.system = platform.system().lower()
        self._load_saved_paths()
    
    def _load_saved_paths(self):
        """Load user-configured binary paths from file"""
        config_file = WORK_DIR / "binary_paths.conf"
        if config_file.exists():
            with open(config_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        self.binary_paths[key] = value
    
    def _save_paths(self):
        """Save configured binary paths"""
        config_file = WORK_DIR / "binary_paths.conf"
        with open(config_file, 'w') as f:
            for key, value in self.binary_paths.items():
                f.write(f"{key}={value}\n")
    
    def check_binary(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a binary is available
        Returns: (is_available, path)
        """
        # First check user-configured path
        if name in self.binary_paths:
            path = self.binary_paths[name]
            if Path(path).exists() and os.access(path, os.X_OK):
                return True, path
        
        # Check system PATH
        system_path = shutil.which(name)
        if system_path:
            return True, system_path
        
        # Check local binaries directory
        local_path = BINARIES_DIR / name
        if local_path.exists() and os.access(local_path, os.X_OK):
            return True, str(local_path)
        
        return False, None
    
    def set_binary_path(self, name: str, path: str) -> bool:
        """Set custom path for a binary"""
        if Path(path).exists():
            self.binary_paths[name] = path
            self._save_paths()
            return True
        return False
    
    async def download_and_install_binary(self, name: str) -> Tuple[bool, str]:
        """
        Download and install a binary
        Returns: (success, message)
        """
        if name not in BINARY_SOURCES:
            return False, f"No download source configured for {name}"
        
        try:
            source = BINARY_SOURCES[name]
            
            if name == "adb":
                return await self._install_platform_tools()
            elif name == "repo":
                return await self._install_repo()
            elif name == "dtc":
                return await self._install_via_package_manager("device-tree-compiler")
            elif name == "mkbootimg":
                return await self._install_mkbootimg()
            
            return False, f"Installation method not implemented for {name}"
            
        except Exception as e:
            logger.error(f"Failed to install {name}: {e}")
            return False, str(e)
    
    async def _install_platform_tools(self) -> Tuple[bool, str]:
        """Download and install Android platform tools (adb, fastboot)"""
        try:
            source = BINARY_SOURCES["adb"].get(self.system, BINARY_SOURCES["adb"]["linux"])
            download_path = BINARIES_DIR / "platform-tools.zip"
            extract_dir = BINARIES_DIR / "platform-tools"
            
            # Download
            async with httpx.AsyncClient(follow_redirects=True, timeout=300) as client:
                response = await client.get(source)
                response.raise_for_status()
                async with aiofiles.open(download_path, 'wb') as f:
                    await f.write(response.content)
            
            # Extract
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(BINARIES_DIR)
            
            # Make executable
            adb_path = extract_dir / "adb"
            fastboot_path = extract_dir / "fastboot"
            
            if adb_path.exists():
                os.chmod(adb_path, 0o755)
                self.binary_paths["adb"] = str(adb_path)
            
            if fastboot_path.exists():
                os.chmod(fastboot_path, 0o755)
                self.binary_paths["fastboot"] = str(fastboot_path)
            
            self._save_paths()
            download_path.unlink()
            
            return True, f"Platform tools installed to {extract_dir}"
            
        except Exception as e:
            return False, f"Failed to install platform tools: {e}"
    
    async def _install_repo(self) -> Tuple[bool, str]:
        """Download and install repo tool"""
        try:
            url = BINARY_SOURCES["repo"]["url"]
            install_path = BINARIES_DIR / "repo"
            
            # Download
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                async with aiofiles.open(install_path, 'wb') as f:
                    await f.write(response.content)
            
            # Make executable
            os.chmod(install_path, 0o755)
            self.binary_paths["repo"] = str(install_path)
            self._save_paths()
            
            return True, f"repo installed to {install_path}"
            
        except Exception as e:
            return False, f"Failed to install repo: {e}"
    
    async def _install_via_package_manager(self, package: str) -> Tuple[bool, str]:
        """Install via system package manager"""
        try:
            # Try apt (Debian/Ubuntu)
            proc = await asyncio.create_subprocess_exec(
                "apt-get", "install", "-y", package,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                return True, f"Installed {package} via apt"
            
            # Try yum (RHEL/CentOS)
            proc = await asyncio.create_subprocess_exec(
                "yum", "install", "-y", package,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                return True, f"Installed {package} via yum"
            
            return False, f"Could not install {package} - no supported package manager found"
            
        except Exception as e:
            return False, f"Failed to install via package manager: {e}"
    
    async def _install_mkbootimg(self) -> Tuple[bool, str]:
        """Clone and install mkbootimg"""
        try:
            repo_dir = BINARIES_DIR / "mkbootimg"
            
            # Clone
            proc = await asyncio.create_subprocess_exec(
                "git", "clone", "--depth=1", BINARY_SOURCES["mkbootimg"]["git"], str(repo_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            
            if proc.returncode != 0:
                return False, "Failed to clone mkbootimg repository"
            
            # Make executable
            mkbootimg_path = repo_dir / "mkbootimg"
            if mkbootimg_path.exists():
                os.chmod(mkbootimg_path, 0o755)
                self.binary_paths["mkbootimg"] = str(mkbootimg_path)
                self._save_paths()
                return True, f"mkbootimg installed to {mkbootimg_path}"
            
            return False, "mkbootimg binary not found after clone"
            
        except Exception as e:
            return False, f"Failed to install mkbootimg: {e}"
    
    def get_all_status(self) -> Dict[str, Dict[str, any]]:
        """Get status of all known binaries"""
        binaries = ["adb", "fastboot", "git", "make", "repo", "dtc", "mkbootimg", 
                    "debootstrap", "gcc", "aarch64-linux-gnu-gcc", "arm-linux-gnueabi-gcc"]
        
        status = {}
        for binary in binaries:
            available, path = self.check_binary(binary)
            status[binary] = {
                "available": available,
                "path": path,
                "can_auto_install": binary in BINARY_SOURCES
            }
        
        return status
    
    def get_binary_path(self, name: str) -> Optional[str]:
        """Get the path to a binary, or None if not available"""
        available, path = self.check_binary(name)
        return path if available else None


# Global instance
binary_manager = BinaryManager()
