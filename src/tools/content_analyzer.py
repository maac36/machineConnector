"""LLM-based content analyzer for understanding files, code, and output."""

import logging
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """
    Analyzes content using LLM to provide insights, explanations, and summaries.

    Supports:
    - Code analysis and explanation
    - File content understanding
    - Command output interpretation
    - Repository structure analysis
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        temperature: float = 0.3
    ):
        """
        Initialize content analyzer.

        Args:
            api_key: OpenAI API key
            model: Model to use for analysis
            temperature: Temperature for generation
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.logger = logging.getLogger(__name__)

    async def analyze_file(
        self,
        file_path: str,
        content: str,
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Analyze file content and provide insights.

        Args:
            file_path: Path to the file
            content: File content
            analysis_type: Type of analysis (general, purpose, security, etc.)

        Returns:
            Dictionary containing analysis results
        """

        self.logger.info(f"Analyzing file: {file_path} (type: {analysis_type})")

        # Build analysis prompt based on type
        if analysis_type == "purpose":
            system_prompt = """You are a code and document analyzer. Analyze the given file content
and explain its purpose, what it does, and its key components."""
            user_prompt = f"""Analyze this file: {file_path}

Content:
```
{content[:10000]}  # Limit to first 10K chars
```

Provide:
1. **Purpose**: What is this file for?
2. **Key Components**: Main functions, classes, or sections
3. **Dependencies**: What does it rely on?
4. **Summary**: Brief overview in 2-3 sentences"""

        elif analysis_type == "security":
            system_prompt = """You are a security analyst. Review the given content for
potential security issues, vulnerabilities, and best practice violations."""
            user_prompt = f"""Security review of: {file_path}

Content:
```
{content[:10000]}
```

Identify:
1. **Security Issues**: Potential vulnerabilities
2. **Risky Patterns**: Dangerous code patterns
3. **Recommendations**: How to fix issues
4. **Risk Level**: LOW/MEDIUM/HIGH"""

        elif analysis_type == "explain":
            system_prompt = """You are a technical educator. Explain the given code or document
in a clear, understandable way for someone learning."""
            user_prompt = f"""Explain this file: {file_path}

Content:
```
{content[:10000]}
```

Provide an easy-to-understand explanation covering:
1. What it does
2. How it works
3. Important concepts
4. Example usage (if applicable)"""

        else:  # general
            system_prompt = """You are a content analyzer. Analyze the given content and
provide useful insights, summaries, and observations."""
            user_prompt = f"""Analyze: {file_path}

Content:
```
{content[:10000]}
```

Provide a comprehensive analysis."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )

            analysis = response.choices[0].message.content.strip()

            return {
                "file_path": file_path,
                "analysis_type": analysis_type,
                "analysis": analysis,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise

    async def analyze_code_repository(
        self,
        repo_path: str,
        file_list: List[str],
        readme_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze an entire code repository structure.

        Args:
            repo_path: Path to repository
            file_list: List of files in the repo
            readme_content: Content of README if available

        Returns:
            Repository analysis
        """

        self.logger.info(f"Analyzing repository: {repo_path}")

        file_tree = "\n".join(file_list[:100])  # First 100 files

        user_prompt = f"""Analyze this code repository structure:

Repository: {repo_path}

File Structure:
```
{file_tree}
```

README:
```
{readme_content[:2000] if readme_content else "No README found"}
```

Provide:
1. **Project Type**: What kind of project is this?
2. **Technology Stack**: Languages, frameworks, tools used
3. **Architecture**: How is the code organized?
4. **Purpose**: What does this project do?
5. **Entry Points**: Main files or scripts to start with
6. **Dependencies**: Key dependencies identified from structure"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a software architect analyzing code repositories."
                    },
                    {"role": "user", "content": user_prompt}
                ]
            )

            analysis = response.choices[0].message.content.strip()

            return {
                "repo_path": repo_path,
                "analysis_type": "repository",
                "analysis": analysis,
                "files_analyzed": len(file_list)
            }

        except Exception as e:
            self.logger.error(f"Repository analysis failed: {e}")
            raise

    async def analyze_command_output(
        self,
        command: str,
        output: str,
        user_intent: str
    ) -> Dict[str, Any]:
        """
        Analyze command execution output and explain what it means.

        Args:
            command: The command that was executed
            output: Command output
            user_intent: Original user request

        Returns:
            Output analysis
        """

        self.logger.info(f"Analyzing output of command: {command}")

        user_prompt = f"""The user wanted: "{user_intent}"

Command executed: {command}

Output:
```
{output[:5000]}
```

Explain:
1. **What the output shows**: Interpret the results
2. **Key findings**: Important information from the output
3. **Answer to user's question**: Direct answer to what they wanted
4. **Next steps**: Suggestions (if applicable)"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that explains command output in plain language."
                    },
                    {"role": "user", "content": user_prompt}
                ]
            )

            analysis = response.choices[0].message.content.strip()

            return {
                "command": command,
                "analysis_type": "output",
                "analysis": analysis
            }

        except Exception as e:
            self.logger.error(f"Output analysis failed: {e}")
            raise

    async def compare_files(
        self,
        file1_path: str,
        file1_content: str,
        file2_path: str,
        file2_content: str
    ) -> Dict[str, Any]:
        """
        Compare two files and explain differences.

        Args:
            file1_path: First file path
            file1_content: First file content
            file2_path: Second file path
            file2_content: Second file content

        Returns:
            Comparison analysis
        """

        self.logger.info(f"Comparing {file1_path} vs {file2_path}")

        user_prompt = f"""Compare these two files:

File 1: {file1_path}
```
{file1_content[:5000]}
```

File 2: {file2_path}
```
{file2_content[:5000]}
```

Provide:
1. **Key Differences**: What's different between them?
2. **Similarities**: What's the same?
3. **Purpose Comparison**: How do their purposes differ?
4. **Recommendation**: When to use which?"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a file comparison expert."
                    },
                    {"role": "user", "content": user_prompt}
                ]
            )

            analysis = response.choices[0].message.content.strip()

            return {
                "file1": file1_path,
                "file2": file2_path,
                "analysis_type": "comparison",
                "analysis": analysis
            }

        except Exception as e:
            self.logger.error(f"File comparison failed: {e}")
            raise

    async def extract_insights(
        self,
        content: str,
        question: str
    ) -> Dict[str, Any]:
        """
        Answer specific questions about content.

        Args:
            content: The content to analyze
            question: Specific question to answer

        Returns:
            Answer and insights
        """

        self.logger.info(f"Extracting insights for question: {question}")

        user_prompt = f"""Content:
```
{content[:8000]}
```

Question: {question}

Provide a detailed answer based on the content above."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions about provided content."
                    },
                    {"role": "user", "content": user_prompt}
                ]
            )

            answer = response.choices[0].message.content.strip()

            return {
                "question": question,
                "analysis_type": "question_answer",
                "analysis": answer
            }

        except Exception as e:
            self.logger.error(f"Insight extraction failed: {e}")
            raise
