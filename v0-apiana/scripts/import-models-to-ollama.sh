#!/bin/bash

# Script to import models into Ollama
# Usage: ./import-models-to-ollama.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Ollama Model Import Script${NC}"
echo "============================"

# Check if ollama is installed
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}Error: Ollama is not installed or not in PATH${NC}"
    echo "Please install Ollama from https://ollama.ai"
    exit 1
fi

# Base directory where models are stored
MODEL_DIR="${1:-/path/to/your/models}"
MODELFILE_DIR="./modelfiles"

# Function to import a model
import_model() {
    local model_name=$1
    local model_path=$2
    local modelfile=$3
    
    echo -e "\n${YELLOW}Importing $model_name...${NC}"
    
    # Check if model directory exists
    if [ ! -d "$model_path" ]; then
        echo -e "${RED}Error: Model directory not found: $model_path${NC}"
        return 1
    fi
    
    # Check if Modelfile exists
    if [ ! -f "$modelfile" ]; then
        echo -e "${RED}Error: Modelfile not found: $modelfile${NC}"
        return 1
    fi
    
    # Copy Modelfile to model directory temporarily
    cp "$modelfile" "$model_path/Modelfile"
    
    # Change to model directory and create the model
    cd "$model_path"
    ollama create "$model_name" -f Modelfile
    
    # Clean up
    rm Modelfile
    cd - > /dev/null
    
    echo -e "${GREEN}✓ Successfully imported $model_name${NC}"
}

# Import each model
echo -e "\n${YELLOW}Starting model imports...${NC}"

# Mistral 7B Merged
import_model "mistral-7b-merged" \
    "$MODEL_DIR/mistralai_Mistral-7B-merged" \
    "$MODELFILE_DIR/mistral-7b-merged.Modelfile"

# Mistral 7B v0.1
import_model "mistral-7b-v0.1" \
    "$MODEL_DIR/mistralai_Mistral-7B-v0.1" \
    "$MODELFILE_DIR/mistral-7b-v0.1.Modelfile"

# Mistral Small 24B
import_model "mistral-small-24b" \
    "$MODEL_DIR/mistralai_Mistral-Small-24B-Base-2501" \
    "$MODELFILE_DIR/mistral-small-24b.Modelfile"

# Osmosis MCP 4B
import_model "osmosis-mcp-4b" \
    "$MODEL_DIR/osmosis-ai_osmosis-mcp-4b" \
    "$MODELFILE_DIR/osmosis-mcp-4b.Modelfile"

echo -e "\n${GREEN}Model import complete!${NC}"
echo -e "\nYou can now use these models with:"
echo -e "  ${YELLOW}ollama run mistral-7b-merged${NC}"
echo -e "  ${YELLOW}ollama run mistral-7b-v0.1${NC}"
echo -e "  ${YELLOW}ollama run mistral-small-24b${NC}"
echo -e "  ${YELLOW}ollama run osmosis-mcp-4b${NC}"
echo -e "\nList all models with: ${YELLOW}ollama list${NC}"