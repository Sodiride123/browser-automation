"""
Centralized Agent Configuration

This module provides a single source of truth for agent definitions.
All agent-related scripts should import from here instead of defining their own.
"""

# Agent definitions - single source of truth
AGENTS = {
    "nova": {
        "name": "Nova",
        "role": "Product Manager",
        "emoji": "🌟",
        "spec": "NOVA_SPEC.md",
        "mentions": ["nova", "Nova", "@nova"],
    },
    "pixel": {
        "name": "Pixel",
        "role": "UX Designer",
        "emoji": "🎨",
        "spec": "PIXEL_SPEC.md",
        "mentions": ["pixel", "Pixel", "@pixel"],
    },
    "bolt": {
        "name": "Bolt",
        "role": "Full-Stack Developer",
        "emoji": "⚡",
        "spec": "BOLT_SPEC.md",
        "mentions": ["bolt", "Bolt", "@bolt"],
    },
    "scout": {
        "name": "Scout",
        "role": "QA Engineer",
        "emoji": "🔍",
        "spec": "SCOUT_SPEC.md",
        "mentions": ["scout", "Scout", "@scout"],
    },
}


def get_agent(agent_id: str) -> dict:
    """Get agent config by ID (case-insensitive)."""
    return AGENTS.get(agent_id.lower())


def list_agents() -> list:
    """Get list of all agent IDs."""
    return list(AGENTS.keys())


def get_agent_by_name(name: str) -> dict:
    """Get agent config by display name."""
    for agent in AGENTS.values():
        if agent["name"].lower() == name.lower():
            return agent
    return None
