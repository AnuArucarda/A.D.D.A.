#!/usr/bin/env python3
"""
Halium Build Assistant API Testing Script
Tests all backend endpoints for functionality and integration
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

class HaliumAPITester:
    def __init__(self, base_url="https://chat-persistence-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_id = f"test-session-{int(time.time())}"
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []
        
    def log_result(self, test_name: str, success: bool, details: str = "", response_data: dict = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "details": details,
            "response_data": response_data
        }
        self.results.append(result)
        print(f"{status}: {test_name} - {details}")
        return result

    def test_endpoint(self, method: str, endpoint: str, expected_status: int = 200, 
                     data: dict = None, test_name: str = None) -> tuple[bool, dict]:
        """Generic endpoint test"""
        url = f"{self.api_url}{endpoint}"
        test_name = test_name or f"{method} {endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, timeout=10)
            else:
                self.log_result(test_name, False, f"Unsupported method: {method}")
                return False, {}

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            try:
                response_data = response.json()
                if not success:
                    details += f" | Error: {response_data.get('detail', 'Unknown error')}"
            except:
                response_data = {"raw_response": response.text[:200]}
                if not success:
                    details += f" | Raw: {response.text[:100]}"

            self.log_result(test_name, success, details, response_data)
            return success, response_data
            
        except requests.exceptions.RequestException as e:
            self.log_result(test_name, False, f"Request failed: {str(e)}")
            return False, {}

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        print("\n🔍 Testing Health Endpoint...")
        success, data = self.test_endpoint("GET", "/health", test_name="Health Check")
        
        if success and data:
            # Check if tools status is present
            tools_status = data.get("tools", {})
            adb_available = tools_status.get("adb", False)
            fastboot_available = tools_status.get("fastboot", False)
            
            self.log_result("ADB Tool Available", adb_available, f"ADB: {'Available' if adb_available else 'Not Available'}")
            self.log_result("Fastboot Tool Available", fastboot_available, f"Fastboot: {'Available' if fastboot_available else 'Not Available'}")
            
        return success

    def test_halium_versions(self):
        """Test /api/halium/versions endpoint"""
        print("\n🔍 Testing Halium Versions...")
        success, data = self.test_endpoint("GET", "/halium/versions", test_name="Get Halium Versions")
        
        if success and data:
            versions = data.get("versions", [])
            expected_versions = ["halium-7.1", "halium-9.0", "halium-10.0", "halium-11.0"]
            
            version_ids = [v.get("id") for v in versions]
            has_all_versions = all(v in version_ids for v in expected_versions)
            
            self.log_result("Contains Expected Versions", has_all_versions, 
                          f"Found {len(versions)} versions: {version_ids}")
            
            # Check if versions have required fields
            if versions:
                first_version = versions[0]
                required_fields = ["id", "name", "android_base", "status"]
                has_required_fields = all(field in first_version for field in required_fields)
                self.log_result("Version Fields Complete", has_required_fields, 
                              f"Fields: {list(first_version.keys())}")
                
        return success

    def test_build_steps(self):
        """Test /api/halium/build-steps endpoint"""
        print("\n🔍 Testing Build Steps...")
        success, data = self.test_endpoint("GET", "/halium/build-steps", test_name="Get Build Steps")
        
        if success and data:
            steps = data.get("steps", [])
            self.log_result("Build Steps Retrieved", len(steps) > 0, 
                          f"Found {len(steps)} build steps")
            
            if steps:
                step_names = [step.get("name") for step in steps]
                expected_steps = ["Environment Setup", "Repo Init", "Device Tree", "Kernel Config"]
                has_expected_steps = any(expected in step_names for expected in expected_steps)
                self.log_result("Contains Expected Steps", has_expected_steps,
                              f"Steps: {step_names[:3]}...")
                
        return success

    def test_devices_endpoint(self):
        """Test /api/devices endpoint"""
        print("\n🔍 Testing Devices Endpoint...")
        success, data = self.test_endpoint("GET", "/devices", test_name="List Devices")
        
        if success and data:
            devices = data.get("devices", [])
            adb_available = data.get("adb_available", False)
            
            self.log_result("Devices Endpoint Working", success, 
                          f"Found {len(devices)} devices, ADB: {adb_available}")
            
            # Even if no devices are connected, endpoint should work
            self.log_result("Returns Device List", isinstance(devices, list), 
                          f"Device list type: {type(devices)}")
            
        return success

    def test_terminal_execute(self):
        """Test /api/terminal/execute endpoint"""
        print("\n🔍 Testing Terminal Execute...")
        
        # Test simple command
        test_command = "echo 'Hello Halium Test'"
        test_data = {
            "command": test_command,
            "session_id": self.session_id
        }
        
        success, data = self.test_endpoint("POST", "/terminal/execute", 
                                         expected_status=200, data=test_data,
                                         test_name="Execute Echo Command")
        
        if success and data:
            has_stdout = "stdout" in data
            has_exit_code = "exit_code" in data
            has_success = "success" in data
            
            self.log_result("Terminal Response Complete", 
                          has_stdout and has_exit_code and has_success,
                          f"Fields: stdout={has_stdout}, exit_code={has_exit_code}, success={has_success}")
            
            if has_exit_code:
                exit_code = data.get("exit_code", -1)
                self.log_result("Command Executed Successfully", exit_code == 0,
                              f"Exit code: {exit_code}")
                
        # Test command history
        success_hist, hist_data = self.test_endpoint("GET", "/terminal/history", 
                                                   test_name="Get Command History")
        if success_hist:
            history = hist_data.get("history", [])
            self.log_result("Command History Available", len(history) >= 0,
                          f"History entries: {len(history)}")
            
        return success

    def test_ai_chat(self):
        """Test /api/ai/chat endpoint"""
        print("\n🔍 Testing AI Chat...")
        
        test_message = "Hello, can you help with Halium porting?"
        test_data = {
            "message": test_message,
            "session_id": self.session_id,
            "device_context": None,
            "auto_execute": False
        }
        
        success, data = self.test_endpoint("POST", "/ai/chat", 
                                         expected_status=200, data=test_data,
                                         test_name="Send AI Chat Message")
        
        if success and data:
            has_response = "response" in data
            has_session_id = "session_id" in data
            has_commands = "extracted_commands" in data
            
            self.log_result("AI Response Complete", 
                          has_response and has_session_id,
                          f"Response length: {len(data.get('response', ''))}")
            
            self.log_result("AI Commands Extraction", has_commands,
                          f"Commands extracted: {len(data.get('extracted_commands', []))}")
            
            # Test chat history
            success_hist, hist_data = self.test_endpoint("GET", f"/ai/history/{self.session_id}",
                                                       test_name="Get Chat History")
            if success_hist:
                messages = hist_data.get("messages", [])
                self.log_result("Chat History Available", len(messages) >= 0,
                              f"Chat messages: {len(messages)}")
                
        return success

    def test_fastboot_endpoints(self):
        """Test fastboot related endpoints"""
        print("\n🔍 Testing Fastboot Endpoints...")
        
        success1, _ = self.test_endpoint("GET", "/fastboot/devices", test_name="List Fastboot Devices")
        return success1

    def test_build_endpoints(self):
        """Test build session endpoints"""
        print("\n🔍 Testing Build Session Endpoints...")
        
        # Test list build sessions
        success1, _ = self.test_endpoint("GET", "/build/sessions", test_name="List Build Sessions")
        
        return success1

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Halium Build Assistant API Tests...")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Core API tests
        self.test_health_endpoint()
        self.test_halium_versions()
        self.test_build_steps()
        self.test_devices_endpoint()
        self.test_terminal_execute()
        self.test_ai_chat()
        self.test_fastboot_endpoints()
        self.test_build_endpoints()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Print failed tests
        failed_tests = [r for r in self.results if not r["success"]]
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = HaliumAPITester()
    
    try:
        success = tester.run_all_tests()
        
        # Save detailed results
        with open("/app/test_reports/backend_test_results.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_tests": tester.tests_run,
                "passed_tests": tester.tests_passed,
                "success_rate": (tester.tests_passed/tester.tests_run)*100 if tester.tests_run > 0 else 0,
                "results": tester.results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: /app/test_reports/backend_test_results.json")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Testing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n💥 Testing failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())