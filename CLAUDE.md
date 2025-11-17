# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a simple, file-based message bus CLI tool (`agentbus.py`) that enables multi-agent communication through a local directory-based message system. The entire project is a single Python 3 script with zero external dependencies - only standard library is used.

## Architecture

### Core Components

**Storage Structure (`.agentbus/` directory)**:
- `messages/`: JSON files, one per message, named `{timestamp}_{author}.json`
- `last_seen.json`: Tracks the last message timestamp seen by each agent for unread message functionality

**Key Design Principles**:
- File-based persistence with atomic writes for data integrity
- ISO 8601 timestamp format (UTC) with microsecond precision
- Timestamp-based message ordering and unread message tracking
- Agent identity is simply a string name - no authentication or authorization

### Important Functions

- `atomic_write()` (line 45): Uses temp file + rename for atomic writes to prevent data corruption
- `send_message()` (line 72): Creates a new message file and automatically updates sender's last_seen
- `get_unread_for()` (line 130): Returns messages newer than agent's last_seen timestamp
- `update_last_seen()` (line 149): Updates agent's last_seen after reading messages

## Common Commands

### Initialize the message bus
```bash
python3 agentbus.py init
```

### Send a message
```bash
python3 agentbus.py send --author "AgentName" "Message content here"
```

### Get all messages
```bash
python3 agentbus.py get-messages
```

### Get unread messages for an agent
```bash
python3 agentbus.py get-messages --for "AgentName"
```

### List all agents
```bash
python3 agentbus.py list-agents
```

## Development Notes

- The script is executable (`#!/usr/bin/env python3`) and can be run directly
- No build process, compilation, or dependency installation required
- Message files use colons replaced with hyphens in timestamps for filename safety (line 73)
- When sending a message, the sender's last_seen is automatically updated to that message's timestamp (lines 178-183)
- Bad/corrupted message files are silently skipped during reads (lines 109-111)
- The `--for` flag in `get-messages` automatically marks messages as read by updating last_seen

## Data Format

**Message JSON Structure**:
```json
{
  "author": "AgentName",
  "timestamp": "2025-11-16T14:56:45.376536+00:00",
  "content": "Message text"
}
```

**last_seen.json Structure**:
```json
{
  "AgentName": "2025-11-16T14:56:45.376536+00:00"
}
```

## MCP Server

This repository includes an MCP (Model Context Protocol) server that exposes AgentBus functionality to Claude and other MCP clients.

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install to Claude Code (automatic configuration)
fastmcp install claude-code agentbus_mcp.py

# Or install to Claude Desktop
fastmcp install claude-desktop agentbus_mcp.py

# Or install to Cursor
fastmcp install cursor agentbus_mcp.py
```

### Running the MCP Server

**STDIO mode (default for MCP):**
```bash
python3 agentbus_mcp.py
```

**HTTP mode (for testing):**
```python
# Edit agentbus_mcp.py to use HTTP transport
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

### Available MCP Tools

The MCP server provides 4 tools that wrap the AgentBus CLI functionality:

1. **send_agent_message**: Post messages to the development channel
2. **get_agent_messages**: Retrieve unread messages for an agent
3. **get_all_agent_messages**: View complete message history without marking as read
4. **list_known_agents**: See active agents and their last activity

### MCP Server Implementation Notes

- The server uses FastMCP framework with decorator-based tool definitions
- All tools are async and use the `Context` parameter for logging and progress reporting
- User-facing validation errors raise `ToolError` exceptions
- Tool docstrings provide comprehensive "when to use" guidance for LLM clients
- The server instructions explain the overall AgentBus concept and typical workflows
