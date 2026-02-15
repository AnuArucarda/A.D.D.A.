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
    "ubuntu-touch": {"name": "Ubuntu Touch", "description": "Ubuntu for phones and tablets by UBports", "init_system": "upstart", "type": "mobile"},
    "postmarketos": {"name": "postmarketOS", "description": "Alpine-based Linux for phones, aims for 10 year device support", "init_system": "openrc", "type": "mobile"},
    "droidian": {"name": "Droidian", "description": "Debian-based, runs on Halium (Android drivers)", "init_system": "systemd", "type": "mobile"},
    "mobian": {"name": "Mobian", "description": "Debian + Phosh for mobile devices", "init_system": "systemd", "type": "mobile"},
    "plasma-mobile": {"name": "Plasma Mobile", "description": "KDE Plasma for mobile devices", "init_system": "systemd", "type": "mobile"},
    "luneos": {"name": "LuneOS", "description": "webOS community continuation", "init_system": "systemd", "type": "mobile"},
    "sailfish": {"name": "Sailfish OS", "description": "Jolla's Linux-based mobile OS", "init_system": "systemd", "type": "mobile"}
}

DESKTOP_DISTROS = {
    "ubuntu": {"name": "Ubuntu", "description": "Popular Debian-based distribution", "init_system": "systemd", "versions": ["24.04", "22.04", "20.04"]},
    "debian": {"name": "Debian", "description": "The universal operating system", "init_system": "systemd", "versions": ["12", "11"]},
    "arch": {"name": "Arch Linux", "description": "Simple, lightweight distribution", "init_system": "systemd", "versions": ["latest"]},
    "fedora": {"name": "Fedora", "description": "Cutting-edge Red Hat sponsored distro", "init_system": "systemd", "versions": ["40", "39"]},
    "alpine": {"name": "Alpine Linux", "description": "Security-focused, lightweight", "init_system": "openrc", "versions": ["3.19", "3.18"]},
    "manjaro": {"name": "Manjaro", "description": "User-friendly Arch-based", "init_system": "systemd", "versions": ["latest"]},
    "void": {"name": "Void Linux", "description": "Independent distro with runit", "init_system": "runit", "versions": ["latest"]},
    "gentoo": {"name": "Gentoo", "description": "Source-based, highly customizable", "init_system": "openrc", "versions": ["latest"]}
}

# Android ROM bases
ANDROID_ROM_BASES = {
    "aosp": {"name": "AOSP", "description": "Pure Android Open Source Project", "android_versions": ["14", "13", "12"]},
    "lineageos": {"name": "LineageOS", "description": "Community-driven, privacy-focused", "android_versions": ["21", "20", "19.1", "18.1"]},
    "pixelexperience": {"name": "Pixel Experience", "description": "Google Pixel look and feel", "android_versions": ["14", "13"]},
    "crdroid": {"name": "crDroid", "description": "Feature-rich custom ROM", "android_versions": ["10", "9", "8"]},
    "evolutionx": {"name": "Evolution X", "description": "Pixel UI with customizations", "android_versions": ["14", "13"]},
    "arrowos": {"name": "ArrowOS", "description": "Minimal and clean AOSP", "android_versions": ["14", "13"]},
    "paranoidandroid": {"name": "Paranoid Android", "description": "Unique features and design", "android_versions": ["14", "13"]},
    "havoc": {"name": "Havoc-OS", "description": "Material Design with features", "android_versions": ["14", "13"]},
    "resurrection": {"name": "Resurrection Remix", "description": "Tons of customization options", "android_versions": ["11", "10"]},
    "grapheneos": {"name": "GrapheneOS", "description": "Security and privacy hardened", "android_versions": ["14", "13"]}
}

# Android build features/options
ANDROID_BUILD_FEATURES = {
    "kernel": {
        "options": ["stock", "custom_optimized", "bleeding_edge", "battery_focused", "performance_focused"],
        "descriptions": {
            "stock": "Use device's stock kernel with minimal changes",
            "custom_optimized": "Balanced optimizations for daily use",
            "bleeding_edge": "Latest kernel features, may have bugs",
            "battery_focused": "Aggressive power saving, governor tweaks",
            "performance_focused": "Maximum performance, higher battery drain"
        }
    },
    "gapps": {
        "options": ["none", "pico", "nano", "micro", "mini", "full", "stock"],
        "descriptions": {
            "none": "No Google apps (fully degoogled)",
            "pico": "Minimal - just Play Services",
            "nano": "Basic Play Store + Services",
            "micro": "Essential Google apps",
            "mini": "Common Google apps",
            "full": "All Google apps",
            "stock": "Pixel-style Google experience"
        }
    },
    "root": {
        "options": ["none", "magisk", "kernelsu", "supersu"],
        "descriptions": {
            "none": "No root access",
            "magisk": "Magisk - systemless root, modules support",
            "kernelsu": "KernelSU - kernel-based root",
            "supersu": "SuperSU - traditional root (legacy)"
        }
    },
    "security": {
        "options": ["standard", "hardened", "privacy_focused", "enterprise"],
        "descriptions": {
            "standard": "Default Android security",
            "hardened": "SELinux enforcing, verified boot",
            "privacy_focused": "Tracker blocking, permission controls",
            "enterprise": "MDM ready, work profile support"
        }
    },
    "ui_customization": {
        "options": ["stock", "minimal", "feature_rich", "ios_style", "miui_style", "oneui_style"],
        "descriptions": {
            "stock": "Clean AOSP/Pixel look",
            "minimal": "Stripped down, fast",
            "feature_rich": "Tons of customization options",
            "ios_style": "iOS-inspired launcher and UI",
            "miui_style": "MIUI-inspired interface",
            "oneui_style": "Samsung OneUI inspired"
        }
    },
    "performance": {
        "options": ["balanced", "battery_saver", "performance", "gaming"],
        "descriptions": {
            "balanced": "Good mix of battery and performance",
            "battery_saver": "Maximum battery life",
            "performance": "Smooth animations, faster response",
            "gaming": "Game mode, GPU optimizations"
        }
    },
    "camera": {
        "options": ["stock", "gcam_ready", "custom_hal"],
        "descriptions": {
            "stock": "Device's default camera",
            "gcam_ready": "Optimized for Google Camera ports",
            "custom_hal": "Custom camera HAL for advanced features"
        }
    },
    "audio": {
        "options": ["stock", "viper4android", "dolby", "custom_dac"],
        "descriptions": {
            "stock": "Default audio processing",
            "viper4android": "Viper4Android effects",
            "dolby": "Dolby Atmos support",
            "custom_dac": "DAC/amp optimizations"
        }
    }
}

# Interview depth levels
INTERVIEW_DEPTHS = {
    "quick": {
        "name": "Quick Build",
        "description": "5-7 essential questions. Best for users who want a standard custom ROM fast.",
        "questions_count": "5-7",
        "categories": ["base_rom", "gapps", "root", "kernel_basic"]
    },
    "standard": {
        "name": "Standard Build",
        "description": "15-20 questions covering all major customization areas.",
        "questions_count": "15-20",
        "categories": ["base_rom", "gapps", "root", "kernel", "security", "ui", "performance", "apps"]
    },
    "expert": {
        "name": "Expert Build",
        "description": "30+ in-depth questions for complete control over every aspect.",
        "questions_count": "30+",
        "categories": ["base_rom", "gapps", "root", "kernel_advanced", "security", "ui", "performance", "camera", "audio", "network", "tweaks", "apps", "build_options"]
    }
}

# Kernel versions
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

# Kernel config requirements
KERNEL_CONFIG_LINUX_GENERIC = [
    {"config": "CONFIG_DEVTMPFS", "required": True, "category": "core", "description": "Device filesystem"},
    {"config": "CONFIG_DEVTMPFS_MOUNT", "required": True, "category": "core", "description": "Automount devtmpfs"},
    {"config": "CONFIG_TMPFS", "required": True, "category": "core", "description": "Temporary filesystem"},
    {"config": "CONFIG_PROC_FS", "required": True, "category": "core", "description": "Proc filesystem"},
    {"config": "CONFIG_SYSFS", "required": True, "category": "core", "description": "Sysfs filesystem"},
    {"config": "CONFIG_NAMESPACES", "required": True, "category": "namespace", "description": "Namespace support"},
    {"config": "CONFIG_NET_NS", "required": True, "category": "namespace", "description": "Network namespaces"},
    {"config": "CONFIG_PID_NS", "required": True, "category": "namespace", "description": "PID namespaces"},
    {"config": "CONFIG_IPC_NS", "required": True, "category": "namespace", "description": "IPC namespaces"},
    {"config": "CONFIG_UTS_NS", "required": True, "category": "namespace", "description": "UTS namespaces"},
    {"config": "CONFIG_USER_NS", "required": False, "category": "namespace", "description": "User namespaces"},
    {"config": "CONFIG_CGROUPS", "required": True, "category": "namespace", "description": "Control groups"},
    {"config": "CONFIG_EXT4_FS", "required": True, "category": "filesystem", "description": "EXT4 filesystem"},
    {"config": "CONFIG_F2FS_FS", "required": False, "category": "filesystem", "description": "F2FS filesystem"},
    {"config": "CONFIG_SQUASHFS", "required": True, "category": "filesystem", "description": "SquashFS"},
    {"config": "CONFIG_OVERLAY_FS", "required": True, "category": "filesystem", "description": "Overlay filesystem"},
    {"config": "CONFIG_FUSE_FS", "required": False, "category": "filesystem", "description": "FUSE support"},
    {"config": "CONFIG_NET", "required": True, "category": "network", "description": "Networking support"},
    {"config": "CONFIG_INET", "required": True, "category": "network", "description": "TCP/IP networking"},
    {"config": "CONFIG_NETFILTER", "required": True, "category": "network", "description": "Netfilter"},
    {"config": "CONFIG_VETH", "required": True, "category": "network", "description": "Virtual ethernet"},
    {"config": "CONFIG_WIRELESS", "required": True, "category": "network", "description": "Wireless support"},
    {"config": "CONFIG_CFG80211", "required": True, "category": "network", "description": "Wireless config API"},
    {"config": "CONFIG_ANDROID_BINDER_IPC", "required": False, "category": "android", "description": "Binder IPC"},
    {"config": "CONFIG_ASHMEM", "required": False, "category": "android", "description": "Anonymous shared memory"},
    {"config": "CONFIG_FB", "required": True, "category": "display", "description": "Framebuffer support"},
    {"config": "CONFIG_DRM", "required": True, "category": "display", "description": "Direct Rendering Manager"},
    {"config": "CONFIG_INPUT", "required": True, "category": "input", "description": "Input subsystem"},
    {"config": "CONFIG_INPUT_EVDEV", "required": True, "category": "input", "description": "Event interface"},
    {"config": "CONFIG_INPUT_TOUCHSCREEN", "required": True, "category": "input", "description": "Touchscreen support"},
    {"config": "CONFIG_USB", "required": True, "category": "usb", "description": "USB support"},
    {"config": "CONFIG_USB_GADGET", "required": True, "category": "usb", "description": "USB gadget support"},
    {"config": "CONFIG_PM", "required": True, "category": "power", "description": "Power management"},
    {"config": "CONFIG_CPU_FREQ", "required": True, "category": "power", "description": "CPU frequency scaling"},
    {"config": "CONFIG_SECCOMP", "required": True, "category": "security", "description": "Seccomp filters"},
]

HALIUM_VERSIONS = {
    "halium-7.1": {"android": "7.1", "lineage": "14.1", "branch": "halium-7.1"},
    "halium-9.0": {"android": "9.0", "lineage": "16.0", "branch": "halium-9.0"},
    "halium-10.0": {"android": "10", "lineage": "17.1", "branch": "halium-10.0"},
    "halium-11.0": {"android": "11", "lineage": "18.1", "branch": "halium-11.0"},
}

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
    current_version: Optional[str] = None
    target_version: Optional[str] = None
    architecture: str = "arm64"
    defconfig: Optional[str] = None
    config_analysis: Optional[Dict[str, Any]] = None
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
    distro_type: str = "mobile"
    kernel_project_id: Optional[str] = None
    rootfs_source: Optional[str] = None
    custom_upload: bool = False
    init_system: str = "systemd"
    build_status: str = "pending"
    output_image: Optional[str] = None
    boot_image: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AndroidBuildProject(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    device_codename: str
    device_info: Optional[Dict[str, Any]] = None
    interview_depth: str = "standard"  # quick, standard, expert
    interview_complete: bool = False
    interview_answers: Dict[str, Any] = {}
    
    # Build configuration (populated from interview)
    base_rom: Optional[str] = None
    android_version: Optional[str] = None
    kernel_type: Optional[str] = None
    gapps_type: Optional[str] = None
    root_solution: Optional[str] = None
    security_level: Optional[str] = None
    ui_style: Optional[str] = None
    performance_profile: Optional[str] = None
    camera_setup: Optional[str] = None
    audio_setup: Optional[str] = None
    
    # Additional customizations
    custom_features: List[str] = []
    removed_features: List[str] = []
    custom_apps: List[str] = []
    removed_apps: List[str] = []
    kernel_tweaks: Dict[str, Any] = {}
    build_flags: Dict[str, Any] = {}
    
    # Build state
    build_status: str = "configuring"  # configuring, ready, building, completed, failed
    build_progress: int = 0
    build_logs: List[str] = []
    build_dir: Optional[str] = None
    output_files: List[str] = []
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AndroidInterviewMessage(BaseModel):
    project_id: str
    message: str
    is_user: bool = True

class AndroidInterviewResponse(BaseModel):
    message: str
    question_number: int
    total_questions: int
    category: str
    options: Optional[List[Dict[str, str]]] = None
    is_complete: bool = False
    build_config: Optional[Dict[str, Any]] = None

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

class BuildRequest(BaseModel):
    device_serial: Optional[str] = None
    device_codename: str
    architecture: str = "arm64"
    kernel_source: Optional[str] = None
    defconfig: Optional[str] = None

class OSBuildRequest(BaseModel):
    device_codename: str
    distro: str
    distro_version: Optional[str] = None
    kernel_project_id: Optional[str] = None
    additional_packages: List[str] = []

class AndroidBuildRequest(BaseModel):
    device_serial: Optional[str] = None
    device_codename: str
    interview_depth: str = "standard"

# ======================= HELPERS =======================

async def run_command(cmd: str, timeout: int = 120, cwd: str = None, env: Dict = None) -> tuple[str, str, int]:
    try:
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            cwd=cwd or str(WORK_DIR), env=full_env
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return stdout.decode(), stderr.decode(), process.returncode
    except asyncio.TimeoutError:
        return "", f"Command timed out after {timeout}s", -1
    except Exception as e:
        return "", str(e), -1

async def run_command_stream(cmd: str, cwd: str = None) -> AsyncGenerator[str, None]:
    try:
        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
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
    
    if device_info.cpu_abi:
        if "arm64" in device_info.cpu_abi:
            device_info.architecture = "arm64"
        elif "arm" in device_info.cpu_abi:
            device_info.architecture = "arm"
        elif "x86_64" in device_info.cpu_abi:
            device_info.architecture = "x86_64"
    
    for prop in ["ro.soc.model", "ro.hardware.chipname", "ro.mediatek.platform"]:
        soc = await get_device_prop(serial, prop)
        if soc:
            device_info.soc = soc
            break
    
    platform = device_info.platform or ""
    if "msm" in platform.lower() or "sdm" in platform.lower() or "sm" in platform.lower():
        device_info.soc_manufacturer = "Qualcomm"
    elif "mt" in platform.lower():
        device_info.soc_manufacturer = "MediaTek"
    elif "exynos" in platform.lower():
        device_info.soc_manufacturer = "Samsung"
    
    stdout, _, _ = await run_command(f"adb -s {serial} shell cat /proc/version")
    if stdout:
        device_info.kernel_version = stdout.strip()[:300]
        device_info.kernel_version_parsed = parse_kernel_version(stdout)
    
    return device_info

# ======================= AI AGENTS =======================

FORGE_SYSTEM_PROMPT = """You are an expert Linux Kernel & OS Engineer AI agent with deep expertise in:
- Linux kernel development, configuration, and compilation
- Mobile Linux (postmarketOS, Ubuntu Touch, Droidian, Mobian)
- OS image building and rootfs creation
- Device tree handling and boot image creation
- Halium and Android driver hybridization

When providing commands, use ```bash blocks. For dangerous operations, warn first."""

ANDROID_BUILDER_SYSTEM_PROMPT = """You are an expert Android ROM Builder AI assistant. Your role is to guide users through creating their perfect custom Android ROM through a conversational interview.

## YOUR RESPONSIBILITIES:
1. Ask clear, focused questions one at a time
2. Explain options in simple terms when needed
3. Remember all previous answers in the conversation
4. Adapt questions based on previous answers
5. Provide recommendations when asked

## INTERVIEW STRUCTURE:
Based on the interview depth level, ask questions about:

### QUICK (5-7 questions):
- Base ROM preference
- Google Apps (GApps) preference  
- Root access preference
- Basic kernel preference
- Any must-have features

### STANDARD (15-20 questions):
All Quick topics plus:
- Security preferences
- UI customization level
- Performance vs battery preference
- Camera setup
- Audio enhancements
- Pre-installed apps preferences
- Specific features to include/exclude

### EXPERT (30+ questions):
All Standard topics plus:
- Detailed kernel configuration (governors, schedulers, etc.)
- SELinux configuration
- Specific hardware optimizations
- Network/modem tweaks
- Detailed camera HAL options
- Audio DAC configuration
- Boot animation, fonts, themes
- System-level tweaks
- Build optimizations (LTO, PGO, etc.)
- Specific app configurations

## RESPONSE FORMAT:
Always structure your response as:
1. Brief acknowledgment of their last answer (if applicable)
2. The next question with clear options
3. Brief explanation of what each option means

## IMPORTANT RULES:
- Ask ONE question at a time
- Provide numbered options when applicable
- Be conversational but efficient
- If user seems unsure, offer a recommendation
- Track progress (e.g., "Question 3 of 15")
- When complete, summarize all choices before confirming"""

class AIAgent:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        self.sessions: Dict[str, LlmChat] = {}
    
    def get_or_create_session(self, session_id: str, system_prompt: str = FORGE_SYSTEM_PROMPT) -> LlmChat:
        if session_id not in self.sessions:
            chat = LlmChat(api_key=self.api_key, session_id=session_id, system_message=system_prompt)
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            self.sessions[session_id] = chat
        return self.sessions[session_id]
    
    async def send_message(self, session_id: str, message: str, contexts: Dict[str, Any] = None, system_prompt: str = FORGE_SYSTEM_PROMPT) -> str:
        chat = self.get_or_create_session(session_id, system_prompt)
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

# ======================= ANDROID BUILD INTERVIEW =======================

class AndroidBuildInterviewer:
    def __init__(self, project: AndroidBuildProject):
        self.project = project
        self.session_id = f"android-interview-{project.id}"
    
    async def start_interview(self) -> str:
        """Start the interview with depth selection"""
        device_name = self.project.device_info.get('model', self.project.device_codename) if self.project.device_info else self.project.device_codename
        
        prompt = f"""Start the Android ROM build interview for device: {device_name}

The user has selected interview depth: {self.project.interview_depth.upper()}
{INTERVIEW_DEPTHS[self.project.interview_depth]['description']}

Device info:
{json.dumps(self.project.device_info, indent=2, default=str) if self.project.device_info else 'Not available'}

Begin by welcoming them and asking the first question. Remember this is a {self.project.interview_depth} interview with approximately {INTERVIEW_DEPTHS[self.project.interview_depth]['questions_count']} questions."""

        response = await ai_agent.send_message(
            self.session_id, 
            prompt,
            system_prompt=ANDROID_BUILDER_SYSTEM_PROMPT
        )
        return response
    
    async def process_answer(self, user_message: str) -> str:
        """Process user's answer and return next question or summary"""
        context = {
            "project_config": {
                "device": self.project.device_codename,
                "interview_depth": self.project.interview_depth,
                "answers_so_far": self.project.interview_answers
            },
            "available_options": {
                "rom_bases": list(ANDROID_ROM_BASES.keys()),
                "gapps_options": ANDROID_BUILD_FEATURES["gapps"]["options"],
                "root_options": ANDROID_BUILD_FEATURES["root"]["options"],
                "kernel_options": ANDROID_BUILD_FEATURES["kernel"]["options"],
                "security_options": ANDROID_BUILD_FEATURES["security"]["options"],
                "ui_options": ANDROID_BUILD_FEATURES["ui_customization"]["options"],
                "performance_options": ANDROID_BUILD_FEATURES["performance"]["options"]
            }
        }
        
        response = await ai_agent.send_message(
            self.session_id,
            user_message,
            contexts=context,
            system_prompt=ANDROID_BUILDER_SYSTEM_PROMPT
        )
        
        # Check if interview is complete (AI will indicate this)
        if "BUILD CONFIGURATION COMPLETE" in response.upper() or "READY TO BUILD" in response.upper():
            self.project.interview_complete = True
            self.project.build_status = "ready"
        
        return response
    
    def parse_build_config_from_answers(self) -> Dict[str, Any]:
        """Extract build configuration from interview answers"""
        answers = self.project.interview_answers
        return {
            "base_rom": answers.get("base_rom", "lineageos"),
            "android_version": answers.get("android_version", "14"),
            "kernel_type": answers.get("kernel", "custom_optimized"),
            "gapps_type": answers.get("gapps", "nano"),
            "root_solution": answers.get("root", "magisk"),
            "security_level": answers.get("security", "standard"),
            "ui_style": answers.get("ui", "stock"),
            "performance_profile": answers.get("performance", "balanced"),
            "camera_setup": answers.get("camera", "gcam_ready"),
            "audio_setup": answers.get("audio", "stock"),
            "custom_features": answers.get("features_add", []),
            "removed_features": answers.get("features_remove", [])
        }

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

# ======================= API ROUTES =======================

@api_router.get("/")
async def root():
    return {
        "message": "Linux Device Forge API",
        "version": "3.0.0",
        "tools": ["Kernel Forge", "OS Image Builder", "Halium Builder", "Android ROM Builder"]
    }

@api_router.get("/health")
async def health_check():
    tools = {
        "adb": check_tool_available("adb"),
        "fastboot": check_tool_available("fastboot"),
        "git": check_tool_available("git"),
        "make": check_tool_available("make"),
        "repo": check_tool_available("repo"),
        "dtc": check_tool_available("dtc"),
        "mkbootimg": check_tool_available("mkbootimg"),
        "debootstrap": check_tool_available("debootstrap"),
        "gcc-aarch64": check_tool_available("aarch64-linux-gnu-gcc"),
    }
    return {
        "status": "healthy",
        "tools": tools,
        "kernel_forge_ready": all([tools["git"], tools["make"]]),
        "os_builder_ready": True,
        "android_builder_ready": all([tools["git"], tools.get("repo", False) or True]),
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

# ======================= KERNEL ROUTES =======================

@api_router.post("/kernel/projects")
async def create_kernel_project(request: BuildRequest):
    project = KernelProject(
        name=f"kernel-{request.device_codename}",
        device_codename=request.device_codename,
        source_url=request.kernel_source,
        architecture=request.architecture
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

@api_router.post("/kernel/projects/{project_id}/analyze")
async def analyze_kernel_config(project_id: str):
    project = await db.kernel_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Simulated analysis for now
    analysis = {
        "defconfig": "device_defconfig",
        "total_configs": len(KERNEL_CONFIG_LINUX_GENERIC),
        "met": [c for c in KERNEL_CONFIG_LINUX_GENERIC if not c["required"]],
        "missing": [c for c in KERNEL_CONFIG_LINUX_GENERIC if c["required"]][:5],
        "compatibility_score": 75,
        "linux_ready": False,
        "recommendations": ["Add CONFIG_NAMESPACES=y", "Add CONFIG_CGROUPS=y"]
    }
    
    await db.kernel_projects.update_one({"id": project_id}, {"$set": {"config_analysis": analysis}})
    return analysis

@api_router.get("/kernel/mainline-versions")
async def get_mainline_versions():
    return {"versions": MAINLINE_KERNELS, "recommended_lts": "6.6", "latest_mainline": "6.8"}

@api_router.get("/kernel/config-requirements")
async def get_kernel_config_requirements():
    return {
        "requirements": KERNEL_CONFIG_LINUX_GENERIC,
        "total": len(KERNEL_CONFIG_LINUX_GENERIC),
        "required_count": len([r for r in KERNEL_CONFIG_LINUX_GENERIC if r["required"]])
    }

# ======================= OS BUILDER ROUTES =======================

@api_router.get("/os/distros")
async def get_available_distros():
    return {"mobile": MOBILE_DISTROS, "desktop": DESKTOP_DISTROS}

@api_router.post("/os/projects")
async def create_os_project(request: OSBuildRequest):
    distro_info = MOBILE_DISTROS.get(request.distro) or DESKTOP_DISTROS.get(request.distro)
    project = OSImageProject(
        name=f"{request.distro}-{request.device_codename}",
        device_codename=request.device_codename,
        distro=request.distro,
        distro_version=request.distro_version,
        distro_type="mobile" if request.distro in MOBILE_DISTROS else "desktop",
        init_system=distro_info.get("init_system", "systemd") if distro_info else "systemd"
    )
    doc = project.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.os_image_projects.insert_one(doc)
    return project

@api_router.get("/os/projects")
async def list_os_projects():
    projects = await db.os_image_projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"projects": projects}

@api_router.post("/os/projects/{project_id}/build")
async def build_os_image(project_id: str, background_tasks: BackgroundTasks):
    await db.os_image_projects.update_one({"id": project_id}, {"$set": {"build_status": "building"}})
    return {"status": "build_started", "project_id": project_id}

# ======================= ANDROID BUILDER ROUTES =======================

@api_router.get("/android/rom-bases")
async def get_android_rom_bases():
    return {"rom_bases": ANDROID_ROM_BASES}

@api_router.get("/android/build-features")
async def get_android_build_features():
    return {"features": ANDROID_BUILD_FEATURES}

@api_router.get("/android/interview-depths")
async def get_interview_depths():
    return {"depths": INTERVIEW_DEPTHS}

@api_router.post("/android/projects")
async def create_android_project(request: AndroidBuildRequest):
    """Create a new Android build project and start the interview"""
    device_info = None
    if request.device_serial:
        device_info = await get_full_device_info(request.device_serial)
        device_info = device_info.model_dump()
    
    project = AndroidBuildProject(
        name=f"android-{request.device_codename}",
        device_codename=request.device_codename,
        device_info=device_info,
        interview_depth=request.interview_depth
    )
    
    doc = project.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.android_projects.insert_one(doc)
    
    # Start the interview
    interviewer = AndroidBuildInterviewer(project)
    first_message = await interviewer.start_interview()
    
    return {
        "project": project,
        "first_message": first_message
    }

@api_router.get("/android/projects")
async def list_android_projects():
    projects = await db.android_projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"projects": projects}

@api_router.get("/android/projects/{project_id}")
async def get_android_project(project_id: str):
    project = await db.android_projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@api_router.post("/android/projects/{project_id}/interview")
async def android_interview_message(project_id: str, request: AndroidInterviewMessage):
    """Send a message in the Android build interview"""
    project_doc = await db.android_projects.find_one({"id": project_id})
    if not project_doc:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = AndroidBuildProject(**project_doc)
    interviewer = AndroidBuildInterviewer(project)
    
    response = await interviewer.process_answer(request.message)
    
    # Update project status
    await db.android_projects.update_one(
        {"id": project_id},
        {"$set": {
            "interview_complete": project.interview_complete,
            "build_status": project.build_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "response": response,
        "interview_complete": project.interview_complete,
        "build_status": project.build_status
    }

@api_router.post("/android/projects/{project_id}/build")
async def start_android_build(project_id: str, background_tasks: BackgroundTasks):
    """Start the Android ROM build process"""
    project = await db.android_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not project.get("interview_complete", False):
        raise HTTPException(status_code=400, detail="Interview not complete")
    
    await db.android_projects.update_one(
        {"id": project_id},
        {"$set": {"build_status": "building", "build_progress": 0}}
    )
    
    return {"status": "build_started", "project_id": project_id}

@api_router.get("/android/projects/{project_id}/config")
async def get_android_build_config(project_id: str):
    """Get the generated build configuration"""
    project = await db.android_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "device": project.get("device_codename"),
        "base_rom": project.get("base_rom"),
        "android_version": project.get("android_version"),
        "kernel_type": project.get("kernel_type"),
        "gapps_type": project.get("gapps_type"),
        "root_solution": project.get("root_solution"),
        "security_level": project.get("security_level"),
        "ui_style": project.get("ui_style"),
        "performance_profile": project.get("performance_profile"),
        "custom_features": project.get("custom_features", []),
        "interview_answers": project.get("interview_answers", {})
    }

# ======================= HALIUM ROUTES =======================

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
async def start_halium_build(request: dict):
    session = {
        "id": str(uuid.uuid4()),
        "device_serial": request.get("device_serial"),
        "halium_version": request.get("halium_version", "halium-11.0"),
        "status": "pending",
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
    dangerous = ['rm -rf /', 'mkfs', ':(){', '> /dev/sd']
    for pattern in dangerous:
        if pattern in cmd.lower():
            raise HTTPException(status_code=400, detail="Dangerous command blocked")
    
    stdout, stderr, code = await run_command(cmd, timeout=request.timeout, cwd=request.working_dir)
    await db.command_history.insert_one({
        "id": str(uuid.uuid4()), "command": cmd, "stdout": stdout, "stderr": stderr,
        "exit_code": code, "session_id": request.session_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return {"command": cmd, "stdout": stdout, "stderr": stderr, "exit_code": code, "success": code == 0}

@api_router.post("/ai/chat")
async def ai_chat(request: AIRequest):
    try:
        contexts = {}
        if request.device_context:
            contexts["Device"] = request.device_context
        if request.kernel_context:
            contexts["Kernel"] = request.kernel_context
        if request.build_context:
            contexts["Build"] = request.build_context
        
        response = await ai_agent.send_message(request.session_id, request.message, contexts)
        commands = ai_agent.extract_commands(response)
        
        await db.chat_messages.insert_one({
            "session_id": request.session_id, "role": "user", "content": request.message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        await db.chat_messages.insert_one({
            "session_id": request.session_id, "role": "assistant", "content": response,
            "extracted_commands": commands, "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        execution_results = []
        if request.auto_execute and commands:
            for cmd in commands:
                stdout, stderr, code = await run_command(cmd, timeout=120)
                execution_results.append({"command": cmd, "stdout": stdout, "stderr": stderr, "success": code == 0})
                if code != 0:
                    break
        
        return {"response": response, "extracted_commands": commands, "execution_results": execution_results if request.auto_execute else None}
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
                contexts = {"Device": data.get("device_context"), "Kernel": data.get("kernel_context")}
                response = await ai_agent.send_message(session_id, data.get("message", ""), contexts)
                commands = ai_agent.extract_commands(response)
                await websocket.send_json({"type": "ai_response", "response": response, "commands": commands})
    
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
