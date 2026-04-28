"""Centralized constants for the application.

All tunable values that were previously hardcoded across multiple files
are managed here. Overridable via config.json optional fields.
"""

# LLM defaults (overridable via config.json)
DEFAULT_MAX_TOKENS = 4096
SYNC_MAX_TOKENS = 8192
DEFAULT_TEMPERATURE = 0.7

# Timeouts (seconds)
DEFAULT_LLM_TIMEOUT = 120.0
SSE_CLIENT_TIMEOUT = 300  # 5 minutes

# Retry
DEFAULT_MAX_RETRIES = 3

# Content limits
MIN_CHAPTER_LENGTH = 50
MAX_CHARACTER_NAME_LENGTH = 100
CONTEXT_CHAR_LIMIT_SHORT = 800
CONTEXT_CHAR_LIMIT_LONG = 2000
CONTEXT_CHAR_LIMIT_TIMELINE = 1500

# Sync
SYNC_DEBUG_RETENTION = 5  # Keep last N sync debug file sets
