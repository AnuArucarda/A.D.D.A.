# A.D.D.A. Architecture Documentation

## System Overview

A.D.D.A. (Android Device Developer Agent) is a full-stack web application that automates the process of building custom operating systems, kernels, and ROMs for Android devices. The system uses AI assistance, real-time device detection, and GitHub integration to make mobile device development accessible to everyone.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  UI Layer   │  │  Components  │  │  WebSocket       │  │
│  │  (Tailwind) │  │  (Modals)    │  │  Client          │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS / WSS
┌────────────────────────┴────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API Router (75+ endpoints)               │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │ AI Provider │  │   Device    │  │    Factory      │   │
│  │  Manager    │  │   Manager   │  │Image Manager    │   │
│  └─────────────┘  └─────────────┘  └─────────────────┘   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │   Build     │  │   GitHub    │  │     Binary      │   │
│  │Orchestrator │  │ Integration │  │    Manager      │   │
│  └─────────────┘  └─────────────┘  └─────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼────────┐
│   MongoDB    │  │     ADB     │  │   GitHub     │
│   Database   │  │   Fastboot  │  │     API      │
└──────────────┘  └─────────────┘  └──────────────┘
```

---

## Core Components

### Frontend Architecture

**Technology Stack:**
- React 18 (with hooks)
- Tailwind CSS (Ubuntu Touch theme)
- Framer Motion (animations)
- Axios (HTTP client)
- WebSocket client (real-time logs)

**Key Components:**

1. **AIProviderModal** (`/frontend/src/components/AIProviderModal.js`)
   - Manages AI provider selection and authentication
   - Supports 8 different AI providers
   - Handles API key storage and validation

2. **DeviceDetectionPanel** (`/frontend/src/components/DeviceDetectionPanel.js`)
   - Real-time ADB device detection
   - Auto-refresh every 5 seconds
   - Displays device information and status

3. **FactoryImageModal** (`/frontend/src/components/FactoryImageModal.js`)
   - Three-tab interface (Auto/URL/Upload)
   - File upload with drag & drop
   - Image extraction status display

4. **ForkBuildModal** (`/frontend/src/components/ForkBuildModal.js`)
   - Browse previous builds
   - Search and filter functionality
   - Build comparison preview

5. **GitHubIntegrationModal** (`/frontend/src/components/GitHubIntegrationModal.js`)
   - Save/Import/Browse recipes
   - GitHub authentication
   - Community marketplace search

**State Management:**
- React hooks (useState, useEffect, useCallback)
- No global state management (Redux/Context) - intentionally simple
- Local component state with prop drilling

**Communication:**
- REST API via Axios
- WebSocket for real-time build logs
- Environment variables for API URLs

---

### Backend Architecture

**Technology Stack:**
- FastAPI (Python 3.11+)
- Motor (async MongoDB driver)
- asyncio (async/await patterns)
- WebSockets (real-time communication)
- httpx (async HTTP client)

**Module Structure:**

#### 1. **server.py** (Main Application)
- FastAPI app initialization
- 75+ API endpoints
- WebSocket endpoint for build logs
- CORS middleware configuration
- MongoDB connection setup

**Key Endpoints:**
```
/api/ai-providers/*          - AI provider management (5 endpoints)
/api/devices/*                - Device detection & control (5 endpoints)
/api/builds/*                 - Build history & forking (9 endpoints)
/api/templates/*              - Build templates (3 endpoints)
/api/presets/*                - Quick build presets (2 endpoints)
/api/factory-images/*         - Factory image management (10 endpoints)
/api/github/*                 - GitHub integration (8 endpoints)
/api/binaries/*               - Binary tool management (4 endpoints)
/ws/build/{build_id}          - WebSocket for real-time logs
```

#### 2. **ai_provider_manager.py**
**Purpose:** Multi-provider AI system

**Supported Providers:**
- Emergent LLM (built-in, uses emergentintegrations library)
- OpenAI (direct API integration)
- Anthropic (direct API integration)
- Google Gemini (direct API integration)
- Perplexity, Groq (API integrations)
- Ollama, llama.cpp (local models)

**Key Features:**
- Provider configuration management
- API key storage and validation
- Provider status checking
- Unified message sending interface

**Security Considerations:**
- API keys stored in memory (not persisted)
- Separate token management per provider
- No logging of sensitive credentials

#### 3. **device_manager.py**
**Purpose:** Android device detection and management via ADB

**Key Features:**
- Real-time device detection
- Device property extraction (manufacturer, model, Android version, kernel)
- Root status detection
- Custom recovery detection
- Remote operations (reboot, flash, install APK)

**ADB Operations:**
```python
- adb devices -l              # List devices
- adb -s {serial} shell getprop {prop}  # Get properties
- adb -s {serial} reboot recovery       # Reboot to recovery
- fastboot -s {serial} flash {partition} {image}  # Flash image
```

**Security Considerations:**
- All ADB commands executed via asyncio.create_subprocess_exec
- No shell injection (parameterized commands)
- Serial number validation

#### 4. **factory_image_manager.py**
**Purpose:** Factory image upload, download, extraction, and analysis

**Key Features:**
- File upload handling
- URL-based downloads (supports Google, Samsung, etc.)
- Auto-detection and manufacturer matching
- ZIP/TAR extraction
- Boot image unpacking
- Kernel config extraction

**Supported Manufacturers:**
- Google Pixel (fully automated)
- Samsung (manual, Odin format)
- OnePlus, Xiaomi, Motorola (manual)

**File Operations:**
- SHA256 hash calculation for verification
- Async file I/O (aiofiles)
- Extraction to `/tmp/linux_forge/`

**Security Considerations:**
- File size limits (implicit via timeout)
- Hash verification
- Path traversal prevention (Path library usage)
- Sandboxed extraction directories

#### 5. **build_history_manager.py**
**Purpose:** MongoDB-based build tracking, forking, and templates

**Database Schema:**

**builds collection:**
```json
{
  "build_id": "string (UUID)",
  "name": "string",
  "type": "kernel|os|android|recovery|halium",
  "device_codename": "string",
  "configuration": {
    "preset_used": "string",
    "custom_configs": {}
  },
  "forked_from": "build_id (optional)",
  "status": "pending|building|completed|failed",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**build_templates collection:**
```json
{
  "template_id": "string",
  "name": "string",
  "description": "string",
  "type": "string",
  "configuration": {},
  "is_public": "boolean",
  "usage_count": "number",
  "created_at": "datetime"
}
```

**Key Operations:**
- Save build with configuration
- Fork existing build
- Compare two builds (diff algorithm)
- Search builds (regex matching)
- Aggregate statistics

**Security Considerations:**
- MongoDB _id excluded from responses
- Input validation via Pydantic models
- No direct MongoDB query injection

#### 6. **github_integration.py**
**Purpose:** GitHub API integration for recipe sharing

**Key Features:**
- Repository creation
- File commit (recipes as YAML)
- Recipe loading from URLs
- Community recipe search
- Repository forking
- Recipe listing

**GitHub API Usage:**
```python
- POST /user/repos              # Create repository
- PUT /repos/{owner}/{repo}/contents/{path}  # Commit file
- GET /repos/{owner}/{repo}/contents/{path}  # Get file
- GET /search/code              # Search repositories
- POST /repos/{owner}/{repo}/forks  # Fork repository
```

**Security Considerations:**
- GitHub tokens stored per-user (in-memory)
- OAuth not implemented (uses Personal Access Tokens)
- No token persistence
- Rate limiting handled by GitHub API

#### 7. **build_orchestrator.py**
**Purpose:** Actual build execution with subprocess management

**Build Types:**
1. **Kernel Build:**
   - Cross-compiler installation (apt-get)
   - Git clone of kernel source
   - Kernel configuration (make defconfig)
   - Custom config application
   - Kernel compilation (make -j)
   - Output artifact management

2. **OS Build:**
   - Rootfs creation
   - Package installation (debootstrap)
   - Configuration file generation

3. **Android ROM Build:**
   - repo tool management
   - Source synchronization (repo sync)
   - Build environment setup
   - ROM compilation (mka bacon)

4. **Recovery Build:**
   - TWRP/OrangeFox/PitchBlack
   - Manifest initialization
   - Recovery compilation

**Subprocess Execution:**
```python
async def _run_command(cmd, cwd, env):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd,
        env=env
    )
    
    async for line in process.stdout:
        yield line.decode('utf-8')
```

**Security Considerations:**
- Commands executed in isolated directories (/tmp/linux_forge/)
- No user input directly in shell commands
- Environment variable isolation
- Build timeout enforcement

#### 8. **binary_manager.py**
**Purpose:** Tool detection and installation

**Managed Binaries:**
- adb, fastboot (Android platform tools)
- git, make, repo
- gcc, cross-compilers
- dtc (device tree compiler)
- mkbootimg

**Installation Methods:**
- Direct download (platform-tools)
- Package manager (apt-get)
- Git clone (mkbootimg)

**Security Considerations:**
- Downloaded files verified by source URL
- Installation via official package managers
- User-configured paths validated

---

## Data Flow Examples

### Example 1: Building a Kernel

```
1. User selects "Kernel Forge" → chooses preset
2. Frontend sends: POST /api/builds/save
   - Configuration stored in MongoDB
   - build_id returned

3. Frontend establishes WebSocket: /ws/build/{build_id}
4. Frontend sends: {"action": "start_build", "project": {...}}

5. Backend (build_orchestrator):
   - Checks for cross-compiler → installs if needed
   - Clones kernel source (git clone)
   - Configures kernel (make defconfig)
   - Applies custom configs
   - Compiles kernel (make -j)
   - Sends real-time logs via WebSocket

6. Build completes:
   - WebSocket sends: {"type": "complete", "success": true}
   - Frontend updates UI
   - User downloads artifacts
```

### Example 2: Forking a Build

```
1. User clicks "Fork" button on a previous build
2. Frontend: GET /api/builds/{build_type}/successful
3. Backend queries MongoDB: db.builds.find({"type": ..., "status": "completed"})
4. User selects build to fork
5. Frontend: POST /api/builds/{build_id}/fork
6. Backend:
   - Retrieves source build
   - Copies configuration
   - Creates new build object
   - Returns forked configuration
7. User modifies and starts new build
```

### Example 3: GitHub Recipe Sharing

```
1. User completes successful build
2. User clicks "Save to GitHub"
3. Frontend shows GitHubIntegrationModal
4. User authenticates with GitHub token
5. Frontend: POST /api/github/set-token
6. User selects repository or creates new one
7. Frontend: POST /api/github/save-recipe
8. Backend:
   - Converts build config to YAML
   - Commits to GitHub via API
   - Returns file URL
9. Recipe now shareable via GitHub URL
```

---

## Security Considerations

### Authentication & Authorization
**Current State:** No authentication implemented
**Reason:** MVP focused on functionality
**Future:** JWT-based authentication planned for v1.1.0

### Input Validation
- All API inputs validated via Pydantic models
- MongoDB queries use parameterized operations
- File paths validated with pathlib
- No direct shell command injection

### API Key Management
- AI provider keys stored in memory only
- GitHub tokens not persisted
- Emergent LLM key in environment variable
- No plaintext credential logging

### Subprocess Execution
- Commands executed in isolated directories
- Environment variables scoped per build
- No user input directly concatenated to shell commands
- Timeout enforcement (prevents infinite builds)

### File Uploads
- Uploads to sandboxed directory (/tmp/linux_forge/)
- File hash verification (SHA256)
- Size limits enforced via httpx timeouts
- No path traversal attacks (Path library usage)

### MongoDB Security
- ObjectId exclusion from API responses
- No direct query string injection
- Aggregation pipeline safety
- Connection string in environment variable

### GitHub Integration
- Personal Access Tokens (not OAuth)
- Tokens scoped to user session
- No token persistence
- Rate limiting by GitHub API

### WebSocket Security
- No authentication on WebSocket (planned for v1.1.0)
- Build logs streamed per build_id
- No cross-build log leakage
- Disconnect handling

---

## Scalability Considerations

### Current Limitations
1. **Single Machine:** All builds run on one server
2. **No Queue:** Concurrent builds may cause resource contention
3. **In-Memory State:** User sessions not persisted
4. **No Caching:** Repeated builds re-download/recompile

### Planned Improvements (v1.1.0+)
1. **Build Queue:** Redis-based task queue (Celery)
2. **Distributed Builds:** Kubernetes for scaling build workers
3. **Build Caching:** Cache compiled artifacts (Docker layers)
4. **Session Persistence:** Redis for user sessions
5. **CDN:** Static assets via CDN

---

## Testing Strategy

### Current Testing
- Manual testing via curl and browser
- ADB device testing with real devices
- GitHub API testing with test repositories

### Planned Testing (v1.1.0)
1. **Unit Tests:** pytest for backend modules
2. **Integration Tests:** API endpoint testing
3. **E2E Tests:** Playwright for frontend flows
4. **Load Tests:** Locust for API performance
5. **Security Tests:** OWASP ZAP scanning

---

## Deployment Architecture

### Current Setup (Development)
```
Frontend: http://localhost:3000 (React dev server)
Backend:  http://localhost:8001 (uvicorn)
MongoDB:  mongodb://localhost:27017
```

### Production Deployment (Planned)
```
Frontend → Nginx → Static files
Backend  → Gunicorn + Uvicorn workers
MongoDB  → MongoDB Atlas (managed)
Builds   → Kubernetes pods (isolated)
```

---

## Performance Considerations

### Backend
- **Async/await:** All I/O operations are async
- **Connection Pooling:** Motor handles MongoDB connections
- **Subprocess Management:** Builds run asynchronously
- **WebSocket:** Efficient real-time communication

### Frontend
- **Code Splitting:** React lazy loading (future)
- **Memoization:** useMemo/useCallback for expensive operations
- **Debouncing:** Search inputs debounced
- **Efficient Rendering:** Framer Motion optimized animations

### Database
- **Indexes:** Needed on build_id, type, device_codename
- **Aggregation:** Statistics calculated on-demand
- **No N+1 Queries:** Single queries for listings

---

## Error Handling

### Backend Strategy
```python
try:
    # Operation
except SpecificException as e:
    logger.error(f"Context: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

### Frontend Strategy
```javascript
try {
  const res = await axios.post(endpoint, data);
  toast.success('Success message');
} catch (e) {
  toast.error(e.response?.data?.detail || 'Generic error');
}
```

### Build Failures
- Real-time log streaming shows exact failure point
- Error messages returned via WebSocket
- Build status updated in MongoDB
- Artifacts preserved for debugging

---

## Monitoring & Logging

### Current Logging
- Python logging module (INFO level)
- Console logs for frontend
- MongoDB operations logged

### Future Monitoring (v1.1.0)
- Prometheus metrics
- Grafana dashboards
- ELK stack for log aggregation
- Sentry for error tracking

---

## Contributing Guidelines

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution process.

---

## API Documentation

Full API documentation available via:
- FastAPI auto-generated docs: http://localhost:8001/docs
- ReDoc documentation: http://localhost:8001/redoc

---

## Technology Choices & Rationale

### Why FastAPI?
- Async support (critical for long builds)
- Auto-generated API docs
- Pydantic validation
- WebSocket support
- Modern Python features

### Why React?
- Component reusability
- Large ecosystem
- Excellent performance
- Great developer experience

### Why MongoDB?
- Flexible schema (build configs vary greatly)
- JSON-like documents (matches API responses)
- Easy aggregation (build statistics)
- Async driver available (Motor)

### Why WebSockets?
- Real-time build logs essential
- Low latency
- Bidirectional communication
- Better than polling

---

## Future Architecture Changes

### v1.1.0
- Add Redis for caching and sessions
- Implement JWT authentication
- Add Celery for task queue

### v1.2.0
- Kubernetes deployment
- Microservices split (build service, API service)
- GraphQL API option

### v2.0.0
- gRPC for internal services
- Event-driven architecture (Kafka)
- Multi-region deployment

---

**Document Version:** 1.0.0  
**Last Updated:** February 15, 2026  
**Author:** AnuArucarda
