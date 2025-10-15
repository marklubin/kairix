# Kairix Server Testing Guide

## Running the Test Suite

### Quick Test
Run all automated tests against the running server:

```bash
uv run python test_server.py
```

### Test Against Different URL
```bash
uv run python test_server.py http://example.com:8888
```

## Test Categories

### ✅ Basic Endpoint Tests
- **Health Check** (`/health`) - Verifies server is responding
- **Models List** (`/v1/models`) - Verifies available AI models

### ✅ Admin Panel Tests
- **Admin Info** (`/admin/info`) - Verifies server configuration
- **Admin Panel** (`/admin`) - Verifies HTML UI is accessible

### ⚠️ Chat Completion Tests
- **Simple Completion** - Tests basic chat with OpenAI
- **No Auth** - Tests endpoint without authentication

### ✅ Additional Tests
- **CORS Headers** - Verifies cross-origin support

## Test Results

The test suite provides color-coded output:
- 🟢 **Green ✓** = Test passed
- 🔴 **Red ✗** = Test failed
- 🟡 **Yellow ⚠** = Warning (non-critical issue)

## Known Issues

### Chat Completion Validation Error
**Status:** FIXED
**Details:** Response model missing `logprobs` field
**Impact:** Previously caused server errors, now resolved
**Fix:** Added monkey-patch in server.py:64-81 to make `logprobs` optional in ResponseTextDeltaEvent

### CORS Headers on OPTIONS
**Status:** Minor warning
**Details:** OPTIONS preflight requests may not return CORS headers
**Impact:** None for direct API access, may affect some browser-based clients
**Workaround:** CORS middleware is active for actual requests

## Manual Testing

### Using the Admin Panel
1. Open browser to `http://localhost:8888/admin`
2. Fill in the message field
3. Click "Send Message"
4. View response in the panel

### Using cURL

**Test Health:**
```bash
curl http://localhost:8888/health
```

**Test Models:**
```bash
curl http://localhost:8888/v1/models
```

**Test Chat Completion:**
```bash
curl -X POST http://localhost:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "x-api-key: test" \
  -d '{"model":"kairix-conversational","messages":[{"role":"user","content":"Hello"}],"stream":false}'
```

## Continuous Testing

For development, you can run tests in watch mode:

```bash
# Run tests every 5 seconds
watch -n 5 'uv run python test_server.py'
```

## Test Coverage

Current test coverage:
- ✅ HTTP endpoints
- ✅ JSON responses
- ✅ HTML rendering
- ✅ Server initialization
- ⚠️ Chat completions (partial)
- ❌ Streaming responses (not yet tested)
- ❌ Context updates (not yet tested)

## Adding New Tests

To add a new test to `test_server.py`:

```python
async def test_my_feature(self) -> bool:
    """Test description."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/my-endpoint")

            if response.status_code == 200:
                self.print_test("My feature", "PASS", "Works!")
                return True
            else:
                self.print_test("My feature", "FAIL", f"HTTP {response.status_code}")
                return False
    except Exception as e:
        self.print_test("My feature", "FAIL", f"Error: {e}")
        return False
```

Then add it to `run_all_tests()`:
```python
await self.test_my_feature()
```
