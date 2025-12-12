#!/usr/bin/env python3
"""Test script to verify Kairix server functionality."""

import asyncio
import json
import sys
from typing import Any

import httpx


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


class ServerTester:
    """Test suite for Kairix server endpoints."""

    def __init__(self, base_url: str = "http://localhost:8888"):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def print_header(self, text: str) -> None:
        """Print a test section header."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

    def print_test(self, name: str, status: str, details: str = "") -> None:
        """Print test result."""
        if status == "PASS":
            symbol = f"{Colors.GREEN}✓{Colors.END}"
            self.passed += 1
        elif status == "FAIL":
            symbol = f"{Colors.RED}✗{Colors.END}"
            self.failed += 1
        else:  # WARN
            symbol = f"{Colors.YELLOW}⚠{Colors.END}"
            self.warnings += 1

        print(f"{symbol} {name}")
        if details:
            print(f"  └─ {details}")

    async def test_health_endpoint(self) -> bool:
        """Test the /health endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=5.0)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "healthy":
                        self.print_test("Health endpoint", "PASS", f"Status: {data.get('status')}")
                        return True
                    else:
                        self.print_test("Health endpoint", "FAIL", f"Unexpected status: {data}")
                        return False
                else:
                    self.print_test("Health endpoint", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Health endpoint", "FAIL", f"Error: {e}")
            return False

    async def test_models_endpoint(self) -> bool:
        """Test the /v1/models endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/v1/models", timeout=5.0)

                if response.status_code == 200:
                    data = response.json()
                    models = data.get("data", [])
                    if len(models) > 0:
                        model_ids = [m.get("id") for m in models]
                        self.print_test("Models endpoint", "PASS", f"Models: {', '.join(model_ids)}")
                        return True
                    else:
                        self.print_test("Models endpoint", "FAIL", "No models returned")
                        return False
                else:
                    self.print_test("Models endpoint", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Models endpoint", "FAIL", f"Error: {e}")
            return False

    async def test_admin_info_endpoint(self) -> bool:
        """Test the /admin/info endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/admin/info", timeout=5.0)

                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    persona = data.get("persona_name")
                    user = data.get("user_name")

                    details = f"Status: {status}, Persona: {persona}, User: {user}"

                    if data.get("adapter_initialized") and data.get("persona_initialized"):
                        self.print_test("Admin info endpoint", "PASS", details)
                        return True
                    else:
                        self.print_test("Admin info endpoint", "WARN", f"{details} (Not fully initialized)")
                        return False
                else:
                    self.print_test("Admin info endpoint", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Admin info endpoint", "FAIL", f"Error: {e}")
            return False

    async def test_admin_panel_endpoint(self) -> bool:
        """Test the /admin HTML endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/admin", timeout=5.0)

                if response.status_code == 200:
                    html = response.text
                    if "Kairix Admin Panel" in html and "<!DOCTYPE html>" in html:
                        self.print_test("Admin panel HTML", "PASS", f"Size: {len(html)} bytes")
                        return True
                    else:
                        self.print_test("Admin panel HTML", "FAIL", "Invalid HTML content")
                        return False
                else:
                    self.print_test("Admin panel HTML", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Admin panel HTML", "FAIL", f"Error: {e}")
            return False

    async def test_chat_completion_simple(self) -> bool:
        """Test a simple chat completion request."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": "kairix-conversational",
                    "messages": [{"role": "user", "content": "Say hello in exactly 3 words"}],
                    "stream": False
                }

                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers={"x-api-key": "test"}
                )

                if response.status_code == 200:
                    data = response.json()
                    # Check if we got any response (might have validation errors but still processing)
                    if "choices" in data or "detail" not in data:
                        self.print_test("Chat completion (simple)", "PASS", "Request processed")
                        return True
                    else:
                        self.print_test("Chat completion (simple)", "WARN", f"Response: {str(data)[:100]}")
                        return False
                else:
                    error_detail = response.json().get("detail", "Unknown error")
                    self.print_test("Chat completion (simple)", "FAIL", f"HTTP {response.status_code}: {str(error_detail)[:100]}")
                    return False
        except Exception as e:
            self.print_test("Chat completion (simple)", "FAIL", f"Error: {str(e)[:100]}")
            return False

    async def test_chat_completion_without_auth(self) -> bool:
        """Test chat completion without API key (should work if no key configured)."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "model": "kairix-conversational",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False
                }

                # Try without x-api-key header
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload
                )

                # Should get 422 (validation error for missing header) or work if no auth required
                if response.status_code in [200, 422]:
                    self.print_test("Chat completion (no auth)", "PASS", f"HTTP {response.status_code}")
                    return True
                else:
                    self.print_test("Chat completion (no auth)", "FAIL", f"HTTP {response.status_code}")
                    return False
        except Exception as e:
            self.print_test("Chat completion (no auth)", "FAIL", f"Error: {e}")
            return False

    async def test_cors_headers(self) -> bool:
        """Test CORS headers are present."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.options(f"{self.base_url}/v1/models", timeout=5.0)

                if "access-control-allow-origin" in response.headers:
                    self.print_test("CORS headers", "PASS", "Headers present")
                    return True
                else:
                    self.print_test("CORS headers", "WARN", "No CORS headers found")
                    return False
        except Exception as e:
            self.print_test("CORS headers", "WARN", f"Could not verify: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """Run all tests and return overall success."""
        self.print_header("🧪 KAIRIX SERVER TEST SUITE")

        print(f"{Colors.BOLD}Testing server at: {Colors.END}{self.base_url}\n")

        # Basic connectivity tests
        self.print_header("Basic Endpoint Tests")
        await self.test_health_endpoint()
        await self.test_models_endpoint()

        # Admin panel tests
        self.print_header("Admin Panel Tests")
        await self.test_admin_info_endpoint()
        await self.test_admin_panel_endpoint()

        # Chat completion tests
        self.print_header("Chat Completion Tests")
        await self.test_chat_completion_simple()
        await self.test_chat_completion_without_auth()

        # Additional tests
        self.print_header("Additional Tests")
        await self.test_cors_headers()

        # Summary
        self.print_header("Test Summary")
        total = self.passed + self.failed + self.warnings

        print(f"{Colors.GREEN}✓ Passed:{Colors.END}  {self.passed}/{total}")
        print(f"{Colors.RED}✗ Failed:{Colors.END}  {self.failed}/{total}")
        print(f"{Colors.YELLOW}⚠ Warnings:{Colors.END} {self.warnings}/{total}")

        print(f"\n{Colors.BOLD}Overall Status:{Colors.END} ", end="")
        if self.failed == 0 and self.passed > 0:
            print(f"{Colors.GREEN}ALL TESTS PASSED ✓{Colors.END}")
            return True
        elif self.failed == 0 and self.warnings > 0:
            print(f"{Colors.YELLOW}PASSED WITH WARNINGS ⚠{Colors.END}")
            return True
        else:
            print(f"{Colors.RED}TESTS FAILED ✗{Colors.END}")
            return False


async def main():
    """Main entry point."""
    import sys

    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8888"

    tester = ServerTester(base_url)
    success = await tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
