"""Audio recording module for capturing microphone input."""

import asyncio
import logging
import time
from typing import Optional, Dict
import tempfile
import os

try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    sd = None
    sf = None
    np = None

logger = logging.getLogger(__name__)


class AudioRecorder:
    """
    Records audio from microphone with smart silence detection.

    Features:
    - Auto-stop on silence detection
    - Manual stop support
    - Configurable sample rate and channels
    - Saves to temporary WAV file for Whisper
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        silence_threshold: float = 0.01,
        auto_stop_silence_duration: float = 1.5
    ):
        """
        Initialize the audio recorder.

        Args:
            sample_rate: Audio sample rate (16kHz recommended for Whisper)
            channels: Number of audio channels (1=mono, 2=stereo)
            silence_threshold: RMS threshold below which is considered silence
            auto_stop_silence_duration: Seconds of continuous silence before auto-stop
        """
        if not AUDIO_AVAILABLE:
            raise ImportError(
                "Audio libraries not installed. Run: pip install sounddevice soundfile numpy"
            )

        self.sample_rate = sample_rate
        self.channels = channels
        self.silence_threshold = silence_threshold
        self.auto_stop_silence_duration = auto_stop_silence_duration

        self.is_recording = False
        self.audio_data = []
        self.silence_start_time = None
        self.logger = logging.getLogger(__name__)

    async def record_until_silence(
        self,
        max_duration: int = 10,
        callback=None
    ) -> Optional[str]:
        """
        Record audio until silence is detected or max duration reached.

        Args:
            max_duration: Maximum recording duration in seconds
            callback: Optional callback function for status updates

        Returns:
            Path to temporary WAV file, or None if recording failed
        """

        if self.is_recording:
            self.logger.warning("Recording already in progress")
            return None

        self.is_recording = True
        self.audio_data = []
        self.silence_start_time = None

        self.logger.info(f"Starting audio recording (max {max_duration}s)")
        if callback:
            callback("🎤 Listening... (speak now)")

        try:
            # Record in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            audio_file = await loop.run_in_executor(
                None,
                self._record_blocking,
                max_duration,
                callback
            )

            return audio_file

        except Exception as e:
            self.logger.error(f"Recording failed: {e}")
            if callback:
                callback(f"❌ Recording error: {str(e)}")
            return None

        finally:
            self.is_recording = False

    def _record_blocking(self, max_duration: int, callback) -> Optional[str]:
        """
        Blocking recording method (runs in executor).

        Args:
            max_duration: Maximum duration in seconds
            callback: Status callback

        Returns:
            Path to audio file
        """

        frames = []
        start_time = time.time()
        silence_start = None

        def audio_callback(indata, frames_count, time_info, status):
            """Callback for sounddevice stream."""
            if status:
                self.logger.warning(f"Audio callback status: {status}")

            # Calculate RMS (root mean square) to detect silence
            rms = np.sqrt(np.mean(indata**2))

            # Append audio data
            frames.append(indata.copy())

            # Check for silence
            nonlocal silence_start
            if rms < self.silence_threshold:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start >= self.auto_stop_silence_duration:
                    # Stop on prolonged silence
                    raise sd.CallbackStop()
            else:
                # Reset silence timer on sound detection
                silence_start = None

        try:
            # Start recording stream
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=audio_callback,
                dtype='float32'
            ):
                # Wait for max duration or until callback stops
                elapsed = 0
                while elapsed < max_duration and self.is_recording:
                    sd.sleep(100)  # Sleep 100ms
                    elapsed = time.time() - start_time

                    # Update UI every second
                    if callback and int(elapsed) != int(elapsed - 0.1):
                        remaining = max_duration - int(elapsed)
                        if silence_start:
                            silence_duration = time.time() - silence_start
                            callback(f"🔇 Silence detected ({silence_duration:.1f}s)...")
                        else:
                            callback(f"🎤 Recording... ({remaining}s remaining)")

        except sd.CallbackStop:
            self.logger.info("Recording stopped due to silence detection")
            if callback:
                callback("✓ Silence detected, processing...")

        # Check if we got any audio
        if not frames:
            self.logger.warning("No audio data recorded")
            if callback:
                callback("⚠ No audio detected")
            return None

        # Concatenate all frames
        audio_data = np.concatenate(frames, axis=0)

        # Save to temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix='.wav',
            prefix='voice_input_'
        )
        temp_file.close()

        sf.write(temp_file.name, audio_data, self.sample_rate)

        duration = len(audio_data) / self.sample_rate
        self.logger.info(f"Recorded {duration:.2f}s of audio, saved to {temp_file.name}")

        if callback:
            callback(f"✓ Recorded {duration:.1f}s")

        return temp_file.name

    async def record_fixed_duration(self, duration: int = 5) -> Optional[str]:
        """
        Record audio for a fixed duration.

        Args:
            duration: Recording duration in seconds

        Returns:
            Path to temporary WAV file
        """

        self.logger.info(f"Recording {duration}s of audio")

        try:
            # Record synchronously
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='float32'
            )
            sd.wait()  # Wait for recording to finish

            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.wav',
                prefix='voice_input_'
            )
            temp_file.close()

            sf.write(temp_file.name, audio_data, self.sample_rate)

            self.logger.info(f"Audio saved to {temp_file.name}")
            return temp_file.name

        except Exception as e:
            self.logger.error(f"Recording failed: {e}")
            return None

    def stop_recording(self):
        """Stop the current recording."""
        self.is_recording = False
        self.logger.info("Recording stopped by user")

    @staticmethod
    def list_input_devices() -> Dict[int, str]:
        """
        List available audio input devices.

        Returns:
            Dictionary mapping device ID to device name
        """
        if not AUDIO_AVAILABLE:
            return {}

        devices = sd.query_devices()
        input_devices = {}

        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                input_devices[i] = device['name']

        return input_devices

    @staticmethod
    def get_default_input_device() -> Optional[int]:
        """Get the default input device ID."""
        if not AUDIO_AVAILABLE:
            return None

        try:
            return sd.default.device[0]  # Input device
        except Exception:
            return None
