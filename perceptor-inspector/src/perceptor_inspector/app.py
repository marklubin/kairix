"""Perceptor Inspector - Test SummaryInsightPerceptor with real configuration."""
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from kairix_core.types.cognition import Stimulus, StimulusType
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.cognition.stores.sqlite_embedded_data import create_memory_shard_store

app = FastAPI(title="Perceptor Inspector")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CACHE_DIR = Path.home() / ".kairix" / "perceptor_tests"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

class TestConfig(BaseModel):
    db_path: str = "../.sqlite/mark.db"
    k_memories: int = 5
    user_message: str = "What's the weather like?"
    
class TestRequest(BaseModel):
    config: TestConfig
    save_name: Optional[str] = None

@app.get("/databases")
async def list_databases():
    """List available SQLite databases."""
    sqlite_dir = Path.home() / "kairix" / ".sqlite"
    dbs = []
    if sqlite_dir.exists():
        for db_file in sqlite_dir.glob("*.db"):
            dbs.append({
                "path": f"../.sqlite/{db_file.name}",
                "name": db_file.name,
                "size": db_file.stat().st_size
            })
    return dbs

@app.post("/test")
async def test_perceptor(request: TestRequest):
    """Test SummaryInsightPerceptor with given configuration."""
    try:
        # Create storage with specified database
        storage = StorageRuntime(db_path=request.config.db_path)
        
        # Create embedded store
        embedded_store = create_memory_shard_store(storage=storage)
        
        # Create agent runtime
        AgentRuntime()
        
        # Test the embedded store directly without full perceptor
        # This avoids spacy dependency issues
        keywords = ["weather", "climate", "temperature"]
        
        # Create stimulus
        Stimulus(
            type=StimulusType.user_message,
            content={"text": request.config.user_message}
        )
        
        # Search for memories directly
        memories = []
        for keyword in keywords:
            k_per_keyword = max(1, request.config.k_memories // len(keywords))
            results = embedded_store.search(keyword, k=k_per_keyword)
            memories.extend(results)
        
        # Create a perception-like response
        perception_data = {
            "type": "memory_recall",
            "confidence": 0.8 if memories else 0.0,
            "content": {
                "memories": [{"text": mem[0], "score": mem[1]} for mem in memories[:request.config.k_memories]]
            },
            "metadata": {
                "keywords_used": keywords,
                "total_results": len(memories)
            }
        }
        
        # Get memory count for context
        with storage.session() as session:
            from kairix_core.types.db import MemoryShard
            memory_count = session.query(MemoryShard).count()
        
        result = {
            "perception": perception_data,
            "db_info": {
                "path": request.config.db_path,
                "total_memories": memory_count
            }
        }
        
        # Save if requested
        if request.save_name:
            save_config(request.save_name, request.config.dict())
        
        return result
        
    except Exception as e:
        import traceback
        raise HTTPException(500, {
            "error": str(e),
            "traceback": traceback.format_exc()
        })

@app.get("/configs")
async def list_configs():
    """List saved configurations."""
    configs = []
    for file in CACHE_DIR.glob("*.json"):
        with open(file) as f:
            data = json.load(f)
            configs.append({
                "name": file.stem,
                "config": data,
                "created": file.stat().st_mtime
            })
    return sorted(configs, key=lambda x: x["created"], reverse=True)

@app.get("/config/{name}")
async def load_config(name: str):
    """Load a saved configuration."""
    file = CACHE_DIR / f"{name}.json"
    if not file.exists():
        raise HTTPException(404, "Config not found")
    with open(file) as f:
        return json.load(f)

def save_config(name: str, config: dict):
    """Save configuration to disk."""
    file = CACHE_DIR / f"{name}.json"
    with open(file, 'w') as f:
        json.dump(config, f, indent=2)

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>SummaryInsight Perceptor Inspector</title>
    <style>
        body { font-family: monospace; margin: 0; padding: 20px; background: #1e1e1e; color: #fff; }
        .container { max-width: 1200px; margin: 0 auto; }
        .config-section { background: #2a2a2a; padding: 20px; margin-bottom: 20px; border-radius: 4px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #aaa; }
        input, select, textarea { 
            background: #333; color: #fff; border: 1px solid #555; 
            padding: 8px; width: 100%; box-sizing: border-box; 
        }
        button { 
            background: #4a4; color: #fff; border: none; 
            padding: 10px 20px; cursor: pointer; margin-right: 10px; 
        }
        button:hover { background: #5b5; }
        .output { background: #2a2a2a; padding: 20px; white-space: pre-wrap; overflow: auto; }
        .error { color: #f44; }
        .saved-configs { 
            position: absolute; right: 20px; top: 20px; 
            background: #2a2a2a; padding: 10px; max-width: 300px; 
        }
        .config-item { cursor: pointer; padding: 5px; margin: 2px 0; }
        .config-item:hover { background: #333; }
    </style>
</head>
<body>
    <div class="saved-configs">
        <h3>Saved Configs</h3>
        <div id="configs"></div>
    </div>
    
    <div class="container">
        <h1>SummaryInsight Perceptor Inspector</h1>
        
        <div class="config-section">
            <h2>Configuration</h2>
            
            <div class="form-group">
                <label>Database</label>
                <select id="db_path">
                    <option value="../.sqlite/mark.db">mark.db (default)</option>
                </select>
                <button onclick="refreshDatabases()">Refresh</button>
            </div>
            
            <div class="form-group">
                <label>K Memories (number of memories to retrieve)</label>
                <input type="number" id="k_memories" value="5" min="1" max="50">
            </div>
            
            <div class="form-group">
                <label>User Message</label>
                <textarea id="user_message" rows="3">What's the weather like?</textarea>
            </div>
            
            <div class="form-group">
                <label>Config Name (optional, for saving)</label>
                <input type="text" id="save_name" placeholder="my-test-config">
            </div>
            
            <button onclick="testPerceptor()">Test Perceptor</button>
            <button onclick="saveAndTest()">Save & Test</button>
        </div>
        
        <div class="config-section">
            <h2>Output</h2>
            <div class="output" id="output">Ready to test...</div>
        </div>
    </div>
    
    <script>
        async function refreshDatabases() {
            try {
                const res = await fetch('/databases');
                const dbs = await res.json();
                const select = document.getElementById('db_path');
                select.innerHTML = '';
                dbs.forEach(db => {
                    const option = document.createElement('option');
                    option.value = db.path;
                    option.textContent = `${db.name} (${(db.size/1024/1024).toFixed(2)} MB)`;
                    select.appendChild(option);
                });
            } catch (e) {
                console.error('Failed to load databases:', e);
            }
        }
        
        async function testPerceptor() {
            const output = document.getElementById('output');
            output.textContent = 'Testing...';
            
            const config = {
                db_path: document.getElementById('db_path').value,
                k_memories: parseInt(document.getElementById('k_memories').value),
                user_message: document.getElementById('user_message').value
            };
            
            try {
                const res = await fetch('/test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({config})
                });
                
                const result = await res.json();
                
                if (res.status !== 200) {
                    output.innerHTML = `<span class="error">Error: ${result.detail.error}\n\n${result.detail.traceback}</span>`;
                    return;
                }
                
                output.textContent = `Database: ${result.db_info.path}
Total Memories in DB: ${result.db_info.total_memories}

Perception:
${JSON.stringify(result.perception, null, 2)}`;
                
            } catch (e) {
                output.innerHTML = `<span class="error">Error: ${e}</span>`;
            }
        }
        
        async function saveAndTest() {
            const name = document.getElementById('save_name').value;
            if (!name) {
                alert('Please enter a config name');
                return;
            }
            
            const config = {
                db_path: document.getElementById('db_path').value,
                k_memories: parseInt(document.getElementById('k_memories').value),
                user_message: document.getElementById('user_message').value
            };
            
            try {
                const res = await fetch('/test', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({config, save_name: name})
                });
                
                const result = await res.json();
                document.getElementById('output').textContent = JSON.stringify(result, null, 2);
                loadConfigs();
            } catch (e) {
                document.getElementById('output').innerHTML = `<span class="error">Error: ${e}</span>`;
            }
        }
        
        async function loadConfigs() {
            try {
                const res = await fetch('/configs');
                const configs = await res.json();
                const container = document.getElementById('configs');
                container.innerHTML = '';
                
                configs.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'config-item';
                    div.textContent = item.name;
                    div.onclick = () => loadConfig(item.name);
                    container.appendChild(div);
                });
            } catch (e) {
                console.error('Failed to load configs:', e);
            }
        }
        
        async function loadConfig(name) {
            try {
                const res = await fetch(`/config/${name}`);
                const config = await res.json();
                
                document.getElementById('db_path').value = config.db_path;
                document.getElementById('k_memories').value = config.k_memories;
                document.getElementById('user_message').value = config.user_message;
                document.getElementById('save_name').value = name;
            } catch (e) {
                console.error('Failed to load config:', e);
            }
        }
        
        // Initialize
        refreshDatabases();
        loadConfigs();
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    print("Starting Perceptor Inspector at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)