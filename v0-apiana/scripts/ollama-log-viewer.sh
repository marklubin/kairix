#!/bin/bash

# Real-time Ollama log viewer with filtering

echo "Ollama Log Viewer"
echo "================="
echo ""
echo "Showing Ollama API requests in real-time..."
echo "Press Ctrl+C to stop"
echo ""

# Different commands for different systems
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if [ -f ~/.ollama/logs/server.log ]; then
        tail -f ~/.ollama/logs/server.log | grep -E "(POST|GET|prompt|generate|response)"
    else
        echo "Log file not found at ~/.ollama/logs/server.log"
        echo "Make sure Ollama is running with logging enabled:"
        echo "OLLAMA_DEBUG=1 ollama serve"
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v journalctl &> /dev/null; then
        # Using systemd
        sudo journalctl -fu ollama | grep -E "(POST|GET|prompt|generate|response)"
    else
        # Direct log file
        tail -f /var/log/ollama.log | grep -E "(POST|GET|prompt|generate|response)"
    fi
fi