"""Filters and detects dangerous PowerShell commands."""

import re
from typing import Dict, List
from prompts.safety import DANGEROUS_PATTERNS, SUSPICIOUS_PATTERNS


class CommandFilter:
    """
    Filters and detects dangerous PowerShell commands.
    """

    def __init__(self):
        """Initialize the command filter."""
        self.dangerous_patterns = DANGEROUS_PATTERNS
        self.suspicious_patterns = SUSPICIOUS_PATTERNS

    def assess(self, command: str) -> Dict:
        """
        Assess command safety.

        Args:
            command: PowerShell command to assess

        Returns:
            Dictionary containing:
            - level: "safe", "suspicious", or "dangerous"
            - matched_patterns: List of matched regex patterns
            - warnings: List of warning messages
            - allow: Boolean indicating if command should be allowed
        """

        matched_dangerous = []
        matched_suspicious = []
        warnings = []

        # Check dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                matched_dangerous.append(pattern)
                warnings.append(f"DANGER: Potentially destructive operation detected matching: {pattern}")

        # Check suspicious patterns (only if not already dangerous)
        if not matched_dangerous:
            for pattern in self.suspicious_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    matched_suspicious.append(pattern)
                    warnings.append(f"CAUTION: Potentially risky operation detected matching: {pattern}")

        # Determine level
        if matched_dangerous:
            level = "dangerous"
            allow = False  # Block dangerous commands by default
        elif matched_suspicious:
            level = "suspicious"
            allow = True  # Allow but warn
        else:
            level = "safe"
            allow = True

        return {
            "level": level,
            "matched_patterns": matched_dangerous + matched_suspicious,
            "warnings": warnings,
            "allow": allow
        }
