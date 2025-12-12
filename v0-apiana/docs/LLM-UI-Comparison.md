# LLM UI Comparison Guide

## TUIs (Terminal)

| Tool | Pros | Cons | Best For |
|------|------|------|----------|
| **Oterm** | Native Ollama support, fast, model switching | Terminal only | Quick chats, server use |
| **Elia** | Beautiful UI, syntax highlighting | Python dependency | Developers |
| **tgpt** | Simple, fast, scriptable | Limited features | Quick queries |

## Web UIs

| Tool | Pros | Cons | Best For |
|------|------|------|----------|
| **Open WebUI** | Full-featured, auth, sharing, plugins | Requires Docker | Team use, full features |
| **Enchanted** | Native macOS, fast, beautiful | macOS only | Mac users |
| **Ollama UI** | Simple, lightweight | Basic features | Minimal setup |

## Desktop Apps

| Tool | Pros | Cons | Best For |
|------|------|------|----------|
| **LM Studio** | Model management, quantization | Large app | Power users |
| **GPT4All** | Easy setup, built-in models | Limited customization | Beginners |
| **Jan** | Modern UI, extensible | Still in development | General use |

## Quick Setup Commands

```bash
# Oterm (Ollama TUI)
pip install oterm && oterm

# Open WebUI (Full Web Interface)
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data --name open-webui --restart always \
  ghcr.io/open-webui/open-webui:main

# Then visit: http://localhost:3000
```

## Features to Look For

- **Model Management**: Download, delete, configure models
- **System Prompts**: Save and switch between different system prompts
- **Conversation History**: Save and search past conversations
- **Import/Export**: Backup your chats
- **API Integration**: Use with other tools
- **Multimodal**: Support for images (if your models support it)