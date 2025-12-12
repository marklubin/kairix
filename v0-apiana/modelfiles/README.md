# Ollama Model Import Guide

This guide explains how to import your local models into Ollama.

## Prerequisites

1. Install Ollama from https://ollama.ai
2. Ensure your models are downloaded locally
3. Have sufficient disk space (models will be duplicated in Ollama's format)

## Model Information

### 1. Mistral 7B Merged
- **Size**: ~14GB (7B parameters)
- **Format**: Safetensors
- **Context**: 4096 tokens
- **Use case**: General purpose, balanced performance

### 2. Mistral 7B v0.1
- **Size**: ~14GB (7B parameters)
- **Format**: Safetensors
- **Context**: 4096 tokens
- **Use case**: Original Mistral model, good baseline

### 3. Mistral Small 24B Base 2501
- **Size**: ~48GB (24B parameters)
- **Format**: Safetensors
- **Context**: 32768 tokens
- **Use case**: High quality, larger context, latest model
- **Note**: Requires significant GPU memory

### 4. Osmosis MCP 4B
- **Size**: ~8GB (4B parameters)
- **Format**: Safetensors
- **Context**: 4096 tokens
- **Use case**: Specialized for MCP (Model Context Protocol)

## Import Process

### Method 1: Using the Script

```bash
# Update the MODEL_DIR in the script to point to your models directory
./scripts/import-models-to-ollama.sh /path/to/your/models
```

### Method 2: Manual Import

For each model:

```bash
# 1. Navigate to the model directory
cd /path/to/your/models/mistralai_Mistral-7B-merged

# 2. Copy the appropriate Modelfile
cp ../../modelfiles/mistral-7b-merged.Modelfile ./Modelfile

# 3. Create the Ollama model
ollama create mistral-7b-merged -f Modelfile

# 4. Clean up
rm Modelfile
```

## Customizing Modelfiles

You can adjust parameters in the Modelfiles:

- **temperature**: Controls randomness (0.0-1.0)
- **top_p**: Nucleus sampling threshold
- **top_k**: Top-k sampling
- **repeat_penalty**: Penalize repetition
- **num_ctx**: Context window size
- **num_gpu**: Number of GPU layers to offload

## Template Formats

Different models use different chat templates:

### ChatML Format (Mistral Latest)
```
<|im_start|>system
You are a helpful assistant.<|im_end|>
<|im_start|>user
Hello!<|im_end|>
<|im_start|>assistant
Hi there!<|im_end|>
```

### Instruction Format (Mistral v0.1)
```
[INST] User message [/INST] Assistant response
```

## Troubleshooting

### Out of Memory
- Reduce `num_gpu` parameter
- Use quantized versions if available
- Close other applications

### Model Won't Load
- Check file paths in Modelfile
- Ensure all safetensors files are present
- Verify Ollama service is running: `ollama serve`

### Slow Performance
- Increase `num_gpu` for more GPU offloading
- Reduce `num_ctx` for faster inference
- Consider using smaller models

## Using the Models

After import, use models with:

```bash
# Interactive chat
ollama run mistral-7b-merged

# API usage
curl http://localhost:11434/api/generate -d '{
  "model": "mistral-7b-merged",
  "prompt": "Hello, how are you?"
}'

# With specific parameters
ollama run mistral-7b-merged --temperature 0.5 --top-p 0.95
```

## Notes

- The import process converts models to Ollama's optimized format
- Original model files are not modified
- Models are stored in `~/.ollama/models/`
- You can delete models with: `ollama rm model-name`