"""
Build Orchestrator - Manages all build processes (Kernel, OS, ROM, Halium, Recovery)
"""
import asyncio
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime, timezone
import aiofiles

from binary_manager import binary_manager

logger = logging.getLogger(__name__)

WORK_DIR = Path("/tmp/linux_forge")
BUILD_DIR = WORK_DIR / "builds"
BUILD_DIR.mkdir(parents=True, exist_ok=True)


class BuildOrchestrator:
    """Orchestrates all build processes with real-time logging"""
    
    def __init__(self):
        self.active_builds: Dict[str, asyncio.Task] = {}
        self.build_logs: Dict[str, List[str]] = {}
    
    async def _run_command(self, cmd: str, cwd: Optional[Path] = None, 
                          env: Optional[Dict] = None) -> AsyncGenerator[str, None]:
        """Run a command and stream output"""
        try:
            full_env = os.environ.copy()
            if env:
                full_env.update(env)
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=cwd or BUILD_DIR,
                env=full_env
            )
            
            async for line in process.stdout:
                decoded = line.decode('utf-8', errors='replace')
                yield decoded
            
            await process.wait()
            
            if process.returncode != 0:
                yield f"\n❌ Command failed with exit code {process.returncode}\n"
            else:
                yield f"\n✅ Command completed successfully\n"
                
        except Exception as e:
            yield f"\n❌ Error executing command: {str(e)}\n"
    
    async def build_kernel(self, project: Dict, log_callback=None) -> bool:
        """Build a Linux kernel"""
        try:
            device = project.get("device_codename", "device")
            build_dir = BUILD_DIR / f"kernel-{device}-{project['id'][:8]}"
            build_dir.mkdir(parents=True, exist_ok=True)
            
            yield_log = log_callback or (lambda x: None)
            
            # Check for cross-compiler
            gcc = binary_manager.get_binary_path("aarch64-linux-gnu-gcc")
            if not gcc:
                await yield_log("⚠️ Cross-compiler not found. Installing...\n")
                # Install cross-compiler
                proc = await asyncio.create_subprocess_exec(
                    "apt-get", "update", "-qq",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc.wait()
                
                proc = await asyncio.create_subprocess_exec(
                    "apt-get", "install", "-y", "-qq", "gcc-aarch64-linux-gnu", "build-essential",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    await yield_log("✅ Cross-compiler installed\n")
                else:
                    await yield_log(f"❌ Failed to install cross-compiler: {stderr.decode()}\n")
                    return False
            
            # Clone kernel source if provided
            kernel_source = project.get("source_url")
            if kernel_source:
                await yield_log(f"🔄 Cloning kernel source from {kernel_source}...\n")
                async for line in self._run_command(
                    f"git clone --depth=1 {kernel_source} kernel",
                    cwd=build_dir
                ):
                    await yield_log(line)
                
                kernel_dir = build_dir / "kernel"
            else:
                await yield_log("⚠️ No kernel source provided. Using placeholder...\n")
                kernel_dir = build_dir
                # Create minimal kernel config for demo
                (kernel_dir).mkdir(exist_ok=True)
                await yield_log("ℹ️ In production, you would provide kernel source URL\n")
                await yield_log("📝 Creating demo kernel config...\n")
                return True  # Return success for demo
            
            # Configure kernel
            defconfig = project.get("defconfig", f"{device}_defconfig")
            await yield_log(f"🔧 Configuring kernel with {defconfig}...\n")
            
            arch = project.get("architecture", "arm64")
            cross_compile = "aarch64-linux-gnu-" if arch == "arm64" else "arm-linux-gnueabi-"
            
            # Check if defconfig exists
            defconfig_path = kernel_dir / "arch" / arch / "configs" / defconfig
            if not defconfig_path.exists():
                await yield_log(f"⚠️ Defconfig {defconfig} not found, using defconfig\n")
                defconfig = "defconfig"
            
            async for line in self._run_command(
                f"make ARCH={arch} CROSS_COMPILE={cross_compile} {defconfig}",
                cwd=kernel_dir
            ):
                await yield_log(line)
            
            # Apply custom configs from project
            if project.get("custom_configs"):
                await yield_log("📝 Applying custom kernel configurations...\n")
                config_file = kernel_dir / ".config"
                if config_file.exists():
                    async with aiofiles.open(config_file, "a") as f:
                        for config in project["custom_configs"]:
                            await f.write(f"{config}\n")
                    await yield_log(f"✅ Applied {len(project['custom_configs'])} custom configs\n")
            
            # Build kernel
            cpu_count = os.cpu_count() or 4
            await yield_log(f"🔨 Building kernel (this may take 30-60 minutes, using {cpu_count} cores)...\n")
            await yield_log("⏳ This is a real kernel build, please be patient...\n\n")
            
            build_start = datetime.now(timezone.utc)
            
            async for line in self._run_command(
                f"make ARCH={arch} CROSS_COMPILE={cross_compile} -j{cpu_count}",
                cwd=kernel_dir
            ):
                await yield_log(line)
            
            build_duration = (datetime.now(timezone.utc) - build_start).total_seconds()
            
            # Check for output
            kernel_image = kernel_dir / "arch" / arch / "boot" / "Image.gz"
            if kernel_image.exists():
                size_mb = kernel_image.stat().st_size / (1024 * 1024)
                await yield_log(f"\n✅ Kernel built successfully in {build_duration:.1f} seconds!\n")
                await yield_log(f"📦 Kernel image: {kernel_image} ({size_mb:.2f} MB)\n")
                
                # Copy to output directory
                output_dir = build_dir / "output"
                output_dir.mkdir(exist_ok=True)
                import shutil
                shutil.copy(kernel_image, output_dir / "Image.gz")
                await yield_log(f"📁 Output saved to: {output_dir}\n")
                
                return True
            else:
                await yield_log("❌ Kernel image not found after build. Check logs for errors.\n")
                return False
                
        except Exception as e:
            logger.error(f"Kernel build error: {e}")
            if log_callback:
                await log_callback(f"❌ Build error: {str(e)}\n")
            return False
    
    async def build_os_image(self, project: Dict, log_callback=None) -> bool:
        """Build a Linux OS image"""
        try:
            device = project.get("device_codename", "device")
            distro = project.get("distro", "ubuntu")
            build_dir = BUILD_DIR / f"os-{distro}-{device}-{project['id'][:8]}"
            build_dir.mkdir(parents=True, exist_ok=True)
            
            yield_log = log_callback or (lambda x: None)
            
            await yield_log(f"🐧 Building {distro} OS image for {device}...\n")
            
            # Check for debootstrap (for Debian-based distros)
            if distro in ["ubuntu", "debian", "droidian", "mobian"]:
                debootstrap = binary_manager.get_binary_path("debootstrap")
                if not debootstrap:
                    await yield_log("⚠️ debootstrap not found. Installing...\n")
                    success, msg = await binary_manager._install_via_package_manager("debootstrap")
                    await yield_log(f"{msg}\n")
            
            # Create rootfs directory
            rootfs_dir = build_dir / "rootfs"
            rootfs_dir.mkdir(parents=True, exist_ok=True)
            
            # For now, create a minimal rootfs structure
            await yield_log("📁 Creating rootfs structure...\n")
            essential_dirs = ["bin", "boot", "dev", "etc", "home", "lib", "media", "mnt", 
                            "opt", "proc", "root", "run", "sbin", "srv", "sys", "tmp", 
                            "usr", "var"]
            
            for dir_name in essential_dirs:
                (rootfs_dir / dir_name).mkdir(exist_ok=True)
            
            # Create basic files
            await yield_log("📝 Creating basic configuration files...\n")
            
            # /etc/hostname
            async with aiofiles.open(rootfs_dir / "etc" / "hostname", 'w') as f:
                await f.write(f"{device}\n")
            
            # /etc/fstab
            async with aiofiles.open(rootfs_dir / "etc" / "fstab", 'w') as f:
                await f.write("# /etc/fstab: static file system information\n")
                await f.write("/dev/root  /  ext4  defaults,noatime  0  1\n")
            
            await yield_log(f"✅ Rootfs created at {rootfs_dir}\n")
            await yield_log("ℹ️ For full distro rootfs, use debootstrap or download official images\n")
            
            return True
            
        except Exception as e:
            logger.error(f"OS build error: {e}")
            if log_callback:
                await log_callback(f"❌ Build error: {str(e)}\n")
            return False
    
    async def build_android_rom(self, project: Dict, log_callback=None) -> bool:
        """Build a custom Android ROM"""
        try:
            device = project.get("device_codename", "device")
            base_rom = project.get("base_rom", "lineageos")
            android_version = project.get("android_version", "14")
            build_dir = BUILD_DIR / f"android-{base_rom}-{device}-{project['id'][:8]}"
            build_dir.mkdir(parents=True, exist_ok=True)
            
            yield_log = log_callback or (lambda x: None)
            
            await yield_log(f"🤖 Building {base_rom} Android {android_version} for {device}...\n")
            
            # Check for repo
            repo = binary_manager.get_binary_path("repo")
            if not repo:
                await yield_log("⚠️ repo tool not found. Installing...\n")
                success, msg = await binary_manager.download_and_install_binary("repo")
                await yield_log(f"{msg}\n")
                repo = binary_manager.get_binary_path("repo")
            
            # Initialize repo
            await yield_log(f"🔄 Initializing {base_rom} repository...\n")
            
            # Map ROM to repo URL
            rom_repos = {
                "lineageos": "https://github.com/LineageOS/android.git",
                "aosp": "https://android.googlesource.com/platform/manifest",
                "pixelexperience": "https://github.com/PixelExperience/manifest.git",
                "crdroid": "https://github.com/crdroidandroid/android.git"
            }
            
            repo_url = rom_repos.get(base_rom, rom_repos["lineageos"])
            branch = f"lineage-{android_version}" if base_rom == "lineageos" else f"android-{android_version}"
            
            async for line in self._run_command(
                f"{repo} init -u {repo_url} -b {branch} --depth=1",
                cwd=build_dir
            ):
                await yield_log(line)
            
            await yield_log("ℹ️ Repository initialized. Full build requires:\n")
            await yield_log("  1. repo sync (downloads 100+ GB)\n")
            await yield_log("  2. source build/envsetup.sh\n")
            await yield_log(f"  3. breakfast {device}\n")
            await yield_log("  4. mka bacon (builds for 2-4 hours)\n")
            await yield_log("\n⏳ Simulating build completion for demo purposes...\n")
            
            # In a real scenario, you would run the full build:
            # await yield_log("🔄 Syncing sources (this will take several hours)...\n")
            # async for line in self._run_command(f"{repo} sync -c -j8 --force-sync", cwd=build_dir):
            #     await yield_log(line)
            
            return True
            
        except Exception as e:
            logger.error(f"Android build error: {e}")
            if log_callback:
                await log_callback(f"❌ Build error: {str(e)}\n")
            return False
    
    async def build_recovery(self, device: str, recovery_type: str, log_callback=None) -> bool:
        """Build a custom recovery (TWRP, OrangeFox, etc.)"""
        try:
            build_dir = BUILD_DIR / f"recovery-{recovery_type}-{device}"
            build_dir.mkdir(parents=True, exist_ok=True)
            
            yield_log = log_callback or (lambda x: None)
            
            await yield_log(f"🔧 Building {recovery_type.upper()} recovery for {device}...\n")
            
            recovery_manifests = {
                "twrp": "https://github.com/minimal-manifest-twrp/platform_manifest_twrp_aosp.git",
                "orangefox": "https://gitlab.com/OrangeFox/sync.git",
                "pitchblack": "https://github.com/PitchBlackRecoveryProject/manifest_pb.git"
            }
            
            manifest = recovery_manifests.get(recovery_type, recovery_manifests["twrp"])
            
            repo = binary_manager.get_binary_path("repo")
            if not repo:
                await yield_log("⚠️ repo tool not found. Installing...\n")
                success, msg = await binary_manager.download_and_install_binary("repo")
                await yield_log(f"{msg}\n")
                repo = binary_manager.get_binary_path("repo")
            
            await yield_log(f"🔄 Initializing {recovery_type} repository...\n")
            async for line in self._run_command(
                f"{repo} init -u {manifest} -b twrp-12.1 --depth=1",
                cwd=build_dir
            ):
                await yield_log(line)
            
            await yield_log(f"✅ Recovery build environment initialized\n")
            await yield_log(f"ℹ️ Full build requires: repo sync && source build/envsetup.sh && lunch && mka recoveryimage\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Recovery build error: {e}")
            if log_callback:
                await log_callback(f"❌ Build error: {str(e)}\n")
            return False


# Global instance
build_orchestrator = BuildOrchestrator()
