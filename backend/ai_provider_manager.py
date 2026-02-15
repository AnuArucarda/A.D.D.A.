"""
AI Provider Manager - Flexible multi-provider AI system
Supports Claude, OpenAI (ChatGPT), Gemini, Perplexity, and local models
"""
import os
import json
import logging
from typing import Dict, Optional, List, Any
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

class AIProvider(str, Enum):
    EMERGENT = "emergent"  # Emergent LLM Key (Claude)
    OPENAI = "openai"  # ChatGPT
    ANTHROPIC = "anthropic"  # Direct Claude
    GOOGLE = "google"  # Gemini
    PERPLEXITY = "perplexity"  # Perplexity
    GROQ = "groq"  # Groq (fast inference)
    OLLAMA = "ollama"  # Local Ollama
    LLAMACPP = "llamacpp"  # Local llama.cpp

class AIProviderManager:
    """
    Manages multiple AI providers with flexible authentication
    Allows users to choose their preferred AI backend
    """
    
    def __init__(self):
        self.providers_config = self._get_providers_config()
        self.user_credentials: Dict[str, str] = {}  # provider -> api_key
        self.default_provider = AIProvider.EMERGENT
        
    def _get_providers_config(self) -> Dict[str, Dict[str, Any]]:
        """Get configuration for all supported AI providers"""
        return {
            AIProvider.EMERGENT: {
                "name": "Emergent LLM",
                "description": "Built-in AI using Emergent Universal Key",
                "requires_auth": False,
                "requires_api_key": False,
                "built_in": True,
                "models": [
                    "claude-sonnet-4-5-20250929",
                    "claude-sonnet-4-20250514",
                    "gpt-5.2",
                    "gemini-2.5-pro"
                ],
                "default_model": "claude-sonnet-4-5-20250929",
                "features": ["chat", "code_generation", "config_generation"],
                "cost": "Included with Emergent"
            },
            AIProvider.OPENAI: {
                "name": "OpenAI (ChatGPT)",
                "description": "ChatGPT o1, o3-mini, GPT-5.2, GPT-4, etc.",
                "requires_auth": True,
                "requires_api_key": True,
                "built_in": False,
                "auth_url": "https://platform.openai.com/api-keys",
                "auth_instructions": "Sign in to OpenAI Platform and create an API key",
                "models": [
                    "gpt-5.2",
                    "gpt-4o",
                    "gpt-4-turbo",
                    "gpt-4",
                    "o1",
                    "o3-mini"
                ],
                "default_model": "gpt-4o",
                "features": ["chat", "code_generation", "vision"],
                "cost": "Pay per token"
            },
            AIProvider.ANTHROPIC: {
                "name": "Anthropic (Claude)",
                "description": "Direct Claude API access",
                "requires_auth": True,
                "requires_api_key": True,
                "built_in": False,
                "auth_url": "https://console.anthropic.com/",
                "auth_instructions": "Sign in to Anthropic Console and create an API key",
                "models": [
                    "claude-sonnet-4-5-20250929",
                    "claude-sonnet-4-20250514",
                    "claude-opus-4-20250514",
                    "claude-3-5-sonnet-20240620"
                ],
                "default_model": "claude-sonnet-4-5-20250929",
                "features": ["chat", "code_generation", "long_context"],
                "cost": "Pay per token"
            },
            AIProvider.GOOGLE: {
                "name": "Google (Gemini)",
                "description": "Gemini 2.5 Pro, Flash, etc.",
                "requires_auth": True,
                "requires_api_key": True,
                "built_in": False,
                "auth_url": "https://makersuite.google.com/app/apikey",
                "auth_instructions": "Sign in with Google and create an API key",
                "models": [
                    "gemini-2.5-pro",
                    "gemini-2.5-flash",
                    "gemini-2.0-flash-exp",
                    "gemini-1.5-pro"
                ],
                "default_model": "gemini-2.5-pro",
                "features": ["chat", "vision", "multimodal"],
                "cost": "Free tier available, then pay per token"
            },
            AIProvider.PERPLEXITY: {
                "name": "Perplexity",
                "description": "AI with real-time web search",
                "requires_auth": True,
                "requires_api_key": True,
                "built_in": False,
                "auth_url": "https://www.perplexity.ai/settings/api",
                "auth_instructions": "Sign in to Perplexity and get API key from settings",
                "models": [
                    "sonar",
                    "sonar-pro",
                    "codellama-70b-instruct"
                ],
                "default_model": "sonar",
                "features": ["chat", "web_search", "real_time_info"],
                "cost": "Pay per request"
            },
            AIProvider.GROQ: {
                "name": "Groq",
                "description": "Ultra-fast inference (Llama, Mixtral)",
                "requires_auth": True,
                "requires_api_key": True,
                "built_in": False,
                "auth_url": "https://console.groq.com/keys",
                "auth_instructions": "Sign in to Groq Console and create an API key",
                "models": [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-70b-versatile",
                    "mixtral-8x7b-32768",
                    "gemma2-9b-it"
                ],
                "default_model": "llama-3.3-70b-versatile",
                "features": ["chat", "ultra_fast"],
                "cost": "Free tier available"
            },
            AIProvider.OLLAMA: {
                "name": "Ollama (Local)",
                "description": "Run models locally on your machine",
                "requires_auth": False,
                "requires_api_key": False,
                "built_in": False,
                "local": True,
                "setup_instructions": "Install Ollama from https://ollama.ai",
                "models": [
                    "llama3.1:70b",
                    "codellama:34b",
                    "mixtral:8x7b",
                    "qwen2.5-coder:32b",
                    "deepseek-coder:33b"
                ],
                "default_model": "llama3.1:70b",
                "features": ["chat", "local", "private"],
                "cost": "Free (requires local compute)"
            },
            AIProvider.LLAMACPP: {
                "name": "llama.cpp (Local)",
                "description": "Local models with llama.cpp backend",
                "requires_auth": False,
                "requires_api_key": False,
                "built_in": False,
                "local": True,
                "setup_instructions": "Set up llama.cpp server locally",
                "models": ["custom"],
                "default_model": "custom",
                "features": ["chat", "local", "private", "customizable"],
                "cost": "Free (requires local compute)"
            }
        }
    
    def get_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get all available providers"""
        return self.providers_config
    
    def get_provider_info(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific provider"""
        return self.providers_config.get(provider)
    
    def set_credential(self, provider: str, api_key: str) -> bool:
        """Set API key for a provider"""
        if provider in self.providers_config:
            self.user_credentials[provider] = api_key
            return True
        return False
    
    def get_credential(self, provider: str) -> Optional[str]:
        """Get API key for a provider"""
        # For Emergent, return the built-in key
        if provider == AIProvider.EMERGENT:
            return os.environ.get('EMERGENT_LLM_KEY')
        return self.user_credentials.get(provider)
    
    def is_provider_ready(self, provider: str) -> tuple[bool, str]:
        """
        Check if a provider is ready to use
        Returns: (is_ready, message)
        """
        provider_info = self.get_provider_info(provider)
        if not provider_info:
            return False, "Provider not found"
        
        # Built-in providers are always ready
        if provider_info.get("built_in"):
            return True, "Ready"
        
        # Local providers don't need API keys but may need setup
        if provider_info.get("local"):
            return True, f"Ensure {provider_info['name']} is running locally"
        
        # Check if API key is set
        if provider_info.get("requires_api_key"):
            if not self.get_credential(provider):
                return False, f"API key required. Get it from: {provider_info.get('auth_url', 'provider website')}"
        
        return True, "Ready"
    
    async def send_message(
        self,
        provider: str,
        model: str,
        message: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[Dict]] = None
    ) -> str:
        """
        Send a message to the specified AI provider
        Returns the AI response
        """
        is_ready, status_msg = self.is_provider_ready(provider)
        if not is_ready:
            return f"Error: {status_msg}"
        
        try:
            if provider == AIProvider.EMERGENT or provider == AIProvider.ANTHROPIC:
                return await self._send_anthropic_message(provider, model, message, system_prompt, context)
            elif provider == AIProvider.OPENAI:
                return await self._send_openai_message(model, message, system_prompt, context)
            elif provider == AIProvider.GOOGLE:
                return await self._send_google_message(model, message, system_prompt, context)
            elif provider == AIProvider.PERPLEXITY:
                return await self._send_perplexity_message(model, message, system_prompt, context)
            elif provider == AIProvider.GROQ:
                return await self._send_groq_message(model, message, system_prompt, context)
            elif provider == AIProvider.OLLAMA:
                return await self._send_ollama_message(model, message, system_prompt, context)
            elif provider == AIProvider.LLAMACPP:
                return await self._send_llamacpp_message(model, message, system_prompt, context)
            else:
                return f"Provider {provider} not yet implemented"
        except Exception as e:
            logger.error(f"Error sending message to {provider}: {e}")
            return f"Error: {str(e)}"
    
    async def _send_anthropic_message(self, provider: str, model: str, message: str, 
                                     system_prompt: Optional[str], context: Optional[List]) -> str:
        """Send message using Emergent integrations or direct Anthropic"""
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = self.get_credential(provider)
        chat = LlmChat(api_key=api_key, system_message=system_prompt or "")
        chat.with_model("anthropic", model)
        
        # Add context messages if provided
        if context:
            for msg in context:
                chat.add_message(msg["role"], msg["content"])
        
        response = await chat.send_message(UserMessage(text=message))
        return response
    
    async def _send_openai_message(self, model: str, message: str,
                                  system_prompt: Optional[str], context: Optional[List]) -> str:
        """Send message to OpenAI"""
        import httpx
        
        api_key = self.get_credential(AIProvider.OPENAI)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    async def _send_google_message(self, model: str, message: str,
                                  system_prompt: Optional[str], context: Optional[List]) -> str:
        """Send message to Google Gemini"""
        import httpx
        
        api_key = self.get_credential(AIProvider.GOOGLE)
        
        # Gemini uses a different format
        full_prompt = ""
        if system_prompt:
            full_prompt += f"{system_prompt}\n\n"
        if context:
            for msg in context:
                full_prompt += f"{msg['role']}: {msg['content']}\n"
        full_prompt += f"user: {message}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}]
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
    
    async def _send_perplexity_message(self, model: str, message: str,
                                      system_prompt: Optional[str], context: Optional[List]) -> str:
        """Send message to Perplexity"""
        import httpx
        
        api_key = self.get_credential(AIProvider.PERPLEXITY)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    async def _send_groq_message(self, model: str, message: str,
                                system_prompt: Optional[str], context: Optional[List]) -> str:
        """Send message to Groq"""
        import httpx
        
        api_key = self.get_credential(AIProvider.GROQ)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    async def _send_ollama_message(self, model: str, message: str,
                                  system_prompt: Optional[str], context: Optional[List]) -> str:
        """Send message to local Ollama instance"""
        import httpx
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": message})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                },
                timeout=120.0
            )
            response.raise_for_status()
            result = response.json()
            return result["message"]["content"]
    
    async def _send_llamacpp_message(self, model: str, message: str,
                                    system_prompt: Optional[str], context: Optional[List]) -> str:
        """Send message to local llama.cpp server"""
        import httpx
        
        full_prompt = ""
        if system_prompt:
            full_prompt += f"{system_prompt}\n\n"
        if context:
            for msg in context:
                full_prompt += f"{msg['role']}: {msg['content']}\n"
        full_prompt += f"user: {message}\nassistant:"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8080/completion",
                json={
                    "prompt": full_prompt,
                    "n_predict": 2048
                },
                timeout=120.0
            )
            response.raise_for_status()
            result = response.json()
            return result["content"]


# Global instance
ai_provider_manager = AIProviderManager()
