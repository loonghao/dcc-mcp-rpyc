"""Skills integration for DCC-MCP-IPC.

Bridges dcc-mcp-core's Rust-native Skills system with the IPC action layer,
allowing zero-code ``SKILL.md``-based scripts to be exposed as MCP tools.
"""

# Import local modules
from dcc_mcp_ipc.skills.scanner import SkillManager

__all__ = ["SkillManager"]
