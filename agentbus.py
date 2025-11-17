#!/usr/bin/env python3
"""
Simple AgentBus CLI (MVP)

Usage:
  agentbus.py init
  agentbus.py send --author NAME MESSAGE
  agentbus.py get-messages [--for NAME]
  agentbus.py list-agents

Data layout (created under current working directory):
  ./.agentbus/
    messages/           # JSON files, one per message
    last_seen.json      # per-agent last-read timestamp

Notes:
- Timestamp format: ISO 8601 (UTC) with microseconds.
- This is intentionally simple. No git, no DB. Files only.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
import tempfile
import shutil
from typing import List, Dict

# Allow override via environment variable
BASE_DIR = os.getenv("AGENTBUS_DIR", os.path.join(os.getcwd(), ".agentbus"))
MESSAGES_DIR = os.path.join(BASE_DIR, "messages")
LAST_SEEN_FILE = os.path.join(BASE_DIR, "last_seen.json")


def ensure_dirs():
    os.makedirs(MESSAGES_DIR, exist_ok=True)
    if not os.path.exists(LAST_SEEN_FILE):
        with open(LAST_SEEN_FILE, "w") as f:
            json.dump({}, f)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def atomic_write(path: str, data: str):
    # write to temp file and rename for atomicity
    dirn = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dirn)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise


def list_message_files() -> List[str]:
    files = [f for f in os.listdir(MESSAGES_DIR) if f.endswith(".json")]
    files.sort()
    return files


def read_message_file(path: str) -> Dict:
    with open(path, "r") as f:
        return json.load(f)


def validate_author(author: str):
    """Validate author name for safety and usability."""
    if not author or not author.strip():
        raise ValueError("Author name cannot be empty")

    author = author.strip()

    if len(author) > 100:
        raise ValueError("Author name too long (max 100 characters)")

    # Check for path-unsafe characters
    unsafe_chars = ['/', '\\', '\x00', '\n', '\r']
    if any(c in author for c in unsafe_chars):
        raise ValueError("Author name contains invalid characters")

    return author


def validate_message(content: str):
    """Validate message content."""
    if not content or not content.strip():
        raise ValueError("Message content cannot be empty")

    content = content.strip()

    if len(content) > 100000:  # 100KB limit
        raise ValueError("Message content too long (max 100,000 characters)")

    return content


def send_message(author: str, content: str) -> Dict:
    """Send a message and return the message object with timestamp."""
    author = validate_author(author)
    content = validate_message(content)

    # Use single timestamp for both filename and message content
    timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    ts_filename = timestamp.replace(":", "-")  # safe for filenames
    filename = f"{ts_filename}_{author}.json"
    fullpath = os.path.join(MESSAGES_DIR, filename)

    message = {
        "author": author,
        "timestamp": timestamp,
        "content": content,
    }
    atomic_write(fullpath, json.dumps(message, ensure_ascii=False, indent=2))
    return message


def load_last_seen() -> Dict[str, str]:
    try:
        with open(LAST_SEEN_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_last_seen(d: Dict[str, str]):
    atomic_write(LAST_SEEN_FILE, json.dumps(d, ensure_ascii=False, indent=2))


def parse_iso(dt: str) -> datetime:
    return datetime.fromisoformat(dt)


def get_all_messages() -> List[Dict]:
    files = list_message_files()
    out = []
    for fn in files:
        path = os.path.join(MESSAGES_DIR, fn)
        try:
            m = read_message_file(path)
            out.append(m)
        except Exception:
            # skip bad files
            continue
    # sort by timestamp just in case
    out.sort(key=lambda m: m.get("timestamp", ""))
    return out


def pretty_print_messages(msgs: List[Dict]):
    if not msgs:
        print("(no messages)")
        return
    for m in msgs:
        ts = m.get("timestamp", "")
        author = m.get("author", "<unknown>")
        content = m.get("content", "")
        print(f"--- {ts} | {author} ---")
        print(content)
        print()


def get_unread_for(agent_name: str) -> List[Dict]:
    last_seen = load_last_seen()
    seen_ts = last_seen.get(agent_name)
    all_msgs = get_all_messages()
    if seen_ts is None:
        # agent has never read anything: return everything
        unread = all_msgs
    else:
        try:
            seen_dt = parse_iso(seen_ts)
        except Exception:
            seen_dt = None
        if seen_dt is None:
            unread = all_msgs
        else:
            unread = [m for m in all_msgs if parse_iso(m["timestamp"]) > seen_dt]
    return unread


def update_last_seen(agent_name: str, msgs: List[Dict]):
    if not msgs:
        return
    last = msgs[-1]["timestamp"]
    last_seen = load_last_seen()
    last_seen[agent_name] = last
    save_last_seen(last_seen)


def list_agents():
    last_seen = load_last_seen()
    if not last_seen:
        print("(no agents recorded yet)")
        return
    for a, ts in last_seen.items():
        print(f"{a}: last_seen={ts}")


def cmd_init(args):
    ensure_dirs()
    print(f"Initialized agentbus at: {BASE_DIR}")
    print("Messages directory:", MESSAGES_DIR)
    print("Last-seen file:", LAST_SEEN_FILE)


def cmd_send(args):
    ensure_dirs()
    try:
        message = send_message(args.author, args.message)

        # Update sender's last_seen to the message they just sent (no race condition)
        last_seen = load_last_seen()
        last_seen[message["author"]] = message["timestamp"]
        save_last_seen(last_seen)

        if args.json:
            print(json.dumps(message, ensure_ascii=False))
        else:
            print(f"Message sent by {message['author']} at {message['timestamp']}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_get_messages(args):
    ensure_dirs()
    if args.for_agent:
        name = args.for_agent
        unread = get_unread_for(name)
        if args.json:
            print(json.dumps(unread, ensure_ascii=False, indent=2))
        elif unread:
            pretty_print_messages(unread)
        else:
            print("(no unread messages)")

        if unread:
            update_last_seen(name, unread)
    else:
        # show all
        all_msgs = get_all_messages()
        if args.json:
            print(json.dumps(all_msgs, ensure_ascii=False, indent=2))
        else:
            pretty_print_messages(all_msgs)


def cmd_list_agents(args):
    ensure_dirs()
    list_agents()


def main():
    parser = argparse.ArgumentParser(prog="agentbus", description="Tiny AgentBus CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_init = sub.add_parser("init", help="Initialize .agentbus directory")
    p_init.set_defaults(func=cmd_init)

    p_send = sub.add_parser("send", help='Send a message: agentbus send --author "Name" "message"')
    p_send.add_argument("--author", required=True, help="Author name")
    p_send.add_argument("message", help="Message content")
    p_send.add_argument("--json", action="store_true", help="Output in JSON format")
    p_send.set_defaults(func=cmd_send)

    p_get = sub.add_parser("get-messages", help="Get messages. Use --for to get unread for an agent")
    p_get.add_argument("--for", dest="for_agent", help="Agent name to get unread messages for")
    p_get.add_argument("--json", action="store_true", help="Output in JSON format")
    p_get.set_defaults(func=cmd_get_messages)

    p_list = sub.add_parser("list-agents", help="Show known agents and their last seen timestamp")
    p_list.set_defaults(func=cmd_list_agents)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()

