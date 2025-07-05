# Kairix User Guide

This comprehensive guide covers all aspects of using Kairix, from basic conversations to advanced memory management.

## Table of Contents

1. [Understanding Kairix](#understanding-kairix)
2. [Working with Agents](#working-with-agents)
3. [Conversations & Memory](#conversations--memory)
4. [Voice Interaction](#voice-interaction)
5. [Importing Data](#importing-data)
6. [Privacy & Security](#privacy--security)
7. [Advanced Features](#advanced-features)

## Understanding Kairix

### What Makes Kairix Different?

Unlike traditional chatbots, Kairix agents have:

- **Persistent Memory**: They remember everything across sessions
- **Evolving Personality**: They learn and adapt from interactions
- **Context Awareness**: They understand conversation flow and history
- **Personal Growth**: They develop insights about you over time

### Core Concepts

**Agents**: Your AI companions with unique identities and memories

**Memories**: Structured information agents retain:
- **Experiential**: What happened in conversations
- **Conceptual**: Ideas and knowledge learned
- **Reflective**: Self-generated insights
- **Task State**: Ongoing projects and goals

**Perceptors**: How agents perceive and understand:
- Conversation history
- Environmental context
- Semantic relationships
- Time awareness

## Working with Agents

### Creating Your First Agent

1. Click **"New Agent"** on the dashboard
2. Choose a name (e.g., "Alex", "Research Assistant")
3. Select a persona type:
   - **Conversational**: General-purpose companion
   - **Task-Focused**: Project and goal oriented
   - **Creative**: Artistic and imaginative
   - **Analytical**: Data and logic focused

### Agent Settings

Access agent settings via the gear icon:

- **Model Selection**: Choose between OpenAI, Ollama, or local models
- **Memory Depth**: How far back the agent recalls
- **Personality Traits**: Adjust conversational style
- **Knowledge Domains**: Specialize in specific areas

### Managing Multiple Agents

- Each agent maintains separate memories
- Switch between agents using the sidebar
- Agents cannot access each other's memories (privacy by design)
- Export/import agent data for backup

## Conversations & Memory

### Effective Communication

**Be Natural**: Talk as you would to a knowledgeable friend

**Provide Context**: Share relevant background information

**Ask Follow-ups**: Agents remember previous topics

**Reference Past Conversations**: "Remember when we discussed..."

### Memory Management

#### Viewing Memories
- Click **"Memory"** tab in agent panel
- Browse by type (Experiential, Conceptual, etc.)
- Search memories by keyword
- See memory formation timeline

#### Memory Controls
- **Pin Important Memories**: Keep crucial information accessible
- **Edit Memories**: Correct or update stored information
- **Delete Memories**: Remove sensitive or incorrect data
- **Export Memories**: Download as JSON for backup

### Building Effective Memory

**Regular Interaction**: More conversations = richer memory

**Diverse Topics**: Broaden agent's knowledge base

**Reflection Prompts**: Ask "What have you learned about me?"

**Explicit Teaching**: "Remember that I prefer..."

## Voice Interaction

### Setup

1. Click **Settings** → **Voice**
2. Grant microphone permissions
3. Select voice model:
   - **Natural**: Human-like speech
   - **Fast**: Lower latency responses
   - **Expressive**: Emotional range

### Voice Commands

- **"Hey Kairix"**: Wake word activation
- **Push-to-Talk**: Hold spacebar while speaking
- **Continuous Mode**: Always listening (privacy warning)

### Voice Features

- **Interruption**: Say "Stop" to halt responses
- **Voice Cloning**: Train on your voice (premium)
- **Language Support**: 20+ languages supported
- **Accent Options**: Regional voice variations

## Importing Data

### ChatGPT Export

1. Export ChatGPT data from OpenAI settings
2. Run import command:
   ```bash
   uv run chatgpt-export-v2 -i conversations.json -o output/
   ```
3. Select which conversations to import
4. Assign to existing or new agent

### Other Data Sources

**Text Documents**
- Drag and drop into chat
- Supports: .txt, .md, .pdf, .docx

**Email Archives**
- Import .mbox or .eml files
- Preserves conversation threads

**Note Apps**
- Notion, Obsidian export support
- Maintains link relationships

## Privacy & Security

### Data Ownership

- **Local First**: All data stored on your infrastructure
- **No Cloud Sync**: Unless explicitly configured
- **Export Anytime**: Full data portability
- **Delete Completely**: True data deletion

### Security Features

- **Encryption at Rest**: Database encryption
- **Encrypted Transport**: TLS for all connections
- **Access Controls**: User authentication required
- **Audit Logs**: Track all data access

### Privacy Best Practices

1. **Review Memories Regularly**: Check what's stored
2. **Use Private Mode**: Temporary conversations without memory
3. **Separate Agents**: For different life contexts
4. **Regular Backups**: Export important agent data

## Advanced Features

### Memory Synthesis

Trigger deeper understanding:
```
"Reflect on our conversations this week"
"What patterns do you notice in my work habits?"
"Summarize what you know about my goals"
```

### Custom Perceptors

Add specialized understanding:
- **Calendar Integration**: Time-aware responses
- **Document Analysis**: Deep file understanding
- **Code Understanding**: Programming assistance
- **Image Recognition**: Visual memory

### Automation

**Scheduled Reflections**: Daily/weekly summaries

**Memory Consolidation**: Automatic insight generation

**Task Tracking**: Project status updates

**Notification Rules**: Alert on specific topics

### Multi-Agent Workflows

Coming in v2.0:
- Agent collaboration
- Shared memory pools
- Specialized agent teams
- Workflow automation

## Tips & Best Practices

### For Best Results

1. **Be Consistent**: Regular interaction improves memory
2. **Share Context**: Don't assume prior knowledge initially  
3. **Correct Mistakes**: Help agents learn accurately
4. **Use Names**: Reference people, places, projects
5. **Time Markers**: "Last Tuesday", "Next month"

### Common Patterns

**Daily Standup**
```
"Good morning! Here's what I'm working on today..."
```

**Project Tracking**
```
"Update on Project X: we completed..."
```

**Learning Together**
```
"I'm studying Y. Can you help me understand..."
```

**Reflection Sessions**
```
"Let's review this week. What stood out?"
```

## Troubleshooting

### Agent Not Remembering

- Check memory depth settings
- Ensure agent is not in private mode
- Verify database connection
- Look for memory storage errors

### Slow Responses

- Check model selection (local vs cloud)
- Monitor system resources
- Reduce memory search depth
- Clear conversation cache

### Voice Issues

- Verify microphone permissions
- Check audio input levels
- Test with different browsers
- Disable noise cancellation

## Getting Help

- **In-App Help**: Click ? icon for contextual help
- **Community Forum**: discuss.kairix.ai
- **Discord Support**: discord.gg/kairix
- **Email Support**: support@kairix.ai

## Keyboard Shortcuts

| Action | Windows/Linux | macOS |
|--------|--------------|-------|
| New Message | Enter | Return |
| New Line | Shift+Enter | Shift+Return |
| Search | Ctrl+K | Cmd+K |
| Switch Agent | Ctrl+[1-9] | Cmd+[1-9] |
| Toggle Voice | Ctrl+V | Cmd+V |
| Clear Chat | Ctrl+L | Cmd+L |
| Settings | Ctrl+, | Cmd+, |