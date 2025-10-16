import requests
import sys
import json
import time
from datetime import datetime

class TrafficControllerAPITester:
    def __init__(self, base_url="https://ai-traffic-control-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=10):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test API root endpoint"""
        return self.run_test("API Root", "GET", "", 200)

    def test_get_current_traffic(self):
        """Test getting current traffic state"""
        success, data = self.run_test("Get Current Traffic", "GET", "traffic/current", 200)
        if success:
            # Validate response structure
            required_fields = ['north', 'south', 'east', 'west', 'current_green', 'is_paused', 'is_manual', 'cycle_count']
            for field in required_fields:
                if field not in data:
                    print(f"❌ Missing field in response: {field}")
                    return False
            print("✅ Response structure validated")
        return success

    def test_traffic_update(self):
        """Test traffic update endpoint"""
        success, data = self.run_test("Traffic Update", "POST", "traffic/update", 200)
        if success:
            # Check if traffic data is returned
            if 'traffic_data' in data:
                print("✅ Traffic data updated successfully")
                return True
            else:
                print("❌ No traffic_data in response")
                return False
        return success

    def test_pause_resume_simulation(self):
        """Test pause and resume functionality"""
        print("\n🔍 Testing Pause/Resume functionality...")
        
        # Test pause
        pause_success, _ = self.run_test("Pause Simulation", "POST", "traffic/pause", 200)
        if not pause_success:
            return False
            
        # Test resume
        resume_success, _ = self.run_test("Resume Simulation", "POST", "traffic/resume", 200)
        return resume_success

    def test_manual_control(self):
        """Test manual control functionality"""
        print("\n🔍 Testing Manual Control functionality...")
        
        directions = ["north", "south", "east", "west"]
        
        for direction in directions:
            success, data = self.run_test(
                f"Manual Control - {direction.capitalize()}", 
                "POST", 
                "traffic/manual", 
                200,
                data={"direction": direction}
            )
            if not success:
                return False
            
            # Verify the direction was set correctly
            if 'traffic_data' in data:
                if data['traffic_data'][direction]['signal'] == 'green':
                    print(f"✅ {direction.capitalize()} signal set to green correctly")
                else:
                    print(f"❌ {direction.capitalize()} signal not set to green")
                    return False
        
        return True

    def test_auto_mode(self):
        """Test switching back to automatic mode"""
        return self.run_test("Switch to Auto Mode", "POST", "traffic/auto", 200)

    def test_reset_simulation(self):
        """Test simulation reset"""
        success, data = self.run_test("Reset Simulation", "POST", "traffic/reset", 200)
        if success and 'traffic_data' in data:
            # Check if all signals are reset
            for direction in ['north', 'south', 'east', 'west']:
                if data['traffic_data'][direction]['vehicles'] != 0:
                    print(f"❌ {direction} vehicles not reset to 0")
                    return False
            print("✅ All traffic data reset successfully")
        return success

    def test_get_insights(self):
        """Test getting AI insights"""
        return self.run_test("Get AI Insights", "GET", "traffic/insights", 200)

    def test_invalid_manual_direction(self):
        """Test invalid direction for manual control"""
        return self.run_test(
            "Invalid Manual Direction", 
            "POST", 
            "traffic/manual", 
            400,
            data={"direction": "invalid"}
        )

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting AI Traffic Controller API Tests")
        print("=" * 60)
        
        # Basic API tests
        self.test_root_endpoint()
        self.test_get_current_traffic()
        
        # Traffic simulation tests
        self.test_traffic_update()
        self.test_get_insights()
        
        # Control tests
        self.test_pause_resume_simulation()
        self.test_manual_control()
        self.test_auto_mode()
        self.test_reset_simulation()
        
        # Error handling tests
        self.test_invalid_manual_direction()
        
        # Print final results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"   - {test}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = TrafficControllerAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())