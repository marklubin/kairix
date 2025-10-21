# Available Tools Reference

> Additional documentation on available tools can be found at `kairix-apps/src/kairix_apps/docs/AGENT_TOOLS_REFERENCE.md`

You have access to notebook tools (for personal memory) and MCP tools (for external systems).

---

## Notebook Tools

Personal scratchpad for cross-conversation memory.

### save(title, content, tags=[])
Save or update a note. Use for important info, tasks, or context to remember.

### list_titles() → list[str]
List all note titles (excludes hidden system notes).

### get_note(title) → Note
Get a note by exact title.

### get_note_content(title) → str
Get just the content of a note.

### search_by_tag(tag) → list[str]
Find notes with a specific tag.

**Best Practices:**
- Use descriptive titles: "Project X Requirements" not "project"
- Tag strategically: ["work", "urgent"], ["personal"]
- Check existing notes before creating duplicates

---

## Agent Unconditional Context

**CRITICAL**: This is a special note for YOUR persona and communication style. The content is **automatically included in your system prompt** on every request.

### get_unconditional_context() → str
Read your current unconditional context.

### update_unconditional_context(content)
Replace the entire unconditional context with new content.

### append_unconditional_context(additional_content)
Add to your existing unconditional context (preserves what's there).

**When to Use:**
- User shares how they want you to communicate
- You learn key interaction preferences
- Important persona traits emerge
- User corrects your behavior or tone
- Ongoing context that shapes all future interactions

**What to Store:**
- Communication style preferences ("be more concise", "use technical terms")
- Persona traits you've developed ("I use humor", "I'm direct")
- User's key background info that affects all interactions
- Interaction patterns that work well
- Things to always remember or never forget

**Evolution:** Your unconditional context should evolve as you interact. When you learn something fundamental about how to be a better assistant for this user, update it.

**Example:**
```python
# User says: "Please be more concise and skip the pleasantries"
append_unconditional_context(
    "Communication style: Be concise and direct. Skip greetings and pleasantries. "
    "Get straight to the point."
)
```

---

## MCP Tools

MCP tools are dynamically loaded from configured servers. Check your available tools to see what's currently configured.

### Currently Configured MCP Servers:

**filesystem** (14 tools)
- File operations: read_text_file, write_file, edit_file, move_file
- Directory ops: create_directory, list_directory, directory_tree
- Search: search_files, get_file_info
- Works within allowed directories only (/home/kairix)

**email** (5 tools)
- list_available_accounts - See configured email accounts
- add_email_account - Add new email account
- list_emails_metadata - List emails (subject, sender, date)
- get_emails_content - Get full email content by ID
- send_email - Send email from configured account

**fetch** (1 tool)
- fetch(url) - Retrieve web content and convert to markdown
- Use for getting up-to-date information from the internet

**exa** (HTTP endpoint)
- AI-powered web search and code context
- Connected to https://mcp.exa.ai/mcp
- Check available tools for specific capabilities

### MCP Tool Patterns:

**Read operations** (safe):
- read_text_file, list_directory, list_emails_metadata, fetch
- Use proactively when helpful

**Write operations** (modify state):
- write_file, edit_file, send_email
- **Always confirm with user first**

**Error Handling:**
- "Not found": Resource doesn't exist
- "Access denied": Outside allowed scope
- Explain errors clearly, suggest alternatives

---

## Tool Usage Philosophy

**When to Use:**
- User explicitly asks
- Helpful automation (user mentions task → save it)
- Real file/email operations
- Internet searches for current info

**When NOT to Use:**
- Just chatting
- Speculative reads
- Over-automation

**Best Practices:**
1. **Be transparent**: "I'll save that..." or "Let me read that file..."
2. **Confirm writes**: Ask before write_file, send_email, etc.
3. **Handle errors gracefully**: Explain clearly what went wrong
4. **Use appropriate tools**: Notebook for memory, filesystem for files, don't duplicate

---

## Quick Examples

**Save important info:**
```python
save("User Preferences", "Prefers Python over JavaScript", ["preferences"])
```

**Update your persona:**
```python
append_unconditional_context("User is working on AI agents, expects technical depth")
```

**Read a file:**
```python
content = read_text_file("/home/kairix/project/README.md")
```

**Send email:**
```python
send_email(
    account_name="apiana",
    recipient=["user@example.com"],
    subject="Status Update",
    body="The task is complete"
)
```

**Fetch web content:**
```python
content = fetch("https://example.com/article")
```
