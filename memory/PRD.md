# Linux Device Forge v3.0 - Product Requirements Document

## Project Overview
A comprehensive web-based platform for building custom Linux kernels, OS images, Android ROMs, and Halium ports for any Android device. Features AI-controlled automation through conversational interfaces.

## Problem Statement
Building custom software for Android devices (Linux ports, custom ROMs, kernels) requires deep expertise. This platform automates and simplifies these processes through AI-guided workflows.

## Target Audience
- Linux kernel developers
- Mobile Linux enthusiasts  
- Android ROM developers
- Device porters
- Hobbyists wanting custom phone software

---

## Four Main Tools

### 1. Kernel Forge
Build, upstream, and backport Linux kernels for any device.
- Kernel source management (git)
- Config analysis (35+ requirements)
- Auto-fix missing configs
- Upstream compatibility analysis (4.x → 6.x)
- Kernel compilation
- Device tree generation

### 2. OS Image Builder
Create bootable Linux images from any distribution.
- **Mobile Distros (7)**: Ubuntu Touch, postmarketOS, Droidian, Mobian, Plasma Mobile, LuneOS, Sailfish
- **Desktop Distros (8)**: Ubuntu, Debian, Arch, Fedora, Alpine, Manjaro, Void, Gentoo
- Custom rootfs upload
- Initramfs generation
- Boot image creation

### 3. Android ROM Builder (NEW)
AI-guided custom Android ROM creation through conversational interview.
- **Interview Depths**:
  - Quick (5-7 questions)
  - Standard (15-20 questions)
  - Expert (30+ questions)
- **ROM Bases (10)**: AOSP, LineageOS, Pixel Experience, crDroid, Evolution X, ArrowOS, Paranoid Android, Havoc-OS, Resurrection Remix, GrapheneOS
- **Customization Options**: Kernel type, GApps, Root, Security, UI, Performance, Camera, Audio
- AI asks questions to understand exactly what user wants
- Generates complete build configuration

### 4. Halium Builder
Android-hybrid Linux porting (preserved).
- Halium 7.1, 9.0, 10.0, 11.0
- Full build pipeline automation

---

## Tech Stack
- **Frontend**: React 19 + Tailwind CSS + Framer Motion
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **AI**: Claude Sonnet 4.5 via Emergent LLM Key
- **UI Theme**: Ubuntu Touch inspired (Aubergine + Orange + Android Green)

---

## What's Been Implemented (v3.0 - Feb 15, 2026)

### Backend APIs
- `/api/android/interview-depths` - Quick/Standard/Expert options
- `/api/android/rom-bases` - 10 Android ROM bases
- `/api/android/build-features` - All customization options
- `/api/android/projects` - Create Android build project
- `/api/android/projects/{id}/interview` - AI interview chat
- `/api/android/projects/{id}/build` - Start ROM build
- All previous APIs preserved (kernel, os, halium, devices, terminal, ai)

### Frontend
- **Four tool tabs**: Kernel Forge, OS Builder, Android ROM, Halium
- **Android ROM Builder**:
  - Interview depth selection (Quick/Standard/Expert cards)
  - "Start Building Your ROM" button (Android green)
  - ROM bases display (10 options)
  - Chat interface for AI interview
  - Progress tracking
- All previous UI preserved

### AI Android Interview System
- Dedicated system prompt for ROM building
- Conversational Q&A flow
- Adapts questions based on depth level
- Remembers all previous answers
- Generates build configuration from answers

---

## Prioritized Backlog

### P0 (Critical)
- [x] AI interview system for Android builds
- [x] Interview depth selection
- [ ] Real ROM build execution

### P1 (High)
- [ ] Interview answer parsing to build config
- [ ] Manifest generation for Android builds
- [ ] Real-time build progress via WebSocket

### P2 (Medium)
- [ ] Save/load build configurations
- [ ] Share configurations with community
- [ ] Build artifact storage

---

## Next Tasks
1. Implement build config generation from interview answers
2. Add repo/manifest handling for Android builds
3. Connect to actual build farm/server
4. Add build progress streaming
5. Implement kernel compilation for Kernel Forge

---

## Notes
- Android ROM Builder uses conversational AI for configuration
- Interview depth determines question count and detail level
- All four tools share device detection and terminal access
- AI can control terminal for automated execution
