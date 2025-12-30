"""Whisper speech-to-text transcription service."""

import logging
import os
from typing import Optional, Dict, Any
import asyncio

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

try:
    import whisper
    LOCAL_WHISPER_AVAILABLE = True
except ImportError:
    LOCAL_WHISPER_AVAILABLE = False
    whisper = None

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Transcribe audio to text using OpenAI Whisper.

    Supports:
    - OpenAI Whisper API (cloud)
    - Local Whisper models (offline)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "whisper-1",
        use_local: bool = False,
        language: str = "en"
    ):
        """
        Initialize Whisper transcriber.

        Args:
            api_key: OpenAI API key (required for API mode)
            model: Model name - "whisper-1" for API, or "tiny/base/small/medium/large" for local
            use_local: If True, use local Whisper model instead of API
            language: Language code for transcription (default: English)
        """
        self.model = model
        self.use_local = use_local
        self.language = language
        self.logger = logging.getLogger(__name__)

        if use_local:
            if not LOCAL_WHISPER_AVAILABLE:
                raise ImportError(
                    "Local Whisper not installed. Run: pip install openai-whisper"
                )
            self.logger.info(f"Loading local Whisper model: {model}")
            self.whisper_model = whisper.load_model(model)
            self.client = None
        else:
            if not OPENAI_AVAILABLE:
                raise ImportError(
                    "OpenAI client not installed. Run: pip install openai"
                )
            if not api_key:
                raise ValueError("OpenAI API key required for API mode")

            self.client = AsyncOpenAI(api_key=api_key)
            self.whisper_model = None
            self.logger.info(f"Using OpenAI Whisper API: {model}")

    async def transcribe_file(
        self,
        audio_file_path: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file to text.

        Args:
            audio_file_path: Path to audio file (WAV, MP3, etc.)
            prompt: Optional prompt to guide the transcription

        Returns:
            Dictionary containing:
            - text: Transcribed text
            - language: Detected language
            - duration: Audio duration (if available)
            - confidence: Confidence score (if available)
        """

        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        self.logger.info(f"Transcribing audio file: {audio_file_path}")

        try:
            if self.use_local:
                result = await self._transcribe_local(audio_file_path, prompt)
            else:
                result = await self._transcribe_api(audio_file_path, prompt)

            self.logger.info(f"Transcription completed: {result['text'][:100]}...")
            return result

        except Exception as e:
            self.logger.error(f"Transcription failed: {e}")
            raise

        finally:
            # Clean up temporary audio file
            try:
                if audio_file_path.startswith(os.path.join(os.path.dirname(__file__), 'temp')):
                    os.remove(audio_file_path)
                    self.logger.debug(f"Cleaned up temp file: {audio_file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up temp file: {e}")

    async def _transcribe_api(
        self,
        audio_file_path: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe using OpenAI Whisper API.

        Args:
            audio_file_path: Path to audio file
            prompt: Optional prompt

        Returns:
            Transcription result
        """

        self.logger.info("Using OpenAI Whisper API")

        with open(audio_file_path, "rb") as audio_file:
            # Call OpenAI Whisper API
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=self.language,
                prompt=prompt,
                response_format="verbose_json"  # Get more details
            )

        # Parse response
        result = {
            "text": response.text.strip(),
            "language": getattr(response, 'language', self.language),
            "duration": getattr(response, 'duration', None),
            "confidence": None,  # API doesn't provide confidence
            "method": "api"
        }

        return result

    async def _transcribe_local(
        self,
        audio_file_path: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe using local Whisper model.

        Args:
            audio_file_path: Path to audio file
            prompt: Optional prompt

        Returns:
            Transcription result
        """

        self.logger.info(f"Using local Whisper model: {self.model}")

        # Run Whisper in executor to avoid blocking
        loop = asyncio.get_event_loop()
        transcribe_result = await loop.run_in_executor(
            None,
            self._whisper_transcribe_blocking,
            audio_file_path,
            prompt
        )

        # Parse result
        result = {
            "text": transcribe_result["text"].strip(),
            "language": transcribe_result.get("language", self.language),
            "duration": None,
            "confidence": None,
            "method": "local"
        }

        return result

    def _whisper_transcribe_blocking(
        self,
        audio_file_path: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Blocking Whisper transcription (runs in executor).

        Args:
            audio_file_path: Audio file path
            prompt: Optional prompt

        Returns:
            Whisper result dictionary
        """

        options = {
            "language": self.language,
            "task": "transcribe"
        }

        if prompt:
            options["initial_prompt"] = prompt

        result = self.whisper_model.transcribe(audio_file_path, **options)
        return result

    async def transcribe_with_fallback(
        self,
        audio_file_path: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe with automatic fallback to alternative method.

        Tries API first, falls back to local if API fails (or vice versa).

        Args:
            audio_file_path: Path to audio file
            prompt: Optional prompt

        Returns:
            Transcription result
        """

        try:
            # Try primary method
            return await self.transcribe_file(audio_file_path, prompt)

        except Exception as e:
            self.logger.warning(f"Primary transcription method failed: {e}")

            # Try fallback
            if self.use_local and OPENAI_AVAILABLE:
                self.logger.info("Falling back to API transcription")
                # Temporarily switch to API
                original_mode = self.use_local
                self.use_local = False
                try:
                    result = await self.transcribe_file(audio_file_path, prompt)
                    return result
                finally:
                    self.use_local = original_mode

            elif not self.use_local and LOCAL_WHISPER_AVAILABLE:
                self.logger.info("Falling back to local transcription")
                # Temporarily switch to local
                original_mode = self.use_local
                self.use_local = True
                try:
                    if not self.whisper_model:
                        self.whisper_model = whisper.load_model("base")
                    result = await self.transcribe_file(audio_file_path, prompt)
                    return result
                finally:
                    self.use_local = original_mode

            else:
                # No fallback available
                raise

    def cleanup_temp_files(self, directory: str = None):
        """
        Clean up temporary audio files.

        Args:
            directory: Directory to clean (default: system temp)
        """
        import tempfile
        import glob

        if not directory:
            directory = tempfile.gettempdir()

        pattern = os.path.join(directory, "voice_input_*.wav")
        temp_files = glob.glob(pattern)

        for file_path in temp_files:
            try:
                os.remove(file_path)
                self.logger.debug(f"Removed temp file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to remove {file_path}: {e}")
