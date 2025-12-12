#!/usr/bin/env python3
"""
Ollama Proxy Logger - Logs all requests and responses to/from Ollama API
"""
import json
import datetime
from flask import Flask, request, Response
import requests

app = Flask(__name__)

# Ollama API endpoint
OLLAMA_API = "http://localhost:11434"

# Log file
LOG_FILE = "ollama_requests.log"

def log_request(method, path, headers, data, response_data):
    """Log request and response details"""
    timestamp = datetime.datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "method": method,
        "path": path,
        "request_headers": dict(headers),
        "request_body": data,
        "response": response_data
    }
    
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(log_entry, indent=2) + "\n---\n")
    
    # Also print to console for real-time monitoring
    print(f"\n[{timestamp}] {method} {path}")
    if data:
        print(f"Request: {json.dumps(data, indent=2)}")
    print(f"Response preview: {str(response_data)[:200]}...")

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    """Proxy all requests to Ollama and log them"""
    # Get request data
    data = None
    if request.method in ['POST', 'PUT']:
        try:
            data = request.get_json()
        except:
            data = request.get_data(as_text=True)
    
    # Forward to Ollama
    url = f"{OLLAMA_API}/{path}"
    headers = {k: v for k, v in request.headers if k.lower() != 'host'}
    
    if request.method == 'POST' and path == 'api/generate':
        # For streaming responses
        resp = requests.post(
            url,
            json=data,
            headers=headers,
            stream=True
        )
        
        def generate():
            full_response = ""
            for line in resp.iter_lines():
                if line:
                    yield line + b'\n'
                    try:
                        chunk = json.loads(line)
                        if 'response' in chunk:
                            full_response += chunk['response']
                    except:
                        pass
            
            # Log the complete interaction
            log_request(request.method, path, request.headers, data, 
                       {"full_response": full_response, "status": resp.status_code})
        
        return Response(generate(), 
                       content_type=resp.headers.get('content-type'),
                       status=resp.status_code)
    else:
        # Non-streaming requests
        resp = requests.request(
            method=request.method,
            url=url,
            json=data,
            headers=headers,
            params=request.args
        )
        
        try:
            response_data = resp.json()
        except:
            response_data = resp.text
        
        log_request(request.method, path, request.headers, data, response_data)
        
        return Response(
            resp.content,
            status=resp.status_code,
            headers=dict(resp.headers)
        )

if __name__ == '__main__':
    print("Ollama Proxy Logger")
    print("===================")
    print(f"Proxying requests from http://localhost:8080 to {OLLAMA_API}")
    print(f"Logging to: {LOG_FILE}")
    print("\nUpdate your Ollama client to use: http://localhost:8080")
    print("Example: curl http://localhost:8080/api/generate -d '{...}'")
    app.run(host='0.0.0.0', port=8080, debug=True)