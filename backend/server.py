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
from binary_manager import binary_manager, BINARY_SOURCES
from build_orchestrator import build_orchestrator
from app_compiler import app_compiler
from ai_build_assistant import ai_build_assistant
from build_presets import get_presets_for_tool, apply_preset_to_project
from ai_provider_manager import ai_provider_manager
from device_manager import device_manager
from build_history_manager import BuildHistoryManager
from factory_image_manager import factory_image_manager
from github_integration import github_integration

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'linux_device_forge')]

# Initialize managers
build_history = BuildHistoryManager(db)

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

# Advanced Root Solutions for Android/Kernel builds
ROOT_SOLUTIONS = {
    "none": {
        "name": "No Root",
        "description": "Standard Android without root access",
        "category": "none",
        "kernel_patch": False,
        "difficulty": "easy"
    },
    
    # ========== MAGISK VARIANTS ==========
    "magisk": {
        "name": "Magisk (Stable)",
        "description": "Official Magisk - Systemless root with module ecosystem",
        "category": "magisk",
        "kernel_patch": False,
        "install_method": "boot_patch",
        "repo": "https://github.com/topjohnwu/Magisk",
        "features": ["Systemless", "Modules", "MagiskHide (deprecated)", "Zygisk"],
        "safetynet": "Basic bypass (deprecated in newer Android)",
        "play_integrity": "Fails on newer devices",
        "difficulty": "easy",
        "recommended_for": "General users, module enthusiasts"
    },
    "magisk_delta": {
        "name": "Magisk Delta",
        "description": "Enhanced Magisk fork with advanced hiding & Zygisk improvements",
        "category": "magisk",
        "kernel_patch": False,
        "install_method": "boot_patch",
        "repo": "https://github.com/HuskyDG/magisk-files",
        "features": ["Enhanced Zygisk", "Better hiding", "Shamiko support", "DenyList++"],
        "safetynet": "Good with Shamiko",
        "play_integrity": "DEVICE integrity possible with Shamiko",
        "difficulty": "easy",
        "recommended_for": "Users needing better detection bypass"
    },
    "magisk_alpha": {
        "name": "Magisk Alpha/Canary",
        "description": "Bleeding-edge Magisk with experimental features",
        "category": "magisk",
        "kernel_patch": False,
        "install_method": "boot_patch",
        "repo": "https://github.com/topjohnwu/Magisk",
        "features": ["Latest features", "Zygisk Next", "Experimental fixes"],
        "safetynet": "Varies",
        "play_integrity": "Experimental",
        "difficulty": "medium",
        "recommended_for": "Testers, developers"
    },
    
    # ========== KERNELSU VARIANTS ==========
    "kernelsu_standard": {
        "name": "KernelSU (Standard)",
        "description": "Standard KernelSU with KProbes - Best compatibility",
        "category": "kernelsu",
        "kernel_patch": True,
        "install_method": "kernel_patch",
        "repo": "https://github.com/tiann/KernelSU",
        "kernel_configs": [
            "CONFIG_KPROBES=y",
            "CONFIG_HAVE_KPROBES=y",
            "CONFIG_KPROBE_EVENTS=y",
            "CONFIG_MODULES=y",
            "CONFIG_OVERLAY_FS=y"
        ],
        "features": ["Kernel-level root", "Better hiding", "Module support", "App profiles"],
        "safetynet": "Excellent with proper setup",
        "play_integrity": "DEVICE integrity achievable",
        "difficulty": "medium",
        "recommended_for": "Users with custom kernel support",
        "patch_method": "kprobe"
    },
    "kernelsu_gki": {
        "name": "KernelSU GKI",
        "description": "KernelSU integrated directly into GKI kernel - No kprobes needed!",
        "category": "kernelsu",
        "kernel_patch": True,
        "install_method": "kernel_integration",
        "repo": "https://github.com/tiann/KernelSU",
        "kernel_configs": [
            "CONFIG_KSU=y",
            "CONFIG_MODULES=y",
            "CONFIG_OVERLAY_FS=y",
            "# KPROBES NOT REQUIRED"
        ],
        "features": ["Fully integrated", "Best performance", "Hardest to detect", "LTS support"],
        "safetynet": "Excellent",
        "play_integrity": "STRONG integrity possible",
        "difficulty": "hard",
        "recommended_for": "GKI 2.0 kernels (Android 12+), advanced users",
        "patch_method": "direct_integration",
        "gki_version": "2.0",
        "notes": "Integrates KernelSU source directly into kernel tree. Cleanest implementation."
    },
    "kernelsu_lkm": {
        "name": "KernelSU LKM (Loadable Kernel Module)",
        "description": "KernelSU as a loadable module - Most flexible",
        "category": "kernelsu",
        "kernel_patch": True,
        "install_method": "kernel_module",
        "repo": "https://github.com/tiann/KernelSU",
        "kernel_configs": [
            "CONFIG_MODULES=y",
            "CONFIG_MODULE_UNLOAD=y",
            "CONFIG_KPROBES=y"
        ],
        "features": ["Loadable/unloadable", "Easy updates", "Minimal kernel changes"],
        "safetynet": "Good",
        "play_integrity": "DEVICE integrity possible",
        "difficulty": "medium",
        "recommended_for": "Developers, testing environments",
        "patch_method": "lkm"
    },
    "kernelsu_wild": {
        "name": "Wild KernelSU",
        "description": "Unofficial KernelSU variant with relaxed kernel requirements",
        "category": "kernelsu",
        "kernel_patch": True,
        "install_method": "kernel_patch",
        "repo": "https://github.com/Ylarod/KernelSU",
        "kernel_configs": [
            "# Minimal requirements",
            "CONFIG_MODULES=y"
        ],
        "features": ["Works on older kernels", "Relaxed config checks", "Broader compatibility"],
        "safetynet": "Good",
        "play_integrity": "DEVICE integrity possible",
        "difficulty": "medium",
        "recommended_for": "Older devices, kernels without kprobe support",
        "patch_method": "alternative",
        "notes": "Less strict kernel version checks. Works on Android 5.0+ kernels."
    },
    "kernelsu_spoofed": {
        "name": "KernelSU (Spoofed + SUSFS)",
        "description": "KernelSU with SUSFS integration for maximum stealth",
        "category": "kernelsu",
        "kernel_patch": True,
        "install_method": "kernel_patch_advanced",
        "repo": "https://github.com/tiann/KernelSU",
        "susfs_repo": "https://github.com/sidex15/SUSFS4KSU",
        "kernel_configs": [
            "CONFIG_KPROBES=y",
            "CONFIG_HAVE_KPROBES=y",
            "CONFIG_KPROBE_EVENTS=y",
            "CONFIG_OVERLAY_FS=y",
            "# SUSFS specific configs"
        ],
        "features": [
            "SUSFS integration",
            "File system hiding",
            "Mount point spoofing",
            "Enhanced stealth",
            "Persistent spoofing"
        ],
        "safetynet": "Excellent",
        "play_integrity": "STRONG integrity achievable",
        "difficulty": "expert",
        "recommended_for": "Banking apps, enterprise security bypass",
        "patch_method": "kprobe_with_susfs",
        "additional_patches": ["SUSFS"],
        "notes": "SUSFS (Storage Umount/Suppress FS) hides root traces at filesystem level"
    },
    "kernelsu_next": {
        "name": "KernelSU Next",
        "description": "Community fork with experimental features",
        "category": "kernelsu",
        "kernel_patch": True,
        "install_method": "kernel_patch",
        "repo": "https://github.com/rifsxd/KernelSU-Next",
        "kernel_configs": [
            "CONFIG_KPROBES=y",
            "CONFIG_HAVE_KPROBES=y",
            "CONFIG_KPROBE_EVENTS=y"
        ],
        "features": ["Experimental features", "Community driven", "Faster updates"],
        "safetynet": "Good",
        "play_integrity": "DEVICE integrity possible",
        "difficulty": "medium",
        "recommended_for": "Testing, experimental features",
        "patch_method": "kprobe"
    },
    
    # ========== APATCH ==========
    "apatch": {
        "name": "APatch",
        "description": "Kernel patch manager - Alternative to KernelSU",
        "category": "apatch",
        "kernel_patch": True,
        "install_method": "kernel_patch",
        "repo": "https://github.com/bmax121/APatch",
        "kernel_configs": [
            "CONFIG_KALLSYMS=y",
            "CONFIG_KALLSYMS_ALL=y"
        ],
        "features": ["Kernel patching", "Module support", "Lightweight", "Easy updates"],
        "safetynet": "Good",
        "play_integrity": "DEVICE integrity possible",
        "difficulty": "medium",
        "recommended_for": "Users wanting KernelSU alternative",
        "patch_method": "apatch"
    },
    
    # ========== LEGACY ==========
    "supersu": {
        "name": "SuperSU",
        "description": "Legacy root solution (deprecated, not recommended)",
        "category": "legacy",
        "kernel_patch": False,
        "install_method": "system_install",
        "features": ["Old method", "No longer maintained"],
        "safetynet": "Fails",
        "play_integrity": "Fails",
        "difficulty": "easy",
        "recommended_for": "Old devices (Android 7 and below)",
        "deprecated": True
    }
}

# Advanced hiding/spoofing options
ROOT_HIDING_MODULES = {
    "shamiko": {
        "name": "Shamiko",
        "description": "Zygisk-based root hiding for Magisk Delta/Alpha",
        "compatible_with": ["magisk_delta", "magisk_alpha"],
        "repo": "https://github.com/LSPosed/LSPosed.github.io/releases",
        "features": ["Hide Magisk", "DenyList enhancement", "Zygisk hiding"],
        "effectiveness": "High",
        "setup_difficulty": "Easy"
    },
    "susfs": {
        "name": "SUSFS (Storage Umount Suppress FS)",
        "description": "Advanced filesystem-level hiding for KernelSU",
        "compatible_with": ["kernelsu_standard", "kernelsu_gki", "kernelsu_spoofed"],
        "repo": "https://github.com/sidex15/SUSFS4KSU",
        "features": [
            "Hide mount points",
            "Spoof /proc/mounts",
            "Hide overlayfs",
            "Persistent hiding"
        ],
        "effectiveness": "Very High",
        "setup_difficulty": "Expert",
        "kernel_patch_required": True
    },
    "zygisk_next": {
        "name": "Zygisk Next",
        "description": "Standalone Zygisk implementation",
        "compatible_with": ["kernelsu_standard", "kernelsu_gki", "apatch"],
        "repo": "https://github.com/Dr-TSNG/ZygiskNext",
        "features": ["Zygisk on KernelSU", "Module support", "LSPosed compatible"],
        "effectiveness": "High",
        "setup_difficulty": "Medium"
    },
    "tricky_store": {
        "name": "Tricky Store",
        "description": "Play Integrity bypass using genuine keybox",
        "compatible_with": ["magisk", "magisk_delta", "kernelsu_standard", "kernelsu_gki"],
        "repo": "https://github.com/5ec1cff/TrickyStore",
        "features": ["DEVICE/STRONG integrity", "Genuine keybox usage", "LSPosed integration"],
        "effectiveness": "Very High",
        "setup_difficulty": "Expert"
    },
    "lsposed": {
        "name": "LSPosed",
        "description": "Xposed framework for Zygisk",
        "compatible_with": ["magisk", "magisk_delta", "kernelsu_standard", "kernelsu_gki"],
        "repo": "https://github.com/LSPosed/LSPosed",
        "features": ["Module framework", "App hooking", "Behavior modification"],
        "effectiveness": "High",
        "setup_difficulty": "Medium"
    },
    "magisk_hide_props": {
        "name": "MagiskHide Props Config",
        "description": "Device fingerprint spoofing",
        "compatible_with": ["magisk", "magisk_delta"],
        "repo": "https://github.com/Magisk-Modules-Repo/MagiskHidePropsConf",
        "features": ["Spoof device fingerprint", "CTS profile", "SafetyNet bypass"],
        "effectiveness": "Medium",
        "setup_difficulty": "Easy"
    }
}

# Kernel patch methods
KERNEL_PATCH_METHODS = {
    "kprobe": {
        "name": "KProbes Method",
        "description": "Uses kernel kprobes to hook functions dynamically",
        "requirements": ["CONFIG_KPROBES=y", "CONFIG_KPROBE_EVENTS=y"],
        "pros": ["No source modification", "Easy to update", "Most common"],
        "cons": ["Slight performance overhead", "Requires kprobe support"],
        "difficulty": "Medium"
    },
    "direct_integration": {
        "name": "Direct Integration (GKI)",
        "description": "Integrates KernelSU source directly into kernel tree",
        "requirements": ["GKI 2.0 kernel", "Source code access"],
        "pros": ["Best performance", "Hardest to detect", "Most stable"],
        "cons": ["Requires kernel source", "Complex setup"],
        "difficulty": "Expert",
        "steps": [
            "1. Download KernelSU source",
            "2. Add to kernel/ksu directory",
            "3. Modify kernel Makefile/Kconfig",
            "4. Enable CONFIG_KSU=y",
            "5. Compile kernel with integrated KSU"
        ]
    },
    "lkm": {
        "name": "Loadable Kernel Module",
        "description": "Compile as separate .ko module",
        "requirements": ["CONFIG_MODULES=y", "CONFIG_MODULE_UNLOAD=y"],
        "pros": ["Easy updates", "Can be loaded/unloaded", "Minimal kernel changes"],
        "cons": ["Slightly less integrated", "Requires module loading support"],
        "difficulty": "Medium"
    },
    "alternative": {
        "name": "Alternative/Wild Method",
        "description": "Relaxed requirements for older kernels",
        "requirements": ["Minimal - just CONFIG_MODULES=y"],
        "pros": ["Works on old kernels", "Broad compatibility"],
        "cons": ["Less features", "Community support"],
        "difficulty": "Medium"
    },
    "kprobe_with_susfs": {
        "name": "KProbe + SUSFS Integration",
        "description": "Standard kprobe method with SUSFS patches applied",
        "requirements": [
            "CONFIG_KPROBES=y",
            "CONFIG_OVERLAY_FS=y",
            "SUSFS patches applied to kernel"
        ],
        "pros": ["Maximum stealth", "Filesystem-level hiding", "Best for banking apps"],
        "cons": ["Complex setup", "Requires kernel patching", "Maintenance overhead"],
        "difficulty": "Expert",
        "steps": [
            "1. Apply KernelSU patches",
            "2. Apply SUSFS patches to fs/ directory",
            "3. Enable required configs",
            "4. Compile kernel",
            "5. Flash KernelSU manager",
            "6. Configure SUSFS via manager"
        ]
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
    return {"available": False, "path": None, "can_install": binary_name in BINARY_SOURCES}

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
    """Get all available root solutions with detailed info"""
    # Organize by category
    organized = {
        "magisk": {},
        "kernelsu": {},
        "apatch": {},
        "legacy": {},
        "none": {}
    }
    
    for key, solution in ROOT_SOLUTIONS.items():
        category = solution.get("category", "none")
        organized[category][key] = solution
    
    return {
        "solutions": ROOT_SOLUTIONS,
        "organized": organized,
        "hiding_modules": ROOT_HIDING_MODULES,
        "patch_methods": KERNEL_PATCH_METHODS
    }

@api_router.get("/root/hiding-modules")
async def get_hiding_modules():
    """Get advanced hiding/spoofing modules"""
    return {"hiding_modules": ROOT_HIDING_MODULES}

@api_router.post("/root/integrate")
async def integrate_root_solution(request: dict):
    """Integrate root solution into kernel or ROM with advanced options"""
    project_id = request.get("project_id")
    project_type = request.get("project_type")  # kernel, android, os
    root_solution = request.get("root_solution", "magisk")
    hiding_modules = request.get("hiding_modules", [])  # List of hiding modules to include
    patch_method = request.get("patch_method")  # For kernel-based root
    
    if not project_id or not project_type:
        raise HTTPException(status_code=400, detail="project_id and project_type required")
    
    if root_solution not in ROOT_SOLUTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid root solution. Choose from: {list(ROOT_SOLUTIONS.keys())}")
    
    # Validate hiding modules
    for module in hiding_modules:
        if module not in ROOT_HIDING_MODULES:
            raise HTTPException(status_code=400, detail=f"Invalid hiding module: {module}")
        
        # Check compatibility
        module_info = ROOT_HIDING_MODULES[module]
        if root_solution not in module_info.get("compatible_with", []):
            raise HTTPException(
                status_code=400, 
                detail=f"{module_info['name']} is not compatible with {ROOT_SOLUTIONS[root_solution]['name']}"
            )
    
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
    
    solution_info = ROOT_SOLUTIONS[root_solution]
    
    # Generate integration instructions
    instructions = {
        "root_solution": root_solution,
        "hiding_modules": hiding_modules,
        "patch_method": patch_method,
        "steps": []
    }
    
    if solution_info.get("kernel_patch"):
        # Kernel-based root
        if patch_method and patch_method in KERNEL_PATCH_METHODS:
            method_info = KERNEL_PATCH_METHODS[patch_method]
            instructions["steps"].extend([
                f"Method: {method_info['name']}",
                f"Difficulty: {method_info['difficulty']}",
                "Required kernel configs:"
            ] + solution_info.get("kernel_configs", []))
            
            if "steps" in method_info:
                instructions["steps"].extend(method_info["steps"])
        
        # Add SUSFS steps if requested
        if "susfs" in hiding_modules:
            instructions["steps"].extend([
                "",
                "SUSFS Integration:",
                "1. Clone SUSFS repository",
                "2. Apply SUSFS patches to kernel fs/ directory",
                "3. Add SUSFS hooks to kernel",
                "4. Compile kernel with SUSFS support",
                "5. Configure SUSFS via KernelSU manager after flash"
            ])
    else:
        # Boot image based root
        instructions["steps"].extend([
            f"1. Flash {solution_info['name']} to boot partition",
            "2. Install manager app",
            "3. Grant root permissions as needed"
        ])
    
    # Add hiding module instructions
    for module in hiding_modules:
        module_info = ROOT_HIDING_MODULES[module]
        instructions["steps"].extend([
            "",
            f"{module_info['name']} Setup:",
            f"Repo: {module_info.get('repo', 'Check documentation')}",
            f"Effectiveness: {module_info.get('effectiveness', 'Unknown')}",
            f"Difficulty: {module_info.get('setup_difficulty', 'Unknown')}"
        ])
    
    # Update project
    await collection.update_one(
        {"id": project_id},
        {"$set": {
            "root_solution": root_solution,
            "root_integrated": True,
            "root_hiding_modules": hiding_modules,
            "root_patch_method": patch_method,
            "root_instructions": instructions,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "success": True,
        "message": f"{solution_info['name']} integration configured",
        "requires_kernel_patch": solution_info.get("kernel_patch", False),
        "install_method": solution_info.get("install_method", "boot_patch"),
        "patch_method": patch_method,
        "hiding_modules": [ROOT_HIDING_MODULES[m]["name"] for m in hiding_modules],
        "instructions": instructions,
        "safetynet_status": solution_info.get("safetynet", "Unknown"),
        "play_integrity_status": solution_info.get("play_integrity", "Unknown"),
        "difficulty": solution_info.get("difficulty", "Unknown")
    }

@api_router.get("/root/compare")
async def compare_root_solutions():
    """Compare all root solutions side-by-side"""
    comparison = []
    
    for key, solution in ROOT_SOLUTIONS.items():
        if key == "none":
            continue
        
        comparison.append({
            "id": key,
            "name": solution["name"],
            "category": solution.get("category", "unknown"),
            "kernel_patch": solution.get("kernel_patch", False),
            "safetynet": solution.get("safetynet", "Unknown"),
            "play_integrity": solution.get("play_integrity", "Unknown"),
            "difficulty": solution.get("difficulty", "Unknown"),
            "recommended_for": solution.get("recommended_for", ""),
            "features": solution.get("features", [])
        })
    
    return {"comparison": comparison}
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
                await websocket.send_json({"type": "response", "message": response})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)

# ======================= LOCAL APP COMPILATION =======================

@api_router.get("/compiler/platforms")
async def get_supported_platforms():
    """Get all supported compilation platforms"""
    return {
        "platforms": app_compiler.supported_platforms,
        "ai_providers": app_compiler.ai_providers
    }

@api_router.post("/compiler/compile")
async def compile_local_app(request: dict):
    """Compile the app for a specific platform with AI configuration"""
    platform_type = request.get("platform")
    ai_config = request.get("ai_config", {})
    
    if not platform_type:
        raise HTTPException(status_code=400, detail="platform required")
    
    result = await app_compiler.compile_app(platform_type, ai_config)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    
    return result

@api_router.get("/compiler/downloads/{package_name}")
async def download_compiled_app(package_name: str):
    """Download a compiled app package"""
    package_path = WORK_DIR / "app_exports" / f"{package_name}.zip"
    
    if not package_path.exists():
        raise HTTPException(status_code=404, detail="Package not found")
    
    return FileResponse(
        package_path,
        media_type="application/zip",
        filename=f"{package_name}.zip"
    )

# ======================= BUILD PRESETS & PREVIOUS BUILD ROUTES =======================

@api_router.get("/presets/{tool_type}")
async def get_build_presets(tool_type: str):
    """Get quick build presets for a specific tool"""
    presets = get_presets_for_tool(tool_type)
    return {"presets": presets, "tool_type": tool_type}

@api_router.post("/projects/clone")
async def clone_previous_build(request: dict):
    """Clone a previous build as a base for a new build"""
    source_project_id = request.get("source_project_id")
    project_type = request.get("project_type")
    new_name = request.get("new_name")
    preset_id = request.get("preset_id")  # Optional: apply preset on top
    
    if not source_project_id or not project_type:
        raise HTTPException(status_code=400, detail="source_project_id and project_type required")
    
    # Get source project
    collection_map = {
        "kernel": db.kernel_projects,
        "android": db.android_projects,
        "os": db.os_image_projects,
        "halium": db.halium_builds,
        "recovery": db.recovery_builds
    }
    
    collection = collection_map.get(project_type)
    if not collection:
        raise HTTPException(status_code=400, detail="Invalid project type")
    
    source_project = await collection.find_one({"id": source_project_id}, {"_id": 0})
    if not source_project:
        raise HTTPException(status_code=404, detail="Source project not found")
    
    # Clone project
    cloned_project = source_project.copy()
    cloned_project["id"] = str(uuid.uuid4())
    cloned_project["name"] = new_name or f"{source_project.get('name', 'project')}-clone"
    cloned_project["created_at"] = datetime.now(timezone.utc).isoformat()
    cloned_project["cloned_from"] = source_project_id
    cloned_project["build_status"] = "pending"
    cloned_project["output_files"] = []
    
    # Apply preset if requested
    if preset_id:
        preset_config = apply_preset_to_project(preset_id, project_type, cloned_project)
        cloned_project.update(preset_config)
    
    await collection.insert_one(cloned_project)
    
    return {
        "success": True,
        "cloned_project": cloned_project,
        "preset_applied": preset_id is not None
    }

@api_router.post("/projects/quick-build")
async def create_quick_build(request: dict):
    """Create a project with quick build preset"""
    tool_type = request.get("tool_type")
    preset_id = request.get("preset_id")
    device_info = request.get("device_info")
    base_project_id = request.get("base_project_id")  # Optional: use previous build as base
    
    if not tool_type or not preset_id:
        raise HTTPException(status_code=400, detail="tool_type and preset_id required")
    
    # Get preset
    presets = get_presets_for_tool(tool_type)
    preset = presets.get(preset_id)
    if not preset:
        raise HTTPException(status_code=400, detail="Invalid preset")
    
    # Load base project if specified
    base_config = {}
    if base_project_id:
        collection_map = {
            "kernel": db.kernel_projects,
            "android": db.android_projects,
            "os": db.os_image_projects,
            "halium": db.halium_builds,
            "recovery": db.recovery_builds
        }
        collection = collection_map.get(tool_type)
        if collection:
            base_project = await collection.find_one({"id": base_project_id}, {"_id": 0})
            if base_project:
                base_config = base_project
    
    # Apply preset
    config = apply_preset_to_project(preset_id, tool_type, base_config)
    
    # Create project
    device_codename = device_info.get("codename") or device_info.get("device") or "unknown"
    
    if tool_type == "kernel":
        project = KernelProject(
            name=f"kernel-{preset['name']}-{device_codename}",
            device_codename=device_codename,
            target_version=config.get("kernel_version"),
            architecture=device_info.get("architecture", "arm64"),
            build_status="ready",
            **{k: v for k, v in config.items() if k in ["configs", "governor", "scheduler", "priority"]}
        )
        doc = project.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.kernel_projects.insert_one(doc)
        return {"project": project, "preset": preset}
    
    elif tool_type == "os":
        project = OSImageProject(
            name=f"os-{preset['name']}-{device_codename}",
            device_codename=device_codename,
            distro=config.get("recommended_distro", "postmarketos"),
            distro_type="mobile",
            build_status="ready"
        )
        doc = project.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.os_image_projects.insert_one(doc)
        return {"project": project, "preset": preset}
    
    return {"error": "Project creation not implemented for this tool type yet"}

# ======================= AI BUILD ASSISTANT ROUTES =======================

@api_router.post("/ai/build-assistant")
async def chat_with_build_assistant(request: dict):
    """Chat with AI build assistant for any tool"""
    session_id = request.get("session_id")
    message = request.get("message")
    tool_type = request.get("tool_type", "kernel")  # kernel, os, android, recovery, halium
    context = request.get("context", {})
    
    if not session_id or not message:
        raise HTTPException(status_code=400, detail="session_id and message required")
    
    response = await ai_build_assistant.send_message(session_id, message, tool_type, context)
    
    return {"response": response}

@api_router.post("/ai/generate-kernel-config")
async def generate_kernel_config(request: dict):
    """Generate kernel configuration from natural language description"""
    description = request.get("description")
    device_info = request.get("device_info", {})
    
    if not description:
        raise HTTPException(status_code=400, detail="description required")
    
    config = await ai_build_assistant.generate_kernel_config(description, device_info)
    
    return {"config": config, "description": description}

@api_router.post("/ai/recommend-os")
async def recommend_os_config(request: dict):
    """Get OS recommendation from natural language description"""
    description = request.get("description")
    device_info = request.get("device_info", {})
    
    if not description:
        raise HTTPException(status_code=400, detail="description required")
    
    recommendation = await ai_build_assistant.generate_os_recommendation(description, device_info)
    
    return {"recommendation": recommendation, "description": description}

@api_router.get("/ai/capabilities")
async def get_ai_capabilities():
    """Get information about AI assistant capabilities for each tool"""
    return {
        "tools": {
            "kernel": {
                "name": "Kernel Forge AI",
                "capabilities": [
                    "Generate kernel configs from natural language",
                    "Optimize for performance/battery/features",
                    "Recommend kernel versions",
                    "Explain technical decisions"
                ],
                "example_queries": [
                    "I want maximum battery life",
                    "Build a gaming kernel",
                    "I need Docker support",
                    "Optimize for Ubuntu Touch"
                ]
            },
            "os": {
                "name": "OS Builder AI",
                "capabilities": [
                    "Recommend best distro for use case",
                    "Suggest package selections",
                    "Compare distros",
                    "Set realistic expectations"
                ],
                "example_queries": [
                    "I want a daily driver phone",
                    "Best distro for privacy",
                    "Linux for an old tablet",
                    "Something like Ubuntu but lighter"
                ]
            },
            "android": {
                "name": "Android ROM AI",
                "capabilities": [
                    "Answer quick questions during build",
                    "Compare ROM options",
                    "Recommend GApps/root solutions",
                    "Explain trade-offs"
                ],
                "example_queries": [
                    "Magisk or KernelSU for banking apps?",
                    "What's the difference between AOSP and LineageOS?",
                    "Which GApps package should I use?",
                    "Best ROM for privacy"
                ]
            },
            "recovery": {
                "name": "Recovery Builder AI",
                "capabilities": [
                    "Recommend best recovery for device",
                    "Compare recovery features",
                    "Root solution integration advice",
                    "Device-specific guidance"
                ],
                "example_queries": [
                    "TWRP or OrangeFox?",
                    "Most stable recovery",
                    "Recovery with best UI",
                    "Need root with recovery"
                ]
            },
            "halium": {
                "name": "Halium AI",
                "capabilities": [
                    "Version selection guidance",
                    "Compatibility checking",
                    "Set realistic expectations",
                    "Alternative approaches"
                ],
                "example_queries": [
                    "Can I run Linux on my device?",
                    "Which Halium version?",
                    "Will camera work?",
                    "Halium vs custom kernel"
                ]
            }
        }
    }

# ======================= AI PROVIDER MANAGEMENT =======================

@api_router.get("/ai-providers")
async def get_ai_providers():
    """Get all available AI providers"""
    return {
        "providers": ai_provider_manager.get_all_providers(),
        "default_provider": ai_provider_manager.default_provider
    }

@api_router.get("/ai-providers/{provider}/info")
async def get_provider_info(provider: str):
    """Get detailed information about a specific provider"""
    info = ai_provider_manager.get_provider_info(provider)
    if not info:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    is_ready, status_msg = ai_provider_manager.is_provider_ready(provider)
    
    return {
        **info,
        "is_ready": is_ready,
        "status_message": status_msg
    }

@api_router.post("/ai-providers/{provider}/set-credential")
async def set_provider_credential(provider: str, api_key: str):
    """Set API key for a provider"""
    success = ai_provider_manager.set_credential(provider, api_key)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return {"success": True, "message": f"Credential set for {provider}"}

@api_router.get("/ai-providers/{provider}/status")
async def check_provider_status(provider: str):
    """Check if a provider is ready to use"""
    is_ready, message = ai_provider_manager.is_provider_ready(provider)
    return {
        "provider": provider,
        "is_ready": is_ready,
        "message": message
    }

class AIMessageRequest(BaseModel):
    provider: str
    model: str
    message: str
    system_prompt: Optional[str] = None
    context: Optional[List[Dict]] = None

@api_router.post("/ai-providers/send-message")
async def send_ai_message(request: AIMessageRequest):
    """Send a message to any AI provider"""
    try:
        response = await ai_provider_manager.send_message(
            provider=request.provider,
            model=request.model,
            message=request.message,
            system_prompt=request.system_prompt,
            context=request.context
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ======================= DEVICE MANAGEMENT =======================

@api_router.get("/devices/connected")
async def get_connected_devices():
    """Get all connected Android devices"""
    devices = await device_manager.get_connected_devices()
    return {"devices": devices, "count": len(devices)}

@api_router.get("/devices/{serial}/details")
async def get_device_details(serial: str):
    """Get detailed information about a specific device"""
    device_info = await device_manager.get_device_info(serial)
    return device_info

@api_router.post("/devices/{serial}/reboot")
async def reboot_device(serial: str, mode: str = "system"):
    """Reboot device to different modes (system, recovery, bootloader)"""
    success = await device_manager.reboot_device(serial, mode)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reboot device")
    return {"success": True, "message": f"Device rebooting to {mode}"}

class FlashImageRequest(BaseModel):
    partition: str
    image_path: str

@api_router.post("/devices/{serial}/flash")
async def flash_image(serial: str, request: FlashImageRequest):
    """Flash an image to a device partition"""
    success, message = await device_manager.flash_image(
        serial, request.partition, request.image_path
    )
    if not success:
        raise HTTPException(status_code=500, detail=message)
    return {"success": True, "message": message}

@api_router.post("/devices/{serial}/install-apk")
async def install_apk(serial: str, apk_path: str):
    """Install an APK on the device"""
    success, message = await device_manager.install_apk(serial, apk_path)
    if not success:
        raise HTTPException(status_code=500, detail=message)
    return {"success": True, "message": message}

# ======================= BUILD HISTORY & FORK MANAGEMENT =======================

@api_router.get("/builds/history")
async def get_build_history(
    build_type: Optional[str] = None,
    device_codename: Optional[str] = None,
    limit: int = 50
):
    """Get build history"""
    builds = await build_history.get_builds_by_type(build_type, device_codename, limit)
    return {"builds": builds, "count": len(builds)}

@api_router.get("/builds/{build_id}")
async def get_build_details(build_id: str):
    """Get details of a specific build"""
    build = await build_history.get_build(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return build

@api_router.get("/builds/{build_type}/successful")
async def get_successful_builds(
    build_type: str,
    device_codename: Optional[str] = None,
    limit: int = 20
):
    """Get successful builds for forking"""
    builds = await build_history.get_successful_builds(build_type, device_codename, limit)
    return {"builds": builds, "count": len(builds)}

class ForkBuildRequest(BaseModel):
    modifications: Optional[Dict] = None

@api_router.post("/builds/{build_id}/fork")
async def fork_build(build_id: str, request: ForkBuildRequest):
    """Fork an existing build"""
    forked = await build_history.fork_build(build_id, request.modifications)
    if not forked:
        raise HTTPException(status_code=404, detail="Source build not found")
    return forked

@api_router.get("/builds/{build_id_1}/compare/{build_id_2}")
async def compare_builds(build_id_1: str, build_id_2: str):
    """Compare two builds"""
    comparison = await build_history.compare_builds(build_id_1, build_id_2)
    return comparison

class SaveBuildRequest(BaseModel):
    name: str
    type: str
    device_codename: Optional[str] = None
    configuration: Dict
    status: str = "pending"
    description: Optional[str] = None

@api_router.post("/builds/save")
async def save_build(request: SaveBuildRequest):
    """Save a new build to history"""
    build_id = await build_history.save_build(request.dict())
    return {"build_id": build_id, "message": "Build saved successfully"}

class UpdateBuildStatusRequest(BaseModel):
    status: str
    additional_data: Optional[Dict] = None

@api_router.patch("/builds/{build_id}/status")
async def update_build_status(build_id: str, request: UpdateBuildStatusRequest):
    """Update build status"""
    success = await build_history.update_build_status(
        build_id, request.status, request.additional_data
    )
    if not success:
        raise HTTPException(status_code=404, detail="Build not found")
    return {"success": True, "message": "Build status updated"}

@api_router.delete("/builds/{build_id}")
async def delete_build(build_id: str):
    """Delete a build from history"""
    success = await build_history.delete_build(build_id)
    if not success:
        raise HTTPException(status_code=404, detail="Build not found")
    return {"success": True, "message": "Build deleted"}

@api_router.get("/builds/search")
async def search_builds(
    query: str,
    build_type: Optional[str] = None,
    limit: int = 50
):
    """Search builds"""
    builds = await build_history.search_builds(query, build_type, limit)
    return {"builds": builds, "count": len(builds)}

# ======================= BUILD TEMPLATES =======================

class SaveTemplateRequest(BaseModel):
    build_id: str
    name: str
    description: str
    is_public: bool = False

@api_router.post("/templates/save")
async def save_build_template(request: SaveTemplateRequest):
    """Save a build as a reusable template"""
    template_id = await build_history.save_as_template(
        request.build_id,
        request.name,
        request.description,
        request.is_public
    )
    if not template_id:
        raise HTTPException(status_code=404, detail="Source build not found")
    return {"template_id": template_id, "message": "Template saved successfully"}

@api_router.get("/templates")
async def get_templates(
    build_type: Optional[str] = None,
    public_only: bool = False
):
    """Get available build templates"""
    templates = await build_history.get_templates(build_type, public_only)
    return {"templates": templates, "count": len(templates)}

@api_router.post("/templates/{template_id}/use")
async def use_template(template_id: str):
    """Use a template for a new build"""
    template = await build_history.use_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

# ======================= BUILD STATISTICS =======================

@api_router.get("/builds/stats")
async def get_build_statistics(build_type: Optional[str] = None):
    """Get build statistics"""
    stats = await build_history.get_build_statistics(build_type)
    return stats

# ======================= BUILD PRESETS =======================

@api_router.get("/presets/{tool_type}")
async def get_build_presets(tool_type: str):
    """Get presets for a specific tool type"""
    presets = get_presets_for_tool(tool_type)
    return {"tool_type": tool_type, "presets": presets}

class ApplyPresetRequest(BaseModel):
    preset_id: str
    base_config: Optional[Dict] = None

@api_router.post("/presets/{tool_type}/apply")
async def apply_build_preset(tool_type: str, request: ApplyPresetRequest):
    """Apply a preset to a configuration"""
    config = apply_preset_to_project(request.preset_id, tool_type, request.base_config)
    return {"configuration": config}

# ======================= FACTORY IMAGE MANAGEMENT =======================

@api_router.get("/factory-images/manufacturers")
async def get_manufacturer_sources():
    """Get list of known manufacturer image sources"""
    sources = factory_image_manager.get_manufacturer_sources()
    return {"manufacturers": sources}

class FactoryImageUploadRequest(BaseModel):
    file_path: str
    device_codename: str
    metadata: Optional[Dict] = None

@api_router.post("/factory-images/upload")
async def upload_factory_image(request: FactoryImageUploadRequest):
    """Upload a factory image file"""
    try:
        result = await factory_image_manager.upload_factory_image(
            request.file_path,
            request.device_codename,
            request.metadata
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class FactoryImageDownloadRequest(BaseModel):
    url: str
    device_codename: str
    manufacturer: Optional[str] = None

@api_router.post("/factory-images/download")
async def download_factory_image(request: FactoryImageDownloadRequest):
    """Download factory image from URL"""
    try:
        result = await factory_image_manager.download_factory_image(
            request.url,
            request.device_codename,
            request.manufacturer
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AutoDetectImagesRequest(BaseModel):
    device_info: Dict

@api_router.post("/factory-images/auto-detect")
async def auto_detect_and_download_images(request: AutoDetectImagesRequest):
    """Auto-detect device and download factory images"""
    result = await factory_image_manager.auto_detect_and_download(request.device_info)
    return result

@api_router.get("/factory-images/uploaded")
async def get_uploaded_images():
    """Get all uploaded factory images"""
    images = factory_image_manager.get_uploaded_images()
    return {"images": images}

@api_router.post("/factory-images/{device_codename}/extract")
async def extract_factory_image(device_codename: str):
    """Extract and analyze factory image"""
    try:
        result = await factory_image_manager.extract_factory_image(device_codename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/factory-images/{device_codename}/extracted")
async def get_extracted_data(device_codename: str):
    """Get extracted factory image data"""
    data = factory_image_manager.get_extracted_data(device_codename)
    if not data:
        raise HTTPException(status_code=404, detail="No extracted data found")
    return data

class ExtractBootImageRequest(BaseModel):
    boot_image_path: str

@api_router.post("/factory-images/extract-boot")
async def extract_boot_image_components(request: ExtractBootImageRequest):
    """Extract kernel, ramdisk, and device tree from boot.img"""
    try:
        components = await factory_image_manager.extract_boot_image_components(
            request.boot_image_path
        )
        return components
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ExtractKernelConfigRequest(BaseModel):
    kernel_image_path: str

@api_router.post("/factory-images/extract-kernel-config")
async def extract_kernel_config(request: ExtractKernelConfigRequest):
    """Extract kernel configuration from kernel image"""
    try:
        config = await factory_image_manager.extract_kernel_config(
            request.kernel_image_path
        )
        if config:
            return {"config": config}
        else:
            return {"error": "Failed to extract kernel config"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ======================= GITHUB INTEGRATION =======================

class GitHubTokenRequest(BaseModel):
    user_id: str
    github_token: str

@api_router.post("/github/set-token")
async def set_github_token(request: GitHubTokenRequest):
    """Set GitHub personal access token for a user"""
    github_integration.set_user_token(request.user_id, request.github_token)
    return {"success": True, "message": "GitHub token configured"}

class CreateRepoRequest(BaseModel):
    user_id: str
    repo_name: str
    description: str
    is_private: bool = False

@api_router.post("/github/create-repo")
async def create_github_repository(request: CreateRepoRequest):
    """Create a new GitHub repository for storing recipes"""
    result = await github_integration.create_repository(
        request.user_id,
        request.repo_name,
        request.description,
        request.is_private
    )
    return result

class SaveRecipeToGitHubRequest(BaseModel):
    user_id: str
    repo_owner: str
    repo_name: str
    recipe_name: str
    recipe_data: Dict[str, Any]
    branch: str = "main"

@api_router.post("/github/save-recipe")
async def save_recipe_to_github(request: SaveRecipeToGitHubRequest):
    """Save a build recipe to GitHub repository"""
    result = await github_integration.save_recipe_to_github(
        request.user_id,
        request.repo_owner,
        request.repo_name,
        request.recipe_name,
        request.recipe_data,
        request.branch
    )
    return result

@api_router.get("/github/load-recipe")
async def load_recipe_from_github(github_url: str, user_id: Optional[str] = None):
    """Load a build recipe from GitHub URL"""
    recipe = await github_integration.load_recipe_from_github(github_url, user_id)
    return recipe

@api_router.get("/github/search-recipes")
async def search_community_recipes(
    query: str,
    build_type: Optional[str] = None,
    limit: int = 30
):
    """Search for community recipes on GitHub"""
    recipes = await github_integration.search_community_recipes(query, build_type, limit)
    return {"recipes": recipes, "count": len(recipes)}

class ForkRepoRequest(BaseModel):
    user_id: str
    repo_owner: str
    repo_name: str

@api_router.post("/github/fork-repo")
async def fork_recipe_repository(request: ForkRepoRequest):
    """Fork a recipe repository to user's GitHub account"""
    result = await github_integration.fork_recipe_repository(
        request.user_id,
        request.repo_owner,
        request.repo_name
    )
    return result

@api_router.get("/github/user-repos")
async def get_user_repositories(user_id: str, recipe_repos_only: bool = True):
    """Get user's GitHub repositories"""
    repos = await github_integration.get_user_repositories(user_id, recipe_repos_only)
    return {"repositories": repos, "count": len(repos)}

@api_router.get("/github/list-recipes")
async def list_recipes_in_repository(
    repo_owner: str,
    repo_name: str,
    user_id: Optional[str] = None,
    branch: str = "main"
):
    """List all recipes in a GitHub repository"""
    recipes = await github_integration.list_recipes_in_repository(
        repo_owner,
        repo_name,
        user_id,
        branch
    )
    return {"recipes": recipes, "count": len(recipes)}

# ======================= APP SETUP =======================

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount the API router
app.include_router(api_router)

@app.get("/")
async def root():
    return {
        "app": "Linux Device Forge",
        "version": "3.0.0",
        "status": "running",
        "features": ["Kernel Forge", "OS Builder", "Android ROM Builder", "Halium", "Recovery Builder", "Binary Management"]
    }

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
