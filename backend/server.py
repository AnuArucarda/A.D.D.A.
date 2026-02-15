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

# Import our new modules
from binary_manager import binary_manager
from build_orchestrator import build_orchestrator

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

# Root Solutions for Android/Kernel builds
ROOT_SOLUTIONS = {
    "none": {
        "name": "No Root",
        "description": "Standard Android without root access",
        "kernel_patch": False
    },
    "magisk": {
        "name": "Magisk",
        "description": "Systemless root with module support, SafetyNet bypass",
        "kernel_patch": False,
        "install_method": "boot_patch",
        "repo": "https://github.com/topjohnwu/Magisk"
    },
    "magisk_delta": {
        "name": "Magisk Delta",
        "description": "Magisk fork with additional hiding features",
        "kernel_patch": False,
        "install_method": "boot_patch",
        "repo": "https://github.com/HuskyDG/magisk-files"
    },
    "kernelsu": {
        "name": "KernelSU",
        "description": "Kernel-based root, better hiding, module support",
        "kernel_patch": True,
        "install_method": "kernel_patch",
        "repo": "https://github.com/tiann/KernelSU",
        "kernel_configs": [
            "CONFIG_KPROBES=y",
            "CONFIG_HAVE_KPROBES=y",
            "CONFIG_KPROBE_EVENTS=y"
        ]
    },
    "kernelsu_next": {
        "name": "KernelSU Next",
        "description": "Next-gen KernelSU with improved compatibility",
        "kernel_patch": True,
        "install_method": "kernel_patch",
        "repo": "https://github.com/rifsxd/KernelSU-Next",
        "kernel_configs": [
            "CONFIG_KPROBES=y",
            "CONFIG_HAVE_KPROBES=y",
            "CONFIG_KPROBE_EVENTS=y"
        ]
    },
    "apatch": {
        "name": "APatch",
        "description": "Android kernel patch root solution",
        "kernel_patch": True,
        "install_method": "kernel_patch",
        "repo": "https://github.com/bmax121/APatch"
    },
    "supersu": {
        "name": "SuperSU",
        "description": "Legacy root solution (deprecated)",
        "kernel_patch": False,
        "install_method": "system_install"
    }
}

# Custom Recovery options
CUSTOM_RECOVERIES = {
    "twrp": {
        "name": "TWRP",
        "full_name": "Team Win Recovery Project",
        "description": "Most popular custom recovery with touch interface",
        "repo": "https://github.com/TeamWin/android_bootable_recovery",
        "manifest": "https://github.com/minimal-manifest-twrp/platform_manifest_twrp_aosp",
        "branches": ["twrp-12.1", "twrp-11", "twrp-10", "twrp-9.0"]
    },
    "orangefox": {
        "name": "OrangeFox",
        "full_name": "OrangeFox Recovery",
        "description": "Feature-rich recovery based on TWRP with modern UI",
        "repo": "https://gitlab.com/OrangeFox/Recovery",
        "manifest": "https://gitlab.com/OrangeFox/sync",
        "branches": ["fox_12.1", "fox_11.0", "fox_10.0"]
    },
    "pitchblack": {
        "name": "PitchBlack",
        "full_name": "PitchBlack Recovery Project",
        "description": "Dark-themed TWRP-based recovery",
        "repo": "https://github.com/PitchBlackRecoveryProject",
        "manifest": "https://github.com/PitchBlackRecoveryProject/manifest_pb",
        "branches": ["android-12.1", "android-11.0"]
    },
    "shrp": {
        "name": "SHRP",
        "full_name": "SkyHawk Recovery Project",
        "description": "Modern recovery with unique features",
        "repo": "https://github.com/nicklaspersson/android_bootable_recovery",
        "manifest": "https://github.com/nicklaspersson/manifest",
        "branches": ["android-12.1", "android-11.0"]
    },
    "pbrp": {
        "name": "PBRP",
        "full_name": "PitchBlack Recovery Project",
        "description": "Feature-packed recovery with OTA support",
        "repo": "https://github.com/nicklaspersson/recovery_manifest",
        "branches": ["android-12.1"]
    }
}

# Linux kernel capabilities/security features
LINUX_KERNEL_SECURITY = {
    "capabilities": {
        "configs": [
            "CONFIG_SECURITY=y",
            "CONFIG_SECURITYFS=y",
            "CONFIG_SECURITY_NETWORK=y",
            "CONFIG_SECURITY_PATH=y"
        ],
        "description": "POSIX capabilities for fine-grained privileges"
    },
    "namespaces": {
        "configs": [
            "CONFIG_NAMESPACES=y",
            "CONFIG_USER_NS=y",
            "CONFIG_PID_NS=y",
            "CONFIG_NET_NS=y",
            "CONFIG_UTS_NS=y",
            "CONFIG_IPC_NS=y"
        ],
        "description": "Namespace isolation for containers/sandboxing"
    },
    "selinux": {
        "configs": [
            "CONFIG_SECURITY_SELINUX=y",
            "CONFIG_SECURITY_SELINUX_BOOTPARAM=y",
            "CONFIG_SECURITY_SELINUX_DISABLE=y"
        ],
        "description": "SELinux mandatory access control"
    },
    "apparmor": {
        "configs": [
            "CONFIG_SECURITY_APPARMOR=y",
            "CONFIG_SECURITY_APPARMOR_BOOTPARAM_VALUE=1"
        ],
        "description": "AppArmor application security"
    },
    "sudo_support": {
        "configs": [
            "CONFIG_AUDITSYSCALL=y",
            "CONFIG_AUDIT=y"
        ],
        "description": "Audit support for sudo logging"
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
    
    # Recipe/Export
    saved_as_recipe: bool = False
    recipe_name: Optional[str] = None
    recipe_description: Optional[str] = None
    export_package_path: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BuildRecipe(BaseModel):
    """Saved build configuration that can be reused or shared"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    author: Optional[str] = None
    
    # Target info
    device_codename: str
    device_model: Optional[str] = None
    architecture: str = "arm64"
    
    # Build type
    build_type: str  # kernel, os, android, halium
    
    # Configuration (varies by build type)
    config: Dict[str, Any] = {}
    
    # For Android builds
    interview_depth: Optional[str] = None
    interview_answers: Optional[Dict[str, Any]] = None
    base_rom: Optional[str] = None
    android_version: Optional[str] = None
    gapps_type: Optional[str] = None
    root_solution: Optional[str] = None
    kernel_type: Optional[str] = None
    
    # For Kernel builds
    kernel_source: Optional[str] = None
    defconfig: Optional[str] = None
    kernel_version: Optional[str] = None
    config_patches: List[str] = []
    
    # For OS builds
    distro: Optional[str] = None
    distro_version: Optional[str] = None
    packages: List[str] = []
    
    # For Halium builds
    halium_version: Optional[str] = None
    
    # Metadata
    tags: List[str] = []
    downloads: int = 0
    rating: float = 0.0
    is_public: bool = False
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BuildExportPackage(BaseModel):
    """Complete build export with images and scripts"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    project_type: str  # kernel, os, android, halium
    
    # Package info
    name: str
    device_codename: str
    description: Optional[str] = None
    
    # Contents
    images: List[str] = []  # boot.img, system.img, etc.
    scripts: List[str] = []  # build scripts
    configs: List[str] = []  # configuration files
    manifests: List[str] = []  # repo manifests
    patches: List[str] = []  # applied patches
    
    # Package file
    package_path: Optional[str] = None
    package_size: Optional[int] = None
    checksum: Optional[str] = None
    
    # Build info for reproducibility
    build_host: Optional[str] = None
    build_date: Optional[str] = None
    build_commands: List[str] = []
    environment_vars: Dict[str, str] = {}
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    tools = binary_manager.get_all_status()
    return {
        "status": "healthy",
        "tools": tools,
        "kernel_forge_ready": tools.get("git", {}).get("available", False) and tools.get("make", {}).get("available", False),
        "os_builder_ready": True,
        "android_builder_ready": tools.get("git", {}).get("available", False),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ======================= BINARY MANAGEMENT ROUTES =======================

@api_router.get("/binaries/status")
async def get_binaries_status():
    """Get status of all required binaries"""
    return {
        "binaries": binary_manager.get_all_status(),
        "configured_paths": binary_manager.binary_paths
    }

@api_router.post("/binaries/{binary_name}/set-path")
async def set_binary_path(binary_name: str, path: str):
    """Set custom path for a binary"""
    success = binary_manager.set_binary_path(binary_name, path)
    if success:
        return {"success": True, "message": f"Path set for {binary_name}"}
    raise HTTPException(status_code=400, detail="Invalid path or binary not found")

@api_router.post("/binaries/{binary_name}/install")
async def install_binary(binary_name: str):
    """Download and install a binary"""
    success, message = await binary_manager.download_and_install_binary(binary_name)
    if success:
        return {"success": True, "message": message}
    raise HTTPException(status_code=400, detail=message)

@api_router.get("/binaries/{binary_name}/path")
async def get_binary_path(binary_name: str):
    """Get the path to a specific binary"""
    available, path = binary_manager.check_binary(binary_name)
    if available:
        return {"available": True, "path": path}
    return {"available": False, "path": None, "can_install": binary_name in binary_manager.BINARY_SOURCES}

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

# ======================= RECIPE & EXPORT ROUTES =======================

@api_router.post("/recipes")
async def save_recipe(recipe_data: dict):
    """Save a build configuration as a reusable recipe"""
    recipe = BuildRecipe(
        name=recipe_data.get("name", "Unnamed Recipe"),
        description=recipe_data.get("description"),
        author=recipe_data.get("author"),
        device_codename=recipe_data.get("device_codename", "unknown"),
        device_model=recipe_data.get("device_model"),
        architecture=recipe_data.get("architecture", "arm64"),
        build_type=recipe_data.get("build_type", "android"),
        config=recipe_data.get("config", {}),
        interview_depth=recipe_data.get("interview_depth"),
        interview_answers=recipe_data.get("interview_answers"),
        base_rom=recipe_data.get("base_rom"),
        android_version=recipe_data.get("android_version"),
        gapps_type=recipe_data.get("gapps_type"),
        root_solution=recipe_data.get("root_solution"),
        kernel_type=recipe_data.get("kernel_type"),
        kernel_source=recipe_data.get("kernel_source"),
        defconfig=recipe_data.get("defconfig"),
        kernel_version=recipe_data.get("kernel_version"),
        distro=recipe_data.get("distro"),
        distro_version=recipe_data.get("distro_version"),
        halium_version=recipe_data.get("halium_version"),
        tags=recipe_data.get("tags", []),
        is_public=recipe_data.get("is_public", False)
    )
    
    doc = recipe.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.recipes.insert_one(doc)
    
    return recipe

@api_router.get("/recipes")
async def list_recipes(build_type: Optional[str] = None, device: Optional[str] = None, public_only: bool = False):
    """List saved recipes with optional filters"""
    query = {}
    if build_type:
        query["build_type"] = build_type
    if device:
        query["device_codename"] = device
    if public_only:
        query["is_public"] = True
    
    recipes = await db.recipes.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"recipes": recipes, "count": len(recipes)}

@api_router.get("/recipes/{recipe_id}")
async def get_recipe(recipe_id: str):
    """Get a specific recipe"""
    recipe = await db.recipes.find_one({"id": recipe_id}, {"_id": 0})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Increment download count
    await db.recipes.update_one({"id": recipe_id}, {"$inc": {"downloads": 1}})
    
    return recipe

@api_router.delete("/recipes/{recipe_id}")
async def delete_recipe(recipe_id: str):
    """Delete a recipe"""
    result = await db.recipes.delete_one({"id": recipe_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"message": "Recipe deleted", "id": recipe_id}

@api_router.post("/recipes/{recipe_id}/apply")
async def apply_recipe(recipe_id: str, device_codename: str):
    """Create a new project from a recipe"""
    recipe = await db.recipes.find_one({"id": recipe_id}, {"_id": 0})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Create appropriate project type from recipe
    if recipe.get("build_type") == "android":
        project = AndroidBuildProject(
            name=f"{recipe.get('name')}-{device_codename}",
            device_codename=device_codename,
            interview_depth=recipe.get("interview_depth", "standard"),
            interview_complete=True,  # Skip interview, use recipe
            interview_answers=recipe.get("interview_answers", {}),
            base_rom=recipe.get("base_rom"),
            android_version=recipe.get("android_version"),
            gapps_type=recipe.get("gapps_type"),
            root_solution=recipe.get("root_solution"),
            kernel_type=recipe.get("kernel_type"),
            build_status="ready"
        )
        doc = project.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.android_projects.insert_one(doc)
        return {"project_type": "android", "project": project}
    
    elif recipe.get("build_type") == "kernel":
        project = KernelProject(
            name=f"kernel-{device_codename}",
            device_codename=device_codename,
            source_url=recipe.get("kernel_source"),
            defconfig=recipe.get("defconfig"),
            target_version=recipe.get("kernel_version")
        )
        doc = project.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.kernel_projects.insert_one(doc)
        return {"project_type": "kernel", "project": project}
    
    elif recipe.get("build_type") == "os":
        project = OSImageProject(
            name=f"{recipe.get('distro')}-{device_codename}",
            device_codename=device_codename,
            distro=recipe.get("distro"),
            distro_version=recipe.get("distro_version")
        )
        doc = project.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.os_image_projects.insert_one(doc)
        return {"project_type": "os", "project": project}
    
    return {"error": "Unknown build type"}

@api_router.post("/exports/create")
async def create_export_package(project_id: str, project_type: str):
    """Create a complete export package with images, scripts, and configs"""
    
    # Get project based on type
    if project_type == "android":
        project = await db.android_projects.find_one({"id": project_id}, {"_id": 0})
    elif project_type == "kernel":
        project = await db.kernel_projects.find_one({"id": project_id}, {"_id": 0})
    elif project_type == "os":
        project = await db.os_image_projects.find_one({"id": project_id}, {"_id": 0})
    elif project_type == "halium":
        project = await db.halium_builds.find_one({"id": project_id}, {"_id": 0})
    else:
        raise HTTPException(status_code=400, detail="Invalid project type")
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create export directory
    export_dir = WORK_DIR / "exports" / project_id
    export_dir.mkdir(parents=True, exist_ok=True)
    
    device_codename = project.get("device_codename", "device")
    
    # Create package structure
    package = BuildExportPackage(
        project_id=project_id,
        project_type=project_type,
        name=f"{project_type}-{device_codename}-export",
        device_codename=device_codename,
        build_date=datetime.now(timezone.utc).isoformat()
    )
    
    # Generate build script
    build_script = generate_build_script(project, project_type)
    script_path = export_dir / "build.sh"
    async with aiofiles.open(script_path, 'w') as f:
        await f.write(build_script)
    package.scripts.append(str(script_path))
    
    # Generate config file
    config_content = json.dumps(project, indent=2, default=str)
    config_path = export_dir / "build_config.json"
    async with aiofiles.open(config_path, 'w') as f:
        await f.write(config_content)
    package.configs.append(str(config_path))
    
    # Generate README
    readme_content = generate_readme(project, project_type)
    readme_path = export_dir / "README.md"
    async with aiofiles.open(readme_path, 'w') as f:
        await f.write(readme_content)
    
    # Generate environment file
    env_content = generate_env_file(project, project_type)
    env_path = export_dir / "build_env.sh"
    async with aiofiles.open(env_path, 'w') as f:
        await f.write(env_content)
    package.scripts.append(str(env_path))
    
    # Copy output files if they exist
    if project.get("output_files"):
        for output_file in project["output_files"]:
            if Path(output_file).exists():
                dest = export_dir / Path(output_file).name
                shutil.copy(output_file, dest)
                package.images.append(str(dest))
    
    # Create the zip package
    zip_path = WORK_DIR / "exports" / f"{project_type}-{device_codename}-{project_id[:8]}.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(export_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(export_dir)
                zipf.write(file_path, arcname)
    
    package.package_path = str(zip_path)
    package.package_size = zip_path.stat().st_size
    
    # Calculate checksum
    import hashlib
    sha256_hash = hashlib.sha256()
    with open(zip_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    package.checksum = sha256_hash.hexdigest()
    
    # Save package info
    doc = package.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.export_packages.insert_one(doc)
    
    return package

@api_router.get("/exports")
async def list_exports(project_type: Optional[str] = None):
    """List all export packages"""
    query = {}
    if project_type:
        query["project_type"] = project_type
    
    exports = await db.export_packages.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"exports": exports}

@api_router.get("/exports/{export_id}/download")
async def download_export(export_id: str):
    """Download an export package"""
    export = await db.export_packages.find_one({"id": export_id}, {"_id": 0})
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    
    package_path = export.get("package_path")
    if not package_path or not Path(package_path).exists():
        raise HTTPException(status_code=404, detail="Export file not found")
    
    return FileResponse(
        package_path,
        media_type="application/zip",
        filename=Path(package_path).name
    )

def generate_build_script(project: dict, project_type: str) -> str:
    """Generate a complete build script for reproducibility"""
    device = project.get("device_codename", "device")
    
    script = f'''#!/bin/bash
# Auto-generated build script by Linux Device Forge
# Device: {device}
# Build Type: {project_type}
# Generated: {datetime.now(timezone.utc).isoformat()}

set -e

echo "=== Linux Device Forge Build Script ==="
echo "Device: {device}"
echo "Type: {project_type}"
echo ""

# Source environment
source ./build_env.sh

'''
    
    if project_type == "android":
        base_rom = project.get("base_rom", "lineageos")
        android_ver = project.get("android_version", "14")
        script += f'''
# Android ROM Build Configuration
BASE_ROM="{base_rom}"
ANDROID_VERSION="{android_ver}"
GAPPS="{project.get('gapps_type', 'none')}"
ROOT="{project.get('root_solution', 'none')}"
KERNEL="{project.get('kernel_type', 'stock')}"

echo "Building $BASE_ROM Android $ANDROID_VERSION for {device}"

# Initialize repo
mkdir -p android && cd android
repo init -u https://github.com/{base_rom}/{base_rom}.git -b lineage-$ANDROID_VERSION

# Sync sources
repo sync -c -j$(nproc) --force-sync

# Set up environment
source build/envsetup.sh
breakfast {device}

# Build
mka bacon

echo "Build complete! Output in out/target/product/{device}/"
'''
    
    elif project_type == "kernel":
        script += f'''
# Kernel Build Configuration
KERNEL_SOURCE="{project.get('source_url', '')}"
DEFCONFIG="{project.get('defconfig', device + '_defconfig')}"
ARCH="arm64"
CROSS_COMPILE="aarch64-linux-gnu-"

echo "Building kernel for {device}"

# Clone kernel source
git clone --depth=1 $KERNEL_SOURCE kernel
cd kernel

# Configure
make ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE $DEFCONFIG

# Build
make ARCH=$ARCH CROSS_COMPILE=$CROSS_COMPILE -j$(nproc)

echo "Kernel build complete!"
'''
    
    elif project_type == "os":
        distro = project.get("distro", "ubuntu")
        script += f'''
# OS Image Build Configuration
DISTRO="{distro}"
VERSION="{project.get('distro_version', 'latest')}"
ARCH="arm64"

echo "Building $DISTRO $VERSION for {device}"

# Create rootfs
mkdir -p rootfs
debootstrap --arch=$ARCH $VERSION rootfs

# Customize rootfs
echo "{device}" > rootfs/etc/hostname

# Create boot image
# (requires kernel image)

echo "OS image build complete!"
'''
    
    elif project_type == "halium":
        halium_ver = project.get("halium_version", "halium-11.0")
        script += f'''
# Halium Build Configuration
HALIUM_VERSION="{halium_ver}"

echo "Building Halium $HALIUM_VERSION for {device}"

# Initialize Halium
mkdir -p halium && cd halium
repo init -u https://github.com/halium/android.git -b $HALIUM_VERSION

# Add device repos to local manifest
mkdir -p .repo/local_manifests

# Sync
repo sync -c -j$(nproc) --force-sync

# Build
source build/envsetup.sh
breakfast {device}
mka halium-boot
mka systemimage

echo "Halium build complete!"
'''
    
    script += '''
echo ""
echo "=== Build Complete ==="
echo "Check the output directory for built images"
'''
    
    return script

def generate_readme(project: dict, project_type: str) -> str:
    """Generate README for the export package"""
    device = project.get("device_codename", "device")
    
    readme = f'''# Linux Device Forge Export Package

## Device: {device}
## Build Type: {project_type.upper()}
## Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}

---

## Contents

- `build.sh` - Main build script to reproduce this build
- `build_env.sh` - Environment variables for the build
- `build_config.json` - Complete build configuration
- `README.md` - This file

## Quick Start

```bash
# Make scripts executable
chmod +x build.sh build_env.sh

# Run the build
./build.sh
```

## Requirements

'''
    
    if project_type == "android":
        readme += '''
- Ubuntu 20.04+ or similar Linux distro
- 16GB+ RAM
- 200GB+ free disk space
- repo tool installed
- Android build dependencies

### Install dependencies (Ubuntu):
```bash
sudo apt-get install git-core gnupg flex bison build-essential zip curl \\
    zlib1g-dev libc6-dev-i386 libncurses5 lib32ncurses5-dev \\
    x11proto-core-dev libx11-dev lib32z1-dev libgl1-mesa-dev \\
    libxml2-utils xsltproc unzip fontconfig python3
```
'''
    elif project_type == "kernel":
        readme += '''
- Linux build environment
- Cross-compilation toolchain (aarch64-linux-gnu-gcc)
- Git
- Make, GCC

### Install dependencies (Ubuntu):
```bash
sudo apt-get install build-essential gcc-aarch64-linux-gnu git
```
'''
    elif project_type == "os":
        readme += '''
- Linux build environment
- debootstrap (for Debian-based)
- mkbootimg
- Root access for some operations

### Install dependencies (Ubuntu):
```bash
sudo apt-get install debootstrap qemu-user-static
```
'''
    
    readme += f'''

## Build Configuration

```json
{json.dumps(project, indent=2, default=str)}
```

## Notes

- This package was generated by Linux Device Forge
- The build script is designed to be reproducible
- Modify build_config.json to customize the build
- Check the project documentation for device-specific instructions

## Support

For issues or questions, visit: https://github.com/halium/projectmanagement/issues

---
*Generated by Linux Device Forge v3.0*
'''
    
    return readme

def generate_env_file(project: dict, project_type: str) -> str:
    """Generate environment variables file"""
    device = project.get("device_codename", "device")
    
    env = f'''#!/bin/bash
# Environment variables for {project_type} build
# Device: {device}

export DEVICE="{device}"
export BUILD_TYPE="{project_type}"
export ARCH="arm64"
export CROSS_COMPILE="aarch64-linux-gnu-"

# Build directories
export BUILD_DIR="$(pwd)"
export OUT_DIR="$BUILD_DIR/out"

# Parallel jobs
export JOBS=$(nproc)

'''
    
    if project_type == "android":
        env += f'''
# Android specific
export BASE_ROM="{project.get('base_rom', 'lineageos')}"
export ANDROID_VERSION="{project.get('android_version', '14')}"
export USE_CCACHE=1
export CCACHE_DIR="$BUILD_DIR/.ccache"
'''
    elif project_type == "kernel":
        env += f'''
# Kernel specific
export KERNEL_DIR="$BUILD_DIR/kernel"
export DEFCONFIG="{project.get('defconfig', device + '_defconfig')}"
'''
    
    return env

# ======================= HALIUM ROUTES =======================

@api_router.get("/halium/versions")
async def get_halium_versions():
    """Get available Halium versions"""
    versions = []
    for key, info in HALIUM_VERSIONS.items():
        versions.append({
            "id": key,
            "name": key.replace("-", " ").title(),
            "android_base": f"Android {info['android']}",
            "lineage_base": f"LineageOS {info['lineage']}",
            "status": "latest" if key == "halium-11.0" else "stable"
        })
    return {"versions": versions}

@api_router.get("/halium/builds")
async def list_halium_builds():
    """List all Halium builds"""
    builds = await db.halium_builds.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"builds": builds}

@api_router.post("/halium/build")
async def start_halium_build(request: dict, background_tasks: BackgroundTasks):
    """Start a Halium build"""
    device_serial = request.get("device_serial")
    halium_version = request.get("halium_version", "halium-11.0")
    
    # Get device info
    if device_serial:
        device_info = await get_full_device_info(device_serial)
        device_codename = device_info.codename or device_info.device
    else:
        device_codename = request.get("device_codename", "unknown")
    
    # Create build record
    build_id = str(uuid.uuid4())
    build_doc = {
        "id": build_id,
        "device_codename": device_codename,
        "halium_version": halium_version,
        "status": "building",
        "progress": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.halium_builds.insert_one(build_doc)
    
    return {"build_id": build_id, "status": "started", "message": "Halium build initiated"}

# ======================= RECOVERY BUILDER ROUTES =======================

@api_router.get("/recovery/types")
async def get_recovery_types():
    """Get available custom recovery types"""
    return {"recoveries": CUSTOM_RECOVERIES}

@api_router.post("/recovery/build")
async def start_recovery_build(request: dict, background_tasks: BackgroundTasks):
    """Start building a custom recovery"""
    device_codename = request.get("device_codename")
    recovery_type = request.get("recovery_type", "twrp")
    
    if not device_codename:
        raise HTTPException(status_code=400, detail="device_codename required")
    
    if recovery_type not in CUSTOM_RECOVERIES:
        raise HTTPException(status_code=400, detail=f"Invalid recovery type. Choose from: {list(CUSTOM_RECOVERIES.keys())}")
    
    # Create build record
    build_id = str(uuid.uuid4())
    build_doc = {
        "id": build_id,
        "device_codename": device_codename,
        "recovery_type": recovery_type,
        "status": "building",
        "progress": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.recovery_builds.insert_one(build_doc)
    
    # Start build in background
    # background_tasks.add_task(build_orchestrator.build_recovery, device_codename, recovery_type)
    
    return {
        "build_id": build_id,
        "status": "started",
        "recovery": CUSTOM_RECOVERIES[recovery_type]["full_name"],
        "device": device_codename
    }

@api_router.get("/recovery/builds")
async def list_recovery_builds():
    """List all recovery builds"""
    builds = await db.recovery_builds.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"builds": builds}

@api_router.get("/recovery/builds/{build_id}")
async def get_recovery_build(build_id: str):
    """Get specific recovery build details"""
    build = await db.recovery_builds.find_one({"id": build_id}, {"_id": 0})
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return build

# ======================= ROOT INTEGRATION ROUTES =======================

@api_router.get("/root/solutions")
async def get_root_solutions():
    """Get available root solutions"""
    return {"solutions": ROOT_SOLUTIONS}

@api_router.post("/root/integrate")
async def integrate_root_solution(request: dict):
    """Integrate root solution into kernel or ROM"""
    project_id = request.get("project_id")
    project_type = request.get("project_type")  # kernel, android, os
    root_solution = request.get("root_solution", "magisk")
    
    if not project_id or not project_type:
        raise HTTPException(status_code=400, detail="project_id and project_type required")
    
    if root_solution not in ROOT_SOLUTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid root solution. Choose from: {list(ROOT_SOLUTIONS.keys())}")
    
    # Get project
    collection_map = {
        "kernel": db.kernel_projects,
        "android": db.android_projects,
        "os": db.os_image_projects
    }
    
    collection = collection_map.get(project_type)
    if not collection:
        raise HTTPException(status_code=400, detail="Invalid project type")
    
    project = await collection.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update project with root solution
    await collection.update_one(
        {"id": project_id},
        {"$set": {
            "root_solution": root_solution,
            "root_integrated": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    solution_info = ROOT_SOLUTIONS[root_solution]
    
    return {
        "success": True,
        "message": f"{solution_info['name']} will be integrated into the build",
        "requires_kernel_patch": solution_info.get("kernel_patch", False),
        "install_method": solution_info.get("install_method", "boot_patch")
    }
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
