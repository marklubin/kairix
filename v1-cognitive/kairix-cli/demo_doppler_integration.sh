#!/bin/bash
# Demo script showing Doppler integration with user management

echo "=== Kairix CLI - Doppler Integration Demo ==="
echo

echo "1. Creating a new user 'testuser'..."
echo "   - This will clone the 'mark' Doppler config which contains all API keys"
echo "   - API keys like OPENAI_API_KEY, ELEVENLABS_API_KEY are preserved"
echo "   - User-specific vars like KAIRIX_USER, KAIRIX_DB_PATH are set"
echo
echo "Command: uv run kairix users create testuser --subdomain tst"
echo

echo "2. Viewing user's environment variables..."
echo "   - Shows all inherited API keys plus user-specific settings"
echo
echo "Command: uv run kairix users getenv testuser"
echo

echo "3. Setting a user-specific environment variable..."
echo "   - This overrides just for this user, not affecting others"
echo
echo "Command: uv run kairix users setenv testuser CUSTOM_MODEL gpt-4"
echo

echo "4. The systemd services use user-specific Doppler configs:"
echo "   - Server: doppler run -c user-testuser -p kairix -- uv run python -m kairix_apps.server"
echo "   - Website: doppler run -c user-testuser -p kairix -- npm run serve"
echo

echo "5. Each user's services are completely isolated:"
echo "   - kairix-testuser-server (runs on port from Doppler config)"
echo "   - kairix-testuser-website (runs on port from Doppler config)"
echo

echo "6. Shared services (magg, caddy) are system-wide:"
echo "   - Managed with: kairix system start/stop/status/logs"
echo

echo "=== Key Features ==="
echo "✅ Idempotent - won't overwrite existing Doppler configs"
echo "✅ API keys inherited from 'mark' template"
echo "✅ User-specific overrides possible"
echo "✅ Each user gets isolated services and database"
echo "✅ Ports come from Doppler, not hardcoded"