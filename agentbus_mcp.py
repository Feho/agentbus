#!/usr/bin/env python3
"""
AgentBus MCP Server

Exposes AgentBus functionality as MCP tools for Claude and other MCP clients.
This server enables multi-agent communication through a message bus system.
"""
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
import sys
import os

# Import functions from the existing agentbus module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agentbus import (
    ensure_dirs,
    send_message,
    get_unread_for,
    update_last_seen,
    get_all_messages,
    load_last_seen,
    BASE_DIR
)

# Create the MCP server instance
mcp = FastMCP(
    name="AgentBus",
    instructions="""
    AgentBus is a lightweight message bus for asynchronous multi-agent collaboration.

    ## What is AgentBus?

    AgentBus enables AI agents and team members to communicate asynchronously through
    a shared message channel. Think of it as a persistent chat system where agents can:
    - Post messages to request code reviews
    - Ask for help or advice on technical challenges
    - Report progress on tasks
    - Discuss architectural decisions
    - Coordinate on ongoing work

    ## Agent Identity

    When using AgentBus, use your name unless specified otherwise.
    This ensures consistent message threading and helps others recognize your contributions.

    ## How It Works

    Messages are persisted and each agent tracks which messages they've already read.
    When you retrieve messages, you only see what you haven't read yet - like checking
    your unread emails. After reading, those messages are marked as seen for you.

    ## Typical Workflows

    **Code Review Requests**: After implementing a feature, send a message describing
    your changes and request review from the team.

    **Asking for Help**: When stuck on a technical problem, post a message with context
    about what you've tried and what you need help with.

    **Progress Updates**: On longer tasks, periodically send status updates so the team
    knows what you're working on.

    **Team Discussion**: Participate in ongoing technical or architectural discussions
    by posting your thoughts and checking for responses.

    ## Best Practices

    - Be specific: Include file paths, function names, and technical details
    - Provide context: Explain why you're asking or what you've tried
    - Use prefixes: "Question:", "Code Review:", "Progress:", "Completed:"
    """
)


@mcp.tool
async def send_agent_message(author: str, message: str, ctx: Context) -> str:
    """
    Post a message to the development channel for other agents and team members.

    Use this tool to communicate with other agents working on the codebase. Your message
    will be visible to all agents who check the bus, and they can respond asynchronously.

    When to use:
    - **Request code review**: After completing a feature or fix, describe your changes
      and ask for review feedback
    - **Ask for help**: When facing technical challenges, post questions with context
      about what you've tried
    - **Report progress**: Update the team on status of long-running tasks
    - **Discuss decisions**: Share thoughts on architectural or technical choices
    - **Announce completion**: Let the team know when you've finished a task
    - **Respond to messages**: Reply to questions or requests from other agents

    Message best practices:
    - Use clear prefixes: "Code Review:", "Question:", "Progress:", "Completed:"
    - Include specifics: file paths, function names, line numbers
    - Provide context: explain the situation and what you need
    - Be concise but thorough

    Examples:
    - "Code Review: Implemented user auth in src/auth.ts. Added JWT validation,
       rate limiting, and session management. Please review for security concerns."
    - "Question: Best approach for zero-downtime DB migration? Need to add column
       to users table (1M+ rows, PostgreSQL)."
    - "Progress: Payment module refactoring 60% complete. Stripe done, PayPal next."
    - "Completed: All unit tests passing. Feature ready for integration testing."

    Args:
        author: Your agent name
        message: The message content to post to the development channel

    Returns:
        Confirmation that your message was posted successfully
    """
    if not author or not author.strip():
        raise ToolError("Author name is required and cannot be empty")

    if not message or not message.strip():
        raise ToolError("Message content is required and cannot be empty")

    await ctx.info(f"Posting message from '{author}' to development channel...")

    try:
        ensure_dirs()
        send_message(author.strip(), message.strip())
        await ctx.info(f"✓ Message posted successfully")
        return f"Message posted to development channel from {author}"

    except Exception as e:
        raise ToolError(f"Failed to send message: {str(e)}")


@mcp.tool
async def get_agent_messages(for_agent: str, ctx: Context) -> list:
    """
    Check for new messages directed at you or relevant to your work.

    Retrieves messages you haven't seen yet - like checking your unread emails.
    After reading, those messages are automatically marked as seen for you, so you
    won't see them again on the next check.

    When to use:
    - **Check for responses**: After posting a question or code review request,
      check back to see if anyone has replied
    - **Monitor discussions**: Periodically check to see ongoing conversations
      or new requests from other agents
    - **Get updates**: See what other agents are working on or asking about
    - **Find assignments**: Check if anyone has posted work for you to do
    - **Stay informed**: Keep up with team communication and decisions

    Recommended frequency:
    - After posting a message: Check back after some time for responses
    - During active development: Check periodically (every 15-30 minutes)
    - Before starting new work: Check for any relevant discussions or blockers
    - When requested: If user asks you to check the development channel

    What you get:
    - Only messages you haven't read yet (unread messages)
    - Messages are sorted by timestamp (oldest first)
    - After retrieval, they're marked as read for you

    Args:
        for_agent: Your agent name

    Returns:
        List of unread messages, each containing author, timestamp, and content.
        Returns empty list if you're all caught up.
    """
    if not for_agent or not for_agent.strip():
        raise ToolError("Agent name is required and cannot be empty")

    agent_name = for_agent.strip()
    await ctx.info(f"Checking unread messages for '{agent_name}'...")

    try:
        ensure_dirs()
        unread = get_unread_for(agent_name)

        if unread:
            await ctx.info(f"✓ Found {len(unread)} unread message(s)")
            update_last_seen(agent_name, unread)
            await ctx.info(f"✓ Marked as read")
        else:
            await ctx.info("✓ No new messages - you're all caught up!")

        return unread

    except Exception as e:
        raise ToolError(f"Failed to retrieve messages: {str(e)}")


@mcp.tool
async def get_all_agent_messages(ctx: Context) -> list:
    """
    View the complete message history without marking anything as read.

    Shows every message ever posted to the development channel, sorted by time.
    Unlike get_agent_messages, this doesn't mark messages as read, so it won't
    affect your unread status.

    When to use:
    - **Review history**: See the full context of past discussions
    - **Search for info**: Look for previous conversations about a topic
    - **Audit trail**: Review what work has been done or discussed
    - **Onboard**: Catch up on everything that happened before you joined
    - **Debug**: Understand the sequence of events or decisions
    - **Browse without committing**: Preview messages without marking them read

    Use cases:
    - "Show me all discussions about the authentication system"
    - "What has been discussed while I was away?"
    - "I need to see the full conversation thread"
    - "Review all code review requests from the past week"

    Note: This shows ALL messages regardless of when you last checked. Use
    get_agent_messages if you only want to see what's new since your last check.

    Returns:
        Complete list of all messages sorted by timestamp, each containing
        author, timestamp, and content.
    """
    await ctx.info("Retrieving complete message history...")

    try:
        ensure_dirs()
        messages = get_all_messages()
        await ctx.info(f"✓ Retrieved {len(messages)} total message(s)")
        return messages

    except Exception as e:
        raise ToolError(f"Failed to retrieve messages: {str(e)}")


@mcp.tool
async def list_known_agents(ctx: Context) -> dict:
    """
    See which agents are participating in the development channel.

    Lists all agents who have read at least one message, along with when they
    last checked for messages. This helps you understand who's active and who
    might be available to help or review.

    When to use:
    - **Check activity**: See who's been active recently
    - **Find help**: Identify which agents are online/engaged
    - **Coordinate work**: Know who to direct questions or requests to
    - **Team awareness**: Understand the active participants
    - **Verify presence**: Confirm your messages are being seen

    What the timestamps mean:
    - Recent timestamp (minutes ago): Agent is actively checking messages
    - Older timestamp (hours/days ago): Agent may be inactive or busy
    - No entry: Agent hasn't read any messages yet

    Returns:
        Dictionary mapping agent names to their last activity timestamps.
        Empty dict if no agents have read messages yet.

    Example return value:
    {
        "Claude": "2025-11-16T20:30:45.123456+00:00",
        "Gemini": "2025-11-16T19:15:22.987654+00:00",
        "ReviewBot": "2025-11-15T14:22:10.555555+00:00"
    }
    """
    await ctx.info("Listing active agents...")

    try:
        ensure_dirs()
        last_seen = load_last_seen()
        agent_count = len(last_seen)

        if agent_count == 0:
            await ctx.info("No agents have read messages yet")
        else:
            await ctx.info(f"✓ Found {agent_count} active agent(s)")

        return last_seen

    except Exception as e:
        raise ToolError(f"Failed to list agents: {str(e)}")


# Entry point for running the server
if __name__ == "__main__":
    # Run with STDIO transport by default (for MCP protocol)
    mcp.run()
