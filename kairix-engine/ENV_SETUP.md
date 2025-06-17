# Environment Configuration for Talk.py

This project supports multiple environment configurations stored in the `env/` directory.

## Available Environments

- `mac` - Local Mac development environment
- `cayucos` - Cayucos deployment environment

## Usage

### Running talk.py with different environments

```bash
# Run with mac environment
just run-talk mac

# Run with cayucos environment
just run-talk cayucos
```

### List available environments

```bash
just list-envs
```

### Running tests with different environments

```bash
# Run smoke tests
just test-talk-smoke mac

# Run full integration tests
just test-talk-integration cayucos
```

## Environment File Structure

Environment files should be placed in `env/` directory with `.env` extension:
```
env/
├── mac.env
└── cayucos.env
```

### Required Environment Variables

Each environment file must include:

```bash
# ElevenLabs Configuration
ELEVENLABS_API_KEY=your-api-key

# Optional ElevenLabs settings
ELEVENLABS_VOICE_ID=voice-id  # Default: Rachel (21m00Tcm4TlvDq8ikWAM)
ELEVENLABS_MODEL_ID=model-id  # Default: eleven_monolingual_v1
ELEVENLABS_STABILITY=0.5      # Voice stability (0-1)
ELEVENLABS_SIMILARITY_BOOST=0.5  # Voice similarity (0-1)
ELEVENLABS_STYLE=0.5          # Voice style (0-1)
ELEVENLABS_USE_SPEAKER_BOOST=true  # Speaker boost on/off

# Other required keys for the application
# (Add your Neo4j, OpenAI, etc. keys here)
```

## Direct Python Usage

If running Python scripts directly without `just`, set the ENV variable:

```bash
# Load mac environment
ENV=mac python talk.py

# Load cayucos environment  
ENV=cayucos python talk.py
```

## Fallback Behavior

If no environment is specified:
1. First checks if `ELEVENLABS_API_KEY` is already set
2. Tries to load `.env` from current directory
3. Tries to load `env/mac.env` as default
4. Raises error if no environment variables found

## Adding New Environments

1. Create a new `.env` file in `env/` directory
2. Copy required variables from existing environment
3. Update values as needed
4. Use with: `just run-talk your-new-env`