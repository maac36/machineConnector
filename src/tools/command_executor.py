"""Securely executes PowerShell and CMD commands following best practices."""

import subprocess
import asyncio
from typing import Dict, Optional, Literal
import logging
import time
import platform


class PowerShellExecutor:
    """
    Securely executes PowerShell commands following best practices.

    Security features:
    - No shell=True
    - Command passed as list arguments
    - Timeout enforcement
    - Output size limits
    - UTF-8 encoding
    """

    def __init__(
        self,
        timeout: int = 30,
        max_output_size: int = 1024 * 1024  # 1MB
    ):
        """
        Initialize the PowerShell executor.

        Args:
            timeout: Maximum execution time in seconds
            max_output_size: Maximum output size in bytes
        """
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.logger = logging.getLogger(__name__)

    async def execute(self, command: str, timeout: Optional[int] = None) -> Dict:
        """
        Execute PowerShell command securely.

        Args:
            command: PowerShell command string
            timeout: Override default timeout

        Returns:
            Dictionary containing:
            - stdout: Standard output text
            - stderr: Standard error text
            - return_code: Process return code
            - execution_time: Time taken in seconds
            - timed_out: Boolean indicating if execution timed out
        """

        timeout = timeout or self.timeout

        # Build command as list (NEVER use shell=True)
        cmd = [
            "powershell.exe",
            "-NoProfile",           # Don't load profile
            "-NonInteractive",      # No interactive prompts
            "-ExecutionPolicy", "Bypass",  # Allow execution
            "-Command", command
        ]

        self.logger.info(f"Executing: {command}")

        start_time = time.time()

        try:
            # Run with timeout and capture output
            # On Windows, encoding parameter may not be supported - decode manually
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                # Decode manually with error handling
                stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
                stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
                timed_out = False
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                stdout, stderr = "", f"Command timed out after {timeout} seconds"
                timed_out = True
                self.logger.warning(f"Command timed out: {command}")

            execution_time = time.time() - start_time

            # Truncate output if too large
            if len(stdout) > self.max_output_size:
                stdout = stdout[:self.max_output_size] + "\n... (output truncated)"
                self.logger.warning(f"Output truncated (exceeded {self.max_output_size} bytes)")

            if len(stderr) > self.max_output_size:
                stderr = stderr[:self.max_output_size] + "\n... (error output truncated)"

            result = {
                "stdout": stdout,
                "stderr": stderr,
                "return_code": process.returncode if not timed_out else -1,
                "execution_time": execution_time,
                "timed_out": timed_out
            }

            self.logger.info(
                f"Execution completed: return_code={result['return_code']}, "
                f"time={execution_time:.2f}s"
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Execution failed: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "execution_time": execution_time,
                "timed_out": False,
                "error": str(e)
            }

    async def execute_cmd(self, command: str, timeout: Optional[int] = None) -> Dict:
        """
        Execute CMD command securely (fallback for PowerShell failures).

        Args:
            command: CMD command string
            timeout: Override default timeout

        Returns:
            Dictionary containing execution results
        """

        timeout = timeout or self.timeout

        # Build command as list (NEVER use shell=True)
        cmd = ["cmd.exe", "/c", command]

        self.logger.info(f"Executing (CMD): {command}")

        start_time = time.time()

        try:
            # Run with timeout and capture output
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                # Decode manually with error handling
                stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
                stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
                timed_out = False
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                stdout, stderr = "", f"Command timed out after {timeout} seconds"
                timed_out = True
                self.logger.warning(f"Command timed out: {command}")

            execution_time = time.time() - start_time

            # Truncate output if too large
            if len(stdout) > self.max_output_size:
                stdout = stdout[:self.max_output_size] + "\n... (output truncated)"
                self.logger.warning(f"Output truncated (exceeded {self.max_output_size} bytes)")

            if len(stderr) > self.max_output_size:
                stderr = stderr[:self.max_output_size] + "\n... (error output truncated)"

            result = {
                "stdout": stdout,
                "stderr": stderr,
                "return_code": process.returncode if not timed_out else -1,
                "execution_time": execution_time,
                "timed_out": timed_out,
                "shell_type": "cmd"
            }

            self.logger.info(
                f"CMD execution completed: return_code={result['return_code']}, "
                f"time={execution_time:.2f}s"
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"CMD execution failed: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "execution_time": execution_time,
                "timed_out": False,
                "error": str(e),
                "shell_type": "cmd"
            }

    async def execute_bash(self, command: str, timeout: Optional[int] = None) -> Dict:
        """
        Execute Bash command securely (for WSL/Git Bash on Windows).

        Args:
            command: Bash command string
            timeout: Override default timeout

        Returns:
            Dictionary containing execution results
        """

        timeout = timeout or self.timeout

        # Try bash.exe (Git Bash) or wsl.exe (WSL)
        bash_cmd = None
        if platform.system() == "Windows":
            # Try Git Bash first, then WSL
            bash_cmd = ["bash.exe", "-c", command]
        else:
            bash_cmd = ["bash", "-c", command]

        self.logger.info(f"Executing (Bash): {command}")

        start_time = time.time()

        try:
            # Run with timeout and capture output
            process = await asyncio.create_subprocess_exec(
                *bash_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                # Decode manually with error handling
                stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
                stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
                timed_out = False
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                stdout, stderr = "", f"Command timed out after {timeout} seconds"
                timed_out = True
                self.logger.warning(f"Command timed out: {command}")

            execution_time = time.time() - start_time

            # Truncate output if too large
            if len(stdout) > self.max_output_size:
                stdout = stdout[:self.max_output_size] + "\n... (output truncated)"

            if len(stderr) > self.max_output_size:
                stderr = stderr[:self.max_output_size] + "\n... (error output truncated)"

            result = {
                "stdout": stdout,
                "stderr": stderr,
                "return_code": process.returncode if not timed_out else -1,
                "execution_time": execution_time,
                "timed_out": timed_out,
                "shell_type": "bash"
            }

            self.logger.info(
                f"Bash execution completed: return_code={result['return_code']}, "
                f"time={execution_time:.2f}s"
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Bash execution failed: {e}")
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "execution_time": execution_time,
                "timed_out": False,
                "error": str(e),
                "shell_type": "bash"
            }
