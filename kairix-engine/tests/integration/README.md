# Integration Tests for Talk.py Audio Pipeline

This directory contains integration tests for the ElevenLabs TTS integration in talk.py.

## Test Structure

### Smoke Tests (`test_talk_smoke.py`)
Quick tests to verify basic functionality:
- TTS initialization
- Simple audio generation
- Streaming support
- Async support
- Error handling

### Full Integration Tests (`test_talk_integration.py`)
Comprehensive tests including:
- **Reverse TTS/STT Testing**: Generates speech with TTS, feeds it to STT, and verifies accuracy
- **Full Conversation Loop**: Tests the complete pipeline (TTS → STT → Chat → Response)
- **Voice Consistency**: Verifies different voices produce different audio
- **Edge Cases**: Tests with numbers, punctuation, single characters, etc.
- **Multilingual Robustness**: Tests system behavior with non-English input

## Running Tests

### Prerequisites
1. Set up environment variables in `.env`:
```bash
ELEVENLABS_API_KEY=your-api-key
# Optional configurations:
ELEVENLABS_VOICE_ID=voice-id  # Default: Rachel
ELEVENLABS_MODEL_ID=model-id  # Default: eleven_monolingual_v1
```

2. Install dependencies:
```bash
uv sync
```

### Run Tests

#### Quick Smoke Tests
```bash
uv run pytest tests/integration/test_talk_smoke.py -v
```

#### Full Integration Tests
```bash
uv run pytest tests/integration/test_talk_integration.py -v -s
```

#### Run All with Interactive Script
```bash
python run_integration_tests.py
```

## Test Configuration

### Accuracy Thresholds
The tests use configurable thresholds for text similarity:
- **Normalized Levenshtein Distance**: < 0.3 (lower is better)
- **Sequence Similarity**: > 0.7 (higher is better)
- **Word Accuracy**: > 0.6 (higher is better)

### Available Voices
The tests randomly select from these English voices:
- Rachel (21m00Tcm4TlvDq8ikWAM)
- Domi (AZnzlk1XvdvUeBnXmlld)
- Bella (EXAVITQu4vr4xnSDxMaL)
- Antoni (ErXwobaYiN019PkySvjV)
- Elli (MF3mGyEYCl7XYWbV9V6O)
- Josh (TxGEqnHWrfWFTfGW9XjX)
- Arnold (VR6AewLTigWG4xSOukaG)
- Adam (pNInz6obpgDQGcFmaJgB)
- Sam (yoZ06aMxZJJ28mfd3POQ)

## Debugging

Failed tests save audio files to a temporary directory for debugging. The path is printed in the test output.

## Known Limitations

1. STT accuracy depends on audio quality and voice clarity
2. Non-English phrases may have lower accuracy with English STT models
3. Very short phrases (1-2 words) may have slightly lower accuracy
4. Background noise or audio artifacts can affect results