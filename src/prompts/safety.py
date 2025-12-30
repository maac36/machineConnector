"""Safety guidelines and dangerous command patterns."""

from typing import List

# Dangerous PowerShell patterns that should be blocked or heavily warned
DANGEROUS_PATTERNS: List[str] = [
    r'Remove-Item.*-Recurse.*-Force',  # Recursive forced deletion
    r'Format-Volume',  # Disk formatting
    r'Stop-Computer',  # Shutdown
    r'Restart-Computer',  # Restart
    r'Remove-Item.*\\Windows',  # System folder deletion
    r'Set-ItemProperty.*HKLM',  # Registry modification
    r'Invoke-Expression',  # Code injection risk
    r'iex\s',  # Alias for Invoke-Expression
    r'Start-Process.*-Verb RunAs',  # Elevation
    r'Disable-WindowsDefender',  # Security disabling
    r'Set-ExecutionPolicy.*Unrestricted',  # Policy bypass
    r'Remove-Item.*-Path\s+C:\\',  # Deleting from C: root
    r'Clear-RecycleBin.*-Force',  # Empty recycle bin without confirmation
]

# Suspicious patterns that require extra confirmation
SUSPICIOUS_PATTERNS: List[str] = [
    r'Remove-Item',  # Any file deletion
    r'Clear-RecycleBin',  # Recycle bin operations
    r'New-NetFirewallRule',  # Firewall changes
    r'Set-Service',  # Service modifications
    r'Stop-Process',  # Killing processes
    r'Remove-Computer',  # Domain removal
    r'Disable-',  # Disabling features
]


SAFETY_GUIDELINES = """
Safety Guidelines for PowerShell Command Generation:

1. READ-ONLY OPERATIONS (Always safe):
   - Get-ChildItem, Get-Content, Get-Process, Get-Service
   - Test-Path, Test-Connection
   - Select-Object, Where-Object, Sort-Object
   - Format-Table, Format-List

2. CAUTIOUS OPERATIONS (Require user understanding):
   - New-Item (creating files/folders)
   - Set-Content (writing files)
   - Start-Process (launching applications)
   - Copy-Item, Move-Item

3. DANGEROUS OPERATIONS (Require explicit user request):
   - Remove-Item (deletion)
   - Format-* (formatting disks)
   - Stop-Computer, Restart-Computer
   - Registry modifications
   - Service modifications
   - Firewall changes

4. NEVER GENERATE (Unless explicitly and clearly requested):
   - Recursive deletion with -Force
   - System folder modifications
   - Code execution from untrusted sources
   - Disabling security features
"""
