"""Test suite for system prompt management.

Tests database operations, API endpoints, and AI generation functionality.
"""
import asyncio
import httpx
import sys
from typing import Optional


class SystemPromptManagementTests:
    """Comprehensive test suite for system prompt management features."""

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

    async def test_prompts_endpoint(self) -> bool:
        """Test GET /admin/prompts endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/admin/prompts", timeout=10.0)

                if response.status_code == 200:
                    data = response.json()
                    if "prompts" in data and "current_prompt" in data:
                        prompts = data["prompts"]
                        if len(prompts) >= 2:  # Should have at least v1 and v2
                            self.print_test("Prompts list endpoint", "PASS", f"Found {len(prompts)} prompts")
                            return True
                        else:
                            self.print_test("Prompts list endpoint", "FAIL", f"Expected at least 2 prompts, got {len(prompts)}")
                            return False
                    else:
                        self.print_test("Prompts list endpoint", "FAIL", "Missing required fields")
                        return False
                else:
                    self.print_test("Prompts list endpoint", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Prompts list endpoint", "FAIL", f"Error: {e}")
            return False

    async def test_prompt_selection(self) -> bool:
        """Test POST /admin/prompts/select endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                # First get current prompts
                response = await client.get(f"{self.base_url}/admin/prompts")
                data = response.json()
                current_prompt = data["current_prompt"]

                # Find a different prompt to select
                test_prompt = None
                for prompt in data["prompts"]:
                    if prompt["prompt_id"] != current_prompt:
                        test_prompt = prompt["prompt_id"]
                        break

                if not test_prompt:
                    self.print_test("Prompt selection", "WARN", "Only one prompt available, cannot test switching")
                    return True

                # Test selecting a different prompt
                form_data = {"prompt_id": test_prompt}
                response = await client.post(
                    f"{self.base_url}/admin/prompts/select",
                    data=form_data,
                    timeout=15.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success") and result.get("current_prompt") == test_prompt:
                        self.print_test("Prompt selection", "PASS", f"Successfully switched to {test_prompt}")

                        # Switch back to original
                        form_data = {"prompt_id": current_prompt}
                        await client.post(f"{self.base_url}/admin/prompts/select", data=form_data)

                        return True
                    else:
                        self.print_test("Prompt selection", "FAIL", "Invalid response format")
                        return False
                else:
                    self.print_test("Prompt selection", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Prompt selection", "FAIL", f"Error: {e}")
            return False

    async def test_prompt_save(self) -> bool:
        """Test POST /admin/prompts/save endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                # Save a test prompt
                test_prompt_id = "test_custom_prompt"
                form_data = {
                    "prompt_id": test_prompt_id,
                    "name": "Test Custom Prompt",
                    "description": "A test prompt created by automated tests",
                    "content": "You are a test assistant for {agent_name} helping {user_name}.",
                    "version": "test"
                }

                response = await client.post(
                    f"{self.base_url}/admin/prompts/save",
                    data=form_data,
                    timeout=15.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        self.print_test("Prompt save", "PASS", f"Successfully saved {test_prompt_id}")
                        return True
                    else:
                        self.print_test("Prompt save", "FAIL", "Save failed")
                        return False
                else:
                    self.print_test("Prompt save", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Prompt save", "FAIL", f"Error: {e}")
            return False

    async def test_ai_prompt_generation(self) -> bool:
        """Test POST /admin/prompts/generate endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                # Generate a prompt with AI
                form_data = {
                    "requirements": "Create a helpful coding assistant that is concise and clear"
                }

                response = await client.post(
                    f"{self.base_url}/admin/prompts/generate",
                    data=form_data,
                    timeout=60.0  # AI generation may take longer
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success") and result.get("generated_prompt"):
                        generated = result["generated_prompt"]
                        if len(generated) > 50 and "{agent_name}" in generated:
                            self.print_test("AI prompt generation", "PASS", f"Generated {len(generated)} chars with template vars")
                            return True
                        else:
                            self.print_test("AI prompt generation", "FAIL", "Generated prompt too short or missing template vars")
                            return False
                    else:
                        self.print_test("AI prompt generation", "FAIL", "Invalid response format")
                        return False
                else:
                    self.print_test("AI prompt generation", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("AI prompt generation", "FAIL", f"Error: {e}")
            return False

    async def test_prompt_content_format(self) -> bool:
        """Test that prompts have proper template variable format."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/admin/prompts")
                data = response.json()

                all_have_vars = True
                for prompt in data["prompts"]:
                    content = prompt.get("content", "")
                    if "{agent_name}" not in content or "{user_name}" not in content:
                        all_have_vars = False
                        self.print_test("Prompt content format", "FAIL", f"{prompt['prompt_id']} missing template vars")
                        return False

                if all_have_vars:
                    self.print_test("Prompt content format", "PASS", "All prompts have required template variables")
                    return True
                return False
        except Exception as e:
            self.print_test("Prompt content format", "FAIL", f"Error: {e}")
            return False

    async def test_admin_ui_loads(self) -> bool:
        """Test that admin panel loads with prompt UI."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/admin", timeout=5.0)

                if response.status_code == 200:
                    html = response.text
                    # Check for key elements in the UI
                    required_elements = [
                        "System Prompt Configuration",
                        "prompt-select",
                        "prompt-preview",
                        "Generate with AI",
                        "requirements"
                    ]

                    missing = []
                    for element in required_elements:
                        if element not in html:
                            missing.append(element)

                    if not missing:
                        self.print_test("Admin UI loads", "PASS", "All prompt UI elements present")
                        return True
                    else:
                        self.print_test("Admin UI loads", "FAIL", f"Missing elements: {', '.join(missing)}")
                        return False
                else:
                    self.print_test("Admin UI loads", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Admin UI loads", "FAIL", f"Error: {e}")
            return False

    async def run_all_tests(self):
        """Run all system prompt management tests."""
        print("\n\033[1m\033[94m============================================================\033[0m")
        print("\033[1m\033[94m🧪 SYSTEM PROMPT MANAGEMENT TEST SUITE\033[0m")
        print("\033[1m\033[94m============================================================\033[0m")
        print(f"\n\033[1mTesting server at:\033[0m {self.base_url}\n")

        tests = [
            ("Prompts list endpoint", self.test_prompts_endpoint),
            ("Prompt selection", self.test_prompt_selection),
            ("Prompt save", self.test_prompt_save),
            ("AI prompt generation", self.test_ai_prompt_generation),
            ("Prompt content format", self.test_prompt_content_format),
            ("Admin UI loads", self.test_admin_ui_loads),
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

    tests = SystemPromptManagementTests(base_url)
    return await tests.run_all_tests()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
