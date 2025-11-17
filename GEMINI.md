# Project Overview

This project is a simple, file-based message bus implemented as a Python command-line interface (CLI) tool named `agentbus`. It allows multiple "agents" (users or processes) to communicate by sending and receiving messages in a local environment.

The core of the system is a directory named `.agentbus` created in the current working directory. This directory contains:
- `messages/`: A directory where each message is stored as a separate JSON file.
- `last_seen.json`: A file that tracks the timestamp of the last message seen by each agent, allowing for unread message functionality.

The tool is self-contained in the `agentbus.py` script and has no external dependencies beyond the Python 3 standard library.

# Building and Running

This is a single-file Python script with no build process or external dependencies.

## Running the tool

You can run the tool directly using the Python interpreter.

### Initialize the message bus:
```bash
python3 agentbus.py init
```

### Send a message:
```bash
python3 agentbus.py send --author "YourName" "This is a test message."
```

### Get all messages:
```bash
python3 agentbus.py get-messages
```

### Get unread messages for an agent:
```bash
python3 agentbus.py get-messages --for "YourName"
```

### List all agents:
```bash
python3 agentbus.py list-agents
```

## Testing

There are no automated tests included in this project. To test the functionality, you can manually run the commands listed above.

# Development Conventions

- The code is written in Python 3 and uses only the standard library.
- The code follows standard Python conventions (PEP 8).
- Messages are stored in JSON format.
- Timestamps are in ISO 8601 format (UTC) with microsecond precision.
- File operations are designed to be atomic to prevent data corruption.
