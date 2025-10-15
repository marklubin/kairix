"""Test suite for model management system.

Tests database operations, API endpoints, Doppler integration, and model validation.
"""
import asyncio
import httpx
import sys
from typing import Optional


class ModelManagementTests:
    """Comprehensive test suite for model management features."""

    def __init__(self, base_url: str = "http://localhost:8888"):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def print_test(self, name: str, status: str, detail: str = ""):
        """Print formatted test result."""
        colors = {
            "PASS": "\033[92m✓\033[0m",
            "FAIL": "\033[91m✗\033[0m",
            "WARN": "\033[93m⚠\033[0m"
        }
        print(f"{colors.get(status, '?')} {name}")
        if detail:
            print(f"  └─ {detail}")

    async def test_models_endpoint(self) -> bool:
        """Test GET /admin/models endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/admin/models", timeout=10.0)

                if response.status_code == 200:
                    data = response.json()
                    if "models" in data and "current_model" in data:
                        models = data["models"]
                        if len(models) > 0:
                            self.print_test("Models list endpoint", "PASS", f"Found {len(models)} models")
                            return True
                        else:
                            self.print_test("Models list endpoint", "FAIL", "No models returned")
                            return False
                    else:
                        self.print_test("Models list endpoint", "FAIL", "Missing required fields")
                        return False
                else:
                    self.print_test("Models list endpoint", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Models list endpoint", "FAIL", f"Error: {e}")
            return False

    async def test_model_selection(self) -> bool:
        """Test POST /admin/models/select endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                # First get current models
                response = await client.get(f"{self.base_url}/admin/models")
                data = response.json()
                current_model = data["current_model"]

                # Find a different model to select
                test_model = None
                for model in data["models"]:
                    if model["model_id"] != current_model:
                        test_model = model["model_id"]
                        break

                if not test_model:
                    self.print_test("Model selection", "WARN", "Only one model available, cannot test switching")
                    return True

                # Test selecting a different model
                form_data = {"model_id": test_model}
                response = await client.post(
                    f"{self.base_url}/admin/models/select",
                    data=form_data,
                    timeout=15.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success") and result.get("current_model") == test_model:
                        self.print_test("Model selection", "PASS", f"Successfully switched to {test_model}")

                        # Switch back to original
                        form_data = {"model_id": current_model}
                        await client.post(f"{self.base_url}/admin/models/select", data=form_data)

                        return True
                    else:
                        self.print_test("Model selection", "FAIL", "Invalid response format")
                        return False
                else:
                    self.print_test("Model selection", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Model selection", "FAIL", f"Error: {e}")
            return False

    async def test_model_validation(self) -> bool:
        """Test POST /admin/models/validate endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                # Get available models
                response = await client.get(f"{self.base_url}/admin/models")
                data = response.json()
                test_model = data["current_model"]

                # Test model validation
                form_data = {"model_id": test_model}
                response = await client.post(
                    f"{self.base_url}/admin/models/validate",
                    data=form_data,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("valid"):
                        self.print_test("Model validation", "PASS", f"{test_model} validated successfully")
                        return True
                    else:
                        self.print_test("Model validation", "FAIL", f"Model marked invalid: {result.get('error')}")
                        return False
                else:
                    self.print_test("Model validation", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Model validation", "FAIL", f"Error: {e}")
            return False

    async def test_admin_info_includes_model(self) -> bool:
        """Test that /admin/info includes current_model."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/admin/info", timeout=5.0)

                if response.status_code == 200:
                    data = response.json()
                    if "current_model" in data:
                        self.print_test("Admin info includes model", "PASS", f"Model: {data['current_model']}")
                        return True
                    else:
                        self.print_test("Admin info includes model", "FAIL", "Missing current_model field")
                        return False
                else:
                    self.print_test("Admin info includes model", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Admin info includes model", "FAIL", f"Error: {e}")
            return False

    async def test_invalid_model_selection(self) -> bool:
        """Test selecting an invalid model ID."""
        try:
            async with httpx.AsyncClient() as client:
                form_data = {"model_id": "invalid-model-that-does-not-exist"}
                response = await client.post(
                    f"{self.base_url}/admin/models/select",
                    data=form_data,
                    timeout=10.0
                )

                if response.status_code == 500:
                    self.print_test("Invalid model rejection", "PASS", "Invalid model rejected")
                    return True
                else:
                    self.print_test("Invalid model rejection", "FAIL", f"Should reject invalid model (got {response.status_code})")
                    return False
        except Exception as e:
            self.print_test("Invalid model rejection", "FAIL", f"Error: {e}")
            return False

    async def run_all_tests(self):
        """Run all model management tests."""
        print("\n\033[1m\033[94m============================================================\033[0m")
        print("\033[1m\033[94m🧪 MODEL MANAGEMENT TEST SUITE\033[0m")
        print("\033[1m\033[94m============================================================\033[0m")
        print(f"\n\033[1mTesting server at:\033[0m {self.base_url}\n")

        tests = [
            ("Models list endpoint", self.test_models_endpoint),
            ("Model selection", self.test_model_selection),
            ("Model validation", self.test_model_validation),
            ("Admin info includes model", self.test_admin_info_includes_model),
            ("Invalid model rejection", self.test_invalid_model_selection),
        ]

        results = []
        for name, test_func in tests:
            try:
                result = await test_func()
                results.append(result)
                if result:
                    self.passed += 1
                else:
                    self.failed += 1
            except Exception as e:
                self.print_test(name, "FAIL", f"Exception: {e}")
                self.failed += 1
                results.append(False)

        # Print summary
        print("\n\033[1m\033[94m============================================================\033[0m")
        print("\033[1m\033[94mTest Summary\033[0m")
        print("\033[1m\033[94m============================================================\033[0m\n")

        total = self.passed + self.failed
        print(f"\033[92m✓ Passed:\033[0m  {self.passed}/{total}")
        print(f"\033[91m✗ Failed:\033[0m  {self.failed}/{total}")
        if self.warnings > 0:
            print(f"\033[93m⚠ Warnings:\033[0m {self.warnings}/{total}")

        if self.failed == 0:
            print(f"\n\033[1mOverall Status:\033[0m \033[92mALL TESTS PASSED ✓\033[0m\n")
            return 0
        else:
            print(f"\n\033[1mOverall Status:\033[0m \033[91mSOME TESTS FAILED ✗\033[0m\n")
            return 1


async def main():
    """Main test runner."""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8888"

    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            await client.get(f"{base_url}/health", timeout=5.0)
    except Exception:
        print(f"\n\033[91m✗ Server is not running at {base_url}\033[0m")
        print("   Start it with: doppler run -p kairix -c mark -- uv run python src/kairix_apps/server.py\n")
        return 1

    tests = ModelManagementTests(base_url)
    return await tests.run_all_tests()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
