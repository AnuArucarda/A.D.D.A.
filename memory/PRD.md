# Linux Device Forge - Product Requirements Document

## Project Overview
A comprehensive web-based Linux Device Forge that enables building custom Linux kernels and OS images for any Android device. The tool automates kernel development, OS image creation, and Halium porting through an AI-controlled terminal interface.

## Problem Statement
Porting Linux to Android devices requires deep expertise in kernel development, device trees, boot images, and OS customization. This tool unifies and automates these complex processes using AI assistance.

## Target Audience
- Linux kernel developers
- Mobile Linux enthusiasts (Ubuntu Touch, postmarketOS users)
- Device porters and ROM developers
- Embedded systems engineers

## User Personas
1. **Kernel Developer** - Wants to upstream their device's kernel to mainline
2. **Mobile Linux User** - Wants to run Ubuntu Touch or postmarketOS on their device
3. **ROM Developer** - Needs to build custom OS images for devices
4. **Hobbyist** - Curious about running Linux on their phone

---

## Core Architecture

### Tech Stack
- **Frontend**: React 19 + Tailwind CSS + Framer Motion
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI**: Claude Sonnet 4.5 via Emergent LLM Key
- **UI Theme**: Ubuntu Touch/UBports inspired (Aubergine + Orange)

### Three Main Tools

#### 1. Kernel Forge
- Kernel source management (git clone)
- Config analysis (44 requirements for Linux boot)
- Config auto-fix for missing options
- Upstream compatibility analysis (4.x → 5.x → 6.x)
- Kernel compilation with cross-toolchains
- Device tree generation from device info

#### 2. OS Image Builder
- **Mobile Distros (7)**: Ubuntu Touch, postmarketOS, Droidian, Mobian, Plasma Mobile, LuneOS, Sailfish
- **Desktop Distros (8)**: Ubuntu, Debian, Arch, Fedora, Alpine, Manjaro, Void, Gentoo
- Custom rootfs upload support
- Debootstrap-based rootfs creation
- Initramfs generation
- Boot image creation (mkbootimg)

#### 3. Halium Builder (Preserved)
- Halium versions: 7.1, 9.0, 10.0, 11.0
- Android-hybrid Linux approach
- Full build pipeline automation

---

## What's Been Implemented (v2.0 - Feb 15, 2026)

### Backend APIs
- `/api/health` - System health with tool availability
- `/api/devices` - ADB device listing
- `/api/devices/{serial}/info` - Comprehensive device info
- `/api/devices/{serial}/extract-dtb` - DTB/DTBO extraction
- `/api/kernel/projects` - CRUD for kernel projects
- `/api/kernel/projects/{id}/analyze` - Config analysis
- `/api/kernel/projects/{id}/fix-config` - Auto-fix missing configs
- `/api/kernel/projects/{id}/analyze-upstream` - Upstream path analysis
- `/api/kernel/projects/{id}/compile` - Kernel compilation
- `/api/kernel/mainline-versions` - LTS and mainline versions
- `/api/kernel/config-requirements` - 44 config requirements
- `/api/os/distros` - Mobile (7) + Desktop (8) distros
- `/api/os/projects` - CRUD for OS image projects
- `/api/os/projects/{id}/build` - Build OS image
- `/api/os/projects/{id}/upload-rootfs` - Custom rootfs upload
- `/api/halium/versions` - Halium versions
- `/api/halium/build` - Start Halium build
- `/api/ai/chat` - AI assistant with Claude Sonnet 4.5
- `/api/terminal/execute` - Terminal command execution
- WebSocket `/ws/{session_id}` - Real-time streaming

### Frontend
- Three-tool tabbed interface (Kernel Forge, OS Builder, Halium)
- Device panel with ADB info extraction
- Kernel project management with config analysis
- OS distro selection (Mobile/Desktop toggle)
- Custom rootfs upload area
- Halium version selector (preserved)
- Terminal with command execution
- AI Engineer chat with auto-execute option
- Ubuntu Touch themed UI (Aubergine #1A1618, Orange #E95420)

### Testing Results
- Backend: 97% pass rate
- Frontend: 100% pass rate
- Integration: 100% pass rate

---

## Prioritized Backlog

### P0 (Critical)
- [x] Kernel config analysis
- [x] OS distro selection
- [x] AI terminal control
- [ ] Real-time build progress via WebSocket

### P1 (High)
- [ ] Actual kernel compilation execution
- [ ] Debootstrap rootfs creation
- [ ] Boot image generation with mkbootimg
- [ ] DTB extraction and decompilation

### P2 (Medium)
- [ ] Kernel patch management
- [ ] Driver backporting automation
- [ ] Firmware database integration
- [ ] Build artifact storage

### P3 (Low)
- [ ] User authentication
- [ ] Project sharing
- [ ] Build history visualization
- [ ] Export/import configurations

---

## Next Tasks
1. Implement actual kernel compilation with progress streaming
2. Add debootstrap rootfs creation for Debian/Ubuntu
3. Integrate mkbootimg for boot image generation
4. Add DTB → DTS decompilation workflow
5. Implement kernel patch application system

---

## Notes
- ADB/fastboot must be installed on host machine
- Cross-compilation toolchains needed for arm/arm64
- AI can extract and execute commands automatically
- All tools unified under Ubuntu Touch themed interface
