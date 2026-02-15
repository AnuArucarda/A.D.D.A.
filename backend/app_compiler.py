"""
App Compiler - Generates standalone desktop and mobile apps
"""
import os
import platform
import asyncio
import json
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
import aiofiles
import logging

logger = logging.getLogger(__name__)

WORK_DIR = Path("/tmp/linux_forge")
EXPORT_DIR = WORK_DIR / "app_exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


class AppCompiler:
    """Compile the web app into standalone desktop/mobile applications"""
    
    def __init__(self):
        self.supported_platforms = {
            "linux_deb": {
                "name": "Debian/Ubuntu Package (.deb)",
                "description": "Native Linux app for Debian-based systems (Ubuntu, Mint, Pop!_OS)",
                "method": "electron",
                "format": ".deb"
            },
            "linux_appimage": {
                "name": "Linux AppImage (Universal)",
                "description": "Portable Linux app that runs on any distro without installation",
                "method": "electron",
                "format": ".AppImage"
            },
            "linux_rpm": {
                "name": "Red Hat Package (.rpm)",
                "description": "Native Linux app for RHEL-based systems (Fedora, CentOS, openSUSE)",
                "method": "electron",
                "format": ".rpm"
            },
            "linux_flatpak": {
                "name": "Flatpak",
                "description": "Sandboxed Linux app with automatic updates",
                "method": "electron",
                "format": ".flatpak"
            },
            "android_apk": {
                "name": "Android App (.apk)",
                "description": "Native Android app with embedded build environment",
                "method": "capacitor",
                "format": ".apk"
            },
            "windows_exe": {
                "name": "Windows Installer (.exe)",
                "description": "Native Windows application",
                "method": "electron",
                "format": ".exe"
            },
            "macos_dmg": {
                "name": "macOS App (.dmg)",
                "description": "Native macOS application",
                "method": "electron",
                "format": ".dmg"
            }
        }
        
        self.ai_providers = {
            "emergent": {
                "name": "Emergent LLM (Universal Key)",
                "models": ["claude-sonnet-4-5", "gpt-4o", "gemini-2-flash"],
                "requires_key": False,
                "built_in": True
            },
            "openai": {
                "name": "OpenAI",
                "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
                "requires_key": True,
                "built_in": False
            },
            "anthropic": {
                "name": "Anthropic Claude",
                "models": ["claude-sonnet-4-5", "claude-opus-4", "claude-haiku-3-5"],
                "requires_key": True,
                "built_in": False
            },
            "google": {
                "name": "Google Gemini",
                "models": ["gemini-2-flash", "gemini-2-pro", "gemini-1.5-pro"],
                "requires_key": True,
                "built_in": False
            },
            "ollama": {
                "name": "Ollama (Local)",
                "models": ["llama3.3", "qwen2.5-coder", "deepseek-coder", "mixtral"],
                "requires_key": False,
                "built_in": False,
                "local": True
            },
            "lmstudio": {
                "name": "LM Studio (Local)",
                "models": ["custom"],
                "requires_key": False,
                "built_in": False,
                "local": True
            }
        }
    
    async def generate_electron_config(self, platform_type: str, ai_config: Dict) -> str:
        """Generate Electron configuration for desktop apps"""
        
        config = {
            "name": "linux-device-forge",
            "productName": "Linux Device Forge",
            "version": "3.0.0",
            "description": "Android to Linux Device Converter",
            "main": "electron-main.js",
            "author": "Linux Device Forge Team",
            "license": "MIT",
            "build": {
                "appId": "com.linuxforge.app",
                "productName": "Linux Device Forge",
                "directories": {
                    "output": "dist"
                },
                "files": [
                    "build/**/*",
                    "backend/**/*",
                    "electron-main.js",
                    "preload.js"
                ],
                "linux": {
                    "target": ["deb", "AppImage", "rpm"],
                    "category": "Development",
                    "icon": "assets/icon.png"
                },
                "win": {
                    "target": ["nsis"],
                    "icon": "assets/icon.ico"
                },
                "mac": {
                    "target": ["dmg"],
                    "icon": "assets/icon.icns",
                    "category": "public.app-category.developer-tools"
                }
            },
            "scripts": {
                "start": "electron .",
                "build": "electron-builder",
                "build:linux": "electron-builder --linux",
                "build:win": "electron-builder --win",
                "build:mac": "electron-builder --mac"
            },
            "devDependencies": {
                "electron": "^28.0.0",
                "electron-builder": "^24.9.1"
            },
            "ai_config": ai_config
        }
        
        return json.dumps(config, indent=2)
    
    async def generate_electron_main(self, ai_config: Dict) -> str:
        """Generate Electron main process code"""
        
        main_js = f"""
const {{ app, BrowserWindow, ipcMain }} = require('electron');
const path = require('path');
const {{ spawn }} = require('child_process');

let mainWindow;
let backendProcess;

// AI Configuration
const AI_CONFIG = {json.dumps(ai_config, indent=2)};

// Start Python backend
function startBackend() {{
    const backendPath = path.join(__dirname, 'backend', 'server.py');
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    
    backendProcess = spawn(pythonCmd, [backendPath], {{
        env: {{
            ...process.env,
            AI_PROVIDER: AI_CONFIG.provider,
            AI_API_KEY: AI_CONFIG.api_key || '',
            AI_MODEL: AI_CONFIG.model || '',
            OLLAMA_HOST: AI_CONFIG.ollama_host || 'http://localhost:11434'
        }}
    }});
    
    backendProcess.stdout.on('data', (data) => {{
        console.log(`Backend: ${{data}}`);
    }});
    
    backendProcess.stderr.on('data', (data) => {{
        console.error(`Backend Error: ${{data}}`);
    }});
}}

function createWindow() {{
    mainWindow = new BrowserWindow({{
        width: 1400,
        height: 900,
        icon: path.join(__dirname, 'assets', 'icon.png'),
        webPreferences: {{
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        }}
    }});
    
    // Wait for backend to start, then load frontend
    setTimeout(() => {{
        mainWindow.loadURL('http://localhost:3000');
    }}, 3000);
    
    mainWindow.on('closed', () => {{
        mainWindow = null;
    }});
}}

app.whenReady().then(() => {{
    startBackend();
    createWindow();
    
    app.on('activate', () => {{
        if (BrowserWindow.getAllWindows().length === 0) {{
            createWindow();
        }}
    }});
}});

app.on('window-all-closed', () => {{
    if (backendProcess) {{
        backendProcess.kill();
    }}
    if (process.platform !== 'darwin') {{
        app.quit();
    }}
}});

app.on('before-quit', () => {{
    if (backendProcess) {{
        backendProcess.kill();
    }}
}});

// IPC handlers for AI configuration updates
ipcMain.handle('get-ai-config', () => {{
    return AI_CONFIG;
}});

ipcMain.handle('update-ai-config', (event, newConfig) => {{
    Object.assign(AI_CONFIG, newConfig);
    // Restart backend with new config
    if (backendProcess) {{
        backendProcess.kill();
        startBackend();
    }}
    return {{ success: true }};
}});
"""
        return main_js
    
    async def generate_capacitor_config(self, ai_config: Dict) -> str:
        """Generate Capacitor configuration for Android app"""
        
        config = {
            "appId": "com.linuxforge.app",
            "appName": "Linux Device Forge",
            "webDir": "build",
            "bundledWebRuntime": False,
            "plugins": {
                "SplashScreen": {
                    "launchShowDuration": 2000,
                    "backgroundColor": "#2C001E"
                }
            },
            "server": {
                "androidScheme": "https"
            },
            "android": {
                "buildOptions": {
                    "keystorePath": "android/app/release.keystore",
                    "keystoreAlias": "linuxforge"
                }
            },
            "ai_config": ai_config
        }
        
        return json.dumps(config, indent=2)
    
    async def generate_dockerfile(self, ai_config: Dict) -> str:
        """Generate Dockerfile for containerized local deployment"""
        
        dockerfile = f"""
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \\
    python3.11 python3-pip nodejs npm git curl \\
    adb fastboot build-essential gcc-aarch64-linux-gnu \\
    && rm -rf /var/lib/apt/lists/*

# Copy application
WORKDIR /app
COPY backend /app/backend
COPY frontend /app/frontend

# Install Python dependencies
RUN pip3 install -r /app/backend/requirements.txt

# Install Node dependencies and build frontend
WORKDIR /app/frontend
RUN npm install && npm run build

# Set AI configuration
ENV AI_PROVIDER={ai_config.get('provider', 'emergent')}
ENV AI_API_KEY={ai_config.get('api_key', '')}
ENV AI_MODEL={ai_config.get('model', '')}

# Expose ports
EXPOSE 3000 8001

# Start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
"""
        return dockerfile
    
    async def compile_app(self, platform_type: str, ai_config: Dict) -> Dict:
        """
        Compile the app for specified platform
        Returns: {'success': bool, 'message': str, 'download_url': Optional[str]}
        """
        
        if platform_type not in self.supported_platforms:
            return {
                "success": False,
                "message": f"Unsupported platform: {platform_type}"
            }
        
        platform_info = self.supported_platforms[platform_type]
        export_name = f"linux-forge-{platform_type}-{ai_config.get('provider', 'emergent')}"
        export_path = EXPORT_DIR / export_name
        export_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Generate configuration files
            if platform_info["method"] == "electron":
                # Desktop app compilation
                package_json = await self.generate_electron_config(platform_type, ai_config)
                main_js = await self.generate_electron_main(ai_config)
                
                async with aiofiles.open(export_path / "package.json", 'w') as f:
                    await f.write(package_json)
                
                async with aiofiles.open(export_path / "electron-main.js", 'w') as f:
                    await f.write(main_js)
                
                # Create README
                readme = await self._generate_readme(platform_type, ai_config)
                async with aiofiles.open(export_path / "README.md", 'w') as f:
                    await f.write(readme)
                
                message = f"Desktop app package created for {platform_info['name']}"
                
            elif platform_info["method"] == "capacitor":
                # Android app compilation
                cap_config = await self.generate_capacitor_config(ai_config)
                
                async with aiofiles.open(export_path / "capacitor.config.json", 'w') as f:
                    await f.write(cap_config)
                
                # Create build instructions
                instructions = await self._generate_android_instructions(ai_config)
                async with aiofiles.open(export_path / "BUILD_INSTRUCTIONS.md", 'w') as f:
                    await f.write(instructions)
                
                message = f"Android app package created"
            
            # Create zip package
            zip_path = EXPORT_DIR / f"{export_name}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(export_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(export_path)
                        zipf.write(file_path, arcname)
            
            return {
                "success": True,
                "message": message,
                "package_path": str(zip_path),
                "platform": platform_info['name'],
                "ai_provider": ai_config.get('provider', 'emergent')
            }
            
        except Exception as e:
            logger.error(f"App compilation error: {e}")
            return {
                "success": False,
                "message": f"Compilation failed: {str(e)}"
            }
    
    async def _generate_readme(self, platform_type: str, ai_config: Dict) -> str:
        """Generate README for compiled app"""
        
        readme = f"""# Linux Device Forge - Local Desktop App

## Platform: {self.supported_platforms[platform_type]['name']}
## AI Provider: {ai_config.get('provider', 'emergent').upper()}

### Installation Instructions

"""
        
        if "deb" in platform_type:
            readme += """
#### Debian/Ubuntu Installation:
```bash
sudo dpkg -i linux-device-forge.deb
sudo apt-get install -f  # Fix dependencies if needed
```

Run the app: `linux-device-forge` or find it in your applications menu.
"""
        
        elif "appimage" in platform_type:
            readme += """
#### AppImage Installation:
```bash
chmod +x LinuxDeviceForge.AppImage
./LinuxDeviceForge.AppImage
```

No installation needed! Just run the AppImage file.
"""
        
        elif "rpm" in platform_type:
            readme += """
#### Fedora/RHEL Installation:
```bash
sudo rpm -i linux-device-forge.rpm
# OR
sudo dnf install linux-device-forge.rpm
```
"""
        
        readme += f"""

### AI Configuration

This build is configured to use: **{ai_config.get('provider', 'emergent')}**

"""
        
        if ai_config.get('provider') == 'emergent':
            readme += """
✓ Using Emergent LLM - No additional setup required!
The app uses the built-in Emergent universal API key.
"""
        else:
            readme += f"""
⚠️ API Key Required!

You need to configure your {ai_config.get('provider')} API key:

1. Open the app
2. Go to Settings → AI Configuration
3. Enter your API key
4. Select your preferred model

**Get your API key:**
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com/
- Google: https://makersuite.google.com/app/apikey
"""
        
        readme += """

### System Requirements

- **OS:** Linux (any modern distro)
- **RAM:** 4GB minimum, 8GB recommended
- **Storage:** 10GB free space (200GB+ for Android ROM builds)
- **Build Tools:** adb, fastboot, git (can be auto-installed)

### Features

✅ Kernel Forge - Build & upstream Linux kernels
✅ OS Builder - Create Linux images for any distro
✅ Android ROM Builder - AI-guided custom ROM creation
✅ Recovery Builder - Build TWRP, OrangeFox, etc.
✅ Halium Builder - Hybrid Android/Linux ports
✅ Binary Manager - Auto-install missing tools
✅ AI Assistant - Powered by Claude Sonnet 4.5

### Usage

1. Connect your Android device via USB
2. Enable USB debugging on your device
3. Launch Linux Device Forge
4. Follow the AI-guided workflows

### Troubleshooting

**Backend not starting?**
```bash
# Check if Python 3.11+ is installed
python3 --version

# Manually start backend for debugging
cd /opt/linux-device-forge/backend
python3 server.py
```

**Frontend not loading?**
- Check if backend is running on port 8001
- Try accessing directly: http://localhost:3000

### Support

- Issues: https://github.com/linux-device-forge/issues
- Docs: https://docs.linuxforge.dev
- Community: https://discord.gg/linuxforge

---
*Built with Linux Device Forge Compiler v3.0*
"""
        
        return readme
    
    async def _generate_android_instructions(self, ai_config: Dict) -> str:
        """Generate build instructions for Android app"""
        
        instructions = f"""# Android App Build Instructions

## Prerequisites

1. **Android Studio** (latest version)
2. **Node.js** 18+ and npm
3. **Java JDK** 17+
4. **Capacitor CLI**: `npm install -g @capacitor/cli`

## Build Steps

### 1. Prepare the Project

```bash
# Install dependencies
npm install

# Add Android platform
npx cap add android

# Copy web assets to Android project
npx cap sync android
```

### 2. Configure AI Provider

Edit `android/app/src/main/assets/capacitor.config.json`:

```json
{{
  "ai_config": {{
    "provider": "{ai_config.get('provider', 'emergent')}",
    "api_key": "YOUR_API_KEY_HERE",
    "model": "{ai_config.get('model', 'claude-sonnet-4-5')}"
  }}
}}
```

### 3. Build APK

#### Debug Build (for testing):
```bash
cd android
./gradlew assembleDebug
```
Output: `android/app/build/outputs/apk/debug/app-debug.apk`

#### Release Build (for distribution):
```bash
# First, create a signing key
keytool -genkey -v -keystore release.keystore -alias linuxforge -keyalg RSA -keysize 2048 -validity 10000

# Build signed APK
./gradlew assembleRelease
```
Output: `android/app/build/outputs/apk/release/app-release.apk`

### 4. Install on Device

```bash
# Via ADB
adb install app-debug.apk

# Or open in Android Studio and click "Run"
```

## Features in Android App

✓ Full build environment (uses Termux components)
✓ ADB over WiFi support
✓ Kernel building
✓ Recovery installation
✓ Works offline (except AI calls)

## Troubleshooting

**Build fails?**
- Ensure Java 17 is set: `export JAVA_HOME=/path/to/jdk17`
- Clean build: `./gradlew clean`

**App crashes on start?**
- Check logcat: `adb logcat | grep LinuxForge`
- Verify API key is set correctly

## Publishing to Play Store

1. Create Play Console account
2. Prepare store listing (screenshots, description)
3. Upload signed APK
4. Submit for review

---
*Android build powered by Capacitor*
"""
        
        return instructions


# Global instance
app_compiler = AppCompiler()
