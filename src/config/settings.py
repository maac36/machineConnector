"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """
    Application configuration using pydantic-settings.
    Loads from .env file and environment variables.
    """

    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o", env="OPENAI_MODEL")
    openai_temperature: float = Field(0.3, env="OPENAI_TEMPERATURE")

    # Execution Configuration
    max_execution_timeout: int = Field(30, env="MAX_EXECUTION_TIMEOUT")
    max_output_size: int = Field(1048576, env="MAX_OUTPUT_SIZE")  # 1MB

    # Retry Configuration
    max_retries: int = Field(3, env="MAX_RETRIES")
    enable_auto_retry: bool = Field(True, env="ENABLE_AUTO_RETRY")  # Auto-retry on failures
    max_auto_retries: int = Field(2, env="MAX_AUTO_RETRIES")  # Number of automatic retry attempts
    auto_retry_confidence_threshold: str = Field("medium", env="AUTO_RETRY_CONFIDENCE_THRESHOLD")  # Minimum confidence to auto-retry (low/medium/high)

    # Security Configuration
    enable_dangerous_commands: bool = Field(False, env="ENABLE_DANGEROUS_COMMANDS")
    require_confirmation: bool = Field(True, env="REQUIRE_CONFIRMATION")

    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(None, env="LOG_FILE")

    # Session Configuration
    session_persistence: bool = Field(False, env="SESSION_PERSISTENCE")
    checkpoint_dir: Optional[str] = Field(None, env="CHECKPOINT_DIR")

    # Audio/Voice Configuration
    enable_voice_input: bool = Field(True, env="ENABLE_VOICE_INPUT")
    whisper_model: str = Field("whisper-1", env="WHISPER_MODEL")  # API model or local: tiny/base/small/medium/large
    use_local_whisper: bool = Field(False, env="USE_LOCAL_WHISPER")  # True for local, False for API
    audio_sample_rate: int = Field(16000, env="AUDIO_SAMPLE_RATE")
    audio_channels: int = Field(1, env="AUDIO_CHANNELS")  # Mono
    recording_duration: int = Field(5, env="RECORDING_DURATION")  # Max seconds to record
    silence_threshold: float = Field(0.01, env="SILENCE_THRESHOLD")  # Auto-stop on silence
    auto_stop_silence_duration: float = Field(1.5, env="AUTO_STOP_SILENCE_DURATION")  # Seconds of silence to auto-stop

    # Conversation Memory Configuration
    enable_conversation_memory: bool = Field(True, env="ENABLE_CONVERSATION_MEMORY")
    max_conversations_in_memory: int = Field(5, env="MAX_CONVERSATIONS_IN_MEMORY")
    memory_storage_file: Optional[str] = Field(None, env="MEMORY_STORAGE_FILE")  # Default: ~/.claude/langgraph_powershell/conversation_memory.json
    include_context_in_prompt: bool = Field(True, env="INCLUDE_CONTEXT_IN_PROMPT")  # Include conversation history in LLM prompts
    context_conversations_count: int = Field(3, env="CONTEXT_CONVERSATIONS_COUNT")  # Number of recent conversations to include as context

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
