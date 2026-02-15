from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, AsyncGenerator
import uuid
from datetime import datetime, timezone
import asyncio
import subprocess
import shutil
import json
import re
import aiofiles
import httpx
import tarfile
import zipfile

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'linux_device_forge')]

# Claude AI integration
from emergentintegrations.llm.chat import LlmChat, UserMessage

# Create the main app
app = FastAPI(title="Linux Device Forge API")

# Create API router
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ======================= CONSTANTS =======================

WORK_DIR = Path("/tmp/linux_forge")
WORK_DIR.mkdir(parents=True, exist_ok=True)

# Supported Linux Distributions
MOBILE_DISTROS = {
    "ubuntu-touch": {
        "name": "Ubuntu Touch",
        "description": "Ubuntu for phones and tablets by UBports",
        "rootfs_url": "https://ci.ubports.com/job/xenial-rootfs-armhf/",
        "init_system": "upstart",
        "type": "mobile"
    },
    "postmarketos": {
        "name": "postmarketOS",
        "description": "Alpine-based Linux for phones, aims for 10 year device support",
        "rootfs_url": "https://images.postmarketos.org/",
        "init_system": "openrc",
        "type": "mobile"
    },
    "droidian": {
        "name": "Droidian",
        "description": "Debian-based, runs on Halium (Android drivers)",
        "rootfs_url": "https://github.com/droidian-images/rootfs-api28gsi-all/releases",
        "init_system": "systemd",
        "type": "mobile"
    },
    "mobian": {
        "name": "Mobian",
        "description": "Debian + Phosh for mobile devices",
        "rootfs_url": "https://images.mobian-project.org/",
        "init_system": "systemd",
        "type": "mobile"
    },
    "plasma-mobile": {
        "name": "Plasma Mobile",
        "description": "KDE Plasma for mobile devices",
        "rootfs_url": "https://plasma-mobile.org/get/",
        "init_system": "systemd",
        "type": "mobile"
    },
    "luneos": {
        "name": "LuneOS",
        "description": "webOS community continuation",
        "rootfs_url": "https://github.com/pLuneOS/",
        "init_system": "systemd",
        "type": "mobile"
    },
    "sailfish": {
        "name": "Sailfish OS",
        "description": "Jolla's Linux-based mobile OS",
        "rootfs_url": "https://sailfishos.org/",
        "init_system": "systemd",
        "type": "mobile"
    }
}

DESKTOP_DISTROS = {
    "ubuntu": {
        "name": "Ubuntu",
        "description": "Popular Debian-based distribution",
        "rootfs_url": "https://cdimage.ubuntu.com/ubuntu-base/releases/",
        "init_system": "systemd",
        "versions": ["24.04", "22.04", "20.04"]
    },
    "debian": {
        "name": "Debian",
        "description": "The universal operating system",
        "rootfs_url": "https://www.debian.org/distrib/",
        "init_system": "systemd",
        "versions": ["12", "11"]
    },
    "arch": {
        "name": "Arch Linux",
        "description": "Simple, lightweight distribution",
        "rootfs_url": "https://archlinuxarm.org/",
        "init_system": "systemd",
        "versions": ["latest"]
    },
    "fedora": {
        "name": "Fedora",
        "description": "Cutting-edge Red Hat sponsored distro",
        "rootfs_url": "https://fedoraproject.org/",
        "init_system": "systemd",
        "versions": ["40", "39"]
    },
    "alpine": {
        "name": "Alpine Linux",
        "description": "Security-focused, lightweight",
        "rootfs_url": "https://alpinelinux.org/downloads/",
        "init_system": "openrc",
        "versions": ["3.19", "3.18"]
    },
    "manjaro": {
        "name": "Manjaro",
        "description": "User-friendly Arch-based",
        "rootfs_url": "https://manjaro.org/",
        "init_system": "systemd",
        "versions": ["latest"]
    },
    "void": {
        "name": "Void Linux",
        "description": "Independent distro with runit",
        "rootfs_url": "https://voidlinux.org/",
        "init_system": "runit",
        "versions": ["latest"]
    },
    "gentoo": {
        "name": "Gentoo",
        "description": "Source-based, highly customizable",
        "rootfs_url": "https://www.gentoo.org/",
        "init_system": "openrc",
        "versions": ["latest"]
    }
}

# Kernel versions for upstreaming
MAINLINE_KERNELS = {
    "6.8": {"status": "mainline", "eol": False},
    "6.6": {"status": "lts", "eol": False},
    "6.1": {"status": "lts", "eol": False},
    "5.15": {"status": "lts", "eol": False},
    "5.10": {"status": "lts", "eol": False},
    "5.4": {"status": "lts", "eol": False},
    "4.19": {"status": "lts", "eol": False},
    "4.14": {"status": "eol", "eol": True},
    "4.9": {"status": "eol", "eol": True},
    "4.4": {"status": "eol", "eol": True},
}

# Kernel config requirements for generic Linux boot
KERNEL_CONFIG_LINUX_GENERIC = [
    # Core requirements
    {"config": "CONFIG_DEVTMPFS", "required": True, "category": "core", "description": "Device filesystem"},
    {"config": "CONFIG_DEVTMPFS_MOUNT", "required": True, "category": "core", "description": "Automount devtmpfs"},
    {"config": "CONFIG_TMPFS", "required": True, "category": "core", "description": "Temporary filesystem"},
    {"config": "CONFIG_PROC_FS", "required": True, "category": "core", "description": "Proc filesystem"},
    {"config": "CONFIG_SYSFS", "required": True, "category": "core", "description": "Sysfs filesystem"},
    
    # Namespaces & Containers
    {"config": "CONFIG_NAMESPACES", "required": True, "category": "namespace", "description": "Namespace support"},
    {"config": "CONFIG_NET_NS", "required": True, "category": "namespace", "description": "Network namespaces"},
    {"config": "CONFIG_PID_NS", "required": True, "category": "namespace", "description": "PID namespaces"},
    {"config": "CONFIG_IPC_NS", "required": True, "category": "namespace", "description": "IPC namespaces"},
    {"config": "CONFIG_UTS_NS", "required": True, "category": "namespace", "description": "UTS namespaces"},
    {"config": "CONFIG_USER_NS", "required": False, "category": "namespace", "description": "User namespaces"},
    {"config": "CONFIG_CGROUPS", "required": True, "category": "namespace", "description": "Control groups"},
    
    # Filesystem
    {"config": "CONFIG_EXT4_FS", "required": True, "category": "filesystem", "description": "EXT4 filesystem"},
    {"config": "CONFIG_F2FS_FS", "required": False, "category": "filesystem", "description": "F2FS filesystem"},
    {"config": "CONFIG_SQUASHFS", "required": True, "category": "filesystem", "description": "SquashFS (for rootfs)"},
    {"config": "CONFIG_OVERLAY_FS", "required": True, "category": "filesystem", "description": "Overlay filesystem"},
    {"config": "CONFIG_FUSE_FS", "required": False, "category": "filesystem", "description": "FUSE support"},
    
    # Networking
    {"config": "CONFIG_NET", "required": True, "category": "network", "description": "Networking support"},
    {"config": "CONFIG_INET", "required": True, "category": "network", "description": "TCP/IP networking"},
    {"config": "CONFIG_NETFILTER", "required": True, "category": "network", "description": "Netfilter"},
    {"config": "CONFIG_NF_NAT", "required": True, "category": "network", "description": "NAT support"},
    {"config": "CONFIG_VETH", "required": True, "category": "network", "description": "Virtual ethernet"},
    {"config": "CONFIG_BRIDGE", "required": False, "category": "network", "description": "Network bridging"},
    {"config": "CONFIG_WIRELESS", "required": True, "category": "network", "description": "Wireless support"},
    {"config": "CONFIG_CFG80211", "required": True, "category": "network", "description": "Wireless config API"},
    {"config": "CONFIG_MAC80211", "required": True, "category": "network", "description": "MAC80211 stack"},
    
    # Android compatibility (for hybrid approach)
    {"config": "CONFIG_ANDROID_BINDER_IPC", "required": False, "category": "android", "description": "Binder IPC"},
    {"config": "CONFIG_ASHMEM", "required": False, "category": "android", "description": "Anonymous shared memory"},
    
    # Display
    {"config": "CONFIG_FB", "required": True, "category": "display", "description": "Framebuffer support"},
    {"config": "CONFIG_DRM", "required": True, "category": "display", "description": "Direct Rendering Manager"},
    {"config": "CONFIG_DRM_FBDEV_EMULATION", "required": True, "category": "display", "description": "DRM FB emulation"},
    
    # Input
    {"config": "CONFIG_INPUT", "required": True, "category": "input", "description": "Input subsystem"},
    {"config": "CONFIG_INPUT_EVDEV", "required": True, "category": "input", "description": "Event interface"},
    {"config": "CONFIG_INPUT_TOUCHSCREEN", "required": True, "category": "input", "description": "Touchscreen support"},
    
    # USB
    {"config": "CONFIG_USB", "required": True, "category": "usb", "description": "USB support"},
    {"config": "CONFIG_USB_GADGET", "required": True, "category": "usb", "description": "USB gadget support"},
    {"config": "CONFIG_USB_CONFIGFS", "required": False, "category": "usb", "description": "USB ConfigFS"},
    
    # Power
    {"config": "CONFIG_PM", "required": True, "category": "power", "description": "Power management"},
    {"config": "CONFIG_PM_SLEEP", "required": True, "category": "power", "description": "Suspend/hibernate"},
    {"config": "CONFIG_CPU_FREQ", "required": True, "category": "power", "description": "CPU frequency scaling"},
    
    # Security
    {"config": "CONFIG_SECURITY", "required": False, "category": "security", "description": "Security options"},
    {"config": "CONFIG_SECCOMP", "required": True, "category": "security", "description": "Seccomp filters"},
    {"config": "CONFIG_SECURITY_SELINUX", "required": False, "category": "security", "description": "SELinux"},
    {"config": "CONFIG_SECURITY_APPARMOR", "required": False, "category": "security", "description": "AppArmor"},
]

# Toolchains for cross-compilation
TOOLCHAINS = {
    "aarch64": {
        "prefix": "aarch64-linux-gnu-",
        "arch": "arm64",
        "package": "gcc-aarch64-linux-gnu"
    },
    "armv7": {
        "prefix": "arm-linux-gnueabihf-",
        "arch": "arm",
        "package": "gcc-arm-linux-gnueabihf"
    },
    "x86_64": {
        "prefix": "",
        "arch": "x86_64",
        "package": "build-essential"
    }
}

# Halium versions (kept from original)
HALIUM_VERSIONS = {
    "halium-7.1": {"android": "7.1", "lineage": "14.1", "branch": "halium-7.1"},
    "halium-9.0": {"android": "9.0", "lineage": "16.0", "branch": "halium-9.0"},
    "halium-10.0": {"android": "10", "lineage": "17.1", "branch": "halium-10.0"},
    "halium-11.0": {"android": "11", "lineage": "18.1", "branch": "halium-11.0"},
}

HALIUM_MANIFEST_URL = "https://github.com/halium/android.git"

# ======================= MODELS =======================

class DeviceInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    serial: str
    model: Optional[str] = None
    device: Optional[str] = None
    codename: Optional[str] = None
    product: Optional[str] = None
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    android_version: Optional[str] = None
    sdk_version: Optional[str] = None
    kernel_version: Optional[str] = None
    kernel_version_parsed: Optional[Dict[str, Any]] = None
    build_fingerprint: Optional[str] = None
    cpu_abi: Optional[str] = None
    architecture: Optional[str] = None
    hardware: Optional[str] = None
    platform: Optional[str] = None
    soc: Optional[str] = None
    soc_manufacturer: Optional[str] = None
    partitions: Optional[Dict[str, Any]] = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class KernelProject(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    device_codename: str
    source_url: Optional[str] = None
    source_type: str = "git"  # git, tar, local
    current_version: Optional[str] = None
    target_version: Optional[str] = None
    architecture: str = "arm64"
    defconfig: Optional[str] = None
    config_analysis: Optional[Dict[str, Any]] = None
    patches_applied: List[str] = []
    build_status: str = "pending"
    build_dir: Optional[str] = None
    output_files: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OSImageProject(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    device_codename: str
    distro: str
    distro_version: Optional[str] = None
    distro_type: str = "mobile"  # mobile, desktop, custom
    kernel_project_id: Optional[str] = None
    rootfs_source: Optional[str] = None  # url or path
    custom_upload: bool = False
    init_system: str = "systemd"
    desktop_environment: Optional[str] = None
    packages_to_add: List[str] = []
    packages_to_remove: List[str] = []
    build_status: str = "pending"
    build_dir: Optional[str] = None
    output_image: Optional[str] = None
    boot_image: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BackportRequest(BaseModel):
    kernel_project_id: str
    feature_or_driver: str
    source_version: str
    target_version: str

class UpstreamAnalysis(BaseModel):
    current_version: str
    target_version: str
    compatibility_score: int
    required_changes: List[Dict[str, Any]]
    breaking_changes: List[str]
    recommended_patches: List[str]
    estimated_effort: str

class BuildRequest(BaseModel):
    device_serial: Optional[str] = None
    device_codename: str
    architecture: str = "arm64"
    kernel_source: Optional[str] = None
    defconfig: Optional[str] = None
    target_kernel_version: Optional[str] = None

class OSBuildRequest(BaseModel):
    device_codename: str
    distro: str
    distro_version: Optional[str] = None
    kernel_project_id: Optional[str] = None
    custom_rootfs_path: Optional[str] = None
    desktop_environment: Optional[str] = None
    additional_packages: List[str] = []

class HaliumBuildRequest(BaseModel):
    device_serial: str
    halium_version: str = "halium-11.0"
    build_type: str = "lineage"
    build_dir: str = "/home/user/halium"
    auto_mode: bool = True

# Request models
class CommandRequest(BaseModel):
    command: str
    session_id: Optional[str] = None
    working_dir: Optional[str] = None
    timeout: int = 120

class AIRequest(BaseModel):
    message: str
    session_id: str
    device_context: Optional[Dict[str, Any]] = None
    kernel_context: Optional[Dict[str, Any]] = None
    build_context: Optional[Dict[str, Any]] = None
    auto_execute: bool = False

# ======================= HELPERS =======================

async def run_command(cmd: str, timeout: int = 120, cwd: str = None, env: Dict = None) -> tuple[str, str, int]:
    """Execute a shell command"""
    try:
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd or str(WORK_DIR),
            env=full_env
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return stdout.decode(), stderr.decode(), process.returncode
    except asyncio.TimeoutError:
        return "", f"Command timed out after {timeout}s", -1
    except Exception as e:
        return "", str(e), -1

async def run_command_stream(cmd: str, cwd: str = None) -> AsyncGenerator[str, None]:
    """Execute command and stream output"""
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd or str(WORK_DIR)
        )
        async for line in process.stdout:
            yield line.decode()
        await process.wait()
    except Exception as e:
        yield f"Error: {str(e)}\n"

def check_tool_available(tool: str) -> bool:
    return shutil.which(tool) is not None

def parse_kernel_version(version_string: str) -> Dict[str, Any]:
    """Parse kernel version string into components"""
    result = {"raw": version_string, "major": 0, "minor": 0, "patch": 0}
    match = re.search(r'(\d+)\.(\d+)\.(\d+)', version_string)
    if match:
        result["major"] = int(match.group(1))
        result["minor"] = int(match.group(2))
        result["patch"] = int(match.group(3))
        result["version"] = f"{result['major']}.{result['minor']}"
    return result

def parse_adb_devices(output: str) -> List[Dict[str, str]]:
    devices = []
    lines = output.strip().split('\n')[1:]
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                devices.append({'serial': parts[0], 'state': parts[1]})
    return devices

async def get_device_prop(serial: str, prop: str) -> str:
    stdout, _, _ = await run_command(f"adb -s {serial} shell getprop {prop}")
    return stdout.strip()

async def get_full_device_info(serial: str) -> DeviceInfo:
    """Get comprehensive device information"""
    device_info = DeviceInfo(serial=serial)
    
    device_info.model = await get_device_prop(serial, "ro.product.model")
    device_info.device = await get_device_prop(serial, "ro.product.device")
    device_info.codename = device_info.device
    device_info.product = await get_device_prop(serial, "ro.product.name")
    device_info.manufacturer = await get_device_prop(serial, "ro.product.manufacturer")
    device_info.brand = await get_device_prop(serial, "ro.product.brand")
    device_info.android_version = await get_device_prop(serial, "ro.build.version.release")
    device_info.sdk_version = await get_device_prop(serial, "ro.build.version.sdk")
    device_info.build_fingerprint = await get_device_prop(serial, "ro.build.fingerprint")
    device_info.cpu_abi = await get_device_prop(serial, "ro.product.cpu.abi")
    device_info.hardware = await get_device_prop(serial, "ro.hardware")
    device_info.platform = await get_device_prop(serial, "ro.board.platform")
    
    # Determine architecture
    if device_info.cpu_abi:
        if "arm64" in device_info.cpu_abi or "aarch64" in device_info.cpu_abi:
            device_info.architecture = "arm64"
        elif "arm" in device_info.cpu_abi:
            device_info.architecture = "arm"
        elif "x86_64" in device_info.cpu_abi:
            device_info.architecture = "x86_64"
        elif "x86" in device_info.cpu_abi:
            device_info.architecture = "x86"
    
    # SoC info
    for prop in ["ro.soc.model", "ro.hardware.chipname", "ro.mediatek.platform", "ro.hardware.soc"]:
        soc = await get_device_prop(serial, prop)
        if soc:
            device_info.soc = soc
            break
    
    # SoC manufacturer
    platform = device_info.platform or ""
    if "msm" in platform.lower() or "sdm" in platform.lower() or "sm" in platform.lower():
        device_info.soc_manufacturer = "Qualcomm"
    elif "mt" in platform.lower() or "mediatek" in platform.lower():
        device_info.soc_manufacturer = "MediaTek"
    elif "exynos" in platform.lower():
        device_info.soc_manufacturer = "Samsung"
    elif "kirin" in platform.lower():
        device_info.soc_manufacturer = "HiSilicon"
    elif "tensor" in platform.lower():
        device_info.soc_manufacturer = "Google"
    
    # Kernel version
    stdout, _, _ = await run_command(f"adb -s {serial} shell cat /proc/version")
    if stdout:
        device_info.kernel_version = stdout.strip()[:300]
        device_info.kernel_version_parsed = parse_kernel_version(stdout)
    
    # Partitions
    for cmd in [
        f"adb -s {serial} shell ls -la /dev/block/by-name/",
        f"adb -s {serial} shell ls -la /dev/block/platform/*/by-name/",
        f"adb -s {serial} shell ls -la /dev/block/bootdevice/by-name/"
    ]:
        stdout, _, code = await run_command(cmd)
        if stdout and code == 0:
            partitions = {}
            for line in stdout.strip().split('\n'):
                match = re.search(r'(\w+)\s*->\s*(.+)$', line)
                if match:
                    partitions[match.group(1)] = match.group(2)
            if partitions:
                device_info.partitions = partitions
                break
    
    return device_info

# ======================= AI AGENT =======================

FORGE_SYSTEM_PROMPT = """You are an expert Linux Kernel & OS Engineer AI agent with deep expertise in:

## KERNEL DEVELOPMENT
- Linux kernel architecture and subsystems
- Kernel configuration (Kconfig, defconfig, menuconfig)
- Cross-compilation for ARM, ARM64, x86
- Device tree (DTS/DTB) creation and modification
- Driver development and porting
- Kernel upstreaming and backporting strategies
- Git workflow for kernel development

## MOBILE LINUX
- postmarketOS mainline kernel approach
- Halium/Android driver hybridization
- Ubuntu Touch, Droidian, Mobian, Plasma Mobile
- Mobile-specific drivers: touchscreen, modem, sensors, cameras
- Libhybris for Android driver compatibility

## OS IMAGE BUILDING  
- Rootfs creation (debootstrap, pacstrap, apk)
- Initramfs generation
- Boot image creation (mkbootimg, abootimg)
- Partition layouts and flashing
- Init systems: systemd, OpenRC, runit

## DEVICE SUPPORT
- Qualcomm (MSM/SDM/SM platforms)
- MediaTek (MT platforms)
- Samsung Exynos
- Device tree extraction from DTBO/boot images
- Firmware/blob extraction

When providing commands, use ```bash blocks. Explain complex operations.
For kernel work, always specify ARCH, CROSS_COMPILE, and defconfig.
For dangerous operations (flashing, dd), warn the user first.

You can analyze kernel configs, suggest patches, generate device trees, and guide the complete process of building a custom Linux kernel and OS image for any Android device."""

class AIAgent:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        self.sessions: Dict[str, LlmChat] = {}
    
    def get_or_create_session(self, session_id: str) -> LlmChat:
        if session_id not in self.sessions:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=FORGE_SYSTEM_PROMPT
            )
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            self.sessions[session_id] = chat
        return self.sessions[session_id]
    
    async def send_message(self, session_id: str, message: str, contexts: Dict[str, Any] = None) -> str:
        chat = self.get_or_create_session(session_id)
        
        full_message = message
        if contexts:
            for name, ctx in contexts.items():
                if ctx:
                    full_message += f"\n\n[{name}]\n```json\n{json.dumps(ctx, indent=2, default=str)}\n```"
        
        user_msg = UserMessage(text=full_message)
        return await chat.send_message(user_msg)
    
    def extract_commands(self, response: str) -> List[str]:
        commands = []
        pattern = r'```(?:bash|sh|shell)?\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            for cmd in match.strip().split('\n'):
                cmd = cmd.strip()
                if cmd and not cmd.startswith('#'):
                    commands.append(cmd)
        return commands

ai_agent = AIAgent()

# ======================= WEBSOCKET MANAGER =======================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
    
    async def send_message(self, session_id: str, message: Dict):
        if session_id in self.active_connections:
            for ws in self.active_connections[session_id]:
                try:
                    await ws.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# ======================= KERNEL FORGE =======================

class KernelForge:
    def __init__(self, project: KernelProject):
        self.project = project
        self.work_dir = WORK_DIR / "kernels" / project.id
        self.work_dir.mkdir(parents=True, exist_ok=True)
    
    async def log(self, message: str, level: str = "info"):
        await manager.send_message(self.project.id, {"type": "log", "level": level, "message": message})
        logger.info(f"[{self.project.id}] {message}")
    
    async def clone_kernel_source(self, url: str, branch: str = None) -> bool:
        """Clone kernel source from git"""
        await self.log(f"Cloning kernel source from {url}")
        
        cmd = f"git clone --depth=1"
        if branch:
            cmd += f" -b {branch}"
        cmd += f" {url} {self.work_dir}/kernel"
        
        stdout, stderr, code = await run_command(cmd, timeout=600)
        if code != 0:
            await self.log(f"Clone failed: {stderr}", "error")
            return False
        
        self.project.build_dir = str(self.work_dir / "kernel")
        return True
    
    async def analyze_kernel_config(self, defconfig_path: str = None) -> Dict[str, Any]:
        """Analyze kernel configuration for Linux compatibility"""
        await self.log("Analyzing kernel configuration...")
        
        kernel_dir = Path(self.project.build_dir or self.work_dir / "kernel")
        
        # Find defconfig
        if defconfig_path:
            config_path = kernel_dir / defconfig_path
        else:
            # Search for defconfig
            defconfigs = list(kernel_dir.glob("arch/arm64/configs/*_defconfig")) + \
                        list(kernel_dir.glob("arch/arm/configs/*_defconfig"))
            if not defconfigs:
                return {"error": "No defconfig found"}
            config_path = defconfigs[0]
            self.project.defconfig = config_path.name
        
        if not config_path.exists():
            return {"error": f"Config not found: {config_path}"}
        
        async with aiofiles.open(config_path, 'r') as f:
            config_content = await f.read()
        
        analysis = {
            "defconfig": str(config_path),
            "total_configs": len(KERNEL_CONFIG_LINUX_GENERIC),
            "categories": {},
            "met": [],
            "missing": [],
            "recommendations": []
        }
        
        for req in KERNEL_CONFIG_LINUX_GENERIC:
            present = req["config"] in config_content
            enabled = f'{req["config"]}=y' in config_content or f'{req["config"]}=m' in config_content
            
            category = req["category"]
            if category not in analysis["categories"]:
                analysis["categories"][category] = {"met": 0, "missing": 0, "total": 0}
            analysis["categories"][category]["total"] += 1
            
            if enabled:
                analysis["met"].append(req)
                analysis["categories"][category]["met"] += 1
            elif req["required"]:
                analysis["missing"].append(req)
                analysis["categories"][category]["missing"] += 1
                analysis["recommendations"].append(f"Add {req['config']}=y  # {req['description']}")
        
        analysis["compatibility_score"] = int((len(analysis["met"]) / len(KERNEL_CONFIG_LINUX_GENERIC)) * 100)
        analysis["linux_ready"] = len([m for m in analysis["missing"] if m["required"]]) == 0
        
        self.project.config_analysis = analysis
        return analysis
    
    async def apply_config_fixes(self, defconfig_path: str = None) -> bool:
        """Apply missing kernel config options"""
        analysis = self.project.config_analysis
        if not analysis or not analysis.get("missing"):
            await self.log("No config fixes needed")
            return True
        
        kernel_dir = Path(self.project.build_dir)
        config_path = kernel_dir / (defconfig_path or f"arch/arm64/configs/{self.project.defconfig}")
        
        await self.log(f"Applying {len(analysis['missing'])} config fixes...")
        
        additions = ["\n# Linux compatibility additions (auto-generated)"]
        for req in analysis["missing"]:
            if req["required"]:
                additions.append(f"{req['config']}=y")
        
        async with aiofiles.open(config_path, 'a') as f:
            await f.write('\n'.join(additions))
        
        return True
    
    async def analyze_upstream_compatibility(self, target_version: str) -> UpstreamAnalysis:
        """Analyze compatibility for upstreaming to newer kernel"""
        current = self.project.current_version
        if not current:
            # Try to detect from Makefile
            kernel_dir = Path(self.project.build_dir)
            makefile = kernel_dir / "Makefile"
            if makefile.exists():
                async with aiofiles.open(makefile, 'r') as f:
                    content = await f.read()
                match = re.search(r'VERSION\s*=\s*(\d+).*?PATCHLEVEL\s*=\s*(\d+)', content, re.DOTALL)
                if match:
                    current = f"{match.group(1)}.{match.group(2)}"
                    self.project.current_version = current
        
        await self.log(f"Analyzing upstream path: {current} -> {target_version}")
        
        # Determine compatibility
        current_parts = [int(x) for x in current.split('.')[:2]] if current else [0, 0]
        target_parts = [int(x) for x in target_version.split('.')[:2]]
        
        version_diff = (target_parts[0] - current_parts[0]) * 10 + (target_parts[1] - current_parts[1])
        
        breaking_changes = []
        required_changes = []
        
        # Common breaking changes between kernel versions
        if current_parts[0] < 5 and target_parts[0] >= 5:
            breaking_changes.append("Major API changes from 4.x to 5.x")
            required_changes.append({"type": "api", "description": "Update to new DRM/KMS API", "effort": "high"})
        
        if current_parts[0] == 4 and current_parts[1] < 14:
            breaking_changes.append("Very old kernel, significant effort required")
            required_changes.append({"type": "driver", "description": "Many drivers need major updates", "effort": "high"})
        
        if target_parts[0] >= 6:
            required_changes.append({"type": "config", "description": "Enable new Rust support options if needed", "effort": "low"})
        
        # SoC-specific considerations
        if self.project.device_codename:
            required_changes.append({
                "type": "device_tree",
                "description": f"Port device tree for {self.project.device_codename}",
                "effort": "medium"
            })
        
        compatibility_score = max(0, 100 - (version_diff * 10))
        
        return UpstreamAnalysis(
            current_version=current or "unknown",
            target_version=target_version,
            compatibility_score=compatibility_score,
            required_changes=required_changes,
            breaking_changes=breaking_changes,
            recommended_patches=[
                f"https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/log/?h=v{target_version}"
            ],
            estimated_effort="low" if version_diff <= 2 else ("medium" if version_diff <= 5 else "high")
        )
    
    async def compile_kernel(self) -> bool:
        """Compile the kernel"""
        kernel_dir = Path(self.project.build_dir)
        arch = self.project.architecture
        
        toolchain = TOOLCHAINS.get(arch, TOOLCHAINS["aarch64"])
        
        await self.log(f"Compiling kernel for {arch}...")
        
        env = {
            "ARCH": toolchain["arch"],
            "CROSS_COMPILE": toolchain["prefix"]
        }
        
        # Make defconfig
        defconfig = self.project.defconfig or f"{self.project.device_codename}_defconfig"
        cmd = f"make {defconfig}"
        stdout, stderr, code = await run_command(cmd, cwd=str(kernel_dir), env=env, timeout=120)
        if code != 0:
            await self.log(f"Defconfig failed: {stderr}", "error")
            return False
        
        # Compile
        cmd = f"make -j$(nproc)"
        await self.log("Running make (this may take a while)...")
        
        async for line in run_command_stream(cmd, cwd=str(kernel_dir)):
            await manager.send_message(self.project.id, {"type": "output", "line": line})
        
        # Check for output
        image_paths = [
            kernel_dir / "arch" / toolchain["arch"] / "boot" / "Image",
            kernel_dir / "arch" / toolchain["arch"] / "boot" / "Image.gz",
            kernel_dir / "arch" / toolchain["arch"] / "boot" / "zImage",
        ]
        
        for img in image_paths:
            if img.exists():
                self.project.output_files.append(str(img))
                await self.log(f"Kernel image created: {img}")
                return True
        
        await self.log("Kernel compilation completed but no image found", "warning")
        return False
    
    async def generate_device_tree(self, device_info: DeviceInfo) -> str:
        """Generate a basic device tree for the device"""
        await self.log(f"Generating device tree for {device_info.codename}...")
        
        dts_content = f'''/*
 * Device Tree for {device_info.model} ({device_info.codename})
 * Auto-generated by Linux Device Forge
 * 
 * Manufacturer: {device_info.manufacturer}
 * Platform: {device_info.platform}
 * SoC: {device_info.soc or 'Unknown'}
 */

/dts-v1/;

/ {{
    model = "{device_info.model}";
    compatible = "{device_info.manufacturer},{device_info.codename}", "{device_info.platform}";
    
    #address-cells = <2>;
    #size-cells = <2>;
    
    chosen {{
        bootargs = "console=ttyMSM0,115200n8 androidboot.hardware={device_info.hardware or device_info.codename}";
        stdout-path = "serial0:115200n8";
    }};
    
    memory@80000000 {{
        device_type = "memory";
        reg = <0x0 0x80000000 0x0 0x80000000>;
    }};
    
    reserved-memory {{
        #address-cells = <2>;
        #size-cells = <2>;
        ranges;
        
        /* Reserve memory for various firmware */
    }};
    
    /* SoC-specific nodes would go here */
    soc {{
        #address-cells = <1>;
        #size-cells = <1>;
        compatible = "simple-bus";
        ranges;
        
        /* UART */
        serial@0 {{
            compatible = "qcom,msm-uartdm";
            status = "okay";
        }};
    }};
}};
'''
        
        dts_path = self.work_dir / f"{device_info.codename}.dts"
        async with aiofiles.open(dts_path, 'w') as f:
            await f.write(dts_content)
        
        await self.log(f"Device tree template saved to {dts_path}")
        return dts_content

# ======================= OS IMAGE BUILDER =======================

class OSImageBuilder:
    def __init__(self, project: OSImageProject):
        self.project = project
        self.work_dir = WORK_DIR / "images" / project.id
        self.work_dir.mkdir(parents=True, exist_ok=True)
    
    async def log(self, message: str, level: str = "info"):
        await manager.send_message(self.project.id, {"type": "log", "level": level, "message": message})
        logger.info(f"[{self.project.id}] {message}")
    
    async def download_rootfs(self, url: str) -> str:
        """Download rootfs from URL"""
        await self.log(f"Downloading rootfs from {url}")
        
        filename = url.split('/')[-1]
        output_path = self.work_dir / filename
        
        cmd = f"wget -q --show-progress -O {output_path} '{url}'"
        stdout, stderr, code = await run_command(cmd, timeout=1800)
        
        if code != 0:
            await self.log(f"Download failed: {stderr}", "error")
            return None
        
        return str(output_path)
    
    async def extract_rootfs(self, archive_path: str) -> str:
        """Extract rootfs archive"""
        await self.log(f"Extracting rootfs...")
        
        rootfs_dir = self.work_dir / "rootfs"
        rootfs_dir.mkdir(exist_ok=True)
        
        archive = Path(archive_path)
        
        if archive.suffix in ['.gz', '.xz', '.bz2'] and '.tar' in archive.name:
            cmd = f"tar -xf {archive_path} -C {rootfs_dir}"
        elif archive.suffix == '.zip':
            cmd = f"unzip -q {archive_path} -d {rootfs_dir}"
        else:
            cmd = f"tar -xf {archive_path} -C {rootfs_dir}"
        
        stdout, stderr, code = await run_command(cmd, timeout=600)
        
        if code != 0:
            await self.log(f"Extraction failed: {stderr}", "error")
            return None
        
        return str(rootfs_dir)
    
    async def create_rootfs_debootstrap(self, distro: str, version: str, arch: str = "arm64") -> str:
        """Create rootfs using debootstrap (Debian/Ubuntu)"""
        await self.log(f"Creating {distro} {version} rootfs with debootstrap...")
        
        rootfs_dir = self.work_dir / "rootfs"
        rootfs_dir.mkdir(exist_ok=True)
        
        # Map architecture
        arch_map = {"arm64": "arm64", "arm": "armhf", "x86_64": "amd64", "x86": "i386"}
        deb_arch = arch_map.get(arch, "arm64")
        
        # Determine mirror and suite
        if distro == "ubuntu":
            mirror = "http://ports.ubuntu.com/ubuntu-ports" if arch in ["arm64", "arm"] else "http://archive.ubuntu.com/ubuntu"
            suite = version  # e.g., "jammy", "noble"
        else:  # debian
            mirror = "http://deb.debian.org/debian"
            suite = version  # e.g., "bookworm", "bullseye"
        
        cmd = f"debootstrap --arch={deb_arch} --foreign {suite} {rootfs_dir} {mirror}"
        
        stdout, stderr, code = await run_command(cmd, timeout=1800)
        if code != 0:
            await self.log(f"Debootstrap failed: {stderr}", "error")
            return None
        
        return str(rootfs_dir)
    
    async def customize_rootfs(self, rootfs_dir: str) -> bool:
        """Customize rootfs for mobile device"""
        await self.log("Customizing rootfs for mobile device...")
        
        rootfs = Path(rootfs_dir)
        
        # Create essential directories
        for dir_name in ["proc", "sys", "dev", "tmp", "run", "var/log"]:
            (rootfs / dir_name).mkdir(parents=True, exist_ok=True)
        
        # Create basic fstab
        fstab_content = """# /etc/fstab - Auto-generated by Linux Device Forge
proc            /proc           proc    defaults        0       0
sysfs           /sys            sysfs   defaults        0       0
devtmpfs        /dev            devtmpfs defaults       0       0
tmpfs           /tmp            tmpfs   defaults        0       0
tmpfs           /run            tmpfs   defaults        0       0
"""
        async with aiofiles.open(rootfs / "etc" / "fstab", 'w') as f:
            await f.write(fstab_content)
        
        # Create hostname
        async with aiofiles.open(rootfs / "etc" / "hostname", 'w') as f:
            await f.write(f"{self.project.device_codename}\n")
        
        # Create hosts file
        hosts_content = f"""127.0.0.1   localhost
127.0.1.1   {self.project.device_codename}
::1         localhost ip6-localhost ip6-loopback
"""
        async with aiofiles.open(rootfs / "etc" / "hosts", 'w') as f:
            await f.write(hosts_content)
        
        await self.log("Rootfs customization complete")
        return True
    
    async def create_initramfs(self, rootfs_dir: str, kernel_image: str = None) -> str:
        """Create initramfs for boot"""
        await self.log("Creating initramfs...")
        
        initramfs_dir = self.work_dir / "initramfs"
        initramfs_dir.mkdir(exist_ok=True)
        
        # Create basic initramfs structure
        for d in ["bin", "sbin", "etc", "proc", "sys", "dev", "newroot", "lib", "lib64"]:
            (initramfs_dir / d).mkdir(exist_ok=True)
        
        # Create init script
        init_script = '''#!/bin/sh
# Minimal init for Linux Device Forge

mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev

# Find root partition
ROOT_DEV="/dev/mmcblk0p2"

# Try common root locations
for dev in /dev/mmcblk0p2 /dev/sda2 /dev/disk/by-label/rootfs; do
    if [ -b "$dev" ]; then
        ROOT_DEV="$dev"
        break
    fi
done

echo "Mounting root from $ROOT_DEV"
mount -o ro "$ROOT_DEV" /newroot

# Switch to real root
exec switch_root /newroot /sbin/init
'''
        
        init_path = initramfs_dir / "init"
        async with aiofiles.open(init_path, 'w') as f:
            await f.write(init_script)
        os.chmod(init_path, 0o755)
        
        # Copy busybox if available
        if check_tool_available("busybox"):
            shutil.copy(shutil.which("busybox"), initramfs_dir / "bin" / "busybox")
            # Create symlinks
            for cmd in ["sh", "mount", "umount", "switch_root", "cat", "echo", "ls"]:
                (initramfs_dir / "bin" / cmd).symlink_to("busybox")
        
        # Create cpio archive
        initramfs_path = self.work_dir / "initramfs.cpio.gz"
        cmd = f"cd {initramfs_dir} && find . | cpio -o -H newc | gzip > {initramfs_path}"
        stdout, stderr, code = await run_command(cmd)
        
        if code != 0:
            await self.log(f"Initramfs creation failed: {stderr}", "error")
            return None
        
        await self.log(f"Initramfs created: {initramfs_path}")
        return str(initramfs_path)
    
    async def create_boot_image(self, kernel_image: str, initramfs: str, dtb: str = None) -> str:
        """Create Android-compatible boot image"""
        await self.log("Creating boot image...")
        
        boot_img = self.work_dir / "boot.img"
        
        # Use mkbootimg if available
        if check_tool_available("mkbootimg"):
            cmd = f"mkbootimg --kernel {kernel_image} --ramdisk {initramfs}"
            if dtb:
                cmd += f" --dtb {dtb}"
            cmd += f" --output {boot_img}"
            cmd += ' --cmdline "console=ttyMSM0,115200n8 root=/dev/mmcblk0p2 rootwait"'
            
            stdout, stderr, code = await run_command(cmd)
            if code == 0:
                await self.log(f"Boot image created: {boot_img}")
                self.project.boot_image = str(boot_img)
                return str(boot_img)
        
        # Fallback: use abootimg
        if check_tool_available("abootimg"):
            cmd = f"abootimg --create {boot_img} -k {kernel_image} -r {initramfs}"
            stdout, stderr, code = await run_command(cmd)
            if code == 0:
                return str(boot_img)
        
        await self.log("No boot image tool available (mkbootimg/abootimg)", "error")
        return None
    
    async def build(self) -> bool:
        """Execute full OS image build"""
        try:
            # Get rootfs
            if self.project.custom_upload and self.project.rootfs_source:
                rootfs_archive = self.project.rootfs_source
                rootfs_dir = await self.extract_rootfs(rootfs_archive)
            elif self.project.distro in ["ubuntu", "debian"]:
                rootfs_dir = await self.create_rootfs_debootstrap(
                    self.project.distro,
                    self.project.distro_version or "bookworm",
                    "arm64"
                )
            else:
                # Try to download pre-built rootfs
                distro_info = MOBILE_DISTROS.get(self.project.distro) or DESKTOP_DISTROS.get(self.project.distro)
                if distro_info and distro_info.get("rootfs_url"):
                    rootfs_archive = await self.download_rootfs(distro_info["rootfs_url"])
                    if rootfs_archive:
                        rootfs_dir = await self.extract_rootfs(rootfs_archive)
                    else:
                        return False
                else:
                    await self.log(f"No rootfs source for {self.project.distro}", "error")
                    return False
            
            if not rootfs_dir:
                return False
            
            # Customize rootfs
            await self.customize_rootfs(rootfs_dir)
            
            # Create initramfs
            initramfs = await self.create_initramfs(rootfs_dir)
            
            # Create boot image if we have a kernel
            if self.project.kernel_project_id:
                kernel_project = await db.kernel_projects.find_one({"id": self.project.kernel_project_id})
                if kernel_project and kernel_project.get("output_files"):
                    kernel_image = kernel_project["output_files"][0]
                    await self.create_boot_image(kernel_image, initramfs)
            
            self.project.build_status = "completed"
            self.project.output_image = rootfs_dir
            
            await db.os_image_projects.update_one(
                {"id": self.project.id},
                {"$set": {
                    "build_status": "completed",
                    "output_image": rootfs_dir,
                    "boot_image": self.project.boot_image
                }}
            )
            
            await self.log("OS image build completed!")
            return True
            
        except Exception as e:
            await self.log(f"Build failed: {str(e)}", "error")
            return False

# ======================= API ROUTES =======================

@api_router.get("/")
async def root():
    return {
        "message": "Linux Device Forge API",
        "version": "2.0.0",
        "tools": ["Kernel Forge", "OS Image Builder", "Halium Builder"]
    }

@api_router.get("/health")
async def health_check():
    tools = {
        "adb": check_tool_available("adb"),
        "fastboot": check_tool_available("fastboot"),
        "git": check_tool_available("git"),
        "make": check_tool_available("make"),
        "dtc": check_tool_available("dtc"),
        "mkbootimg": check_tool_available("mkbootimg"),
        "debootstrap": check_tool_available("debootstrap"),
        "gcc-aarch64": check_tool_available("aarch64-linux-gnu-gcc"),
        "gcc-arm": check_tool_available("arm-linux-gnueabihf-gcc"),
    }
    return {
        "status": "healthy",
        "tools": tools,
        "kernel_forge_ready": all([tools["git"], tools["make"]]),
        "os_builder_ready": tools.get("debootstrap", False) or True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ======================= DEVICE ROUTES =======================

@api_router.get("/devices")
async def list_devices():
    stdout, stderr, code = await run_command("adb devices")
    devices = parse_adb_devices(stdout) if code == 0 else []
    return {"devices": devices, "adb_available": code == 0}

@api_router.get("/devices/{serial}/info")
async def get_device_info_route(serial: str):
    device_info = await get_full_device_info(serial)
    doc = device_info.model_dump()
    doc['detected_at'] = doc['detected_at'].isoformat()
    await db.devices.update_one({"serial": serial}, {"$set": doc}, upsert=True)
    return device_info

@api_router.get("/devices/{serial}/partitions")
async def get_device_partitions(serial: str):
    device_info = await get_full_device_info(serial)
    
    important = ["boot", "recovery", "system", "vendor", "dtbo", "vbmeta", "userdata", "super", "kernel"]
    partitions = device_info.partitions or {}
    
    categorized = {
        "boot": {k: v for k, v in partitions.items() if k in ["boot", "recovery", "dtbo", "vbmeta", "kernel"]},
        "system": {k: v for k, v in partitions.items() if k in ["system", "vendor", "product", "odm", "super"]},
        "data": {k: v for k, v in partitions.items() if k in ["userdata", "metadata", "cache"]},
        "other": {k: v for k, v in partitions.items() if k not in important}
    }
    
    return {"partitions": partitions, "categorized": categorized, "total": len(partitions)}

@api_router.post("/devices/{serial}/extract-dtb")
async def extract_device_tree_blob(serial: str):
    """Extract DTB/DTBO from device"""
    results = {"serial": serial, "extracted": [], "errors": []}
    
    extract_dir = WORK_DIR / "dtb" / serial
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    # Try to pull DTBO partition
    cmds = [
        (f"adb -s {serial} shell su -c 'cat /dev/block/by-name/dtbo' > {extract_dir}/dtbo.img", "dtbo.img"),
        (f"adb -s {serial} pull /dev/block/by-name/dtbo {extract_dir}/dtbo.img 2>/dev/null", "dtbo.img"),
    ]
    
    for cmd, filename in cmds:
        stdout, stderr, code = await run_command(cmd, timeout=60)
        if code == 0 and (extract_dir / filename).exists() and (extract_dir / filename).stat().st_size > 0:
            results["extracted"].append(str(extract_dir / filename))
            break
    
    # Try to pull boot image for DTB
    boot_cmds = [
        f"adb -s {serial} shell su -c 'cat /dev/block/by-name/boot' > {extract_dir}/boot.img",
        f"adb -s {serial} pull /dev/block/by-name/boot {extract_dir}/boot.img 2>/dev/null",
    ]
    
    for cmd in boot_cmds:
        stdout, stderr, code = await run_command(cmd, timeout=120)
        if code == 0 and (extract_dir / "boot.img").exists():
            results["extracted"].append(str(extract_dir / "boot.img"))
            
            # Try to extract DTB from boot image
            if check_tool_available("unpackbootimg"):
                unpack_dir = extract_dir / "boot_unpacked"
                unpack_dir.mkdir(exist_ok=True)
                await run_command(f"unpackbootimg -i {extract_dir}/boot.img -o {unpack_dir}")
                dtb_files = list(unpack_dir.glob("*.dtb"))
                results["extracted"].extend([str(f) for f in dtb_files])
            break
    
    # Decompile DTB to DTS if dtc available
    if check_tool_available("dtc"):
        for dtb_file in [f for f in results["extracted"] if f.endswith('.dtb')]:
            dts_file = dtb_file.replace('.dtb', '.dts')
            stdout, stderr, code = await run_command(f"dtc -I dtb -O dts -o {dts_file} {dtb_file}")
            if code == 0:
                results["extracted"].append(dts_file)
    
    return results

@api_router.get("/devices/{serial}/kernel-info")
async def get_device_kernel_info(serial: str):
    """Get detailed kernel info from device"""
    version, _, _ = await run_command(f"adb -s {serial} shell cat /proc/version")
    cmdline, _, _ = await run_command(f"adb -s {serial} shell cat /proc/cmdline")
    config, _, _ = await run_command(f"adb -s {serial} shell zcat /proc/config.gz 2>/dev/null")
    
    version_parsed = parse_kernel_version(version)
    
    # Analyze config if available
    config_analysis = []
    if config:
        for req in KERNEL_CONFIG_LINUX_GENERIC:
            enabled = f'{req["config"]}=y' in config or f'{req["config"]}=m' in config
            config_analysis.append({
                "config": req["config"],
                "category": req["category"],
                "required": req["required"],
                "enabled": enabled,
                "status": "ok" if enabled or not req["required"] else "missing"
            })
    
    upstream_target = None
    if version_parsed.get("major", 0) < 6:
        upstream_target = "6.6"  # Recommend LTS
    
    return {
        "version": version.strip(),
        "version_parsed": version_parsed,
        "cmdline": cmdline.strip(),
        "config_available": bool(config),
        "config_analysis": config_analysis,
        "linux_ready": all(c["status"] == "ok" for c in config_analysis if c["required"]),
        "upstream_recommended": upstream_target,
        "mainline_kernels": MAINLINE_KERNELS
    }

# ======================= KERNEL FORGE ROUTES =======================

@api_router.post("/kernel/projects")
async def create_kernel_project(request: BuildRequest):
    """Create a new kernel project"""
    project = KernelProject(
        name=f"kernel-{request.device_codename}",
        device_codename=request.device_codename,
        source_url=request.kernel_source,
        architecture=request.architecture,
        target_version=request.target_kernel_version,
        defconfig=request.defconfig
    )
    
    doc = project.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.kernel_projects.insert_one(doc)
    
    return project

@api_router.get("/kernel/projects")
async def list_kernel_projects():
    projects = await db.kernel_projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"projects": projects}

@api_router.get("/kernel/projects/{project_id}")
async def get_kernel_project(project_id: str):
    project = await db.kernel_projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@api_router.post("/kernel/projects/{project_id}/clone")
async def clone_kernel_source(project_id: str, url: str, branch: str = None):
    """Clone kernel source for a project"""
    project_doc = await db.kernel_projects.find_one({"id": project_id})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = KernelProject(**project_doc)
    forge = KernelForge(project)
    
    success = await forge.clone_kernel_source(url, branch)
    
    if success:
        await db.kernel_projects.update_one(
            {"id": project_id},
            {"$set": {"source_url": url, "build_dir": project.build_dir}}
        )
    
    return {"success": success, "build_dir": project.build_dir}

@api_router.post("/kernel/projects/{project_id}/analyze")
async def analyze_kernel_config(project_id: str, defconfig: str = None):
    """Analyze kernel configuration"""
    project_doc = await db.kernel_projects.find_one({"id": project_id})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = KernelProject(**project_doc)
    forge = KernelForge(project)
    
    analysis = await forge.analyze_kernel_config(defconfig)
    
    await db.kernel_projects.update_one(
        {"id": project_id},
        {"$set": {"config_analysis": analysis}}
    )
    
    return analysis

@api_router.post("/kernel/projects/{project_id}/fix-config")
async def apply_kernel_config_fixes(project_id: str):
    """Apply missing kernel config options"""
    project_doc = await db.kernel_projects.find_one({"id": project_id})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = KernelProject(**project_doc)
    forge = KernelForge(project)
    
    success = await forge.apply_config_fixes()
    
    # Re-analyze after fixes
    if success:
        analysis = await forge.analyze_kernel_config()
        await db.kernel_projects.update_one(
            {"id": project_id},
            {"$set": {"config_analysis": analysis}}
        )
        return {"success": True, "new_analysis": analysis}
    
    return {"success": False}

@api_router.post("/kernel/projects/{project_id}/analyze-upstream")
async def analyze_upstream(project_id: str, target_version: str):
    """Analyze compatibility for upstreaming kernel"""
    project_doc = await db.kernel_projects.find_one({"id": project_id})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = KernelProject(**project_doc)
    forge = KernelForge(project)
    
    analysis = await forge.analyze_upstream_compatibility(target_version)
    return analysis

@api_router.post("/kernel/projects/{project_id}/compile")
async def compile_kernel(project_id: str, background_tasks: BackgroundTasks):
    """Start kernel compilation"""
    project_doc = await db.kernel_projects.find_one({"id": project_id})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = KernelProject(**project_doc)
    forge = KernelForge(project)
    
    await db.kernel_projects.update_one(
        {"id": project_id},
        {"$set": {"build_status": "compiling"}}
    )
    
    background_tasks.add_task(forge.compile_kernel)
    
    return {"status": "compilation_started", "project_id": project_id}

@api_router.post("/kernel/projects/{project_id}/generate-dt")
async def generate_device_tree(project_id: str, serial: str):
    """Generate device tree for device"""
    project_doc = await db.kernel_projects.find_one({"id": project_id})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    
    device_info = await get_full_device_info(serial)
    
    project = KernelProject(**project_doc)
    forge = KernelForge(project)
    
    dts_content = await forge.generate_device_tree(device_info)
    
    return {"dts_content": dts_content, "device_info": device_info}

@api_router.get("/kernel/mainline-versions")
async def get_mainline_kernel_versions():
    """Get available mainline kernel versions"""
    return {
        "versions": MAINLINE_KERNELS,
        "recommended_lts": "6.6",
        "latest_mainline": "6.8"
    }

@api_router.get("/kernel/config-requirements")
async def get_kernel_config_requirements():
    """Get kernel config requirements for Linux boot"""
    by_category = {}
    for req in KERNEL_CONFIG_LINUX_GENERIC:
        cat = req["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(req)
    
    return {
        "requirements": KERNEL_CONFIG_LINUX_GENERIC,
        "by_category": by_category,
        "total": len(KERNEL_CONFIG_LINUX_GENERIC),
        "required_count": len([r for r in KERNEL_CONFIG_LINUX_GENERIC if r["required"]])
    }

# ======================= OS IMAGE BUILDER ROUTES =======================

@api_router.get("/os/distros")
async def get_available_distros():
    """Get available Linux distributions"""
    return {
        "mobile": MOBILE_DISTROS,
        "desktop": DESKTOP_DISTROS,
        "total_mobile": len(MOBILE_DISTROS),
        "total_desktop": len(DESKTOP_DISTROS)
    }

@api_router.post("/os/projects")
async def create_os_image_project(request: OSBuildRequest):
    """Create a new OS image project"""
    distro_info = MOBILE_DISTROS.get(request.distro) or DESKTOP_DISTROS.get(request.distro)
    
    project = OSImageProject(
        name=f"{request.distro}-{request.device_codename}",
        device_codename=request.device_codename,
        distro=request.distro,
        distro_version=request.distro_version,
        distro_type="mobile" if request.distro in MOBILE_DISTROS else "desktop",
        kernel_project_id=request.kernel_project_id,
        init_system=distro_info.get("init_system", "systemd") if distro_info else "systemd",
        desktop_environment=request.desktop_environment,
        packages_to_add=request.additional_packages
    )
    
    doc = project.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.os_image_projects.insert_one(doc)
    
    return project

@api_router.get("/os/projects")
async def list_os_image_projects():
    projects = await db.os_image_projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"projects": projects}

@api_router.get("/os/projects/{project_id}")
async def get_os_image_project(project_id: str):
    project = await db.os_image_projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@api_router.post("/os/projects/{project_id}/build")
async def build_os_image(project_id: str, background_tasks: BackgroundTasks):
    """Start OS image build"""
    project_doc = await db.os_image_projects.find_one({"id": project_id})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = OSImageProject(**project_doc)
    builder = OSImageBuilder(project)
    
    await db.os_image_projects.update_one(
        {"id": project_id},
        {"$set": {"build_status": "building"}}
    )
    
    background_tasks.add_task(builder.build)
    
    return {"status": "build_started", "project_id": project_id}

@api_router.post("/os/projects/{project_id}/upload-rootfs")
async def upload_custom_rootfs(project_id: str, file: UploadFile = File(...)):
    """Upload custom rootfs for OS image project"""
    project_doc = await db.os_image_projects.find_one({"id": project_id})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    
    upload_dir = WORK_DIR / "uploads" / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    await db.os_image_projects.update_one(
        {"id": project_id},
        {"$set": {"rootfs_source": str(file_path), "custom_upload": True}}
    )
    
    return {"uploaded": str(file_path), "size": len(content)}

# ======================= HALIUM BUILDER ROUTES (PRESERVED) =======================

@api_router.get("/halium/versions")
async def get_halium_versions():
    versions = []
    for vid, info in HALIUM_VERSIONS.items():
        versions.append({
            "id": vid,
            "name": vid.replace("-", " ").title(),
            "android_base": f"{info['android']} ({info['lineage']})",
            "status": "latest" if vid == "halium-11.0" else "stable"
        })
    return {"versions": versions}

@api_router.post("/halium/build")
async def start_halium_build(request: HaliumBuildRequest, background_tasks: BackgroundTasks):
    """Start Halium build (preserved from original)"""
    device_info = await get_full_device_info(request.device_serial)
    
    session = {
        "id": str(uuid.uuid4()),
        "device_serial": request.device_serial,
        "device_codename": device_info.device,
        "halium_version": request.halium_version,
        "build_type": request.build_type,
        "build_dir": request.build_dir,
        "status": "pending",
        "progress": 0,
        "logs": [],
        "started_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.halium_builds.insert_one(session)
    
    return session

@api_router.get("/halium/builds")
async def list_halium_builds():
    builds = await db.halium_builds.find({}, {"_id": 0}).sort("started_at", -1).to_list(20)
    return {"builds": builds}

# ======================= TERMINAL & AI ROUTES =======================

@api_router.post("/terminal/execute")
async def execute_command(request: CommandRequest):
    cmd = request.command.strip()
    
    dangerous = ['rm -rf /', 'mkfs', ':(){', '> /dev/sd', 'dd if=']
    for pattern in dangerous:
        if pattern in cmd.lower():
            raise HTTPException(status_code=400, detail="Dangerous command blocked")
    
    stdout, stderr, code = await run_command(cmd, timeout=request.timeout, cwd=request.working_dir)
    
    await db.command_history.insert_one({
        "id": str(uuid.uuid4()),
        "command": cmd,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": code,
        "session_id": request.session_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"command": cmd, "stdout": stdout, "stderr": stderr, "exit_code": code, "success": code == 0}

@api_router.post("/ai/chat")
async def ai_chat(request: AIRequest):
    try:
        contexts = {}
        if request.device_context:
            contexts["Device Context"] = request.device_context
        if request.kernel_context:
            contexts["Kernel Context"] = request.kernel_context
        if request.build_context:
            contexts["Build Context"] = request.build_context
        
        response = await ai_agent.send_message(request.session_id, request.message, contexts)
        commands = ai_agent.extract_commands(response)
        
        # Store messages
        await db.chat_messages.insert_one({
            "session_id": request.session_id,
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        await db.chat_messages.insert_one({
            "session_id": request.session_id,
            "role": "assistant",
            "content": response,
            "extracted_commands": commands,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Auto-execute
        execution_results = []
        if request.auto_execute and commands:
            for cmd in commands:
                stdout, stderr, code = await run_command(cmd, timeout=120)
                execution_results.append({
                    "command": cmd,
                    "stdout": stdout,
                    "stderr": stderr,
                    "success": code == 0
                })
                if code != 0:
                    break
        
        return {
            "response": response,
            "extracted_commands": commands,
            "execution_results": execution_results if request.auto_execute else None
        }
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/ai/history/{session_id}")
async def get_chat_history(session_id: str):
    messages = await db.chat_messages.find({"session_id": session_id}, {"_id": 0}).sort("timestamp", 1).to_list(100)
    return {"messages": messages}

# ======================= WEBSOCKET =======================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "command":
                cmd = data.get("command", "")
                async for line in run_command_stream(cmd, cwd=data.get("cwd")):
                    await websocket.send_json({"type": "output", "line": line})
                await websocket.send_json({"type": "complete"})
            
            elif data.get("type") == "ai_message":
                contexts = {
                    "Device": data.get("device_context"),
                    "Kernel": data.get("kernel_context"),
                    "Build": data.get("build_context")
                }
                response = await ai_agent.send_message(session_id, data.get("message", ""), contexts)
                commands = ai_agent.extract_commands(response)
                await websocket.send_json({
                    "type": "ai_response",
                    "response": response,
                    "commands": commands
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)

# Include router and middleware
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
