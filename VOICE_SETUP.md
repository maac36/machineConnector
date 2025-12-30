# Voice Input Setup Guide

This guide will help you set up voice input for the LangGraph PowerShell CLI using OpenAI Whisper.

## Overview

The application supports voice input using OpenAI's Whisper speech-to-text technology. You can use either:
- **OpenAI Whisper API** (cloud-based, requires API key)
- **Local Whisper models** (offline, runs on your machine)

## Installation

### 1. Install Audio Dependencies

```bash
# Install required audio libraries
pip install sounddevice soundfile numpy

# Optional: Install local Whisper (for offline use)
pip install openai-whisper
```

Or update all dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Audio/Voice Input Settings
ENABLE_VOICE_INPUT=true                    # Enable/disable voice input
WHISPER_MODEL=whisper-1                    # API: "whisper-1" | Local: "tiny", "base", "small", "medium", "large"
USE_LOCAL_WHISPER=false                    # true for local, false for API
AUDIO_SAMPLE_RATE=16000                    # Sample rate (16kHz recommended)
AUDIO_CHANNELS=1                           # 1=mono, 2=stereo
RECORDING_DURATION=10                      # Max recording duration in seconds
SILENCE_THRESHOLD=0.01                     # Silence detection threshold (0.0-1.0)
AUTO_STOP_SILENCE_DURATION=1.5             # Auto-stop after N seconds of silence
```

### 3. Choose Your Whisper Mode

#### Option A: OpenAI API (Recommended)
- **Pros**: Fast, accurate, no GPU required
- **Cons**: Requires internet, API costs

```bash
USE_LOCAL_WHISPER=false
WHISPER_MODEL=whisper-1
OPENAI_API_KEY=sk-your-api-key-here
```

#### Option B: Local Whisper
- **Pros**: Offline, no API costs, privacy
- **Cons**: Slower, requires more RAM/CPU

```bash
USE_LOCAL_WHISPER=true
WHISPER_MODEL=base  # Options: tiny, base, small, medium, large
```

**Local Model Sizes:**
- `tiny`: 39M params, ~1GB RAM, fastest
- `base`: 74M params, ~1GB RAM, good balance
- `small`: 244M params, ~2GB RAM, better accuracy
- `medium`: 769M params, ~5GB RAM, high accuracy
- `large`: 1550M params, ~10GB RAM, best accuracy

## Usage

### Starting Voice Input

Run the application normally:

```bash
python src/main.py
```

### Voice Commands

**Option 1: Type `/voice`**
```
Enter command request: /voice
🎙️  Voice Mode Activated
Speak your command (will auto-stop on silence)...
```

**Option 2: Aliases**
```
Enter command request: /v
Enter command request: voice
```

### Recording Behavior

The system will:
1. **Start listening** when you activate voice mode
2. **Detect silence** automatically
3. **Auto-stop** after 1.5 seconds of silence (configurable)
4. **Transcribe** your speech to text
5. **Execute** the command workflow normally

### Voice Input Flow

```
User types "/voice"
    ↓
🎤 Start recording
    ↓
User speaks: "launch notepad"
    ↓
User stops speaking (silence detected)
    ↓
🔄 Transcribing...
    ↓
✓ Transcribed: "launch notepad"
    ↓
[Normal workflow continues]
    ↓
Generate → Confirm → Execute
```

## Troubleshooting

### "Voice input is not available"

**Cause**: Audio libraries not installed

**Solution**:
```bash
pip install sounddevice soundfile numpy
```

### "No audio detected"

**Causes**:
- Microphone not selected
- Volume too low
- Silence threshold too high

**Solutions**:
1. Check microphone permissions
2. Increase microphone volume
3. Lower `SILENCE_THRESHOLD` in `.env`

### "ModuleNotFoundError: No module named 'sounddevice'"

**Solution**:
```bash
pip install sounddevice soundfile
```

### Local Whisper is slow

**Solutions**:
1. Use a smaller model: `WHISPER_MODEL=tiny` or `base`
2. Switch to API mode: `USE_LOCAL_WHISPER=false`
3. Use GPU acceleration (requires CUDA setup)

### Transcription is inaccurate

**Solutions**:
1. Speak more clearly
2. Use a better microphone
3. Reduce background noise
4. Use larger local model (`medium` or `large`)
5. Switch to API mode for better accuracy

## Testing Audio Devices

### List Available Microphones

```python
from tools.audio_recorder import AudioRecorder

devices = AudioRecorder.list_input_devices()
for device_id, device_name in devices.items():
    print(f"{device_id}: {device_name}")
```

### Test Recording

```bash
# Record 5 seconds and check the output
python -c "
import asyncio
from tools.audio_recorder import AudioRecorder

async def test():
    recorder = AudioRecorder()
    file = await recorder.record_fixed_duration(5)
    print(f'Recorded to: {file}')

asyncio.run(test())
"
```

## Advanced Configuration

### Adjust Silence Detection

If the recording stops too early or too late:

```bash
# More sensitive (stops sooner)
SILENCE_THRESHOLD=0.02
AUTO_STOP_SILENCE_DURATION=1.0

# Less sensitive (waits longer)
SILENCE_THRESHOLD=0.005
AUTO_STOP_SILENCE_DURATION=2.0
```

### Adjust Recording Duration

```bash
# Longer commands
RECORDING_DURATION=15

# Quick commands
RECORDING_DURATION=5
```

### Use Different Language

For local Whisper, you can set the language in code:

```python
self.transcriber = WhisperTranscriber(
    api_key=settings.openai_api_key,
    model=settings.whisper_model,
    use_local=settings.use_local_whisper,
    language="es"  # Spanish, "fr" for French, etc.
)
```

## Cost Considerations

### OpenAI Whisper API Pricing
- $0.006 per minute of audio
- ~$0.01 for a typical 1.5 second command

### Local Whisper
- Free
- Compute cost depends on your hardware

## Security & Privacy

### API Mode
- Audio is sent to OpenAI servers
- Subject to OpenAI's data usage policy
- Audio is not stored after processing

### Local Mode
- Audio never leaves your machine
- Complete privacy
- No internet required

## Examples

### Example 1: Launch Application
```
You speak: "Open notepad"
Transcribed: "Open notepad"
Generated: Start-Process notepad.exe
```

### Example 2: File Operations
```
You speak: "List all files in downloads folder"
Transcribed: "List all files in downloads folder"
Generated: Get-ChildItem C:\Users\YourName\Downloads
```

### Example 3: System Info
```
You speak: "Show me system information"
Transcribed: "Show me system information"
Generated: systeminfo
```

## Next Steps

1. Install dependencies
2. Configure `.env` file
3. Test with `/voice` command
4. Adjust settings as needed
5. Enjoy hands-free command execution!

## Support

For issues or questions:
- Check microphone permissions
- Review logs in console
- Verify API key (if using API mode)
- Test audio devices
- Check firewall settings (for API mode)
