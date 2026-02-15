"""
Build History Manager - Track, compare, and fork builds
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class BuildHistoryManager:
    """Manages build history, templates, and forking"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.builds_collection = db["builds"]
        self.templates_collection = db["build_templates"]
    
    async def save_build(self, build_data: Dict[str, Any]) -> str:
        """
        Save a build to history
        Returns: build_id
        """
        build = {
            **build_data,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "status": build_data.get("status", "pending")
        }
        
        result = await self.builds_collection.insert_one(build)
        build_id = str(result.inserted_id)
        
        # Update the build with its own ID
        await self.builds_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"build_id": build_id}}
        )
        
        return build_id
    
    async def get_build(self, build_id: str) -> Optional[Dict]:
        """Get a specific build by ID"""
        build = await self.builds_collection.find_one(
            {"build_id": build_id},
            {"_id": 0}
        )
        return build
    
    async def get_builds_by_type(
        self, 
        build_type: str,
        device_codename: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get builds filtered by type and optionally by device
        build_type: kernel, os, android, recovery, halium
        """
        query = {"type": build_type}
        if device_codename:
            query["device_codename"] = device_codename
        
        builds = await self.builds_collection.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return builds
    
    async def get_successful_builds(
        self,
        build_type: str,
        device_codename: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get only successful builds for forking"""
        query = {
            "type": build_type,
            "status": "completed"
        }
        if device_codename:
            query["device_codename"] = device_codename
        
        builds = await self.builds_collection.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return builds
    
    async def fork_build(
        self,
        source_build_id: str,
        modifications: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Create a new build based on an existing one
        Returns: new build configuration
        """
        source_build = await self.get_build(source_build_id)
        if not source_build:
            return None
        
        # Create new build configuration
        forked_build = {
            "type": source_build["type"],
            "device_codename": source_build.get("device_codename"),
            "forked_from": source_build_id,
            "configuration": source_build.get("configuration", {}).copy(),
            "name": f"{source_build.get('name', 'Build')} (Fork)",
            "description": f"Forked from: {source_build.get('name', 'previous build')}"
        }
        
        # Apply modifications
        if modifications:
            forked_build["configuration"].update(modifications)
            if "name" in modifications:
                forked_build["name"] = modifications["name"]
            if "description" in modifications:
                forked_build["description"] = modifications["description"]
        
        return forked_build
    
    async def update_build_status(
        self,
        build_id: str,
        status: str,
        additional_data: Optional[Dict] = None
    ) -> bool:
        """
        Update build status
        status: pending, building, completed, failed
        """
        update_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc)
        }
        
        if additional_data:
            update_data.update(additional_data)
        
        result = await self.builds_collection.update_one(
            {"build_id": build_id},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    
    async def compare_builds(
        self,
        build_id_1: str,
        build_id_2: str
    ) -> Dict[str, Any]:
        """Compare two builds and return differences"""
        build1 = await self.get_build(build_id_1)
        build2 = await self.get_build(build_id_2)
        
        if not build1 or not build2:
            return {"error": "One or both builds not found"}
        
        # Compare configurations
        config1 = build1.get("configuration", {})
        config2 = build2.get("configuration", {})
        
        differences = {}
        all_keys = set(config1.keys()) | set(config2.keys())
        
        for key in all_keys:
            val1 = config1.get(key)
            val2 = config2.get(key)
            
            if val1 != val2:
                differences[key] = {
                    "build_1": val1,
                    "build_2": val2
                }
        
        return {
            "build_1": {
                "id": build_id_1,
                "name": build1.get("name"),
                "created_at": build1.get("created_at")
            },
            "build_2": {
                "id": build_id_2,
                "name": build2.get("name"),
                "created_at": build2.get("created_at")
            },
            "differences": differences,
            "difference_count": len(differences)
        }
    
    async def save_as_template(
        self,
        build_id: str,
        template_name: str,
        template_description: str,
        is_public: bool = False
    ) -> Optional[str]:
        """Save a build configuration as a reusable template"""
        build = await self.get_build(build_id)
        if not build:
            return None
        
        template = {
            "name": template_name,
            "description": template_description,
            "type": build["type"],
            "device_codename": build.get("device_codename"),
            "configuration": build.get("configuration", {}),
            "source_build_id": build_id,
            "is_public": is_public,
            "created_at": datetime.now(timezone.utc),
            "usage_count": 0
        }
        
        result = await self.templates_collection.insert_one(template)
        template_id = str(result.inserted_id)
        
        await self.templates_collection.update_one(
            {"_id": result.inserted_id},
            {"$set": {"template_id": template_id}}
        )
        
        return template_id
    
    async def get_templates(
        self,
        build_type: Optional[str] = None,
        public_only: bool = False
    ) -> List[Dict]:
        """Get available build templates"""
        query = {}
        if build_type:
            query["type"] = build_type
        if public_only:
            query["is_public"] = True
        
        templates = await self.templates_collection.find(
            query,
            {"_id": 0}
        ).sort("usage_count", -1).to_list(100)
        
        return templates
    
    async def use_template(self, template_id: str) -> Optional[Dict]:
        """Get template configuration and increment usage count"""
        template = await self.templates_collection.find_one(
            {"template_id": template_id},
            {"_id": 0}
        )
        
        if template:
            # Increment usage count
            await self.templates_collection.update_one(
                {"template_id": template_id},
                {"$inc": {"usage_count": 1}}
            )
        
        return template
    
    async def get_build_statistics(self, build_type: Optional[str] = None) -> Dict:
        """Get statistics about builds"""
        query = {}
        if build_type:
            query["type"] = build_type
        
        total = await self.builds_collection.count_documents(query)
        
        completed_query = {**query, "status": "completed"}
        completed = await self.builds_collection.count_documents(completed_query)
        
        failed_query = {**query, "status": "failed"}
        failed = await self.builds_collection.count_documents(failed_query)
        
        pending_query = {**query, "status": {"$in": ["pending", "building"]}}
        pending = await self.builds_collection.count_documents(pending_query)
        
        # Get most built devices
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": "$device_codename",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        top_devices = await self.builds_collection.aggregate(pipeline).to_list(10)
        
        return {
            "total_builds": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "top_devices": [
                {"device": d["_id"], "builds": d["count"]}
                for d in top_devices
            ]
        }
    
    async def delete_build(self, build_id: str) -> bool:
        """Delete a build from history"""
        result = await self.builds_collection.delete_one({"build_id": build_id})
        return result.deleted_count > 0
    
    async def search_builds(
        self,
        search_query: str,
        build_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Search builds by name, description, or device"""
        query = {
            "$or": [
                {"name": {"$regex": search_query, "$options": "i"}},
                {"description": {"$regex": search_query, "$options": "i"}},
                {"device_codename": {"$regex": search_query, "$options": "i"}}
            ]
        }
        
        if build_type:
            query["type"] = build_type
        
        builds = await self.builds_collection.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return builds
