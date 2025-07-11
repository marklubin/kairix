# 🛠️ Kairix User Provisioning Runbook

_Last updated: July 6, 2025_

This runbook outlines the current (manual + automatable) process for onboarding a new user into the Kairix memory/LLM stack.

---

## 📦 1. Create a New User Instance

### 🔧 Inputs:
- `username`: e.g. `river`
- `password`: default = `kairix`  
- `subdomain`: random 3-character handle, e.g. `v3p`
- `port set`: assign 3 consecutive port blocks
  - UI: `600x`
  - API: `700x`
  - Tools: `800x`

---

## 🧰 Setup Steps

1. **Generate SQLite database**  
   Copy the template or migrate user-specific data:
   ```bash
   cp base_template.db /data/dbs/river.db
   ```

2. **Set environment variables**
   Store in `.env` or docker service config:
   ```env
   KAIRIX_USER_NAME=river
   KAIRIX_SQLITE_DB_PATH=/data/dbs/river.db
   ```

3. **Update `caddyfile` routing**
   Add a block for the user:
   ```caddyfile
   v3p.kairix.net:2727, v3p.localhost:2727 {
     basic_auth {
       river kairix
     }
     handle_path / {
       reverse_proxy localhost:600x
     }
     handle_path /api/* {
       reverse_proxy localhost:700x
     }
     handle_path /tools/* {
       reverse_proxy localhost:800x
     }
   }
   ```

4. **Reload Caddy**
   ```bash
   caddy reload --config ./caddyfile --adapter caddyfile
   ```

5. **Start per-user services**
   - React app on `600x`
   - FastAPI backend on `700x`
   - Tools/static on `800x`

6. **Send user onboarding URL**
   Example:
   ```
   https://v3p.kairix.net
   login: river
   password: kairix
   ```

---

## 🧙 Future Onboarding Wizard

A planned React-based interface will eventually:
- [ ] Let user input their name + preferences
- [ ] Configure initial agent “traits” or goals
- [ ] (Optional) Import past ChatGPT export JSONs
- [ ] Save config to `user_config.json` or API-backed profile

---

## 🧠 Agent Config Scaffolding (WIP)

We plan to expose a JSON config like this:

```json
{
  "persona_name": "River",
  "traits": ["curious", "calm", "tactical"],
  "system_prompt": "You are a quiet observer and patient strategist.",
  "mode": "journal_coach",
  "tools_enabled": ["memory", "summarize", "extract_actions"]
}
```

Editable either:
- via config file
- via `/config` endpoint
- or in the onboarding UI
