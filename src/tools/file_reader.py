"""File reading utility for content extraction and analysis."""

import os
import logging
from typing import Dict, Any, Optional, List
import subprocess
import asyncio

logger = logging.getLogger(__name__)


class FileReader:
    """
    Reads and extracts content from various file types.

    Supports:
    - Text files
    - Code files
    - Configuration files
    - Git repositories
    """

    def __init__(self, max_file_size: int = 10 * 1024 * 1024):  # 10MB default
        """
        Initialize file reader.

        Args:
            max_file_size: Maximum file size to read (bytes)
        """
        self.max_file_size = max_file_size
        self.logger = logging.getLogger(__name__)

    async def read_file(self, file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """
        Read file content.

        Args:
            file_path: Path to file
            encoding: File encoding (default: utf-8)

        Returns:
            Dictionary with file metadata and content
        """

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)

        if file_size > self.max_file_size:
            self.logger.warning(f"File too large ({file_size} bytes), reading first {self.max_file_size} bytes")
            truncated = True
        else:
            truncated = False

        self.logger.info(f"Reading file: {file_path} ({file_size} bytes)")

        try:
            # Try reading with specified encoding
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                if truncated:
                    content = f.read(self.max_file_size)
                else:
                    content = f.read()

            return {
                "file_path": file_path,
                "content": content,
                "size": file_size,
                "truncated": truncated,
                "encoding": encoding,
                "lines": len(content.splitlines()),
                "extension": os.path.splitext(file_path)[1]
            }

        except UnicodeDecodeError:
            # Try with different encodings
            for alt_encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=alt_encoding, errors='replace') as f:
                        content = f.read(self.max_file_size) if truncated else f.read()

                    self.logger.info(f"Successfully read with {alt_encoding} encoding")
                    return {
                        "file_path": file_path,
                        "content": content,
                        "size": file_size,
                        "truncated": truncated,
                        "encoding": alt_encoding,
                        "lines": len(content.splitlines()),
                        "extension": os.path.splitext(file_path)[1]
                    }
                except Exception:
                    continue

            # If all encodings fail, return binary info
            self.logger.error(f"Could not decode file: {file_path}")
            return {
                "file_path": file_path,
                "content": f"[Binary file - could not decode as text]",
                "size": file_size,
                "truncated": False,
                "encoding": "binary",
                "lines": 0,
                "extension": os.path.splitext(file_path)[1]
            }

    async def read_multiple_files(
        self,
        file_paths: List[str],
        encoding: str = "utf-8"
    ) -> List[Dict[str, Any]]:
        """
        Read multiple files concurrently.

        Args:
            file_paths: List of file paths
            encoding: File encoding

        Returns:
            List of file read results
        """

        tasks = [self.read_file(path, encoding) for path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to read {file_paths[i]}: {result}")
            else:
                valid_results.append(result)

        return valid_results

    async def get_git_repo_files(
        self,
        repo_path: str,
        max_files: int = 100
    ) -> List[str]:
        """
        Get list of files in a git repository.

        Args:
            repo_path: Path to git repository
            max_files: Maximum number of files to return

        Returns:
            List of file paths
        """

        if not os.path.exists(os.path.join(repo_path, ".git")):
            # Not a git repo, just list files
            return await self.list_files_recursive(repo_path, max_files)

        self.logger.info(f"Getting files from git repo: {repo_path}")

        try:
            # Use git ls-files to get tracked files
            result = await asyncio.create_subprocess_exec(
                "git", "ls-files",
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                self.logger.warning(f"Git ls-files failed: {stderr.decode()}")
                return await self.list_files_recursive(repo_path, max_files)

            files = stdout.decode().strip().split('\n')
            # Convert to absolute paths
            files = [os.path.join(repo_path, f) for f in files if f]

            return files[:max_files]

        except Exception as e:
            self.logger.error(f"Failed to get git files: {e}")
            return await self.list_files_recursive(repo_path, max_files)

    async def list_files_recursive(
        self,
        directory: str,
        max_files: int = 100,
        exclude_dirs: Optional[List[str]] = None
    ) -> List[str]:
        """
        List files in directory recursively.

        Args:
            directory: Directory to scan
            max_files: Maximum files to return
            exclude_dirs: Directories to exclude (e.g., node_modules, .git)

        Returns:
            List of file paths
        """

        if exclude_dirs is None:
            exclude_dirs = ['.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build']

        files = []

        for root, dirs, filenames in os.walk(directory):
            # Remove excluded directories from search
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for filename in filenames:
                files.append(os.path.join(root, filename))

                if len(files) >= max_files:
                    self.logger.warning(f"Reached max file limit: {max_files}")
                    return files

        return files

    async def read_file_from_command_output(
        self,
        command_output: str,
        file_pattern: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract file path from command output and read it.

        Args:
            command_output: Output from a command
            file_pattern: Optional pattern to find file path

        Returns:
            File content if found
        """

        # Try to find file paths in output
        import re

        # Common file path patterns
        patterns = [
            r'([A-Z]:\\[^\s\n]+)',  # Windows absolute paths
            r'(/[^\s\n]+)',  # Unix absolute paths
            r'\.\\([^\s\n]+)',  # Relative paths
        ]

        if file_pattern:
            patterns.insert(0, file_pattern)

        for pattern in patterns:
            matches = re.findall(pattern, command_output)
            for match in matches:
                if os.path.isfile(match):
                    try:
                        return await self.read_file(match)
                    except Exception as e:
                        self.logger.debug(f"Failed to read {match}: {e}")
                        continue

        return None

    async def get_repository_structure(
        self,
        repo_path: str
    ) -> Dict[str, Any]:
        """
        Get repository structure and metadata.

        Args:
            repo_path: Path to repository

        Returns:
            Repository structure information
        """

        self.logger.info(f"Analyzing repository structure: {repo_path}")

        files = await self.list_files_recursive(repo_path, max_files=200)

        # Count by extension
        extensions = {}
        for file_path in files:
            ext = os.path.splitext(file_path)[1] or 'no_extension'
            extensions[ext] = extensions.get(ext, 0) + 1

        # Try to read README
        readme_content = None
        for readme_name in ['README.md', 'README.txt', 'README', 'readme.md']:
            readme_path = os.path.join(repo_path, readme_name)
            if os.path.exists(readme_path):
                try:
                    result = await self.read_file(readme_path)
                    readme_content = result['content']
                    break
                except Exception:
                    pass

        # Check for common config files
        config_files = []
        common_configs = [
            'package.json', 'requirements.txt', 'pom.xml', 'build.gradle',
            'Cargo.toml', 'go.mod', 'composer.json', '.env.example'
        ]
        for config in common_configs:
            if os.path.exists(os.path.join(repo_path, config)):
                config_files.append(config)

        return {
            "repo_path": repo_path,
            "total_files": len(files),
            "file_list": files,
            "extensions": extensions,
            "readme_content": readme_content,
            "config_files": config_files,
            "is_git_repo": os.path.exists(os.path.join(repo_path, ".git"))
        }
