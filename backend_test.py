#!/usr/bin/env python3
"""
Linux Device Forge Backend API Test Suite
Tests all three tools: Kernel Forge, OS Builder, Halium Builder
"""

import requests
import json
import sys
from datetime import datetime

# Use public endpoint from frontend/.env
BACKEND_URL = "https://device-agent.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

class LinuxDeviceForgeAPITester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "backend_url": BACKEND_URL,
            "tests": []
        }

    def log_test(self, test_name, success, details="", endpoint=""):
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}")
        if details:
            print(f"    {details}")
        
        self.results["tests"].append({
            "name": test_name,
            "success": success,
            "details": details,
            "endpoint": endpoint,
            "timestamp": datetime.now().isoformat()
        })
        
        if success:
            self.passed += 1
        else:
            self.failed += 1

    def test_endpoint(self, method, endpoint, expected_status=200, data=None, description=""):
        """Test API endpoint"""
        url = f"{API_BASE}{endpoint}"
        test_name = f"{method} {endpoint}" + (f" - {description}" if description else "")
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                headers = {'Content-Type': 'application/json'}
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                self.log_test(test_name, False, f"Unsupported method: {method}", endpoint)
                return None
                
            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    self.log_test(test_name, True, f"Status: {response.status_code}, Response: {str(response_data)[:100]}...", endpoint)
                    return response_data
                except json.JSONDecodeError:
                    self.log_test(test_name, True, f"Status: {response.status_code}, Response: text", endpoint)
                    return response.text
            else:
                self.log_test(test_name, False, f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}", endpoint)
                return None
                
        except requests.exceptions.RequestException as e:
            self.log_test(test_name, False, f"Request failed: {str(e)}", endpoint)
            return None

    def test_health_api(self):
        """Test health and tools status API"""
        print("\n=== Testing Health & Tools Status ===")
        
        # Test health endpoint
        health_data = self.test_endpoint("GET", "/health", description="Get tools status including kernel_forge_ready and os_builder_ready")
        
        if health_data:
            # Check specific required fields
            required_fields = ["kernel_forge_ready", "os_builder_ready", "tools"]
            for field in required_fields:
                if field in health_data:
                    self.log_test(f"Health API contains {field}", True, f"{field}: {health_data[field]}")
                else:
                    self.log_test(f"Health API contains {field}", False, f"Missing required field: {field}")

    def test_kernel_forge_apis(self):
        """Test Kernel Forge APIs"""
        print("\n=== Testing Kernel Forge APIs ===")
        
        # Test mainline versions API
        mainline_data = self.test_endpoint("GET", "/kernel/mainline-versions", description="Get kernel versions")
        if mainline_data and "versions" in mainline_data:
            version_count = len(mainline_data["versions"])
            self.log_test("Kernel mainline versions count", version_count > 0, f"Found {version_count} versions")
        
        # Test kernel config requirements API
        config_data = self.test_endpoint("GET", "/kernel/config-requirements", description="Get kernel config requirements")
        if config_data and "requirements" in config_data:
            req_count = len(config_data["requirements"])
            self.log_test("Kernel config requirements count", req_count > 0, f"Found {req_count} config requirements")
        
        # Test kernel projects list API
        self.test_endpoint("GET", "/kernel/projects", description="List kernel projects")
        
        # Test creating a kernel project
        project_data = {
            "device_codename": "test_device",
            "architecture": "arm64"
        }
        create_result = self.test_endpoint("POST", "/kernel/projects", 200, project_data, "Create kernel project")
        
        if create_result and "id" in create_result:
            project_id = create_result["id"]
            self.log_test("Kernel project creation returns ID", True, f"Project ID: {project_id}")
            
            # Test project-specific endpoints
            self.test_endpoint("GET", f"/kernel/projects/{project_id}", description="Get specific kernel project")

    def test_os_builder_apis(self):
        """Test OS Image Builder APIs"""
        print("\n=== Testing OS Image Builder APIs ===")
        
        # Test distros API
        distros_data = self.test_endpoint("GET", "/os/distros", description="Get mobile and desktop distributions")
        
        if distros_data:
            # Check mobile distros
            mobile_distros = distros_data.get("mobile", {})
            desktop_distros = distros_data.get("desktop", {})
            
            self.log_test("Mobile distros count", len(mobile_distros) >= 4, f"Found {len(mobile_distros)} mobile distros")
            self.log_test("Desktop distros count", len(desktop_distros) >= 4, f"Found {len(desktop_distros)} desktop distros")
            
            # Check specific required mobile distros
            required_mobile = ["ubuntu-touch", "postmarketos", "droidian", "mobian"]
            for distro in required_mobile:
                if distro in mobile_distros:
                    self.log_test(f"Mobile distro {distro} present", True, f"Name: {mobile_distros[distro].get('name', 'N/A')}")
                else:
                    self.log_test(f"Mobile distro {distro} present", False, f"Missing required mobile distro: {distro}")
            
            # Check specific required desktop distros
            required_desktop = ["ubuntu", "debian", "arch", "fedora"]
            for distro in required_desktop:
                if distro in desktop_distros:
                    self.log_test(f"Desktop distro {distro} present", True, f"Name: {desktop_distros[distro].get('name', 'N/A')}")
                else:
                    self.log_test(f"Desktop distro {distro} present", False, f"Missing required desktop distro: {distro}")
        
        # Test OS projects list API
        self.test_endpoint("GET", "/os/projects", description="List OS image projects")
        
        # Test creating an OS project
        os_project_data = {
            "device_codename": "test_device",
            "distro": "ubuntu-touch"
        }
        create_result = self.test_endpoint("POST", "/os/projects", 200, os_project_data, "Create OS project")
        
        if create_result and "id" in create_result:
            project_id = create_result["id"]
            self.log_test("OS project creation returns ID", True, f"Project ID: {project_id}")

    def test_halium_apis(self):
        """Test Halium Builder APIs"""
        print("\n=== Testing Halium Builder APIs ===")
        
        # Test Halium versions API
        versions_data = self.test_endpoint("GET", "/halium/versions", description="Get Halium versions")
        
        if versions_data and "versions" in versions_data:
            versions = versions_data["versions"]
            self.log_test("Halium versions count", len(versions) >= 4, f"Found {len(versions)} Halium versions")
            
            # Check specific versions
            required_versions = ["7.1", "9.0", "10.0", "11.0"]
            found_versions = []
            for version in versions:
                if any(req in version.get("id", "") for req in required_versions):
                    found_versions.append(version.get("id", ""))
            
            self.log_test("Required Halium versions present", len(found_versions) >= 4, f"Found versions: {found_versions}")

    def test_device_apis(self):
        """Test Device Management APIs"""
        print("\n=== Testing Device Management APIs ===")
        
        # Test devices list API
        devices_data = self.test_endpoint("GET", "/devices", description="Get device list")
        
        if devices_data:
            device_list = devices_data.get("devices", [])
            adb_available = devices_data.get("adb_available", False)
            
            self.log_test("Devices API returns device list", True, f"Found {len(device_list)} devices, ADB available: {adb_available}")
            
            # Note: ADB not available in container is expected
            if not adb_available:
                self.log_test("ADB availability (container limitation)", True, "ADB not available in container environment - expected")

    def test_ai_integration(self):
        """Test AI Chat Integration"""
        print("\n=== Testing AI Integration ===")
        
        # Test AI chat endpoint
        ai_request_data = {
            "message": "Test AI integration for Linux Device Forge",
            "session_id": "test_session_123"
        }
        
        ai_response = self.test_endpoint("POST", "/ai/chat", 200, ai_request_data, "AI chat works with AI responses")
        
        if ai_response:
            if "response" in ai_response:
                self.log_test("AI chat returns response", True, f"Response length: {len(ai_response['response'])} chars")
            else:
                self.log_test("AI chat returns response", False, "No 'response' field in AI response")

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Linux Device Forge API Tests")
        print(f"Backend URL: {BACKEND_URL}")
        
        # Run all test suites
        self.test_health_api()
        self.test_kernel_forge_apis()
        self.test_os_builder_apis()
        self.test_halium_apis()
        self.test_device_apis()
        self.test_ai_integration()
        
        # Print summary
        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"\n📊 Test Results Summary:")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        # Save results to file
        with open("/app/test_reports/backend_test_results.json", "w") as f:
            self.results.update({
                "summary": {
                    "total_tests": total,
                    "passed": self.passed,
                    "failed": self.failed,
                    "success_rate": success_rate
                }
            })
            json.dump(self.results, f, indent=2)
        
        print(f"📄 Detailed results saved to: /app/test_reports/backend_test_results.json")
        
        return self.failed == 0

def main():
    tester = LinuxDeviceForgeAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())