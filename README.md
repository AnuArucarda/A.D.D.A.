# A.D.D.A. - Android Device Developer Agent

**Making Mobile Devices as Flexible as Desktop Devices**

> *"You should be able to install any operating system you want, whenever you want."*

## 🚀 Vision

A.D.D.A. is a revolutionary, AI-driven platform that makes Android devices as flexible as desktop computers. Install Ubuntu Touch, postmarketOS, Debian, custom Android ROMs, or any Linux distribution on your Android device with unprecedented ease and power.

## ✨ Key Features

### 🤖 Multi-AI Provider System
- Choose from **8 AI providers** (Emergent LLM, OpenAI, Anthropic, Google, Perplexity, Groq, Ollama, llama.cpp)
- Built-in AI with no setup required
- Support for local AI models
- Bring your own API keys

### 📦 Factory Image Management
**Game-changing feature that makes everything accessible:**
- **Auto-Detect:** App automatically downloads factory images for your device
- **From URL:** Paste manufacturer download links
- **Upload:** Drag & drop local factory image files
- Automatic extraction and analysis of boot.img, system.img, vendor.img
- Extract kernel configs, device trees, and proprietary blobs

### 📱 Device Auto-Detection
- Real-time ADB device detection
- Detailed device information (manufacturer, model, Android version, kernel)
- Root status detection
- Remote operations (reboot, flash, install APKs)

### 🔀 Build History & Fork System
- Save all builds with complete configurations
- **Fork previous successful builds** as templates
- Build comparison tools
- Search and filter builds
- Build statistics and analytics

### 🎯 Quick Build Presets
Pre-configured profiles for every use case:
- **Kernel:** Battery Saver, Gaming, Performance, Security Hardened, KernelSU Ready, Docker Ready
- **OS:** Daily Driver, Privacy Focused, Developer, Lightweight, Server
- **Android ROM:** Stock, Privacy, Banking-Compatible, Gaming, Feature Rich
- **Recovery:** TWRP, OrangeFox, PitchBlack, SHRP

### 🔓 Advanced Root Integration
- **13 root solutions:** Magisk family, KernelSU family (Standard, GKI, Wild, Spoofed), APatch
- **6 hiding modules:** SUSFS, Shamiko, Tricky Store, Zygisk Next, LSPosed
- Play Integrity bypass configurations
- Banking app compatibility

### 🐧 Supported Operating Systems

**Mobile Linux:**
- Ubuntu Touch
- postmarketOS
- Droidian
- Mobian
- Plasma Mobile
- LuneOS
- Sailfish OS

**Desktop Linux:**
- Ubuntu, Debian, Arch Linux, Fedora
- Alpine, Manjaro, Void Linux, Gentoo

**Android ROMs:**
- AOSP, LineageOS, Pixel Experience
- crDroid, Evolution X, ArrowOS
- Paranoid Android, Havoc-OS, GrapheneOS

## 🎨 Three Complexity Levels

### Quick Build (Beginners)
5-7 questions → Select preset → Build → Done!

### Selective Build (Intermediate)
15-20 questions covering major customization areas

### AI-Guided Build (Experts)
30+ in-depth questions with complete control over every aspect

## 🏗️ Architecture

### Backend
- **Framework:** FastAPI (Python)
- **Database:** MongoDB
- **AI Integration:** Multi-provider support via Emergent Integrations
- **Device Communication:** ADB/Fastboot automation

### Frontend
- **Framework:** React
- **Styling:** Tailwind CSS with Ubuntu Touch-inspired theme
- **Animations:** Framer Motion
- **Real-time Updates:** Auto-refreshing device detection

### Key Components
- AI Provider Manager
- Factory Image Manager
- Device Manager
- Build History Manager
- Build Orchestrator
- Binary Manager

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ (frontend)
- Python 3.11+ (backend)
- MongoDB
- ADB/Fastboot (for device operations)

### Installation

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001
```

**Frontend:**
```bash
cd frontend
yarn install
yarn start
```

### Environment Setup

**Backend (.env):**
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=linux_device_forge
EMERGENT_LLM_KEY=your_key_here
```

**Frontend (.env):**
```
REACT_APP_BACKEND_URL=http://localhost:8001
```

## 📊 API Endpoints

**65+ API Endpoints** organized by feature:
- AI Providers (5 endpoints)
- Device Management (5 endpoints)
- Build History (9 endpoints)
- Build Templates (3 endpoints)
- Build Presets (2 endpoints)
- Factory Images (10 endpoints)
- Binary Management (4 endpoints)
- Kernel/OS/Android/Recovery/Halium (27+ endpoints)

## 🛠️ Build Tools

### Kernel Forge
Build custom Linux kernels with any configuration:
- LTS kernel versions
- CPU governor selection
- Custom configs (KernelSU, Docker, security hardening)
- Cross-compilation support

### OS Builder
Create bootable Linux images:
- Choose from 15+ distributions
- Package selection
- Desktop environment configuration
- Halium support for Android drivers

### Android ROM Builder
Build custom Android ROMs:
- 10+ ROM bases supported
- GApps configuration
- Root integration
- Security and privacy options
- UI customization

### Recovery Builder
Build custom recoveries:
- TWRP (official)
- OrangeFox (feature-rich)
- PitchBlack (modern UI)
- SHRP (advanced)

## 🎯 Use Cases

### Complete Beginners
*"I want Linux on my phone"*
→ Connect device → Auto-detect → Select Ubuntu Touch → Build → Flash!

### Developers
*"I need a custom kernel with KernelSU"*
→ Fork previous build → Select KernelSU GKI preset → Add Docker support → Build!

### Advanced Users
*"I have factory images"*
→ Upload images → Extract components → Build custom ROM with Magisk Delta + SUSFS!

## 🌟 What Makes This Different

1. **Factory Image Automation** - No more sketchy websites
2. **Multi-AI Freedom** - Use ANY AI provider you prefer
3. **Fork & Iterate** - Learn from successful builds
4. **True Flexibility** - Switch OSes like on a desktop

## 🗺️ Roadmap

### Phase 1 (In Progress)
- ✅ Multi-AI provider system
- ✅ Factory image management
- ✅ Device auto-detection
- ✅ Build history & forking
- ⚠️ Core build automation (in progress)

### Phase 2
- Real-time build log streaming (WebSocket)
- Build queue system
- Build caching
- OTA package generation

### Phase 3
- Community marketplace
- Git integration
- CI/CD support
- Cloud build options

## 📄 License

MIT License - Copyright (c) 2026 AnuArucarda

See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

This project represents a vision of making mobile devices truly flexible and accessible to everyone. Contributions are welcome!

## 📧 Contact

- GitHub: [@AnuArucarda](https://github.com/AnuArucarda)
- Email: arucarda@gmail.com

---

**Built with the vision that mobile devices should be as flexible as desktop devices.**

*Install any OS. Anytime. Anywhere.*
