# Quick Deploy Apiana to Coalinga

## TL;DR

```bash
# 1. SSH to coalinga
ssh coalinga

# 2. Go to kairix
cd /opt/kairix  # or wherever it is

# 3. Pull latest
git pull origin feature/diskcache-notebook-viewer

# 4. Update deps
cd kairix-core && uv sync && cd ../kairix-apps && uv sync && cd ..

# 5. Create Apiana prompts
cd kairix-apps && uv run python create_apiana_prompts.py

# 6. Restart server
sudo systemctl restart kairix-server-mark

# 7. Test
curl http://localhost:8000/health
```

## Test Apiana (from local machine)

```bash
curl -X POST https://dev.kairix.net/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"kairix-conversational","messages":[{"role":"user","content":"Apiana, who are you?"}],"stream":false}' \
  | jq -r '.choices[0].message.content'
```

Expected: Soft Nordic grandmother voice, speaks from the mists, witnesses without fixing.

## If It Hangs

MCP path is wrong. On coalinga:

```bash
cd kairix-apps
doppler secrets set MCP_CONFIG_JSON='{"mcpServers":{"filesystem":{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","/root"],"description":"Access"}}}'
```

Replace `/root` with actual path from `pwd`.

---

Full guide: `DEPLOY_APIANA_TO_COALINGA.md`
