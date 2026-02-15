from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import asyncio
import subprocess
import shutil
import json
import re

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

# ======================= MODELS =======================

class DeviceInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    serial: str
    model: Optional[str] = None
    device: Optional[str] = None
    product: Optional[str] = None
    manufacturer: Optional[str] = None
    android_version: Optional[str] = None
    sdk_version: Optional[str] = None
    kernel_version: Optional[str] = None
    build_fingerprint: Optional[str] = None
    cpu_abi: Optional[str] = None
    partitions: Optional[Dict[str, Any]] = None
    halium_compatible: Optional[bool] = None
    halium_version: Optional[str] = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BuildSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    device_serial: str
    device_codename: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    current_step: Optional[str] = None
    progress: int = 0
    halium_version: Optional[str] = None
    build_type: Optional[str] = None  # lineage, aosp, etc
    logs: List[str] = []
    errors: List[str] = []
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str  # user, assistant, system
    content: str
    command: Optional[str] = None
    output: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CommandRequest(BaseModel):
    command: str
    session_id: Optional[str] = None

class AIRequest(BaseModel):
    message: str
    session_id: str
    device_context: Optional[Dict[str, Any]] = None
    auto_execute: bool = False

class BuildRequest(BaseModel):
    device_serial: str
    halium_version: str = "halium-11.0"
    build_type: str = "lineage"
    auto_mode: bool = True

# ======================= HELPERS =======================

async def run_command(cmd: str, timeout: int = 120) -> tuple[str, str, int]:
    """Execute a shell command and return stdout, stderr, return code"""
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/app"
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return stdout.decode(), stderr.decode(), process.returncode
    except asyncio.TimeoutError:
        return "", "Command timed out", -1
    except Exception as e:
        return "", str(e), -1

def check_tool_available(tool: str) -> bool:
    """Check if a command-line tool is available"""
    return shutil.which(tool) is not None

def parse_adb_devices(output: str) -> List[Dict[str, str]]:
    """Parse adb devices output"""
    devices = []
    lines = output.strip().split('\n')[1:]  # Skip header
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
    device_info.android_version = await get_device_prop(serial, "ro.build.version.release")
    device_info.sdk_version = await get_device_prop(serial, "ro.build.version.sdk")
    device_info.build_fingerprint = await get_device_prop(serial, "ro.build.fingerprint")
    device_info.cpu_abi = await get_device_prop(serial, "ro.product.cpu.abi")
    
    # Kernel version
    stdout, _, _ = await run_command(f"adb -s {serial} shell cat /proc/version")
    device_info.kernel_version = stdout.strip()[:100] if stdout else None
    
    # Get partition info
    stdout, _, _ = await run_command(f"adb -s {serial} shell ls -la /dev/block/by-name/ 2>/dev/null || adb -s {serial} shell ls -la /dev/block/platform/*/by-name/ 2>/dev/null")
    if stdout:
        partitions = {}
        for line in stdout.strip().split('\n'):
            match = re.search(r'(\w+)\s*->\s*(.+)$', line)
            if match:
                partitions[match.group(1)] = match.group(2)
        device_info.partitions = partitions if partitions else None
    
    return device_info

# ======================= AI AGENT =======================

HALIUM_SYSTEM_PROMPT = """You are an expert Halium Build Assistant AI agent. You help users port Halium (Linux) to Android devices.

Your capabilities:
1. Analyze Android devices via ADB/Fastboot commands
2. Guide users through the Halium porting process
3. Help troubleshoot build issues
4. Suggest and execute terminal commands

Key Halium knowledge:
- Halium provides a minimal Android base for Linux distributions (Ubuntu Touch, Droidian, postmarketOS)
- Supported versions: halium-7.1, halium-9.0, halium-10.0, halium-11.0
- Build process involves: repo init, device tree setup, kernel config, rootfs creation
- Device codename is critical - found in ro.product.device
- Kernel sources usually needed from manufacturer or LineageOS

When suggesting commands:
- Format them clearly with ```bash code blocks
- Explain what each command does
- Warn about dangerous operations
- For ADB: use 'adb -s <serial>' format when device serial is known

When analyzing devices:
- Check if device has existing Halium/LineageOS support
- Identify SoC (Qualcomm/MediaTek/Exynos) for kernel compatibility
- Note critical partitions: boot, system, vendor, userdata

Always be helpful and provide step-by-step guidance. If auto_execute mode is enabled, output commands in a structured way."""

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
    
    async def send_message(self, session_id: str, message: str, device_context: Optional[Dict] = None) -> str:
        chat = self.get_or_create_session(session_id)
        
        # Build context-aware message
        full_message = message
        if device_context:
            context_str = f"\n\n[Device Context]\n{json.dumps(device_context, indent=2, default=str)}"
            full_message = message + context_str
        
        user_msg = UserMessage(text=full_message)
        response = await chat.send_message(user_msg)
        return response
    
    def extract_commands(self, response: str) -> List[str]:
        """Extract executable commands from AI response"""
        commands = []
        # Find bash code blocks
        pattern = r'```(?:bash|sh|shell)?\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            # Split multi-line commands
            for cmd in match.strip().split('\n'):
                cmd = cmd.strip()
                if cmd and not cmd.startswith('#'):
                    commands.append(cmd)
        return commands

ai_agent = AIAgent()

# ======================= WEBSOCKET MANAGER =======================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: Dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)
    
    async def broadcast(self, message: Dict):
        for ws in self.active_connections.values():
            await ws.send_json(message)

manager = ConnectionManager()

# ======================= API ROUTES =======================

@api_router.get("/")
async def root():
    return {"message": "Halium Build Assistant API", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    adb_available = check_tool_available("adb")
    fastboot_available = check_tool_available("fastboot")
    return {
        "status": "healthy",
        "tools": {
            "adb": adb_available,
            "fastboot": fastboot_available
        },
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
    # Check if device is connected
    stdout, _, _ = await run_command("adb devices")
    devices = parse_adb_devices(stdout)
    
    if not any(d['serial'] == serial and d['state'] == 'device' for d in devices):
        raise HTTPException(status_code=404, detail="Device not found or not authorized")
    
    device_info = await get_full_device_info(serial)
    
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
    stdout, stderr, code = await run_command(
        f"adb -s {serial} shell ls -la /dev/block/by-name/ 2>/dev/null || "
        f"adb -s {serial} shell ls -la /dev/block/platform/*/by-name/ 2>/dev/null"
    )
    
    partitions = []
    if stdout:
        for line in stdout.strip().split('\n'):
            match = re.search(r'(\w+)\s*->\s*(.+)$', line)
            if match:
                partitions.append({
                    "name": match.group(1),
                    "path": match.group(2)
                })
    
    return {"partitions": partitions, "raw_output": stdout}

@api_router.get("/devices/{serial}/kernel")
async def get_kernel_info(serial: str):
    """Get kernel information from device"""
    version, _, _ = await run_command(f"adb -s {serial} shell cat /proc/version")
    cmdline, _, _ = await run_command(f"adb -s {serial} shell cat /proc/cmdline")
    config_gz, _, _ = await run_command(f"adb -s {serial} shell zcat /proc/config.gz 2>/dev/null | head -50")
    
    return {
        "version": version.strip(),
        "cmdline": cmdline.strip(),
        "config_sample": config_gz.strip() if config_gz else "Config not available"
    }

# ======================= TERMINAL ROUTES =======================

@api_router.post("/terminal/execute")
async def execute_command(request: CommandRequest):
    """Execute a terminal command"""
    cmd = request.command.strip()
    
    # Security: Block dangerous commands
    dangerous_patterns = ['rm -rf /', 'mkfs', 'dd if=', ':(){', 'fork bomb']
    for pattern in dangerous_patterns:
        if pattern in cmd.lower():
            raise HTTPException(status_code=400, detail=f"Dangerous command blocked: {pattern}")
    
    stdout, stderr, code = await run_command(cmd)
    
    # Store command in history
    await db.command_history.insert_one({
        "id": str(uuid.uuid4()),
        "command": cmd,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": code,
        "session_id": request.session_id,
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
            request.device_context
        )
        
        # Extract commands if auto_execute is enabled
        commands = []
        if request.auto_execute:
            commands = ai_agent.extract_commands(response)
        
        # Store message
        await db.chat_messages.insert_one({
            "id": str(uuid.uuid4()),
            "session_id": request.session_id,
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        await db.chat_messages.insert_one({
            "id": str(uuid.uuid4()),
            "session_id": request.session_id,
            "role": "assistant",
            "content": response,
            "extracted_commands": commands,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "response": response,
            "extracted_commands": commands,
            "session_id": request.session_id
        }
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ai/execute-plan")
async def execute_ai_plan(request: AIRequest, background_tasks: BackgroundTasks):
    """Let AI analyze and execute a multi-step plan"""
    try:
        # Get AI response with commands
        response = await ai_agent.send_message(
            request.session_id,
            request.message,
            request.device_context
        )
        
        commands = ai_agent.extract_commands(response)
        results = []
        
        if request.auto_execute and commands:
            for cmd in commands:
                stdout, stderr, code = await run_command(cmd)
                results.append({
                    "command": cmd,
                    "stdout": stdout,
                    "stderr": stderr,
                    "success": code == 0
                })
                
                # If command failed, stop execution
                if code != 0:
                    break
        
        return {
            "response": response,
            "commands": commands,
            "execution_results": results,
            "all_succeeded": all(r['success'] for r in results) if results else None
        }
    except Exception as e:
        logger.error(f"AI plan execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    session = BuildSession(
        device_serial=request.device_serial,
        halium_version=request.halium_version,
        build_type=request.build_type,
        status="pending"
    )
    
    # Get device codename
    codename = await get_device_prop(request.device_serial, "ro.product.device")
    session.device_codename = codename
    
    # Store session
    doc = session.model_dump()
    doc['started_at'] = doc['started_at'].isoformat()
    if doc['completed_at']:
        doc['completed_at'] = doc['completed_at'].isoformat()
    await db.build_sessions.insert_one(doc)
    
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
async def get_build_logs(session_id: str):
    """Get logs for a build session"""
    session = await db.build_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Build session not found")
    return {"logs": session.get("logs", []), "errors": session.get("errors", [])}

# ======================= HALIUM INFO ROUTES =======================

@api_router.get("/halium/versions")
async def get_halium_versions():
    """Get available Halium versions"""
    return {
        "versions": [
            {"id": "halium-7.1", "name": "Halium 7.1", "android_base": "7.1 Nougat", "status": "stable"},
            {"id": "halium-9.0", "name": "Halium 9.0", "android_base": "9.0 Pie", "status": "stable"},
            {"id": "halium-10.0", "name": "Halium 10.0", "android_base": "10 Q", "status": "stable"},
            {"id": "halium-11.0", "name": "Halium 11.0", "android_base": "11 R", "status": "latest"},
        ]
    }

@api_router.get("/halium/compatibility/{codename}")
async def check_halium_compatibility(codename: str):
    """Check if a device has known Halium support"""
    # This would ideally query the Halium devices wiki
    # For now, return basic info
    return {
        "codename": codename,
        "known_support": None,
        "message": "Compatibility checking requires manual verification at https://github.com/halium/projectmanagement/issues",
        "suggestion": f"Search for '{codename}' in Halium project issues and device wiki"
    }

@api_router.get("/halium/build-steps")
async def get_build_steps():
    """Get the standard Halium build steps"""
    return {
        "steps": [
            {"id": 1, "name": "Environment Setup", "description": "Install build dependencies and configure environment"},
            {"id": 2, "name": "Repo Init", "description": "Initialize Halium manifest repository"},
            {"id": 3, "name": "Device Tree", "description": "Set up device-specific repositories"},
            {"id": 4, "name": "Kernel Config", "description": "Configure kernel for Halium compatibility"},
            {"id": 5, "name": "Vendor Blobs", "description": "Extract or download vendor proprietary files"},
            {"id": 6, "name": "Build System", "description": "Compile the Halium system image"},
            {"id": 7, "name": "Build Kernel", "description": "Compile the Linux kernel"},
            {"id": 8, "name": "Generate Rootfs", "description": "Create the Linux root filesystem"},
            {"id": 9, "name": "Flash & Test", "description": "Flash images to device and verify boot"}
        ]
    }

# ======================= FASTBOOT ROUTES =======================

@api_router.get("/fastboot/devices")
async def list_fastboot_devices():
    """List devices in fastboot mode"""
    stdout, stderr, code = await run_command("fastboot devices")
    devices = []
    if stdout:
        for line in stdout.strip().split('\n'):
            if '\t' in line:
                parts = line.split('\t')
                devices.append({"serial": parts[0], "mode": parts[1] if len(parts) > 1 else "fastboot"})
    return {"devices": devices, "fastboot_available": check_tool_available("fastboot")}

@api_router.get("/fastboot/{serial}/info")
async def get_fastboot_info(serial: str):
    """Get device info via fastboot"""
    info = {}
    props = ["product", "serialno", "secure", "unlocked", "variant", "partition-type:boot"]
    
    for prop in props:
        stdout, _, code = await run_command(f"fastboot -s {serial} getvar {prop} 2>&1")
        if ":" in stdout:
            value = stdout.split(":")[-1].strip()
            info[prop.replace(":", "_")] = value
    
    return {"serial": serial, "info": info}

# ======================= WEBSOCKET ENDPOINT =======================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "command":
                cmd = data.get("command", "")
                stdout, stderr, code = await run_command(cmd)
                await manager.send_message(session_id, {
                    "type": "output",
                    "command": cmd,
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": code
                })
            
            elif data.get("type") == "ai_message":
                message = data.get("message", "")
                device_context = data.get("device_context")
                
                response = await ai_agent.send_message(session_id, message, device_context)
                commands = ai_agent.extract_commands(response)
                
                await manager.send_message(session_id, {
                    "type": "ai_response",
                    "response": response,
                    "commands": commands
                })
                
                # Auto-execute if requested
                if data.get("auto_execute") and commands:
                    for cmd in commands:
                        stdout, stderr, code = await run_command(cmd)
                        await manager.send_message(session_id, {
                            "type": "command_result",
                            "command": cmd,
                            "stdout": stdout,
                            "stderr": stderr,
                            "success": code == 0
                        })
                        if code != 0:
                            break
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)

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
