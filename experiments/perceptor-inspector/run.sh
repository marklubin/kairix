#!/bin/bash
cd /Users/mark/kairix/kairix-core
KAIRIX_LOG_LEVEL=INFO \
KAIRIX_USER_NAME=mark \
KAIRIX_AGENT_CONFIGURATION_SET_KEY=openai \
OPENAI_API_KEY=${OPENAI_API_KEY:-sk-dummy} \
uv run python /Users/mark/kairix/perceptor-inspector/src/perceptor_inspector/app.py