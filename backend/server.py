from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'halium_builder')]

# Claude AI integration
from emergentintegrations.llm.chat import LlmChat, UserMessage

# Create the main app
app = FastAPI(title="Halium Build Assistant API")

# Create API router
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ======================= CONSTANTS =======================

HALIUM_VERSIONS = {
    "halium-7.1": {"android": "7.1", "lineage": "14.1", "branch": "halium-7.1"},
    "halium-9.0": {"android": "9.0", "lineage": "16.0", "branch": "halium-9.0"},
    "halium-10.0": {"android": "10", "lineage": "17.1", "branch": "halium-10.0"},
    "halium-11.0": {"android": "11", "lineage": "18.1", "branch": "halium-11.0"},
}

HALIUM_MANIFEST_URL = "https://github.com/halium/android.git"
LINEAGE_WIKI_API = "https://wiki.lineageos.org/api"
HALIUM_DEVICES_URL = "https://raw.githubusercontent.com/halium/projectmanagement/master/devices.json"

BUILD_STEPS = [
    {"id": 1, "name": "Environment Setup", "description": "Install build dependencies and configure environment", "commands": [
        "sudo apt-get update",
        "sudo apt-get install -y git-core gnupg flex bison build-essential zip curl zlib1g-dev libc6-dev-i386 libncurses5 lib32ncurses5-dev x11proto-core-dev libx11-dev lib32z1-dev libgl1-mesa-dev libxml2-utils xsltproc unzip fontconfig python3 python-is-python3 repo"
    ]},
    {"id": 2, "name": "Repo Init", "description": "Initialize Halium manifest repository", "commands": []},
    {"id": 3, "name": "Device Tree Setup", "description": "Set up device-specific repositories", "commands": []},
    {"id": 4, "name": "Repo Sync", "description": "Download all source code", "commands": ["repo sync -c -j$(nproc) --force-sync --no-tags --no-clone-bundle"]},
    {"id": 5, "name": "Kernel Config", "description": "Configure kernel for Halium compatibility", "commands": []},
    {"id": 6, "name": "Extract Vendor", "description": "Extract vendor proprietary files", "commands": []},
    {"id": 7, "name": "Build System", "description": "Compile the Halium system image", "commands": ["source build/envsetup.sh", "breakfast {device}", "mka halium-boot", "mka systemimage"]},
    {"id": 8, "name": "Generate Rootfs", "description": "Create the Linux root filesystem", "commands": []},
    {"id": 9, "name": "Flash & Test", "description": "Flash images to device and verify boot", "commands": []}
]

KERNEL_CONFIG_REQUIREMENTS = [
    {"config": "CONFIG_DEVTMPFS", "required": True, "description": "Device filesystem support"},
    {"config": "CONFIG_DEVTMPFS_MOUNT", "required": True, "description": "Automount devtmpfs"},
    {"config": "CONFIG_TMPFS", "required": True, "description": "Temporary filesystem support"},
    {"config": "CONFIG_UNIX", "required": True, "description": "Unix domain sockets"},
    {"config": "CONFIG_SYSVIPC", "required": True, "description": "System V IPC"},
    {"config": "CONFIG_PROC_FS", "required": True, "description": "Proc filesystem"},
    {"config": "CONFIG_SYSFS", "required": True, "description": "Sysfs filesystem"},
    {"config": "CONFIG_CGROUPS", "required": True, "description": "Control groups"},
    {"config": "CONFIG_NAMESPACES", "required": True, "description": "Namespace support"},
    {"config": "CONFIG_NET_NS", "required": True, "description": "Network namespaces"},
    {"config": "CONFIG_PID_NS", "required": True, "description": "PID namespaces"},
    {"config": "CONFIG_IPC_NS", "required": True, "description": "IPC namespaces"},
    {"config": "CONFIG_UTS_NS", "required": True, "description": "UTS namespaces"},
    {"config": "CONFIG_USER_NS", "required": False, "description": "User namespaces (recommended)"},
    {"config": "CONFIG_FHANDLE", "required": True, "description": "File handle syscalls"},
    {"config": "CONFIG_AUTOFS_FS", "required": False, "description": "Autofs support"},
    {"config": "CONFIG_OVERLAY_FS", "required": True, "description": "Overlay filesystem"},
    {"config": "CONFIG_ANDROID_BINDER_IPC", "required": True, "description": "Android Binder IPC"},
    {"config": "CONFIG_ANDROID_BINDERFS", "required": False, "description": "Binder filesystem"},
    {"config": "CONFIG_ASHMEM", "required": True, "description": "Anonymous shared memory"},
    {"config": "CONFIG_ANDROID_LOW_MEMORY_KILLER", "required": False, "description": "LMK (legacy)"},
    {"config": "CONFIG_MEMCG", "required": True, "description": "Memory control groups"},
    {"config": "CONFIG_VETH", "required": True, "description": "Virtual ethernet"},
    {"config": "CONFIG_BRIDGE", "required": False, "description": "Network bridging"},
    {"config": "CONFIG_NF_NAT", "required": True, "description": "NAT support"},
    {"config": "CONFIG_NETFILTER_XT_MATCH_ADDRTYPE", "required": True, "description": "Netfilter address type"},
    {"config": "CONFIG_NETFILTER_XT_MATCH_CONNTRACK", "required": True, "description": "Netfilter conntrack"},
    {"config": "CONFIG_NETFILTER_XT_MATCH_IPVS", "required": False, "description": "IPVS match"},
    {"config": "CONFIG_POSIX_MQUEUE", "required": True, "description": "POSIX message queues"},
]

# ======================= MODELS =======================

class DeviceInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    serial: str
    model: Optional[str] = None
    device: Optional[str] = None
    product: Optional[str] = None
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    android_version: Optional[str] = None
    sdk_version: Optional[str] = None
    kernel_version: Optional[str] = None
    build_fingerprint: Optional[str] = None
    cpu_abi: Optional[str] = None
    hardware: Optional[str] = None
    platform: Optional[str] = None
    soc: Optional[str] = None
    partitions: Optional[Dict[str, Any]] = None
    halium_compatible: Optional[bool] = None
    halium_version: Optional[str] = None
    lineage_support: Optional[Dict[str, Any]] = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BuildSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_serial: str
    device_codename: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None
    status: str = "pending"
    current_step: int = 0
    current_step_name: Optional[str] = None
    progress: int = 0
    halium_version: str = "halium-11.0"
    build_type: str = "lineage"
    build_dir: Optional[str] = None
    logs: List[Dict[str, Any]] = []
    errors: List[str] = []
    artifacts: List[str] = []
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str
    content: str
    command: Optional[str] = None
    output: Optional[str] = None
    extracted_commands: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DeviceTreeInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_serial: str
    codename: str
    dtbo_path: Optional[str] = None
    boot_img_path: Optional[str] = None
    dtb_extracted: bool = False
    dts_decompiled: bool = False
    dts_content: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FirmwareInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    device_codename: str
    vendor: str
    version: str
    android_version: str
    download_url: Optional[str] = None
    lineage_supported: bool = False
    halium_compatible: bool = False
    notes: Optional[str] = None

class KernelConfigAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    device_serial: str
    codename: str
    kernel_version: str
    config_present: bool = False
    requirements_met: List[Dict[str, Any]] = []
    requirements_missing: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    halium_ready: bool = False

# Request Models
class CommandRequest(BaseModel):
    command: str
    session_id: Optional[str] = None
    working_dir: Optional[str] = None
    timeout: int = 120

class AIRequest(BaseModel):
    message: str
    session_id: str
    device_context: Optional[Dict[str, Any]] = None
    auto_execute: bool = False
    build_context: Optional[Dict[str, Any]] = None

class BuildRequest(BaseModel):
    device_serial: str
    halium_version: str = "halium-11.0"
    build_type: str = "lineage"
    build_dir: str = "/home/user/halium"
    auto_mode: bool = True

class DeviceTreeExtractRequest(BaseModel):
    device_serial: str
    extract_dtbo: bool = True
    extract_boot: bool = True
    decompile: bool = True

class FirmwareSearchRequest(BaseModel):
    device_codename: str
    vendor: Optional[str] = None
    android_version: Optional[str] = None

# ======================= HELPERS =======================

async def run_command(cmd: str, timeout: int = 120, cwd: str = None) -> tuple[str, str, int]:
    """Execute a shell command and return stdout, stderr, return code"""
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd or "/app"
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return stdout.decode(), stderr.decode(), process.returncode
    except asyncio.TimeoutError:
        return "", f"Command timed out after {timeout}s", -1
    except Exception as e:
        return "", str(e), -1

async def run_command_stream(cmd: str, cwd: str = None) -> AsyncGenerator[str, None]:
    """Execute command and stream output line by line"""
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd or "/app"
        )
        async for line in process.stdout:
            yield line.decode()
        await process.wait()
    except Exception as e:
        yield f"Error: {str(e)}\n"

def check_tool_available(tool: str) -> bool:
    """Check if a command-line tool is available"""
    return shutil.which(tool) is not None

def parse_adb_devices(output: str) -> List[Dict[str, str]]:
    """Parse adb devices output"""
    devices = []
    lines = output.strip().split('\n')[1:]
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                devices.append({
                    'serial': parts[0],
                    'state': parts[1]
                })
    return devices

async def get_device_prop(serial: str, prop: str) -> str:
    """Get a device property via adb"""
    stdout, _, _ = await run_command(f"adb -s {serial} shell getprop {prop}")
    return stdout.strip()

async def get_full_device_info(serial: str) -> DeviceInfo:
    """Get comprehensive device information via ADB"""
    device_info = DeviceInfo(serial=serial)
    
    # Basic properties
    device_info.model = await get_device_prop(serial, "ro.product.model")
    device_info.device = await get_device_prop(serial, "ro.product.device")
    device_info.product = await get_device_prop(serial, "ro.product.name")
    device_info.manufacturer = await get_device_prop(serial, "ro.product.manufacturer")
    device_info.brand = await get_device_prop(serial, "ro.product.brand")
    device_info.android_version = await get_device_prop(serial, "ro.build.version.release")
    device_info.sdk_version = await get_device_prop(serial, "ro.build.version.sdk")
    device_info.build_fingerprint = await get_device_prop(serial, "ro.build.fingerprint")
    device_info.cpu_abi = await get_device_prop(serial, "ro.product.cpu.abi")
    device_info.hardware = await get_device_prop(serial, "ro.hardware")
    device_info.platform = await get_device_prop(serial, "ro.board.platform")
    
    # Try to get SoC info
    soc_props = ["ro.soc.model", "ro.hardware.chipname", "ro.mediatek.platform"]
    for prop in soc_props:
        soc = await get_device_prop(serial, prop)
        if soc:
            device_info.soc = soc
            break
    
    # Kernel version
    stdout, _, _ = await run_command(f"adb -s {serial} shell cat /proc/version")
    device_info.kernel_version = stdout.strip()[:200] if stdout else None
    
    # Get partition info
    stdout, _, _ = await run_command(
        f"adb -s {serial} shell ls -la /dev/block/by-name/ 2>/dev/null || "
        f"adb -s {serial} shell ls -la /dev/block/platform/*/by-name/ 2>/dev/null || "
        f"adb -s {serial} shell ls -la /dev/block/bootdevice/by-name/ 2>/dev/null"
    )
    if stdout:
        partitions = {}
        for line in stdout.strip().split('\n'):
            match = re.search(r'(\w+)\s*->\s*(.+)$', line)
            if match:
                partitions[match.group(1)] = match.group(2)
        device_info.partitions = partitions if partitions else None
    
    return device_info

async def check_halium_compatibility(codename: str) -> Dict[str, Any]:
    """Check if device has known Halium support"""
    result = {
        "codename": codename,
        "known_port": False,
        "halium_version": None,
        "status": "unknown",
        "porter": None,
        "notes": None,
        "wiki_url": f"https://github.com/halium/projectmanagement/issues?q={codename}"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Try to fetch Halium devices list
            response = await client.get(HALIUM_DEVICES_URL, timeout=10)
            if response.status_code == 200:
                devices = response.json()
                for device in devices:
                    if device.get("codename", "").lower() == codename.lower():
                        result["known_port"] = True
                        result["halium_version"] = device.get("halium_version")
                        result["status"] = device.get("status", "in-progress")
                        result["porter"] = device.get("porter")
                        result["notes"] = device.get("notes")
                        break
    except Exception as e:
        result["error"] = str(e)
    
    return result

async def check_lineage_support(codename: str) -> Dict[str, Any]:
    """Check LineageOS support for device"""
    result = {
        "codename": codename,
        "supported": False,
        "versions": [],
        "wiki_url": f"https://wiki.lineageos.org/devices/{codename}"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Check LineageOS wiki
            response = await client.get(f"https://wiki.lineageos.org/devices/{codename}", timeout=10, follow_redirects=True)
            if response.status_code == 200:
                result["supported"] = True
                # Parse available versions from page
                content = response.text
                for version in ["21", "20", "19.1", "18.1", "17.1", "16.0", "15.1", "14.1"]:
                    if f"lineage-{version}" in content.lower() or f"lineageos {version}" in content.lower():
                        result["versions"].append(version)
    except Exception as e:
        result["error"] = str(e)
    
    return result

async def search_firmware_sources(codename: str, vendor: str = None) -> List[Dict[str, Any]]:
    """Search for firmware sources for a device"""
    sources = []
    
    # LineageOS
    sources.append({
        "type": "lineageos",
        "name": "LineageOS",
        "url": f"https://download.lineageos.org/{codename}",
        "device_tree": f"https://github.com/LineageOS/android_device_{vendor or 'vendor'}_{codename}"
    })
    
    # TheMuppets (vendor blobs)
    sources.append({
        "type": "vendor_blobs",
        "name": "TheMuppets Vendor",
        "url": f"https://github.com/TheMuppets/proprietary_vendor_{vendor or 'vendor'}"
    })
    
    # Common kernel sources
    if vendor:
        sources.append({
            "type": "kernel",
            "name": f"{vendor.capitalize()} Kernel",
            "url": f"https://github.com/LineageOS/android_kernel_{vendor}_{codename}"
        })
    
    return sources

# ======================= AI AGENT =======================

HALIUM_SYSTEM_PROMPT = """You are an expert Halium Build Assistant AI agent with deep knowledge of:
- Android internals, bootloaders, and kernel development
- Halium porting process and requirements
- LineageOS and AOSP build systems
- Device tree configuration and kernel compilation
- ADB, fastboot, and Android partition layouts

Your capabilities:
1. Analyze Android devices via ADB/Fastboot commands
2. Guide users through the complete Halium porting process
3. Generate device tree configurations
4. Analyze and fix kernel configs for Halium compatibility
5. Troubleshoot build and boot issues
6. Execute terminal commands to automate the process

Key Halium knowledge:
- Halium provides a minimal Android base for Linux distributions (Ubuntu Touch, Droidian, postmarketOS, Mobian)
- Supported versions: halium-7.1 (Android 7.1), halium-9.0 (Pie), halium-10.0 (Q), halium-11.0 (R)
- Build process: repo init → device tree setup → kernel config → vendor blobs → build → rootfs

When suggesting commands:
- Format them in ```bash code blocks
- Use 'adb -s <serial>' format when device serial is known
- Explain dangerous operations before executing
- Chain related commands logically

Device Tree extraction:
- DTBO partition: /dev/block/by-name/dtbo
- Boot image: /dev/block/by-name/boot
- Use 'dtc' to decompile DTB to DTS
- Use 'unpackbootimg' or 'abootimg' to extract boot images

Kernel config requirements for Halium:
- CGROUPS, NAMESPACES (all types), FHANDLE
- OVERLAY_FS, DEVTMPFS, TMPFS
- ANDROID_BINDER_IPC, ASHMEM
- VETH, NF_NAT, MEMCG

When auto_execute mode is enabled, structure your responses with clear command blocks that can be extracted and run automatically. Always verify critical operations before proceeding."""

class AIAgent:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        self.sessions: Dict[str, LlmChat] = {}
    
    def get_or_create_session(self, session_id: str) -> LlmChat:
        if session_id not in self.sessions:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=HALIUM_SYSTEM_PROMPT
            )
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            self.sessions[session_id] = chat
        return self.sessions[session_id]
    
    async def send_message(self, session_id: str, message: str, device_context: Optional[Dict] = None, build_context: Optional[Dict] = None) -> str:
        chat = self.get_or_create_session(session_id)
        
        # Build context-aware message
        full_message = message
        if device_context:
            context_str = f"\n\n[Device Context]\n```json\n{json.dumps(device_context, indent=2, default=str)}\n```"
            full_message = message + context_str
        if build_context:
            build_str = f"\n\n[Build Context]\n```json\n{json.dumps(build_context, indent=2, default=str)}\n```"
            full_message = full_message + build_str
        
        user_msg = UserMessage(text=full_message)
        response = await chat.send_message(user_msg)
        return response
    
    def extract_commands(self, response: str) -> List[str]:
        """Extract executable commands from AI response"""
        commands = []
        pattern = r'```(?:bash|sh|shell)?\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            for cmd in match.strip().split('\n'):
                cmd = cmd.strip()
                if cmd and not cmd.startswith('#'):
                    commands.append(cmd)
        return commands
    
    async def analyze_device_for_halium(self, device_info: Dict) -> str:
        """Generate analysis for Halium porting"""
        prompt = f"""Analyze this Android device for Halium porting potential:

Device: {device_info.get('model')} ({device_info.get('device')})
Manufacturer: {device_info.get('manufacturer')}
Android Version: {device_info.get('android_version')}
SoC/Platform: {device_info.get('platform')} / {device_info.get('soc')}
CPU ABI: {device_info.get('cpu_abi')}
Kernel: {device_info.get('kernel_version', 'Unknown')[:100]}

Provide:
1. Recommended Halium version based on Android version
2. Expected challenges based on SoC/platform
3. Required steps to start porting
4. Commands to gather more device info"""
        
        return await self.send_message("analysis", prompt, device_context=device_info)

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
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict):
        if session_id in self.active_connections:
            for ws in self.active_connections[session_id]:
                try:
                    await ws.send_json(message)
                except:
                    pass
    
    async def broadcast(self, message: Dict):
        for session_id in self.active_connections:
            await self.send_message(session_id, message)

manager = ConnectionManager()

# ======================= BUILD PIPELINE =======================

class BuildPipeline:
    def __init__(self, session: BuildSession):
        self.session = session
        self.build_dir = Path(session.build_dir or "/home/user/halium")
    
    async def log(self, message: str, level: str = "info"):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message
        }
        self.session.logs.append(log_entry)
        await manager.send_message(self.session.id, {"type": "log", "data": log_entry})
        
        # Update in database
        await db.build_sessions.update_one(
            {"id": self.session.id},
            {"$push": {"logs": log_entry}, "$set": {"current_step_name": message}}
        )
    
    async def update_progress(self, step: int, progress: int):
        self.session.current_step = step
        self.session.progress = progress
        await db.build_sessions.update_one(
            {"id": self.session.id},
            {"$set": {"current_step": step, "progress": progress}}
        )
        await manager.send_message(self.session.id, {
            "type": "progress",
            "step": step,
            "progress": progress
        })
    
    async def run_step_command(self, cmd: str, step_name: str) -> bool:
        await self.log(f"Executing: {cmd}")
        await manager.send_message(self.session.id, {"type": "command", "command": cmd})
        
        async for line in run_command_stream(cmd, cwd=str(self.build_dir)):
            await manager.send_message(self.session.id, {"type": "output", "line": line})
        
        stdout, stderr, code = await run_command(cmd, cwd=str(self.build_dir), timeout=3600)
        if code != 0:
            await self.log(f"Step failed: {step_name} - {stderr}", "error")
            self.session.errors.append(f"{step_name}: {stderr}")
            return False
        return True
    
    async def setup_environment(self) -> bool:
        await self.log("Setting up build environment...")
        await self.update_progress(1, 5)
        
        # Check for required tools
        required_tools = ["repo", "git", "make", "gcc", "python3"]
        missing = [t for t in required_tools if not check_tool_available(t)]
        
        if missing:
            await self.log(f"Missing tools: {', '.join(missing)}", "warning")
            # Try to install
            for cmd in BUILD_STEPS[0]["commands"]:
                if not await self.run_step_command(cmd, "Environment Setup"):
                    return False
        
        await self.update_progress(1, 10)
        return True
    
    async def init_repo(self) -> bool:
        await self.log("Initializing Halium repository...")
        await self.update_progress(2, 15)
        
        # Create build directory
        self.build_dir.mkdir(parents=True, exist_ok=True)
        
        halium_info = HALIUM_VERSIONS.get(self.session.halium_version, HALIUM_VERSIONS["halium-11.0"])
        branch = halium_info["branch"]
        
        cmd = f"repo init -u {HALIUM_MANIFEST_URL} -b {branch} --depth=1"
        if not await self.run_step_command(cmd, "Repo Init"):
            return False
        
        await self.update_progress(2, 25)
        return True
    
    async def setup_device_tree(self, codename: str, vendor: str) -> bool:
        await self.log(f"Setting up device tree for {vendor}/{codename}...")
        await self.update_progress(3, 30)
        
        # Create local manifest
        local_manifest_dir = self.build_dir / ".repo" / "local_manifests"
        local_manifest_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate local manifest XML
        manifest_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<manifest>
  <!-- Device tree -->
  <project path="device/{vendor}/{codename}" name="halium/android_device_{vendor}_{codename}" remote="halium" revision="{self.session.halium_version}" />
  
  <!-- Kernel -->
  <project path="kernel/{vendor}/{codename}" name="halium/android_kernel_{vendor}_{codename}" remote="halium" revision="{self.session.halium_version}" />
  
  <!-- Vendor blobs -->
  <project path="vendor/{vendor}" name="halium/proprietary_vendor_{vendor}" remote="halium" revision="{self.session.halium_version}" />
</manifest>
'''
        
        manifest_path = local_manifest_dir / f"{codename}.xml"
        async with aiofiles.open(manifest_path, 'w') as f:
            await f.write(manifest_content)
        
        await self.log(f"Created local manifest: {manifest_path}")
        await self.update_progress(3, 35)
        return True
    
    async def sync_repo(self) -> bool:
        await self.log("Syncing repositories (this may take a while)...")
        await self.update_progress(4, 40)
        
        cmd = "repo sync -c -j$(nproc) --force-sync --no-tags --no-clone-bundle"
        if not await self.run_step_command(cmd, "Repo Sync"):
            return False
        
        await self.update_progress(4, 60)
        return True
    
    async def configure_kernel(self, codename: str, vendor: str) -> bool:
        await self.log("Configuring kernel for Halium...")
        await self.update_progress(5, 65)
        
        # Check and modify kernel defconfig
        kernel_dir = self.build_dir / "kernel" / vendor / codename
        if not kernel_dir.exists():
            await self.log("Kernel directory not found", "warning")
            return True  # Continue anyway
        
        # Find defconfig
        defconfigs = list(kernel_dir.glob("arch/arm64/configs/*_defconfig")) + \
                     list(kernel_dir.glob("arch/arm/configs/*_defconfig"))
        
        if defconfigs:
            defconfig = defconfigs[0]
            await self.log(f"Found defconfig: {defconfig}")
            
            # Read and analyze
            async with aiofiles.open(defconfig, 'r') as f:
                config_content = await f.read()
            
            # Add required configs
            additions = []
            for req in KERNEL_CONFIG_REQUIREMENTS:
                if req["required"] and req["config"] not in config_content:
                    additions.append(f'{req["config"]}=y')
                    await self.log(f"Adding: {req['config']}", "warning")
            
            if additions:
                async with aiofiles.open(defconfig, 'a') as f:
                    await f.write("\n# Halium requirements\n")
                    await f.write("\n".join(additions))
        
        await self.update_progress(5, 70)
        return True
    
    async def extract_vendor(self, serial: str) -> bool:
        await self.log("Extracting vendor blobs from device...")
        await self.update_progress(6, 75)
        
        # This would normally run extract-files.sh from device tree
        vendor_script = self.build_dir / "device" / "*" / "*" / "extract-files.sh"
        scripts = list(self.build_dir.glob("device/*/*/extract-files.sh"))
        
        if scripts:
            script = scripts[0]
            cmd = f"cd {script.parent} && ./extract-files.sh"
            await self.run_step_command(cmd, "Extract Vendor")
        else:
            await self.log("No extract-files.sh found, manual extraction may be needed", "warning")
        
        await self.update_progress(6, 80)
        return True
    
    async def build_system(self, codename: str) -> bool:
        await self.log("Building Halium system image...")
        await self.update_progress(7, 85)
        
        # Source build environment and build
        build_cmds = [
            "source build/envsetup.sh",
            f"breakfast {codename}",
            "mka halium-boot",
            "mka systemimage"
        ]
        
        full_cmd = " && ".join(build_cmds)
        if not await self.run_step_command(f"bash -c '{full_cmd}'", "Build System"):
            return False
        
        await self.update_progress(7, 95)
        return True
    
    async def run(self):
        """Execute the full build pipeline"""
        try:
            self.session.status = "running"
            await db.build_sessions.update_one(
                {"id": self.session.id},
                {"$set": {"status": "running"}}
            )
            
            codename = self.session.device_codename or "device"
            vendor = "vendor"
            
            if self.session.device_info:
                vendor = (self.session.device_info.get("manufacturer") or "vendor").lower()
                codename = self.session.device_info.get("device") or codename
            
            # Execute pipeline steps
            steps = [
                (self.setup_environment, "Environment Setup"),
                (self.init_repo, "Repo Init"),
                (lambda: self.setup_device_tree(codename, vendor), "Device Tree Setup"),
                (self.sync_repo, "Repo Sync"),
                (lambda: self.configure_kernel(codename, vendor), "Kernel Config"),
                (lambda: self.extract_vendor(self.session.device_serial), "Extract Vendor"),
                (lambda: self.build_system(codename), "Build System"),
            ]
            
            for step_func, step_name in steps:
                await self.log(f"Starting: {step_name}")
                if not await step_func():
                    self.session.status = "failed"
                    await db.build_sessions.update_one(
                        {"id": self.session.id},
                        {"$set": {"status": "failed", "completed_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    return False
            
            self.session.status = "completed"
            self.session.progress = 100
            await db.build_sessions.update_one(
                {"id": self.session.id},
                {"$set": {"status": "completed", "progress": 100, "completed_at": datetime.now(timezone.utc).isoformat()}}
            )
            await self.log("Build completed successfully!")
            return True
            
        except Exception as e:
            await self.log(f"Build error: {str(e)}", "error")
            self.session.status = "failed"
            await db.build_sessions.update_one(
                {"id": self.session.id},
                {"$set": {"status": "failed", "completed_at": datetime.now(timezone.utc).isoformat()}}
            )
            return False

# ======================= API ROUTES =======================

@api_router.get("/")
async def root():
    return {"message": "Halium Build Assistant API", "version": "2.0.0"}

@api_router.get("/health")
async def health_check():
    tools = {
        "adb": check_tool_available("adb"),
        "fastboot": check_tool_available("fastboot"),
        "repo": check_tool_available("repo"),
        "git": check_tool_available("git"),
        "dtc": check_tool_available("dtc"),
        "make": check_tool_available("make"),
        "python3": check_tool_available("python3")
    }
    return {
        "status": "healthy",
        "tools": tools,
        "ready_for_build": all([tools["adb"], tools["git"], tools["make"]]),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ======================= DEVICE ROUTES =======================

@api_router.get("/devices")
async def list_devices():
    """List all connected ADB devices"""
    stdout, stderr, code = await run_command("adb devices")
    if code != 0:
        return {"devices": [], "error": stderr, "adb_available": False}
    
    devices = parse_adb_devices(stdout)
    return {"devices": devices, "adb_available": True}

@api_router.get("/devices/{serial}/info")
async def get_device_info(serial: str):
    """Get detailed information about a specific device"""
    stdout, _, _ = await run_command("adb devices")
    devices = parse_adb_devices(stdout)
    
    if not any(d['serial'] == serial and d['state'] == 'device' for d in devices):
        raise HTTPException(status_code=404, detail="Device not found or not authorized")
    
    device_info = await get_full_device_info(serial)
    
    # Check Halium compatibility
    if device_info.device:
        halium_compat = await check_halium_compatibility(device_info.device)
        device_info.halium_compatible = halium_compat.get("known_port", False)
        device_info.halium_version = halium_compat.get("halium_version")
        
        lineage_support = await check_lineage_support(device_info.device)
        device_info.lineage_support = lineage_support
    
    # Store in database
    doc = device_info.model_dump()
    doc['detected_at'] = doc['detected_at'].isoformat()
    await db.devices.update_one(
        {"serial": serial},
        {"$set": doc},
        upsert=True
    )
    
    return device_info

@api_router.get("/devices/{serial}/partitions")
async def get_device_partitions(serial: str):
    """Get device partition layout"""
    commands = [
        f"adb -s {serial} shell ls -la /dev/block/by-name/ 2>/dev/null",
        f"adb -s {serial} shell ls -la /dev/block/platform/*/by-name/ 2>/dev/null",
        f"adb -s {serial} shell ls -la /dev/block/bootdevice/by-name/ 2>/dev/null"
    ]
    
    partitions = []
    raw_output = ""
    
    for cmd in commands:
        stdout, _, code = await run_command(cmd)
        if stdout and code == 0:
            raw_output = stdout
            for line in stdout.strip().split('\n'):
                match = re.search(r'(\w+)\s*->\s*(.+)$', line)
                if match:
                    partitions.append({
                        "name": match.group(1),
                        "path": match.group(2)
                    })
            if partitions:
                break
    
    # Identify important partitions
    important = ["boot", "recovery", "system", "vendor", "dtbo", "vbmeta", "userdata", "super"]
    categorized = {
        "boot_partitions": [p for p in partitions if p["name"] in ["boot", "recovery", "dtbo", "vbmeta"]],
        "system_partitions": [p for p in partitions if p["name"] in ["system", "vendor", "product", "odm", "super"]],
        "data_partitions": [p for p in partitions if p["name"] in ["userdata", "metadata", "cache"]],
        "other": [p for p in partitions if p["name"] not in important]
    }
    
    return {
        "partitions": partitions,
        "categorized": categorized,
        "total_count": len(partitions),
        "raw_output": raw_output
    }

@api_router.get("/devices/{serial}/kernel")
async def get_kernel_info(serial: str):
    """Get kernel information from device"""
    version, _, _ = await run_command(f"adb -s {serial} shell cat /proc/version")
    cmdline, _, _ = await run_command(f"adb -s {serial} shell cat /proc/cmdline")
    
    # Try to get kernel config
    config_content = ""
    config_stdout, _, code = await run_command(f"adb -s {serial} shell zcat /proc/config.gz 2>/dev/null")
    if code == 0 and config_stdout:
        config_content = config_stdout
    
    # Analyze kernel config for Halium
    config_analysis = []
    if config_content:
        for req in KERNEL_CONFIG_REQUIREMENTS:
            present = req["config"] in config_content
            enabled = f'{req["config"]}=y' in config_content or f'{req["config"]}=m' in config_content
            config_analysis.append({
                "config": req["config"],
                "required": req["required"],
                "description": req["description"],
                "present": present,
                "enabled": enabled,
                "status": "ok" if (not req["required"] or enabled) else "missing"
            })
    
    halium_ready = all(c["status"] == "ok" for c in config_analysis if c["required"])
    
    return {
        "version": version.strip(),
        "cmdline": cmdline.strip(),
        "config_available": bool(config_content),
        "config_analysis": config_analysis,
        "halium_ready": halium_ready,
        "missing_configs": [c for c in config_analysis if c["status"] == "missing"]
    }

# ======================= DEVICE TREE EXTRACTION =======================

@api_router.post("/devices/{serial}/extract-dtb")
async def extract_device_tree(serial: str, request: DeviceTreeExtractRequest):
    """Extract Device Tree Blob from device"""
    results = {
        "serial": serial,
        "dtbo_extracted": False,
        "boot_extracted": False,
        "dtb_files": [],
        "dts_files": [],
        "errors": []
    }
    
    # Create extraction directory
    extract_dir = Path(f"/tmp/dtb_extract_{serial}")
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    # Get device codename
    codename = await get_device_prop(serial, "ro.product.device")
    
    if request.extract_dtbo:
        # Extract DTBO partition
        dtbo_path = extract_dir / "dtbo.img"
        
        # Find DTBO partition path
        stdout, _, _ = await run_command(f"adb -s {serial} shell ls -la /dev/block/by-name/dtbo 2>/dev/null")
        if "dtbo" in stdout:
            # Pull DTBO
            await run_command(f"adb -s {serial} shell su -c 'dd if=/dev/block/by-name/dtbo of=/sdcard/dtbo.img' 2>/dev/null")
            stdout, stderr, code = await run_command(f"adb -s {serial} pull /sdcard/dtbo.img {dtbo_path}")
            
            if code == 0:
                results["dtbo_extracted"] = True
                results["dtbo_path"] = str(dtbo_path)
                
                # Extract DTBs from DTBO image
                if check_tool_available("mkdtboimg"):
                    await run_command(f"mkdtboimg dump {dtbo_path} -b {extract_dir}/dtbo", cwd=str(extract_dir))
                    results["dtb_files"].extend([str(f) for f in extract_dir.glob("dtbo.*")])
            else:
                results["errors"].append(f"Failed to pull DTBO: {stderr}")
    
    if request.extract_boot:
        # Extract boot image
        boot_path = extract_dir / "boot.img"
        
        await run_command(f"adb -s {serial} shell su -c 'dd if=/dev/block/by-name/boot of=/sdcard/boot.img' 2>/dev/null")
        stdout, stderr, code = await run_command(f"adb -s {serial} pull /sdcard/boot.img {boot_path}")
        
        if code == 0:
            results["boot_extracted"] = True
            results["boot_path"] = str(boot_path)
            
            # Try to extract DTB from boot image
            if check_tool_available("unpackbootimg"):
                await run_command(f"unpackbootimg -i {boot_path} -o {extract_dir}/boot_unpacked", cwd=str(extract_dir))
                dtb_files = list(Path(f"{extract_dir}/boot_unpacked").glob("*.dtb"))
                results["dtb_files"].extend([str(f) for f in dtb_files])
        else:
            results["errors"].append(f"Failed to pull boot image: {stderr}")
    
    if request.decompile and results["dtb_files"] and check_tool_available("dtc"):
        # Decompile DTB to DTS
        for dtb_file in results["dtb_files"]:
            dts_file = dtb_file.replace(".dtb", ".dts").replace(".img", ".dts")
            stdout, stderr, code = await run_command(f"dtc -I dtb -O dts -o {dts_file} {dtb_file}")
            if code == 0:
                results["dts_files"].append(dts_file)
    
    # Store results in database
    dt_info = DeviceTreeInfo(
        device_serial=serial,
        codename=codename,
        dtbo_path=results.get("dtbo_path"),
        boot_img_path=results.get("boot_path"),
        dtb_extracted=bool(results["dtb_files"]),
        dts_decompiled=bool(results["dts_files"])
    )
    
    doc = dt_info.model_dump()
    doc['extracted_at'] = doc['extracted_at'].isoformat()
    await db.device_trees.update_one(
        {"device_serial": serial},
        {"$set": doc},
        upsert=True
    )
    
    return results

@api_router.get("/devices/{serial}/device-tree-template")
async def generate_device_tree_template(serial: str):
    """Generate a device tree template based on device info"""
    device_info = await get_full_device_info(serial)
    
    codename = device_info.device or "device"
    vendor = (device_info.manufacturer or "vendor").lower()
    
    # Generate device tree structure
    template = {
        "device": {
            "codename": codename,
            "vendor": vendor,
            "model": device_info.model,
            "architecture": "arm64" if "arm64" in (device_info.cpu_abi or "") else "arm"
        },
        "files": {
            "Android.mk": f'''LOCAL_PATH := $(call my-dir)

ifeq ($(TARGET_DEVICE),{codename})
include $(call all-subdir-makefiles,$(LOCAL_PATH))
endif
''',
            "AndroidProducts.mk": f'''PRODUCT_MAKEFILES := \\
    $(LOCAL_DIR)/halium_{codename}.mk

COMMON_LUNCH_CHOICES := \\
    halium_{codename}-userdebug \\
    halium_{codename}-eng
''',
            f"halium_{codename}.mk": f'''$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)
$(call inherit-product, vendor/{vendor}/{codename}/{codename}-vendor.mk)

PRODUCT_NAME := halium_{codename}
PRODUCT_DEVICE := {codename}
PRODUCT_BRAND := {device_info.brand or vendor}
PRODUCT_MODEL := {device_info.model}
PRODUCT_MANUFACTURER := {device_info.manufacturer}
''',
            "BoardConfig.mk": f'''DEVICE_PATH := device/{vendor}/{codename}

# Architecture
TARGET_ARCH := {"arm64" if "arm64" in (device_info.cpu_abi or "") else "arm"}
TARGET_ARCH_VARIANT := {"armv8-a" if "arm64" in (device_info.cpu_abi or "") else "armv7-a-neon"}
TARGET_CPU_ABI := {device_info.cpu_abi or "arm64-v8a"}
TARGET_CPU_VARIANT := generic

# Platform
TARGET_BOARD_PLATFORM := {device_info.platform or "unknown"}

# Kernel
BOARD_KERNEL_BASE := 0x00000000
BOARD_KERNEL_PAGESIZE := 4096
BOARD_KERNEL_CMDLINE := {await get_device_prop(serial, "ro.boot.hardware") or ""}

# Partitions
BOARD_BOOTIMAGE_PARTITION_SIZE := 67108864
BOARD_SYSTEMIMAGE_PARTITION_SIZE := 3221225472
BOARD_VENDORIMAGE_PARTITION_SIZE := 1073741824
BOARD_USERDATAIMAGE_PARTITION_SIZE := 26843545600

# Filesystem
BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true

# Recovery
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/rootdir/etc/fstab.{device_info.hardware or codename}

# SELinux
BOARD_SEPOLICY_DIRS += $(DEVICE_PATH)/sepolicy

# Vendor
TARGET_COPY_OUT_VENDOR := vendor
''',
            "device.mk": f'''# Inherit from common
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)

# Device-specific init
PRODUCT_PACKAGES += \\
    init.{device_info.hardware or codename}.rc

# Audio
PRODUCT_PACKAGES += \\
    android.hardware.audio@6.0-impl \\
    android.hardware.audio.effect@6.0-impl

# Display
PRODUCT_PACKAGES += \\
    android.hardware.graphics.allocator@2.0-impl \\
    android.hardware.graphics.composer@2.1-impl \\
    android.hardware.graphics.mapper@2.0-impl
''',
            f"rootdir/etc/fstab.{device_info.hardware or codename}": f'''# Android fstab file for {device_info.model}
# <src>                                         <mnt_point>     <type>  <mnt_flags and options>                     <fs_mgr_flags>
/dev/block/by-name/system                       /system         ext4    ro,barrier=1                                wait
/dev/block/by-name/vendor                       /vendor         ext4    ro,barrier=1                                wait
/dev/block/by-name/userdata                     /data           ext4    noatime,nosuid,nodev,barrier=1,noauto_da_alloc wait,check,encryptable=footer
/dev/block/by-name/cache                        /cache          ext4    noatime,nosuid,nodev,barrier=1              wait,check
/dev/block/by-name/boot                         /boot           emmc    defaults                                    defaults
/dev/block/by-name/recovery                     /recovery       emmc    defaults                                    defaults
''',
            f"rootdir/etc/init.{device_info.hardware or codename}.rc": f'''on early-init
    mount debugfs /sys/kernel/debug /sys/kernel/debug mode=755

on init
    # Set permissions for persist partition
    mkdir /persist 0771 system system

on boot
    # Permissions for LED
    chown system system /sys/class/leds/red/brightness
    chown system system /sys/class/leds/green/brightness
    chown system system /sys/class/leds/blue/brightness
'''
        },
        "kernel_info": {
            "version": device_info.kernel_version,
            "cmdline": await get_device_prop(serial, "ro.boot.hardware")
        },
        "instructions": [
            f"1. Create directory: device/{vendor}/{codename}/",
            "2. Copy these template files to the directory",
            f"3. Find kernel source for {device_info.platform or 'your SoC'}",
            "4. Add device to local manifest",
            "5. Extract vendor blobs using extract-files.sh",
            "6. Modify kernel defconfig for Halium requirements",
            "7. Build with: breakfast {codename} && mka halium-boot systemimage"
        ]
    }
    
    return template

# ======================= FIRMWARE ROUTES =======================

@api_router.post("/firmware/search")
async def search_firmware(request: FirmwareSearchRequest):
    """Search for firmware/ROM sources for a device"""
    codename = request.device_codename
    vendor = request.vendor
    
    results = {
        "codename": codename,
        "sources": [],
        "halium_status": None,
        "lineage_status": None,
        "recommendations": []
    }
    
    # Check Halium compatibility
    halium_status = await check_halium_compatibility(codename)
    results["halium_status"] = halium_status
    
    # Check LineageOS support
    lineage_status = await check_lineage_support(codename)
    results["lineage_status"] = lineage_status
    
    # Get firmware sources
    results["sources"] = await search_firmware_sources(codename, vendor)
    
    # Generate recommendations
    if halium_status.get("known_port"):
        results["recommendations"].append(f"Device has existing Halium port ({halium_status.get('halium_version')})")
        results["recommendations"].append("Check Halium project issues for device-specific instructions")
    elif lineage_status.get("supported"):
        versions = lineage_status.get("versions", [])
        if "18.1" in versions or "17.1" in versions:
            results["recommendations"].append("LineageOS 18.1/17.1 supported - use halium-11.0 or halium-10.0")
        elif "16.0" in versions:
            results["recommendations"].append("LineageOS 16.0 supported - use halium-9.0")
        results["recommendations"].append("Use LineageOS device tree as base for Halium port")
    else:
        results["recommendations"].append("No official LineageOS support - check XDA for unofficial ROMs")
        results["recommendations"].append("May need to create device tree from scratch")
    
    return results

@api_router.get("/firmware/halium-manifest/{halium_version}")
async def get_halium_manifest(halium_version: str):
    """Get Halium manifest information"""
    if halium_version not in HALIUM_VERSIONS:
        raise HTTPException(status_code=404, detail=f"Unknown Halium version: {halium_version}")
    
    info = HALIUM_VERSIONS[halium_version]
    
    return {
        "version": halium_version,
        "android_base": info["android"],
        "lineage_base": info["lineage"],
        "branch": info["branch"],
        "manifest_url": HALIUM_MANIFEST_URL,
        "init_command": f"repo init -u {HALIUM_MANIFEST_URL} -b {info['branch']} --depth=1",
        "sync_command": "repo sync -c -j$(nproc) --force-sync --no-tags --no-clone-bundle"
    }

# ======================= TERMINAL ROUTES =======================

@api_router.post("/terminal/execute")
async def execute_command(request: CommandRequest):
    """Execute a terminal command"""
    cmd = request.command.strip()
    
    # Security: Block dangerous commands
    dangerous_patterns = ['rm -rf /', 'mkfs', ':(){', 'fork bomb', '> /dev/sd']
    for pattern in dangerous_patterns:
        if pattern in cmd.lower():
            raise HTTPException(status_code=400, detail=f"Dangerous command blocked")
    
    stdout, stderr, code = await run_command(cmd, timeout=request.timeout, cwd=request.working_dir)
    
    # Store command in history
    await db.command_history.insert_one({
        "id": str(uuid.uuid4()),
        "command": cmd,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": code,
        "session_id": request.session_id,
        "working_dir": request.working_dir,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "command": cmd,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": code,
        "success": code == 0
    }

@api_router.get("/terminal/history")
async def get_command_history(session_id: Optional[str] = None, limit: int = 50):
    """Get command execution history"""
    query = {"session_id": session_id} if session_id else {}
    history = await db.command_history.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return {"history": history}

# ======================= AI ROUTES =======================

@api_router.post("/ai/chat")
async def ai_chat(request: AIRequest):
    """Chat with the AI assistant"""
    try:
        response = await ai_agent.send_message(
            request.session_id,
            request.message,
            request.device_context,
            request.build_context
        )
        
        commands = ai_agent.extract_commands(response)
        
        # Store messages
        user_msg = ChatMessage(
            session_id=request.session_id,
            role="user",
            content=request.message
        )
        assistant_msg = ChatMessage(
            session_id=request.session_id,
            role="assistant",
            content=response,
            extracted_commands=commands
        )
        
        await db.chat_messages.insert_one({**user_msg.model_dump(), "timestamp": user_msg.timestamp.isoformat()})
        await db.chat_messages.insert_one({**assistant_msg.model_dump(), "timestamp": assistant_msg.timestamp.isoformat()})
        
        # Auto-execute if requested
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
            "session_id": request.session_id,
            "execution_results": execution_results if request.auto_execute else None
        }
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ai/analyze-device")
async def ai_analyze_device(serial: str):
    """AI analysis of device for Halium porting"""
    device_info = await get_full_device_info(serial)
    analysis = await ai_agent.analyze_device_for_halium(device_info.model_dump())
    
    return {
        "device_info": device_info,
        "analysis": analysis
    }

@api_router.get("/ai/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    messages = await db.chat_messages.find(
        {"session_id": session_id},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(100)
    return {"messages": messages}

# ======================= BUILD ROUTES =======================

@api_router.post("/build/start")
async def start_build(request: BuildRequest, background_tasks: BackgroundTasks):
    """Start a Halium build process"""
    # Get device info
    device_info = await get_full_device_info(request.device_serial)
    
    session = BuildSession(
        device_serial=request.device_serial,
        device_codename=device_info.device,
        device_info=device_info.model_dump(),
        halium_version=request.halium_version,
        build_type=request.build_type,
        build_dir=request.build_dir,
        status="pending"
    )
    
    # Store session
    doc = session.model_dump()
    doc['started_at'] = doc['started_at'].isoformat()
    doc['completed_at'] = None
    await db.build_sessions.insert_one(doc)
    
    # Start build in background if auto mode
    if request.auto_mode:
        pipeline = BuildPipeline(session)
        background_tasks.add_task(pipeline.run)
        session.status = "starting"
    
    return session

@api_router.get("/build/sessions")
async def list_build_sessions(limit: int = 20):
    """List all build sessions"""
    sessions = await db.build_sessions.find({}, {"_id": 0}).sort("started_at", -1).limit(limit).to_list(limit)
    return {"sessions": sessions}

@api_router.get("/build/{session_id}")
async def get_build_session(session_id: str):
    """Get a specific build session"""
    session = await db.build_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Build session not found")
    return session

@api_router.get("/build/{session_id}/logs")
async def get_build_logs(session_id: str, tail: int = 100):
    """Get logs for a build session"""
    session = await db.build_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Build session not found")
    
    logs = session.get("logs", [])
    return {
        "logs": logs[-tail:] if tail else logs,
        "total": len(logs),
        "errors": session.get("errors", [])
    }

@api_router.post("/build/{session_id}/cancel")
async def cancel_build(session_id: str):
    """Cancel a running build"""
    result = await db.build_sessions.update_one(
        {"id": session_id, "status": "running"},
        {"$set": {"status": "cancelled", "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Build not running or not found")
    
    return {"message": "Build cancelled", "session_id": session_id}

# ======================= HALIUM INFO ROUTES =======================

@api_router.get("/halium/versions")
async def get_halium_versions():
    """Get available Halium versions"""
    versions = []
    for vid, info in HALIUM_VERSIONS.items():
        versions.append({
            "id": vid,
            "name": vid.replace("-", " ").title(),
            "android_base": f"{info['android']} ({info['lineage']})",
            "status": "latest" if vid == "halium-11.0" else "stable"
        })
    return {"versions": versions}

@api_router.get("/halium/build-steps")
async def get_build_steps():
    """Get the standard Halium build steps"""
    return {"steps": BUILD_STEPS}

@api_router.get("/halium/kernel-requirements")
async def get_kernel_requirements():
    """Get kernel configuration requirements for Halium"""
    return {
        "requirements": KERNEL_CONFIG_REQUIREMENTS,
        "total": len(KERNEL_CONFIG_REQUIREMENTS),
        "required_count": len([r for r in KERNEL_CONFIG_REQUIREMENTS if r["required"]])
    }

@api_router.get("/halium/compatibility/{codename}")
async def check_device_compatibility(codename: str):
    """Check if a device has known Halium support"""
    halium_compat = await check_halium_compatibility(codename)
    lineage_compat = await check_lineage_support(codename)
    
    # Determine recommended Halium version
    recommended_version = None
    if lineage_compat.get("supported"):
        versions = lineage_compat.get("versions", [])
        if "21" in versions or "20" in versions or "18.1" in versions:
            recommended_version = "halium-11.0"
        elif "17.1" in versions:
            recommended_version = "halium-10.0"
        elif "16.0" in versions:
            recommended_version = "halium-9.0"
        elif "14.1" in versions or "15.1" in versions:
            recommended_version = "halium-7.1"
    
    return {
        "codename": codename,
        "halium": halium_compat,
        "lineageos": lineage_compat,
        "recommended_halium_version": halium_compat.get("halium_version") or recommended_version,
        "porting_difficulty": "easy" if halium_compat.get("known_port") else ("medium" if lineage_compat.get("supported") else "hard")
    }

# ======================= FASTBOOT ROUTES =======================

@api_router.get("/fastboot/devices")
async def list_fastboot_devices():
    """List devices in fastboot mode"""
    stdout, stderr, code = await run_command("fastboot devices")
    devices = []
    if stdout:
        for line in stdout.strip().split('\n'):
            if line.strip():
                parts = line.split()
                if parts:
                    devices.append({"serial": parts[0], "mode": parts[1] if len(parts) > 1 else "fastboot"})
    return {"devices": devices, "fastboot_available": check_tool_available("fastboot")}

@api_router.get("/fastboot/{serial}/info")
async def get_fastboot_info(serial: str):
    """Get device info via fastboot"""
    info = {}
    props = ["product", "serialno", "secure", "unlocked", "variant", "slot-count", "current-slot"]
    
    for prop in props:
        stdout, _, code = await run_command(f"fastboot -s {serial} getvar {prop} 2>&1")
        if ":" in stdout:
            value = stdout.split(":")[-1].strip()
            info[prop.replace("-", "_")] = value
    
    return {"serial": serial, "info": info}

@api_router.post("/fastboot/{serial}/flash")
async def fastboot_flash(serial: str, partition: str, image_path: str):
    """Flash an image to a partition via fastboot"""
    # Security check
    allowed_partitions = ["boot", "recovery", "dtbo", "vbmeta", "system", "vendor"]
    if partition not in allowed_partitions:
        raise HTTPException(status_code=400, detail=f"Partition not allowed: {partition}")
    
    if not Path(image_path).exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    
    stdout, stderr, code = await run_command(f"fastboot -s {serial} flash {partition} {image_path}")
    
    return {
        "success": code == 0,
        "partition": partition,
        "image": image_path,
        "output": stdout + stderr
    }

# ======================= WEBSOCKET ENDPOINT =======================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "command":
                cmd = data.get("command", "")
                # Stream command output
                async for line in run_command_stream(cmd, cwd=data.get("cwd")):
                    await websocket.send_json({"type": "output", "line": line})
                
                # Send completion
                await websocket.send_json({"type": "command_complete", "command": cmd})
            
            elif data.get("type") == "ai_message":
                message = data.get("message", "")
                device_context = data.get("device_context")
                build_context = data.get("build_context")
                
                response = await ai_agent.send_message(session_id, message, device_context, build_context)
                commands = ai_agent.extract_commands(response)
                
                await websocket.send_json({
                    "type": "ai_response",
                    "response": response,
                    "commands": commands
                })
                
                # Auto-execute if requested
                if data.get("auto_execute") and commands:
                    for cmd in commands:
                        await websocket.send_json({"type": "executing", "command": cmd})
                        async for line in run_command_stream(cmd):
                            await websocket.send_json({"type": "output", "line": line})
                        await websocket.send_json({"type": "command_complete", "command": cmd})
            
            elif data.get("type") == "subscribe_build":
                build_id = data.get("build_id")
                # Client wants to receive build updates
                await websocket.send_json({"type": "subscribed", "build_id": build_id})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)

# Include router
app.include_router(api_router)

# CORS middleware
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
