# Kairix User Management Guide

## Overview

The `kairixctl` tool automates user onboarding for the Kairix system. It generates Caddy configurations, suggests database setup commands, and provides a complete checklist for adding new users.

## Installation

The tool is part of the kairix-tools package:

```bash
cd kairix-sre-agent
just install
```

## Commands

### Create New User

```bash
just new-user
# or
uv run python kairixctl.py new-user
```

Interactive prompts will ask for:
- **Username**: e.g., "river"
- **Display name**: Optional full name
- **Subdomain**: 3-character subdomain (auto-generated if blank)
- **Password**: Default is "kairix"

The tool will:
1. Auto-detect the next available port base
2. Generate a bcrypt-hashed password for Caddy
3. Create the complete Caddyfile configuration block
4. Provide all necessary commands and a checklist

### List All Users

```bash
just list-users
```

Shows all users configured in the Caddyfile with their:
- Username
- Subdomain
- Port assignments (UI, API, Tools)

### Check User Status

```bash
just check-user alice
```

Shows:
- User configuration details
- Service health status (running/down)
- Port assignments

## Example Workflow

### 1. Add a New User

```bash
$ just new-user
Username: sarah
Display name (optional): Sarah Connor
Subdomain (3 chars, or auto-generate): 
Password [kairix]: 
📝 Generated subdomain: sar
🔍 Auto-detected next port base: 6015

✅ Caddy config for sar.kairix.net generated.
➡️  Add the following block to your Caddyfile:
--------------------------------------------------
http://sar.kairix.net, sar.localhost {
	basic_auth {
		sarah $2a$14$Zkx19XLiW6VYouLHR5NmfOFU0z2GTNmpkT/5qqR7hx4IjWJPDhjvG
	}

	handle_path / {
		reverse_proxy localhost:6015
	}

	handle_path /api/* {
		reverse_proxy localhost:7015
	}

	handle_path /tools/* {
		reverse_proxy localhost:8015
	}
}
--------------------------------------------------
```

### 2. Follow the Checklist

The tool provides a complete checklist:

```
📋 Checklist:
  ✅ Config generated
  ❗ Add config to Caddyfile
  ❗ Copy database template
  ❗ Set up user environment
  ❗ Start user services
  ❗ Reload Caddy
  🧪 Test the new instance
```

### 3. Execute Commands

```bash
# Copy the Caddy config block to your Caddyfile
vim ~/kairix/caddyfile

# Copy database
cp base_template.db /data/dbs/sarah.db

# Set up environment
just set-env sarah

# Reload Caddy
caddy reload --config ./Caddyfile --adapter caddyfile

# Test
curl -u sarah:kairix https://sar.kairix.net:2727/api/status
```

## Port Allocation

The tool automatically finds the next available port base:
- Reads existing ports from Caddyfile
- Finds the highest used port in the 6000 range
- Assigns the next sequential number

Port ranges:
- UI: 6xxx (e.g., 6015)
- API: 7xxx (e.g., 7015)
- Tools: 8xxx (e.g., 8015)

## Subdomain Generation

If no subdomain is provided:
1. Uses first 3 characters of username (if valid)
2. Otherwise generates random 3-character subdomain
3. Format: `[a-z0-9]{3}`

## Password Security

- Default password: "kairix"
- Automatically bcrypt-hashed with cost factor 14
- Compatible with Caddy's basic_auth
- Use `--no-hash-password` for plain text (not recommended)

## Advanced Options

### Custom Port Base

```bash
uv run python kairixctl.py new-user --port-base 6020
```

### Custom Database Template

```bash
uv run python kairixctl.py new-user --db-template /path/to/custom.db
```

### Pre-set All Values

```bash
uv run python kairixctl.py new-user \
  --username john \
  --subdomain jdx \
  --port-base 6016 \
  --password secretpass
```

## Integration with SRE Agent

After adding a new user:
1. The SRE agent will automatically discover them on next run
2. No need to update SRE agent configuration
3. Services will be monitored immediately

Check with:
```bash
just sre-services
```

## Troubleshooting

### "Port base must be between 6000-6999"
- The tool enforces standard port ranges
- UI ports must be in 6xxx range

### Subdomain Already Exists
- Check existing users: `just list-users`
- Choose a different 3-character subdomain

### Caddy Won't Reload
- Check Caddyfile syntax
- Ensure no duplicate subdomains
- Verify port conflicts

### Services Not Starting
- Check if ports are already in use: `lsof -i :6015`
- Verify database was copied correctly
- Check user environment setup

## Best Practices

1. **Always use bcrypt hashing** (default behavior)
2. **Follow port sequence** to avoid conflicts
3. **Document user additions** with the summary output
4. **Test immediately** after setup
5. **Monitor with SRE agent** for ongoing health

---

*Part of the Kairix Tools suite*