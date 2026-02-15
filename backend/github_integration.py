"""
GitHub Integration Manager - Save, load, and share build recipes via GitHub
Enables community marketplace, version control, and recipe sharing
"""
import os
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import aiofiles
import httpx
from datetime import datetime, timezone
import yaml

logger = logging.getLogger(__name__)


class GitHubIntegrationManager:
    """
    Manages GitHub integration for build recipes
    - Save recipes to user's GitHub repositories
    - Import recipes from GitHub URLs
    - Browse community recipes
    - Version control for builds
    """
    
    def __init__(self):
        self.github_api_base = "https://api.github.com"
        self.user_tokens: Dict[str, str] = {}  # user_id -> github_token
        self.recipe_cache: Dict[str, Dict] = {}
    
    def set_user_token(self, user_id: str, github_token: str):
        """Set GitHub personal access token for a user"""
        self.user_tokens[user_id] = github_token
    
    def get_user_token(self, user_id: str) -> Optional[str]:
        """Get GitHub token for a user"""
        return self.user_tokens.get(user_id)
    
    async def create_repository(
        self,
        user_id: str,
        repo_name: str,
        description: str,
        is_private: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new GitHub repository for storing build recipes
        """
        token = self.get_user_token(user_id)
        if not token:
            return {"error": "GitHub token not configured"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.github_api_base}/user/repos",
                    headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    json={
                        "name": repo_name,
                        "description": description,
                        "private": is_private,
                        "auto_init": True
                    },
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    return response.json()
                else:
                    return {"error": response.json().get("message", "Failed to create repository")}
                    
        except Exception as e:
            logger.error(f"Failed to create GitHub repository: {e}")
            return {"error": str(e)}
    
    async def save_recipe_to_github(
        self,
        user_id: str,
        repo_owner: str,
        repo_name: str,
        recipe_name: str,
        recipe_data: Dict[str, Any],
        branch: str = "main"
    ) -> Dict[str, Any]:
        """
        Save a build recipe to GitHub repository
        Creates a YAML file with the recipe configuration
        """
        token = self.get_user_token(user_id)
        if not token:
            return {"error": "GitHub token not configured"}
        
        try:
            # Convert recipe to YAML format
            recipe_yaml = yaml.dump(recipe_data, default_flow_style=False, sort_keys=False)
            
            # Prepare file path
            file_path = f"recipes/{recipe_data.get('type', 'build')}/{recipe_name}.yml"
            
            # Check if file exists
            existing_sha = await self._get_file_sha(token, repo_owner, repo_name, file_path, branch)
            
            # Prepare commit data
            commit_data = {
                "message": f"{'Update' if existing_sha else 'Add'} recipe: {recipe_name}",
                "content": self._base64_encode(recipe_yaml),
                "branch": branch
            }
            
            if existing_sha:
                commit_data["sha"] = existing_sha
            
            # Create/update file
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.github_api_base}/repos/{repo_owner}/{repo_name}/contents/{file_path}",
                    headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    json=commit_data,
                    timeout=30.0
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    return {
                        "success": True,
                        "file_url": result["content"]["html_url"],
                        "sha": result["content"]["sha"],
                        "message": f"Recipe saved to GitHub: {file_path}"
                    }
                else:
                    return {"error": response.json().get("message", "Failed to save recipe")}
                    
        except Exception as e:
            logger.error(f"Failed to save recipe to GitHub: {e}")
            return {"error": str(e)}
    
    async def load_recipe_from_github(
        self,
        github_url: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load a build recipe from a GitHub URL
        Supports:
        - Direct file URLs (github.com/.../blob/...)
        - Raw URLs (raw.githubusercontent.com/...)
        - API URLs (api.github.com/...)
        """
        try:
            # Parse GitHub URL
            parsed = self._parse_github_url(github_url)
            if not parsed:
                return {"error": "Invalid GitHub URL"}
            
            repo_owner, repo_name, file_path, branch = parsed
            
            # Get token if available (for private repos)
            token = self.get_user_token(user_id) if user_id else None
            
            # Fetch file content
            headers = {"Accept": "application/vnd.github.v3.raw"}
            if token:
                headers["Authorization"] = f"token {token}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.github_api_base}/repos/{repo_owner}/{repo_name}/contents/{file_path}",
                    headers=headers,
                    params={"ref": branch} if branch else {},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    # Parse YAML content
                    content = response.text
                    recipe_data = yaml.safe_load(content)
                    
                    # Add metadata
                    recipe_data["_github_source"] = {
                        "url": github_url,
                        "repo": f"{repo_owner}/{repo_name}",
                        "file": file_path,
                        "imported_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    return recipe_data
                else:
                    return {"error": f"Failed to fetch recipe: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Failed to load recipe from GitHub: {e}")
            return {"error": str(e)}
    
    async def search_community_recipes(
        self,
        query: str,
        build_type: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Search for community recipes on GitHub
        Uses GitHub code search API
        """
        try:
            # Build search query
            search_terms = [query, "adda-recipe", "android-device-developer"]
            if build_type:
                search_terms.append(f"type:{build_type}")
            
            search_query = " ".join(search_terms) + " language:YAML"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.github_api_base}/search/code",
                    params={
                        "q": search_query,
                        "per_page": limit,
                        "sort": "indexed"
                    },
                    headers={"Accept": "application/vnd.github.v3+json"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    results = response.json()
                    recipes = []
                    
                    for item in results.get("items", []):
                        recipes.append({
                            "name": item["name"],
                            "repository": item["repository"]["full_name"],
                            "url": item["html_url"],
                            "description": item["repository"].get("description"),
                            "stars": item["repository"]["stargazers_count"],
                            "last_updated": item["repository"]["updated_at"]
                        })
                    
                    return recipes
                else:
                    logger.warning(f"GitHub search failed: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to search community recipes: {e}")
            return []
    
    async def fork_recipe_repository(
        self,
        user_id: str,
        repo_owner: str,
        repo_name: str
    ) -> Dict[str, Any]:
        """
        Fork a recipe repository to user's GitHub account
        """
        token = self.get_user_token(user_id)
        if not token:
            return {"error": "GitHub token not configured"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.github_api_base}/repos/{repo_owner}/{repo_name}/forks",
                    headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 202:
                    return response.json()
                else:
                    return {"error": response.json().get("message", "Failed to fork repository")}
                    
        except Exception as e:
            logger.error(f"Failed to fork repository: {e}")
            return {"error": str(e)}
    
    async def get_user_repositories(
        self,
        user_id: str,
        recipe_repos_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get user's GitHub repositories
        Optionally filter for recipe repositories
        """
        token = self.get_user_token(user_id)
        if not token:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.github_api_base}/user/repos",
                    headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    params={"per_page": 100, "sort": "updated"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    repos = response.json()
                    
                    if recipe_repos_only:
                        # Filter for repositories containing recipes
                        repos = [
                            r for r in repos
                            if "recipe" in r["name"].lower() or
                               "adda" in r["name"].lower() or
                               "recipe" in (r.get("description") or "").lower()
                        ]
                    
                    return repos
                else:
                    logger.warning(f"Failed to get repositories: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to get user repositories: {e}")
            return []
    
    async def list_recipes_in_repository(
        self,
        repo_owner: str,
        repo_name: str,
        user_id: Optional[str] = None,
        branch: str = "main"
    ) -> List[Dict[str, Any]]:
        """
        List all recipes in a GitHub repository
        """
        try:
            token = self.get_user_token(user_id) if user_id else None
            
            headers = {"Accept": "application/vnd.github.v3+json"}
            if token:
                headers["Authorization"] = f"token {token}"
            
            async with httpx.AsyncClient() as client:
                # Get repository tree
                response = await client.get(
                    f"{self.github_api_base}/repos/{repo_owner}/{repo_name}/git/trees/{branch}",
                    headers=headers,
                    params={"recursive": "1"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    tree = response.json()
                    recipes = []
                    
                    for item in tree.get("tree", []):
                        path = item["path"]
                        # Look for YAML files in recipes directory
                        if path.startswith("recipes/") and (path.endswith(".yml") or path.endswith(".yaml")):
                            recipes.append({
                                "name": Path(path).stem,
                                "path": path,
                                "type": path.split("/")[1] if len(path.split("/")) > 1 else "unknown",
                                "url": f"https://github.com/{repo_owner}/{repo_name}/blob/{branch}/{path}",
                                "sha": item["sha"]
                            })
                    
                    return recipes
                else:
                    logger.warning(f"Failed to list recipes: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to list recipes in repository: {e}")
            return []
    
    def _parse_github_url(self, url: str) -> Optional[Tuple[str, str, str, Optional[str]]]:
        """
        Parse GitHub URL to extract owner, repo, file path, and branch
        Returns: (owner, repo, file_path, branch) or None
        """
        try:
            # Handle different GitHub URL formats
            if "github.com" in url:
                # https://github.com/owner/repo/blob/branch/path/file.yml
                parts = url.split("github.com/")[1].split("/")
                owner = parts[0]
                repo = parts[1]
                
                if "blob" in parts:
                    blob_idx = parts.index("blob")
                    branch = parts[blob_idx + 1]
                    file_path = "/".join(parts[blob_idx + 2:])
                else:
                    branch = None
                    file_path = "/".join(parts[2:])
                
                return (owner, repo, file_path, branch)
            
            elif "raw.githubusercontent.com" in url:
                # https://raw.githubusercontent.com/owner/repo/branch/path/file.yml
                parts = url.split("raw.githubusercontent.com/")[1].split("/")
                owner = parts[0]
                repo = parts[1]
                branch = parts[2]
                file_path = "/".join(parts[3:])
                
                return (owner, repo, file_path, branch)
            
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to parse GitHub URL: {e}")
            return None
    
    async def _get_file_sha(
        self,
        token: str,
        repo_owner: str,
        repo_name: str,
        file_path: str,
        branch: str
    ) -> Optional[str]:
        """Get SHA of existing file on GitHub"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.github_api_base}/repos/{repo_owner}/{repo_name}/contents/{file_path}",
                    headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    params={"ref": branch},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()["sha"]
                else:
                    return None
                    
        except Exception:
            return None
    
    def _base64_encode(self, content: str) -> str:
        """Base64 encode string for GitHub API"""
        import base64
        return base64.b64encode(content.encode()).decode()


# Global instance
github_integration = GitHubIntegrationManager()
