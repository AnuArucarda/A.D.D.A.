"""
Factory Image Manager - Upload, download, and extract factory images
Automatically detect device and pull manufacturer images
"""
import os
import re
import asyncio
import zipfile
import tarfile
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import aiofiles
import httpx
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

WORK_DIR = Path("/tmp/linux_forge")
FACTORY_IMAGES_DIR = WORK_DIR / "factory_images"
EXTRACTED_DIR = WORK_DIR / "extracted_images"
FACTORY_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

# Known manufacturer factory image sources
MANUFACTURER_IMAGE_SOURCES = {
    "google": {
        "name": "Google (Pixel)",
        "base_url": "https://developers.google.com/android/images",
        "download_pattern": "https://dl.google.com/dl/android/aosp/{codename}-{build_id}-factory-{hash}.zip",
        "devices": {
            # Pixel 8 Series
            "husky": "Pixel 8 Pro",
            "shiba": "Pixel 8",
            # Pixel 7 Series  
            "cheetah": "Pixel 7 Pro",
            "panther": "Pixel 7",
            "lynx": "Pixel 7a",
            # Pixel 6 Series
            "raven": "Pixel 6 Pro",
            "oriole": "Pixel 6",
            "bluejay": "Pixel 6a",
            # Pixel 5 Series
            "redfin": "Pixel 5",
            "barbet": "Pixel 5a",
            # Older Pixels
            "sunfish": "Pixel 4a",
            "bramble": "Pixel 4a 5G",
            "flame": "Pixel 4",
            "coral": "Pixel 4 XL",
            "bonito": "Pixel 3a XL",
            "sargo": "Pixel 3a",
        }
    },
    "samsung": {
        "name": "Samsung",
        "base_url": "https://samfw.com",
        "note": "Samsung uses Odin format, requires conversion",
        "devices": {}
    },
    "oneplus": {
        "name": "OnePlus",
        "base_url": "https://www.oneplus.com/support/softwareupgrade",
        "devices": {}
    },
    "xiaomi": {
        "name": "Xiaomi",
        "base_url": "https://xiaomirom.com/en/",
        "note": "Fastboot and Recovery ROMs available",
        "devices": {}
    },
    "motorola": {
        "name": "Motorola",
        "base_url": "https://mirrors.lolinet.com/firmware/moto/",
        "devices": {}
    }
}


class FactoryImageManager:
    """Manages factory image upload, download, and extraction"""
    
    def __init__(self):
        self.uploaded_images: Dict[str, Dict] = {}
        self.extracted_data: Dict[str, Dict] = {}
    
    async def upload_factory_image(
        self, 
        file_path: str, 
        device_codename: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Upload a factory image file
        Returns: Information about the uploaded image
        """
        source_path = Path(file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Create device directory
        device_dir = FACTORY_IMAGES_DIR / device_codename
        device_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate hash
        file_hash = await self._calculate_file_hash(source_path)
        
        # Copy file
        dest_path = device_dir / source_path.name
        async with aiofiles.open(source_path, 'rb') as src:
            async with aiofiles.open(dest_path, 'wb') as dst:
                while chunk := await src.read(8192):
                    await dst.write(chunk)
        
        # Store metadata
        image_info = {
            "device_codename": device_codename,
            "filename": source_path.name,
            "path": str(dest_path),
            "size": source_path.stat().st_size,
            "hash": file_hash,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "type": self._detect_image_type(source_path.name)
        }
        
        self.uploaded_images[device_codename] = image_info
        
        return image_info
    
    async def download_factory_image(
        self,
        url: str,
        device_codename: str,
        manufacturer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Download factory image from URL
        """
        logger.info(f"Downloading factory image from {url}")
        
        device_dir = FACTORY_IMAGES_DIR / device_codename
        device_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract filename from URL
        filename = url.split('/')[-1]
        if '?' in filename:
            filename = filename.split('?')[0]
        
        dest_path = device_dir / filename
        
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=600.0) as client:
                async with client.stream('GET', url) as response:
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    async with aiofiles.open(dest_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Could emit progress here via WebSocket
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                logger.info(f"Download progress: {progress:.1f}%")
            
            # Calculate hash
            file_hash = await self._calculate_file_hash(dest_path)
            
            image_info = {
                "device_codename": device_codename,
                "filename": filename,
                "path": str(dest_path),
                "size": dest_path.stat().st_size,
                "hash": file_hash,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "source_url": url,
                "manufacturer": manufacturer,
                "type": self._detect_image_type(filename)
            }
            
            self.uploaded_images[device_codename] = image_info
            
            return image_info
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise
    
    async def auto_detect_and_download(
        self,
        device_info: Dict
    ) -> Optional[Dict[str, Any]]:
        """
        Auto-detect device and download appropriate factory images
        """
        manufacturer = device_info.get("manufacturer", "").lower()
        codename = device_info.get("codename", "")
        build_id = device_info.get("build_id", "")
        
        logger.info(f"Auto-detecting images for {manufacturer} {codename}")
        
        if manufacturer == "google":
            return await self._download_google_factory_image(codename, build_id)
        elif manufacturer == "samsung":
            return {"error": "Samsung images require manual download from samfw.com"}
        elif manufacturer in ["oneplus", "xiaomi", "motorola"]:
            return {"error": f"{manufacturer.title()} images require manual download"}
        else:
            return {"error": f"No auto-download available for {manufacturer}"}
    
    async def _download_google_factory_image(
        self,
        codename: str,
        build_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Download Google Pixel factory image
        """
        # Check if device is supported
        if codename not in MANUFACTURER_IMAGE_SOURCES["google"]["devices"]:
            return {"error": f"Device {codename} not found in Google factory images database"}
        
        # Fetch available images from Google
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://developers.google.com/android/images"
                )
                response.raise_for_status()
                
                # Parse HTML to find download link
                # This is simplified - in production, you'd parse the HTML properly
                content = response.text
                
                # Look for download link matching codename
                pattern = rf'href="(https://dl\.google\.com/dl/android/aosp/{codename}-.*?\.zip)"'
                match = re.search(pattern, content)
                
                if match:
                    download_url = match.group(1)
                    logger.info(f"Found factory image: {download_url}")
                    
                    return await self.download_factory_image(
                        download_url,
                        codename,
                        "google"
                    )
                else:
                    return {"error": f"No factory image found for {codename}"}
                    
        except Exception as e:
            logger.error(f"Failed to fetch Google factory images: {e}")
            return {"error": str(e)}
    
    async def extract_factory_image(
        self,
        device_codename: str
    ) -> Dict[str, Any]:
        """
        Extract factory image and parse contents
        Returns: Information about extracted files
        """
        if device_codename not in self.uploaded_images:
            raise ValueError(f"No factory image found for {device_codename}")
        
        image_info = self.uploaded_images[device_codename]
        image_path = Path(image_info["path"])
        
        # Create extraction directory
        extract_dir = EXTRACTED_DIR / device_codename
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Extracting factory image to {extract_dir}")
        
        extracted_files = []
        
        try:
            # Handle ZIP files
            if image_path.suffix == '.zip':
                with zipfile.ZipFile(image_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                    extracted_files = zip_ref.namelist()
            
            # Handle TAR files
            elif image_path.suffix in ['.tar', '.tgz', '.tar.gz']:
                with tarfile.open(image_path, 'r:*') as tar_ref:
                    tar_ref.extractall(extract_dir)
                    extracted_files = tar_ref.getnames()
            
            else:
                return {"error": f"Unsupported file type: {image_path.suffix}"}
            
            # Analyze extracted contents
            analysis = await self._analyze_extracted_images(extract_dir, extracted_files)
            
            self.extracted_data[device_codename] = {
                "device_codename": device_codename,
                "extract_dir": str(extract_dir),
                "extracted_files": extracted_files,
                "analysis": analysis,
                "extracted_at": datetime.now(timezone.utc).isoformat()
            }
            
            return self.extracted_data[device_codename]
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise
    
    async def _analyze_extracted_images(
        self,
        extract_dir: Path,
        files: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze extracted factory image contents
        Identify partitions, kernel, device tree, etc.
        """
        analysis = {
            "partitions": [],
            "kernel_image": None,
            "device_tree": None,
            "boot_image": None,
            "system_image": None,
            "vendor_image": None,
            "recovery_image": None,
            "radio_image": None,
            "bootloader": None,
            "scripts": [],
            "metadata": {}
        }
        
        for file in files:
            file_lower = file.lower()
            file_path = extract_dir / file
            
            # Identify key files
            if 'boot.img' in file_lower:
                analysis["boot_image"] = str(file_path)
                # Could extract kernel and ramdisk from boot.img
            elif 'system.img' in file_lower or 'system.raw' in file_lower:
                analysis["system_image"] = str(file_path)
            elif 'vendor.img' in file_lower:
                analysis["vendor_image"] = str(file_path)
            elif 'recovery.img' in file_lower:
                analysis["recovery_image"] = str(file_path)
            elif 'radio' in file_lower or 'modem' in file_lower:
                analysis["radio_image"] = str(file_path)
            elif 'bootloader' in file_lower:
                analysis["bootloader"] = str(file_path)
            elif file_lower.endswith('.sh'):
                analysis["scripts"].append(str(file_path))
            elif 'zImage' in file or 'Image' in file:
                analysis["kernel_image"] = str(file_path)
            elif '.dtb' in file_lower or 'device-tree' in file_lower:
                analysis["device_tree"] = str(file_path)
        
        # Extract metadata if android-info.txt exists
        android_info = extract_dir / "android-info.txt"
        if android_info.exists():
            async with aiofiles.open(android_info, 'r') as f:
                content = await f.read()
                analysis["metadata"]["android_info"] = content
        
        return analysis
    
    async def extract_boot_image_components(
        self,
        boot_image_path: str
    ) -> Dict[str, Any]:
        """
        Extract kernel, ramdisk, and device tree from boot.img
        Uses unpack_bootimg or similar tools
        """
        boot_path = Path(boot_image_path)
        if not boot_path.exists():
            raise FileNotFoundError(f"Boot image not found: {boot_image_path}")
        
        output_dir = boot_path.parent / "boot_unpacked"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Use unpackbootimg or similar tool
            proc = await asyncio.create_subprocess_exec(
                "unpackbootimg",
                "-i", str(boot_path),
                "-o", str(output_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                # List extracted components
                components = {
                    "kernel": None,
                    "ramdisk": None,
                    "device_tree": None,
                    "cmdline": None,
                    "base": None,
                    "pagesize": None
                }
                
                for file in output_dir.iterdir():
                    if 'kernel' in file.name.lower():
                        components["kernel"] = str(file)
                    elif 'ramdisk' in file.name.lower():
                        components["ramdisk"] = str(file)
                    elif 'dtb' in file.name.lower() or 'dt' in file.name.lower():
                        components["device_tree"] = str(file)
                    elif 'cmdline' in file.name.lower():
                        async with aiofiles.open(file, 'r') as f:
                            components["cmdline"] = await f.read()
                
                return components
            else:
                logger.error(f"unpackbootimg failed: {stderr.decode()}")
                return {"error": "Failed to unpack boot image"}
                
        except FileNotFoundError:
            logger.warning("unpackbootimg not found, trying alternative method")
            return {"error": "unpackbootimg not available"}
        except Exception as e:
            logger.error(f"Boot image extraction failed: {e}")
            return {"error": str(e)}
    
    async def extract_kernel_config(
        self,
        kernel_image_path: str
    ) -> Optional[str]:
        """
        Extract kernel configuration from kernel image
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "extract-ikconfig",
                kernel_image_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                return stdout.decode()
            else:
                logger.warning(f"Failed to extract kernel config: {stderr.decode()}")
                return None
                
        except FileNotFoundError:
            logger.warning("extract-ikconfig not found")
            return None
        except Exception as e:
            logger.error(f"Kernel config extraction failed: {e}")
            return None
    
    def _detect_image_type(self, filename: str) -> str:
        """Detect type of factory image file"""
        filename_lower = filename.lower()
        
        if 'factory' in filename_lower:
            return "factory_package"
        elif 'ota' in filename_lower:
            return "ota_package"
        elif 'fastboot' in filename_lower:
            return "fastboot_package"
        elif 'odin' in filename_lower:
            return "odin_package"
        elif filename_lower.endswith('.zip'):
            return "zip_package"
        elif filename_lower.endswith('.tar') or filename_lower.endswith('.tar.gz'):
            return "tar_package"
        else:
            return "unknown"
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def get_uploaded_images(self) -> Dict[str, Dict]:
        """Get all uploaded factory images"""
        return self.uploaded_images
    
    def get_extracted_data(self, device_codename: str) -> Optional[Dict]:
        """Get extracted data for a device"""
        return self.extracted_data.get(device_codename)
    
    def get_manufacturer_sources(self) -> Dict:
        """Get list of known manufacturer image sources"""
        return MANUFACTURER_IMAGE_SOURCES


# Global instance
factory_image_manager = FactoryImageManager()
