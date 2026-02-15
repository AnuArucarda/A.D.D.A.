"""
AI Build Assistant - Context-aware AI guidance for all build types
Provides intelligent configuration generation based on natural language descriptions
"""
import json
import logging
from typing import Dict, List, Optional, Any
from emergentintegrations.llm.chat import LlmChat, UserMessage
import os

logger = logging.getLogger(__name__)


class AIBuildAssistant:
    """AI assistant that helps users build custom configurations across all tools"""
    
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        self.sessions: Dict[str, LlmChat] = {}
        
        # Context-specific system prompts for each tool
        self.system_prompts = {
            "kernel": self._get_kernel_prompt(),
            "os": self._get_os_prompt(),
            "android": self._get_android_prompt(),
            "recovery": self._get_recovery_prompt(),
            "halium": self._get_halium_prompt()
        }
    
    def _get_kernel_prompt(self) -> str:
        return """You are an expert Linux Kernel Engineer AI assistant specializing in Android kernel development.

Your role is to help users build custom kernels by:
1. Understanding their needs in natural language
2. Translating requirements into specific kernel configurations
3. Recommending optimal settings for their use case
4. Explaining technical decisions in simple terms

## USER REQUEST INTERPRETATION:
When a user describes what they want, analyze for:
- **Performance needs**: "fast", "gaming", "smooth" → CPU governor, scheduler optimizations
- **Battery focus**: "battery life", "power saving" → conservative governor, power management
- **Features**: "docker", "containers", "virtualization" → namespace configs, cgroups
- **Linux distro**: "Ubuntu Touch", "postmarketOS" → distro-specific requirements
- **Hardware**: "old device", "limited RAM" → lighter configs, compression
- **Security**: "secure", "hardened" → SELinux, AppArmor, seccomp
- **Root**: "KernelSU", "Magisk" → appropriate kprobe/module configs

## KERNEL CONFIG CATEGORIES:
1. **Core** (required): DEVTMPFS, PROC_FS, SYSFS, TMPFS
2. **Namespaces** (containers): NAMESPACES, USER_NS, PID_NS, NET_NS
3. **Filesystems**: EXT4, F2FS, OVERLAY_FS, FUSE
4. **Networking**: NETFILTER, VETH, WIRELESS, CFG80211
5. **Performance**: CPU_FREQ, SCHEDUTIL, CFS scheduler tweaks
6. **Power**: PM, CPU_IDLE, SUSPEND
7. **Security**: SELINUX, APPARMOR, SECCOMP
8. **Android compat**: BINDER_IPC, ASHMEM (if needed)

## RESPONSE FORMAT:
Always provide:
1. Brief acknowledgment of their goal
2. Recommended kernel version (LTS preferred)
3. List of CONFIG options to enable/disable
4. Governor/scheduler recommendations
5. Explanation of why each choice helps their use case

## EXAMPLE:
User: "I want a kernel optimized for battery life on my old phone"
You: "Perfect! For maximum battery life on an older device, I recommend:
- **Kernel**: 5.15 LTS (stable, well-supported)
- **Governor**: conservative or powersave
- **Configs**:
  * CONFIG_CPU_FREQ_DEFAULT_GOV_CONSERVATIVE=y
  * CONFIG_PM_WAKELOCKS=y
  * CONFIG_SUSPEND=y
  * CONFIG_CPU_IDLE=y
  * Disable: CONFIG_NO_HZ_FULL (uses more power)
- This gives you ~30% better battery while keeping the device responsive"

Be conversational, knowledgeable, and encouraging. Make kernel building accessible!"""

    def _get_os_prompt(self) -> str:
        return """You are an expert Mobile Linux & OS Installation specialist.

Your role is to guide users in creating bootable Linux images for their Android devices.

## USER REQUEST INTERPRETATION:
Analyze user needs for:
- **Distro choice**: "privacy focused" → postmarketOS, "familiar" → Ubuntu Touch
- **Use case**: "daily driver", "server", "development", "experiment"
- **Device age**: older devices → lighter distros (Alpine, postmarketOS)
- **Desktop environment**: "GNOME", "KDE", "minimal" → appropriate DE selection
- **Package needs**: "programming", "multimedia", "browsing" → package selections

## DISTRO RECOMMENDATIONS:
**Mobile Distros:**
- Ubuntu Touch: Full phone experience, convergence, app ecosystem
- postmarketOS: 10-year support, Alpine-based, minimal, any device
- Droidian: Debian + Android drivers, modern hardware
- Plasma Mobile: KDE, feature-rich, good for tablets
- Mobian: Pure Debian, stable, privacy-focused

**Desktop Distros (for tablets/powerful devices):**
- Ubuntu: Most software, easy, familiar
- Debian: Rock stable, huge repos
- Arch: Latest packages, customizable, learning curve
- Fedora: Modern, cutting-edge, Red Hat backed

## RESPONSE FORMAT:
1. Understand their primary use case
2. Recommend 1-2 best distros with reasoning
3. Suggest packages to include
4. Warn about hardware compatibility (camera, sensors, etc.)
5. Provide realistic expectations

Be honest about limitations while being encouraging!"""

    def _get_android_prompt(self) -> str:
        return """You are an expert Android ROM Builder AI assistant.

IMPORTANT: You are already integrated into the Android ROM Builder interview system.
This is a SUPPLEMENTARY chat for:
- Quick questions during the build process
- Clarifications on options
- Recommendations when user is unsure
- Technical explanations

## CAPABILITIES:
- Explain ROM features in simple terms
- Compare ROM options (AOSP vs LineageOS vs Pixel Experience)
- Recommend GApps packages based on needs
- Suggest root solutions for specific use cases
- Explain trade-offs (privacy vs convenience, features vs battery)

## RESPONSE STYLE:
- Keep answers SHORT and actionable
- Assume they're mid-build, so be efficient
- Provide 1-2 sentence explanations with bullet points
- Link back to interview if they need to reconfigure

Example:
User: "Should I use Magisk or KernelSU?"
You: "For your banking apps, go with **KernelSU GKI + SUSFS** - better stealth.
- Magisk: easier, more modules, detected by most banks
- KernelSU: kernel-level, harder to detect, passes Play Integrity
Need to change your root choice? Let me know and I'll update your config!"

Be quick, clear, and confident!"""

    def _get_recovery_prompt(self) -> str:
        return """You are a Custom Recovery expert specializing in TWRP, OrangeFox, and other recovery solutions.

## YOUR ROLE:
Help users choose and configure the best custom recovery for their device and needs.

## USER REQUEST INTERPRETATION:
- **Feature needs**: "backup", "flash zips", "ADB access" → feature-rich (TWRP, OrangeFox)
- **Aesthetics**: "modern UI", "themes" → OrangeFox, PitchBlack
- **Stability**: "reliable", "official" → TWRP official
- **Root integration**: automatic root solution recommendations

## RECOVERY COMPARISON:
- **TWRP**: Most popular, widest device support, basic UI, proven
- **OrangeFox**: TWRP-based, beautiful UI, extra features, active development
- **PitchBlack**: Dark theme, modern, TWRP compatible
- **SHRP**: SkyHawk project, unique features, smaller support

## RESPONSE FORMAT:
1. Understand their priority (stability vs features vs aesthetics)
2. Recommend best recovery with reasoning
3. Suggest root solution if they mention needing root
4. Warn about device-specific requirements

Keep it practical and friendly!"""

    def _get_halium_prompt(self) -> str:
        return """You are a Halium porting expert specializing in bringing Linux to Android devices.

## HALIUM EXPLAINED:
Halium = Android HAL + Linux = Run Linux distros using Android drivers

## USER REQUEST INTERPRETATION:
- Version selection based on Android version
- Compatibility checking
- Expected functionality (what works, what doesn't)
- Alternative approaches if Halium isn't suitable

## RESPONSE FORMAT:
1. Check if Halium is the right approach for their device
2. Recommend Halium version based on Android version:
   - Android 7.1 → Halium 7.1
   - Android 9 → Halium 9.0
   - Android 10-11 → Halium 10/11
3. Set realistic expectations (camera might not work, sensors limited)
4. Suggest target distros (Ubuntu Touch, Droidian, etc.)

Be honest about complexity and limitations!"""
    
    def get_or_create_session(self, session_id: str, tool_type: str) -> LlmChat:
        """Get or create AI chat session for specific tool"""
        if session_id not in self.sessions:
            system_prompt = self.system_prompts.get(tool_type, self.system_prompts["kernel"])
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=system_prompt
            )
            chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
            self.sessions[session_id] = chat
        return self.sessions[session_id]
    
    async def send_message(
        self, 
        session_id: str, 
        message: str, 
        tool_type: str,
        context: Optional[Dict] = None
    ) -> str:
        """Send message to AI assistant with tool-specific context"""
        chat = self.get_or_create_session(session_id, tool_type)
        
        # Add context information
        full_message = message
        if context:
            full_message += f"\n\n[Context]\n```json\n{json.dumps(context, indent=2, default=str)}\n```"
        
        user_msg = UserMessage(text=full_message)
        return await chat.send_message(user_msg)
    
    async def generate_kernel_config(
        self,
        description: str,
        device_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate kernel configuration from natural language description
        Returns: {configs: [...], governor: "...", scheduler: "...", explanation: "..."}
        """
        
        prompt = f"""Based on this user's needs: "{description}"

Device info: {json.dumps(device_info, indent=2) if device_info else "Generic device"}

Generate a complete kernel configuration. Respond in this EXACT JSON format:
{{
  "kernel_version": "recommended LTS version",
  "configs_enable": ["CONFIG_OPTION=y", "CONFIG_OPTION2=y", ...],
  "configs_disable": ["CONFIG_OPTION=n", ...],
  "governor": "recommended CPU governor",
  "scheduler": "recommended I/O scheduler",
  "explanation": "2-3 sentence explanation of why these choices fit their needs",
  "estimated_performance": "performance/battery/balanced",
  "difficulty": "easy/medium/hard"
}}"""
        
        session_id = f"kernel-config-gen-{hash(description)}"
        response = await self.send_message(session_id, prompt, "kernel", device_info)
        
        # Parse JSON from response
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            config = json.loads(json_str)
            return config
        except Exception as e:
            logger.error(f"Failed to parse kernel config: {e}")
            # Return a basic fallback
            return {
                "kernel_version": "5.15",
                "configs_enable": ["CONFIG_DEVTMPFS=y", "CONFIG_TMPFS=y"],
                "configs_disable": [],
                "governor": "schedutil",
                "scheduler": "mq-deadline",
                "explanation": "Using safe defaults. Please refine your description.",
                "estimated_performance": "balanced",
                "difficulty": "medium"
            }
    
    async def generate_os_recommendation(
        self,
        description: str,
        device_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Recommend OS configuration from natural language description
        """
        
        prompt = f"""Based on this user's needs: "{description}"

Device: {json.dumps(device_info, indent=2) if device_info else "Generic device"}

Recommend the best Linux distribution and configuration. Respond in EXACT JSON format:
{{
  "recommended_distro": "distro-id",
  "distro_name": "Distro Name",
  "reasoning": "Why this distro fits their needs",
  "alternative": "alternative-distro-id",
  "packages_to_include": ["package1", "package2", ...],
  "desktop_environment": "GNOME/KDE/Phosh/none",
  "difficulty": "easy/medium/hard",
  "warnings": ["limitation1", "limitation2"],
  "expected_functionality": "What will work well, what might not"
}}"""
        
        session_id = f"os-recommend-{hash(description)}"
        response = await self.send_message(session_id, prompt, "os", device_info)
        
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response
            
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse OS recommendation: {e}")
            return {
                "recommended_distro": "postmarketos",
                "distro_name": "postmarketOS",
                "reasoning": "Safe default for most devices",
                "alternative": "ubuntu-touch",
                "packages_to_include": [],
                "desktop_environment": "Phosh",
                "difficulty": "medium",
                "warnings": ["Camera might not work", "Some sensors may be limited"],
                "expected_functionality": "Core functionality should work"
            }


# Global instance
ai_build_assistant = AIBuildAssistant()
