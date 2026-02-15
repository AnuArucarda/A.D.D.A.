# Security Policy

## Overview

A.D.D.A. (Android Device Developer Agent) takes security seriously. This document outlines our security considerations, known vulnerabilities, mitigation strategies, and responsible disclosure policy.

**Current Version:** v1.0.0  
**Last Updated:** February 15, 2026

---

## Security Model

### Threat Model

**Assets:**
1. User build configurations (stored in MongoDB)
2. API keys (AI providers, GitHub tokens) - in-memory only
3. Factory images (stored temporarily in /tmp/)
4. Build artifacts (kernel images, ROMs)
5. Device access via ADB

**Threat Actors:**
1. **Malicious Users:** Attempting to exploit API endpoints
2. **Network Attackers:** Man-in-the-middle attacks
3. **Insider Threats:** Access to server filesystem
4. **Automated Bots:** Scanning for vulnerabilities

**Attack Vectors:**
1. API injection (SQL, NoSQL, Command)
2. File upload attacks (path traversal, malicious files)
3. Subprocess exploitation (command injection)
4. API key theft
5. Build artifact tampering
6. WebSocket hijacking

---

## Current Security Measures

### 1. Input Validation

**API Endpoints:**
- ✅ All inputs validated via Pydantic models
- ✅ Type checking enforced
- ✅ Required fields validated
- ✅ String length limits (implicit via Pydantic)

**Example:**
```python
class SaveBuildRequest(BaseModel):
    name: str
    type: str  # Limited to: kernel|os|android|recovery|halium
    device_codename: Optional[str] = None
    configuration: Dict
    status: str = "pending"
```

**MongoDB Queries:**
- ✅ No string concatenation for queries
- ✅ Parameterized queries only
- ✅ ObjectId exclusion from API responses
- ✅ Aggregation pipeline reviewed

### 2. Subprocess Execution

**Command Injection Prevention:**
```python
# ❌ VULNERABLE (not used)
os.system(f"git clone {user_url}")

# ✅ SAFE (what we use)
proc = await asyncio.create_subprocess_exec(
    "git", "clone", "--depth=1", user_url, "kernel",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
```

**Isolation:**
- ✅ Builds run in isolated directories (/tmp/linux_forge/)
- ✅ Separate directory per build (UUID-based)
- ✅ Environment variables scoped
- ✅ Timeouts enforced (120s for most operations)

### 3. File Upload Security

**Factory Image Uploads:**
- ✅ File hash verification (SHA256)
- ✅ Path validation via pathlib (no path traversal)
- ✅ Sandboxed extraction directories
- ✅ File type validation (ZIP, TAR only)

**Example:**
```python
# Path traversal prevention
dest_path = FACTORY_IMAGES_DIR / device_codename / filename
# Automatically prevents ../../../etc/passwd
```

**Limitations (⚠️):**
- ❌ No file size limit enforcement (relies on timeout)
- ❌ No antivirus scanning of uploaded files
- ❌ No compression bomb detection

### 4. API Key Management

**Storage:**
- ✅ In-memory only (not persisted to disk/database)
- ✅ Per-user isolation (user_id → token mapping)
- ✅ No logging of sensitive values
- ✅ Environment variables for server keys

**Transmission:**
- ⚠️ HTTPS required (but not enforced in code)
- ⚠️ No encryption at rest (keys in memory)

**Example:**
```python
# Good practice
self.user_tokens: Dict[str, str] = {}  # In-memory only
api_key = os.environ.get('EMERGENT_LLM_KEY')  # From env var

# Never do this
# api_key = "sk-hardcoded-key-here"  # ❌
```

### 5. Database Security

**MongoDB:**
- ✅ Connection string in environment variable
- ✅ ObjectId (_id) excluded from API responses
- ✅ No direct query injection possible
- ✅ Async driver (Motor) with connection pooling

**Current Setup (Development):**
```
MONGO_URL=mongodb://localhost:27017
```

**Production Recommendations:**
- [ ] Enable MongoDB authentication
- [ ] Use TLS/SSL for MongoDB connections
- [ ] Implement role-based access control (RBAC)
- [ ] Enable audit logging

### 6. GitHub Integration

**Token Handling:**
- ✅ Tokens stored per-user (in-memory)
- ✅ Not persisted to database
- ✅ Used only for authorized API calls

**API Usage:**
- ✅ Rate limiting handled by GitHub
- ✅ Token scopes limited to repo operations
- ✅ No token logging

**Limitations (⚠️):**
- ❌ No OAuth flow (uses Personal Access Tokens)
- ❌ Tokens not encrypted in transit (application-level)
- ❌ No token expiration enforcement

### 7. WebSocket Security

**Current Implementation:**
```python
@app.websocket("/ws/build/{build_id}")
async def websocket_build_logs(websocket: WebSocket, build_id: str):
    await websocket.accept()
    # No authentication check
```

**Issues (🚨):**
- ❌ **No authentication** on WebSocket connections
- ❌ Anyone with build_id can connect
- ❌ No rate limiting
- ❌ No origin validation

**Mitigation:**
- Build IDs are UUIDs (hard to guess)
- WebSocket connections are ephemeral
- No sensitive data in logs (intended design)

**Planned Fix (v1.1.0):**
- Implement JWT token authentication
- Validate token before accepting WebSocket

---

## Known Vulnerabilities

### Critical (🚨)

**1. No Authentication System**
- **Severity:** Critical
- **Impact:** Anyone can access all API endpoints
- **Current Mitigation:** Intended for single-user deployment
- **Fix Timeline:** v1.1.0 (JWT auth)

**2. WebSocket Without Auth**
- **Severity:** High
- **Impact:** Anyone with build_id can view logs
- **Current Mitigation:** UUIDs are hard to guess
- **Fix Timeline:** v1.1.0

### High (⚠️)

**3. Subprocess Execution Privileges**
- **Severity:** High
- **Impact:** Builds run with server user privileges
- **Current Mitigation:** Isolated directories, timeouts
- **Recommendation:** Use containers (Docker) for builds

**4. API Key Storage in Memory**
- **Severity:** Medium
- **Impact:** Memory dumps could expose keys
- **Current Mitigation:** Keys not persisted
- **Recommendation:** Use secrets management (HashiCorp Vault)

**5. No Rate Limiting**
- **Severity:** Medium
- **Impact:** API abuse possible
- **Current Mitigation:** None
- **Fix Timeline:** v1.1.0 (Redis-based rate limiting)

### Medium (ℹ️)

**6. CORS Wildcard**
- **Severity:** Medium
- **Impact:** Any origin can access API
- **Current Setup:** `CORS_ORIGINS="*"`
- **Recommendation:** Restrict to known origins

**7. No HTTPS Enforcement**
- **Severity:** Medium
- **Impact:** Credentials could be intercepted
- **Current Setup:** Development uses HTTP
- **Recommendation:** Add HTTPS redirect in production

**8. File Upload Size Limits**
- **Severity:** Low
- **Impact:** Large uploads could exhaust disk space
- **Current Mitigation:** Timeout-based
- **Recommendation:** Add explicit size limits

---

## Security Best Practices for Deployment

### Production Checklist

**Infrastructure:**
- [ ] Deploy behind reverse proxy (Nginx)
- [ ] Enable HTTPS with valid certificates
- [ ] Configure firewall (UFW/iptables)
- [ ] Isolate MongoDB network access
- [ ] Use non-root user for processes

**Application:**
- [ ] Set strong MongoDB credentials
- [ ] Restrict CORS to known origins
- [ ] Enable rate limiting (Redis)
- [ ] Implement JWT authentication
- [ ] Add API key rotation

**Monitoring:**
- [ ] Enable access logs
- [ ] Set up intrusion detection (Fail2Ban)
- [ ] Monitor failed authentication attempts
- [ ] Alert on suspicious activity
- [ ] Regular security audits

**Data:**
- [ ] Encrypt MongoDB connections (TLS)
- [ ] Back up database regularly
- [ ] Encrypt backups
- [ ] Secure secrets management (Vault)
- [ ] Rotate API keys regularly

### Environment Variables

**Required in Production:**
```bash
# MongoDB (with auth)
MONGO_URL=mongodb://user:pass@localhost:27017
DB_NAME=adda_production

# CORS (restrict origins)
CORS_ORIGINS=https://yourdomain.com

# Emergent LLM Key (if using)
EMERGENT_LLM_KEY=sk-emergent-xxxxx

# Optional: JWT secret
JWT_SECRET=your-secret-key-here
```

**Never Commit:**
- ❌ API keys
- ❌ Database passwords
- ❌ JWT secrets
- ❌ GitHub tokens

---

## Secure Coding Guidelines

### For Contributors

**1. Input Validation**
```python
# Always use Pydantic models
class MyRequest(BaseModel):
    name: str  # Automatic validation
    value: int  # Type checking

# Never trust user input
user_input = request.query_params.get("query")
# Validate before use
```

**2. Subprocess Execution**
```python
# ✅ GOOD: Use exec with list
await asyncio.create_subprocess_exec(
    "command", "arg1", "arg2",
    stdout=asyncio.subprocess.PIPE
)

# ❌ BAD: Shell injection possible
await asyncio.create_subprocess_shell(
    f"command {user_input}",  # Dangerous!
    shell=True
)
```

**3. File Operations**
```python
# ✅ GOOD: Use pathlib
from pathlib import Path
safe_path = base_dir / user_filename
# Automatically prevents path traversal

# ❌ BAD: String concatenation
unsafe_path = f"/tmp/{user_filename}"  # Vulnerable
```

**4. MongoDB Queries**
```python
# ✅ GOOD: Parameterized
db.collection.find_one({"id": user_id}, {"_id": 0})

# ❌ BAD: String formatting
query = f"{{id: '{user_id}'}}"  # Injection possible
```

**5. Logging**
```python
# ✅ GOOD: Redact sensitive data
logger.info(f"User {user_id} logged in")

# ❌ BAD: Log sensitive data
logger.info(f"API key: {api_key}")  # Never do this
```

---

## Responsible Disclosure

### Reporting Security Issues

If you discover a security vulnerability in A.D.D.A., please report it responsibly:

**📧 Email:** arucarda@gmail.com  
**Subject:** [SECURITY] A.D.D.A. Vulnerability Report

**Please Include:**
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

**What to Expect:**
- Acknowledgment within 48 hours
- Status update within 7 days
- Fix timeline estimate
- Credit in CHANGELOG (if desired)

**Please Do NOT:**
- Publicly disclose before we've had time to fix
- Exploit the vulnerability
- Test on production instances without permission

---

## Security Roadmap

### v1.1.0 (Next Release)
- [ ] JWT-based authentication
- [ ] WebSocket authentication
- [ ] Rate limiting (Redis-based)
- [ ] API key rotation
- [ ] CORS origin restriction
- [ ] File upload size limits
- [ ] HTTPS enforcement

### v1.2.0
- [ ] OAuth 2.0 integration
- [ ] Role-based access control (RBAC)
- [ ] Container isolation for builds (Docker)
- [ ] Secrets management (Vault integration)
- [ ] Comprehensive audit logging
- [ ] Penetration testing

### v2.0.0
- [ ] End-to-end encryption
- [ ] Zero-knowledge architecture
- [ ] Hardware security module (HSM) support
- [ ] Compliance certifications (SOC 2)

---

## Security Audit History

**v1.0.0 - Initial Release (February 15, 2026)**
- Self-audit completed
- Known issues documented
- Mitigation strategies planned

**Future Audits:**
- Third-party security audit planned for v1.1.0
- Penetration testing planned for v1.2.0

---

## References

**Standards & Frameworks:**
- OWASP Top 10 (2021)
- CWE Top 25 Most Dangerous Software Weaknesses
- NIST Cybersecurity Framework

**Useful Resources:**
- [OWASP API Security Project](https://owasp.org/www-project-api-security/)
- [MongoDB Security Checklist](https://docs.mongodb.com/manual/administration/security-checklist/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

## Disclaimer

A.D.D.A. v1.0.0 is provided "as is" without warranty of any kind. Use in production environments is at your own risk. The author assumes no liability for security breaches or data loss.

For production deployments, we strongly recommend:
1. Professional security audit
2. Implementing all recommended security measures
3. Regular security updates
4. Continuous monitoring

---

## Contact

**Security Team:** arucarda@gmail.com  
**GitHub:** [@AnuArucarda](https://github.com/AnuArucarda)  
**Repository:** https://github.com/AnuArucarda/A.D.D.A.

---

**Last Updated:** February 15, 2026  
**Document Version:** 1.0.0  
**Author:** AnuArucarda
