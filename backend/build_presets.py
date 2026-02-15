"""
Build Presets - Pre-configured build profiles for quick building
"""
from typing import Dict, List, Any


# ==================== KERNEL BUILD PRESETS ====================

KERNEL_PRESETS = {
    "battery_saver": {
        "name": "🔋 Battery Saver",
        "description": "Maximum battery life with conservative settings",
        "priority": "battery",
        "kernel_version": "5.15",
        "governor": "conservative",
        "scheduler": "deadline",
        "configs": [
            "CONFIG_CPU_FREQ_DEFAULT_GOV_CONSERVATIVE=y",
            "CONFIG_PM_WAKELOCKS=y",
            "CONFIG_SUSPEND=y",
            "CONFIG_CPU_IDLE=y",
            "CONFIG_PM_AUTOSLEEP=y",
            "CONFIG_PM_WAKELOCKS_LIMIT=y",
            "# Disable power-hungry features",
            "CONFIG_NO_HZ_FULL=n",
            "CONFIG_CPU_BOOST=n"
        ],
        "expected_improvement": "+30-40% battery life",
        "trade_offs": "Slightly slower performance"
    },
    "performance": {
        "name": "⚡ Extreme Performance",
        "description": "Maximum speed with overclocking support",
        "priority": "performance",
        "kernel_version": "6.6",
        "governor": "performance",
        "scheduler": "kyber",
        "configs": [
            "CONFIG_CPU_FREQ_DEFAULT_GOV_PERFORMANCE=y",
            "CONFIG_CPU_OVERCLOCK=y",
            "CONFIG_NO_HZ_FULL=y",
            "CONFIG_PREEMPT=y",
            "CONFIG_HIGH_RES_TIMERS=y",
            "CONFIG_FAIR_GROUP_SCHED=y",
            "CONFIG_SCHED_AUTOGROUP=y",
            "CONFIG_CLEANCACHE=y",
            "CONFIG_FRONTSWAP=y"
        ],
        "expected_improvement": "+20-30% raw performance",
        "trade_offs": "Higher power consumption, heat generation"
    },
    "gaming": {
        "name": "🎮 Gaming Optimized",
        "description": "Low latency, high FPS, GPU optimizations",
        "priority": "gaming",
        "kernel_version": "6.1",
        "governor": "schedutil",
        "scheduler": "deadline",
        "configs": [
            "CONFIG_PREEMPT_VOLUNTARY=y",
            "CONFIG_HIGH_RES_TIMERS=y",
            "CONFIG_NO_HZ=y",
            "CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y",
            "CONFIG_SCHED_TUNE=y",
            "CONFIG_CPU_INPUT_BOOST=y",
            "# GPU optimizations",
            "CONFIG_QCOM_KGSL=y",
            "CONFIG_DRM=y"
        ],
        "expected_improvement": "Smoother gameplay, reduced latency",
        "trade_offs": "Moderate battery drain"
    },
    "balanced": {
        "name": "⚖️ Balanced",
        "description": "Good mix of performance and efficiency",
        "priority": "balanced",
        "kernel_version": "5.15",
        "governor": "schedutil",
        "scheduler": "mq-deadline",
        "configs": [
            "CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y",
            "CONFIG_PM=y",
            "CONFIG_SUSPEND=y",
            "CONFIG_CPU_IDLE=y",
            "CONFIG_SCHED_MC=y",
            "CONFIG_FAIR_GROUP_SCHED=y"
        ],
        "expected_improvement": "Best of both worlds",
        "trade_offs": "None - safe default"
    },
    "linux_distro": {
        "name": "🐧 Linux Distro Ready",
        "description": "All configs for running full Linux distros",
        "priority": "linux_compatibility",
        "kernel_version": "5.15",
        "governor": "schedutil",
        "scheduler": "mq-deadline",
        "configs": [
            "CONFIG_NAMESPACES=y",
            "CONFIG_NET_NS=y",
            "CONFIG_PID_NS=y",
            "CONFIG_IPC_NS=y",
            "CONFIG_UTS_NS=y",
            "CONFIG_USER_NS=y",
            "CONFIG_CGROUPS=y",
            "CONFIG_OVERLAY_FS=y",
            "CONFIG_FUSE_FS=y",
            "CONFIG_EXT4_FS=y",
            "CONFIG_TMPFS=y",
            "CONFIG_PROC_FS=y",
            "CONFIG_SYSFS=y",
            "CONFIG_DEVTMPFS=y"
        ],
        "expected_improvement": "Full Linux compatibility",
        "trade_offs": "Slightly larger kernel"
    },
    "security_hardened": {
        "name": "🔒 Security Hardened",
        "description": "Maximum security with SELinux, AppArmor",
        "priority": "security",
        "kernel_version": "6.6",
        "governor": "schedutil",
        "scheduler": "mq-deadline",
        "configs": [
            "CONFIG_SECURITY=y",
            "CONFIG_SECURITY_SELINUX=y",
            "CONFIG_SECURITY_APPARMOR=y",
            "CONFIG_SECCOMP=y",
            "CONFIG_SECCOMP_FILTER=y",
            "CONFIG_AUDIT=y",
            "CONFIG_HARDENED_USERCOPY=y",
            "CONFIG_FORTIFY_SOURCE=y",
            "CONFIG_PAGE_TABLE_ISOLATION=y"
        ],
        "expected_improvement": "Enterprise-grade security",
        "trade_offs": "Minimal performance impact"
    },
    "kernelsu_ready": {
        "name": "🔓 KernelSU Ready",
        "description": "Pre-configured for KernelSU integration",
        "priority": "root_support",
        "kernel_version": "5.15",
        "governor": "schedutil",
        "scheduler": "mq-deadline",
        "configs": [
            "CONFIG_KPROBES=y",
            "CONFIG_HAVE_KPROBES=y",
            "CONFIG_KPROBE_EVENTS=y",
            "CONFIG_MODULES=y",
            "CONFIG_MODULE_UNLOAD=y",
            "CONFIG_OVERLAY_FS=y"
        ],
        "expected_improvement": "Ready for kernel-level root",
        "trade_offs": "None"
    },
    "docker_ready": {
        "name": "🐋 Docker Ready",
        "description": "Full containerization support",
        "priority": "containers",
        "kernel_version": "5.15",
        "governor": "schedutil",
        "scheduler": "mq-deadline",
        "configs": [
            "CONFIG_NAMESPACES=y",
            "CONFIG_NET_NS=y",
            "CONFIG_PID_NS=y",
            "CONFIG_IPC_NS=y",
            "CONFIG_UTS_NS=y",
            "CONFIG_USER_NS=y",
            "CONFIG_CGROUPS=y",
            "CONFIG_CGROUP_CPUACCT=y",
            "CONFIG_CGROUP_DEVICE=y",
            "CONFIG_CGROUP_FREEZER=y",
            "CONFIG_CGROUP_SCHED=y",
            "CONFIG_MEMCG=y",
            "CONFIG_VETH=y",
            "CONFIG_BRIDGE=y",
            "CONFIG_NETFILTER_XT_MATCH_ADDRTYPE=y",
            "CONFIG_NETFILTER_XT_MATCH_CONNTRACK=y",
            "CONFIG_OVERLAY_FS=y"
        ],
        "expected_improvement": "Full Docker/Podman support",
        "trade_offs": "Slightly larger kernel"
    }
}

# ==================== OS BUILD PRESETS ====================

OS_PRESETS = {
    "daily_driver": {
        "name": "📱 Daily Driver",
        "description": "Reliable phone experience with essential apps",
        "recommended_distro": "ubuntu-touch",
        "packages": ["telegram-desktop", "dekko2", "morph-browser", "camera-app"],
        "de": "Unity8",
        "priority": "stability",
        "expected_experience": "Full phone functionality"
    },
    "privacy_focused": {
        "name": "🔒 Privacy Focused",
        "description": "Maximum privacy with minimal tracking",
        "recommended_distro": "postmarketos",
        "packages": ["firefox", "signal-cli", "firejail", "tor"],
        "de": "Phosh",
        "priority": "privacy",
        "expected_experience": "Private, secure, minimal telemetry"
    },
    "lightweight": {
        "name": "🪶 Lightweight",
        "description": "Minimal resource usage for older devices",
        "recommended_distro": "alpine",
        "packages": ["busybox", "dropbear", "links"],
        "de": "None (terminal only)",
        "priority": "minimal",
        "expected_experience": "Fast on old hardware, terminal-based"
    },
    "desktop_experience": {
        "name": "💻 Desktop Experience",
        "description": "Full desktop with convergence for tablets",
        "recommended_distro": "plasma-mobile",
        "packages": ["kde-applications", "firefox", "libreoffice", "gimp"],
        "de": "Plasma Mobile",
        "priority": "features",
        "expected_experience": "Desktop-class apps and convergence"
    },
    "developer": {
        "name": "👨‍💻 Developer",
        "description": "Development tools, compilers, containers",
        "recommended_distro": "debian",
        "packages": ["build-essential", "git", "vim", "docker.io", "python3", "nodejs"],
        "de": "Phosh",
        "priority": "development",
        "expected_experience": "Full dev environment on mobile"
    },
    "server": {
        "name": "🖥️ Server/Headless",
        "description": "No GUI, optimized for server workloads",
        "recommended_distro": "debian",
        "packages": ["openssh-server", "nginx", "postgresql", "docker.io"],
        "de": "None",
        "priority": "server",
        "expected_experience": "Lightweight server, SSH access"
    }
}

# ==================== ANDROID ROM PRESETS ====================

ANDROID_ROM_PRESETS = {
    "stock_like": {
        "name": "📱 Stock Android",
        "description": "Clean AOSP experience, minimal modifications",
        "base_rom": "aosp",
        "gapps": "pico",
        "root": "none",
        "kernel": "stock",
        "ui": "stock",
        "priority": "clean"
    },
    "privacy_focused": {
        "name": "🔒 Privacy Focused",
        "description": "No Google, no tracking, maximum privacy",
        "base_rom": "lineageos",
        "gapps": "none",
        "root": "magisk",
        "kernel": "custom_optimized",
        "ui": "minimal",
        "priority": "privacy"
    },
    "feature_rich": {
        "name": "✨ Feature Rich",
        "description": "All the bells and whistles, heavy customization",
        "base_rom": "crdroid",
        "gapps": "full",
        "root": "magisk_delta",
        "kernel": "performance_focused",
        "ui": "feature_rich",
        "priority": "features"
    },
    "banking_compatible": {
        "name": "🏦 Banking Compatible",
        "description": "Passes SafetyNet/Play Integrity for banking apps",
        "base_rom": "pixelexperience",
        "gapps": "stock",
        "root": "kernelsu_spoofed",
        "kernel": "custom_optimized",
        "ui": "stock",
        "priority": "compatibility",
        "hiding_modules": ["susfs", "tricky_store"]
    },
    "gaming": {
        "name": "🎮 Gaming",
        "description": "Maximum FPS, low latency, GPU optimizations",
        "base_rom": "evolutionx",
        "gapps": "mini",
        "root": "magisk",
        "kernel": "performance_focused",
        "ui": "minimal",
        "priority": "gaming"
    },
    "minimal": {
        "name": "🪶 Minimal",
        "description": "Lightweight, fast, bare essentials",
        "base_rom": "lineageos",
        "gapps": "none",
        "root": "none",
        "kernel": "stock",
        "ui": "minimal",
        "priority": "minimal"
    }
}

# ==================== RECOVERY PRESETS ====================

RECOVERY_PRESETS = {
    "stable": {
        "name": "🛡️ Most Stable",
        "description": "Official TWRP, proven and reliable",
        "recovery_type": "twrp",
        "root": "magisk",
        "priority": "stability"
    },
    "feature_rich": {
        "name": "✨ Feature Rich",
        "description": "OrangeFox with all the extras",
        "recovery_type": "orangefox",
        "root": "magisk_delta",
        "priority": "features"
    },
    "modern_ui": {
        "name": "🎨 Modern UI",
        "description": "Beautiful interface with themes",
        "recovery_type": "pitchblack",
        "root": "kernelsu_standard",
        "priority": "aesthetics"
    },
    "advanced": {
        "name": "🔧 Advanced",
        "description": "SHRP with unique tools and features",
        "recovery_type": "shrp",
        "root": "kernelsu_gki",
        "priority": "advanced"
    }
}

# ==================== HALIUM PRESETS ====================

HALIUM_PRESETS = {
    "stable": {
        "name": "🛡️ Stable (Halium 10)",
        "description": "Most tested, widest device support",
        "halium_version": "halium-10.0",
        "target_distro": "ubuntu-touch",
        "priority": "stability"
    },
    "latest": {
        "name": "🚀 Latest (Halium 11)",
        "description": "Newest features, modern Android base",
        "halium_version": "halium-11.0",
        "target_distro": "droidian",
        "priority": "features"
    },
    "legacy": {
        "name": "📱 Legacy Devices",
        "description": "For older Android 7.1 devices",
        "halium_version": "halium-7.1",
        "target_distro": "ubuntu-touch",
        "priority": "compatibility"
    }
}


def get_presets_for_tool(tool_type: str) -> Dict[str, Any]:
    """Get presets for a specific tool type"""
    presets_map = {
        "kernel": KERNEL_PRESETS,
        "os": OS_PRESETS,
        "android": ANDROID_ROM_PRESETS,
        "recovery": RECOVERY_PRESETS,
        "halium": HALIUM_PRESETS
    }
    return presets_map.get(tool_type, {})


def apply_preset_to_project(preset_id: str, tool_type: str, base_config: Dict = None) -> Dict[str, Any]:
    """
    Apply a preset to a project configuration
    Can optionally merge with base_config from a previous build
    """
    presets = get_presets_for_tool(tool_type)
    preset = presets.get(preset_id)
    
    if not preset:
        return base_config or {}
    
    # Start with base config if provided
    config = base_config.copy() if base_config else {}
    
    # Apply preset on top
    config.update({
        "preset_used": preset_id,
        "preset_name": preset["name"],
        **preset
    })
    
    return config
