# LangGraph PowerShell Command Executor

A Python-based LangGraph system that uses LLM to generate PowerShell commands from natural language, executes them securely, and validates the results.

## Features

- **Natural Language to PowerShell**: Convert plain English commands to PowerShell using OpenAI GPT-4
- **🎤 Voice Input**: Speak your commands using Whisper speech-to-text (API or local models)
- **📊 Content Analysis**: Read files, analyze code, and understand repositories using LLM
- **💾 Conversation Memory**: Remembers last 5 conversations for context-aware follow-up questions
- **Multi-Shell Support**: Automatic fallback between PowerShell, CMD, and Bash
- **Human-in-the-Loop**: Requires user confirmation before executing any command
- **Security-First**: Multi-layer safety checks including pattern matching and LLM safety assessment
- **Result Validation**: LLM validates if command execution achieved the intended goal
- **Beautiful CLI**: Rich terminal UI with syntax highlighting and formatted output
- **Retry Logic**: Regenerate commands with user feedback if initial attempt isn't satisfactory

## Architecture

```
START → generate_command → await_confirmation → execute_command → validate_result → analyze_content* → present_result → END
           ↑                      ↓                                       ↓                 ↑
           └──────── retry ←──────┘                              try_alternative_shell ─────┘

* analyze_content is optional (triggered by keywords like "explain", "analyze")
```

### Components

- **CommandGenerator**: Uses OpenAI to convert natural language → PowerShell/CMD/Bash
- **PowerShellExecutor**: Securely executes commands using subprocess (no shell injection)
- **ContentAnalyzer**: LLM-based analysis of files, code, and repositories
- **FileReader**: Reads and extracts content from files and git repositories
- **WhisperTranscriber**: Speech-to-text using OpenAI Whisper (API or local)
- **AudioRecorder**: Captures voice input with silence detection
- **ResultValidator**: LLM validates execution results against user intent
- **CommandFilter**: Pattern-based detection of dangerous operations
- **LangGraph Workflow**: Orchestrates the flow with state management

## Installation

### Prerequisites

- Python 3.13+
- Windows OS (PowerShell)
- OpenAI API key

### Setup

1. **Clone or navigate to the project directory**
   ```bash
   cd D:\workspace\langgraph-powershell
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   ```bash
   venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment**
   ```bash
   copy .env.example .env
   ```

   Edit `.env` and add your OpenAI API key:
   ```env
   OPENAI_API_KEY=sk-your-actual-api-key-here
   ```

## Usage

### Running the Program

```bash
# Activate virtual environment (if not already activated)
venv\Scripts\activate

# Run the program
python src/main.py
```

### Quick Launch (after initial setup)

```bash
cd D:\workspace\langgraph-powershell && venv\Scripts\activate && python src/main.py
```

### Voice Input 🎤

The application supports voice commands using OpenAI Whisper!

**Setup Voice Input:**
```bash
# Install audio dependencies
pip install sounddevice soundfile numpy

# Optional: Local Whisper for offline use
pip install openai-whisper
```

**Using Voice:**
```
Enter command request: /voice

🎙️  Voice Mode Activated
Speak your command (will auto-stop on silence)...
🎤 Listening...
✓ Transcribed: launch notepad

[Command proceeds normally]
```

**Voice Commands:**
- `/voice` - Activate voice input
- `/v` - Short alias
- `voice` - Alternative

📖 **Detailed Guide**: See [VOICE_SETUP.md](VOICE_SETUP.md) for complete voice configuration

### Conversation Memory 💾

The system remembers your last 5 conversations, enabling context-aware follow-up questions!

**Features:**
- Automatic context tracking
- Persisted to disk (~/.claude/langgraph_powershell/conversation_memory.json)
- Provides LLM with previous conversation history
- View and manage history with commands

**Using Memory:**
```
# First command
Enter command request: list files in my documents folder

✓ Execution Status: SUCCESS
[Shows file listing]

# Follow-up question (uses memory!)
Enter command request: show me only the PDF files from that folder

Generated Command:
  Get-ChildItem C:\Users\Name\Documents -Filter *.pdf

# The LLM remembered:
# 1. Previous command was about Documents folder
# 2. "that folder" refers to Documents
# 3. Context: user wants filtered view
```

**Memory Commands:**
- `/history` or `/h` - View conversation history table
- `/clear` or `/c` - Clear conversation history

**Example: View History**
```
Enter command request: /history

📜 Conversation History (5 conversations):

#  Timestamp            User Input                  Command                     Status
1  2025-12-30 10:23:15  launch notepad              Start-Process notepad.exe   ✓
2  2025-12-30 10:24:30  list files in downloads     Get-ChildItem C:\Users...   ✓
3  2025-12-30 10:25:45  read config.json and...     type config.json            ✓
4  2025-12-30 10:27:10  show only PDF files         Get-ChildItem ... -Filt...  ✓
5  2025-12-30 10:28:33  what is my IP address       ipconfig                    ✓
```

**Configuration:**
```env
ENABLE_CONVERSATION_MEMORY=true         # Enable/disable memory
MAX_CONVERSATIONS_IN_MEMORY=5           # Number to keep (1-10)
INCLUDE_CONTEXT_IN_PROMPT=true          # Pass history to LLM
CONTEXT_CONVERSATIONS_COUNT=3           # How many to include (1-5)
```

**Benefits:**
- **Follow-up questions**: "Do it again", "show me more", "what about X?"
- **Reference previous results**: "Use that folder", "the same file"
- **Contextual understanding**: LLM knows what you were doing
- **Natural conversation flow**: No need to repeat context

### Example Session

```
PowerShell Command Assistant

Enter command request: search for abc.txt on my C: drive

Generated Command:
Get-ChildItem -Path C:\ -Filter "abc.txt" -Recurse -ErrorAction SilentlyContinue

Explanation: Recursively searches the entire C: drive for files named abc.txt

Execute this command? [y/N]: y

✓ Execution Status: SUCCESS
Return Code: 0
Execution Time: 2.34s

Output:
    Directory: C:\Users\Documents

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a---          12/30/2025  10:23 AM           1024 abc.txt

✓ Validation: PASSED
Successfully located the requested file abc.txt

Enter command request: launch notepad

Generated Command:
Start-Process notepad.exe

Explanation: Launches the Notepad text editor application

Execute this command? [y/N]: y

✓ Execution Status: SUCCESS

Enter command request: exit
Goodbye! 👋
```

## Example Commands

### File Operations
- `"search for abc.txt"`
- `"find all PDF files in my Documents folder"`
- `"show me the contents of config.json"`

### Launching Applications
- `"launch notepad"`
- `"open calculator"`
- `"start chrome"`
- `"run Visual Studio Code"`

### System Information
- `"show running processes"`
- `"list processes using more than 100MB RAM"`
- `"check disk space on C: drive"`
- `"what's my IP address"`

### File Management
- `"open current folder in explorer"`
- `"create a folder called test"`
- `"copy file.txt to backup folder"`

### 📊 Content Analysis & Understanding

The system can **read, analyze, and explain** files and code using LLM:

**Analyze Files:**
- `"read config.json and explain what it does"`
- `"read app.py and check what is the purpose"`
- `"analyze requirements.txt and tell me what this project needs"`

**Code Understanding:**
- `"checkout the repo from https://github.com/user/project and explain the program"`
- `"read main.py and explain how it works"`
- `"analyze server.js and describe the architecture"`

**Security Analysis:**
- `"read auth.py and check for security vulnerabilities"`
- `"analyze login function and review security"`

**Multi-Step Operations:**
```
User: "clone https://github.com/example/repo and tell me what this project does"

1. Executes: git clone https://github.com/example/repo
2. Reads repository structure and README
3. Analyzes codebase with LLM
4. Displays comprehensive project analysis

📊 Analysis Results:

Target: ./repo
Analysis Type: Repository

╭─ LLM Analysis ─────────────────────────────╮
│                                            │
│ **Project Type**: Web Application         │
│                                            │
│ **Technology Stack**:                      │
│ - Frontend: React, TypeScript              │
│ - Backend: Node.js, Express                │
│ - Database: PostgreSQL                     │
│                                            │
│ **Purpose**: E-commerce platform with      │
│ user authentication, product catalog,      │
│ and payment processing.                    │
│                                            │
│ **Entry Points**: server.js, app.tsx      │
│                                            │
│ **Dependencies**: 45 npm packages          │
╰────────────────────────────────────────────╯
```

**How It Works:**
1. Detects analysis keywords ("explain", "analyze", "check what")
2. Executes command to get/read content
3. Extracts file content or repository structure
4. Uses LLM to analyze and provide insights
5. Displays formatted analysis results

## Security Features

### Multi-Layer Protection

1. **Pattern-Based Filtering**: Regex detection of dangerous operations
   - Blocks: `Format-Volume`, `Remove-Item -Recurse -Force`, system modifications
   - Warns: `Remove-Item`, `Stop-Process`, service modifications

2. **LLM Safety Assessment**: OpenAI evaluates command safety before generation

3. **User Confirmation**: Required for all commands (syntax highlighted preview)

4. **Secure Execution**:
   - No `shell=True` (prevents command injection)
   - Timeout enforcement (30s default)
   - Output size limits (1MB max)
   - UTF-8 encoding with error handling

5. **Audit Logging**: All commands logged for review

### Blocked Operations

The following dangerous patterns are blocked by default:
- Recursive deletion with `-Force`
- Disk formatting
- System shutdown/restart
- Registry modifications
- Security feature disabling

## Configuration

Edit `.env` to customize behavior:

```env
# OpenAI Settings
OPENAI_MODEL=gpt-4o          # Model to use
OPENAI_TEMPERATURE=0.3       # Lower = more consistent

# Execution
MAX_EXECUTION_TIMEOUT=30     # Command timeout in seconds
MAX_RETRIES=3                # Max retry attempts

# Security
REQUIRE_CONFIRMATION=true    # Require user approval
ENABLE_DANGEROUS_COMMANDS=false  # Block dangerous commands

# Logging
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
LOG_FILE=                   # Optional log file path
```

## Project Structure

```
langgraph-powershell/
├── src/
│   ├── config/          # Configuration management
│   ├── graph/           # LangGraph workflow (state, nodes, edges, workflow)
│   ├── tools/           # Command generator, executor, validator
│   ├── prompts/         # LLM prompts
│   ├── security/        # Command filtering and sanitization
│   ├── utils/           # Logging and CLI helpers
│   └── main.py          # CLI entry point
├── tests/               # Unit and integration tests
├── .env                 # Environment configuration (create from .env.example)
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
black src/
ruff check src/
```

### Type Checking

```bash
mypy src/
```

## Troubleshooting

### API Key Error
```
Error: OpenAI API key not found
```
**Solution**: Make sure `.env` file exists and contains `OPENAI_API_KEY=sk-...`

### Import Errors
```
ModuleNotFoundError: No module named 'langgraph'
```
**Solution**: Activate virtual environment and run `pip install -r requirements.txt`

### PowerShell Not Found
```
Error: 'powershell.exe' is not recognized
```
**Solution**: Ensure you're running on Windows with PowerShell installed

### Timeout Errors
```
Command timed out after 30 seconds
```
**Solution**: Increase `MAX_EXECUTION_TIMEOUT` in `.env` or the command may be hanging

## How It Works

1. **User Input**: Enter natural language command (e.g., "find abc.txt")

2. **Command Generation**: OpenAI converts to PowerShell with safety assessment
   ```
   Get-ChildItem -Path C:\ -Filter "abc.txt" -Recurse -ErrorAction SilentlyContinue
   ```

3. **Safety Check**: Pattern matching detects dangerous operations

4. **User Confirmation**: Shows command with syntax highlighting and warnings

5. **Execution**: Secure subprocess execution with timeout and output limits

6. **Validation**: LLM validates if execution achieved user's intent

7. **Results Display**: Formatted output with validation feedback

## License

MIT License

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

For issues or questions:
- Check the Troubleshooting section
- Review the configuration options
- Check logs if `LOG_FILE` is configured
- Open an issue on GitHub

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph)
- Powered by [OpenAI GPT-4](https://openai.com/)
- CLI built with [Rich](https://github.com/Textualize/rich)
