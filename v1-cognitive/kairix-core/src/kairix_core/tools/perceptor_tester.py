"""Simple web service for testing perceptors independently."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn

from kairix_core.cognition.perceptor.summary_insight import SummaryInsightPerceptor
from kairix_core.cognition.perceptor.environmental_context import EnvironmentalContextPerceptor
from kairix_core.types.cognition import Stimulus, StimulusType
from kairix_core.runtime.agent import AgentRuntime
from kairix_core.runtime.storage import StorageRuntime
from kairix_core.cognition.stores.sqlite_embedded_data import create_memory_shard_store

app = FastAPI(title="Perceptor Tester")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class TestRequest(BaseModel):
    perceptor: str
    stimulus_type: str
    content: str
    config: Optional[Dict[str, Any]] = {}

@app.post("/test")
async def test_perceptor(request: TestRequest):
    try:
        # Create perceptor based on type
        if request.perceptor == "summary_insight":
            store = create_memory_shard_store(storage=StorageRuntime())
            perceptor = SummaryInsightPerceptor(
                AgentRuntime(), 
                embedded_sumary_store=store,
                k_memories=request.config.get("k_memories", 5)
            )
        elif request.perceptor == "environmental_context":
            perceptor = EnvironmentalContextPerceptor(
                cache_duration_seconds=request.config.get("cache_duration", 300)
            )
        else:
            raise HTTPException(400, f"Unknown perceptor: {request.perceptor}")
        
        # Create stimulus
        stimulus = Stimulus(
            type=StimulusType[request.stimulus_type.upper()],
            content={"text": request.content}
        )
        
        # Process and return perception
        perception = perceptor.process_stimulus(stimulus)
        return {"perception": perception.dict() if perception else None}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Perceptor Tester</title>
        <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
        <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
        <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            select, textarea, button { width: 100%; margin: 10px 0; padding: 10px; }
            .result { background: #f0f0f0; padding: 10px; margin-top: 20px; white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <div id="root"></div>
        <script type="text/babel">
            function App() {
                const [perceptor, setPerceptor] = React.useState('summary_insight');
                const [stimulusType, setStimulusType] = React.useState('USER_MESSAGE');
                const [content, setContent] = React.useState('');
                const [result, setResult] = React.useState(null);
                const [loading, setLoading] = React.useState(false);
                
                const test = async () => {
                    setLoading(true);
                    try {
                        const res = await fetch('/test', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({perceptor, stimulus_type: stimulusType, content})
                        });
                        setResult(await res.json());
                    } catch(e) {
                        setResult({error: e.toString()});
                    }
                    setLoading(false);
                };
                
                return (
                    <div className="container">
                        <h1>Perceptor Tester</h1>
                        <select value={perceptor} onChange={e => setPerceptor(e.target.value)}>
                            <option value="summary_insight">Summary Insight</option>
                            <option value="environmental_context">Environmental Context</option>
                        </select>
                        <select value={stimulusType} onChange={e => setStimulusType(e.target.value)}>
                            <option value="USER_MESSAGE">User Message</option>
                            <option value="ASSISTANT_MESSAGE">Assistant Message</option>
                            <option value="SYSTEM_MESSAGE">System Message</option>
                        </select>
                        <textarea 
                            rows="5" 
                            placeholder="Enter stimulus content..."
                            value={content}
                            onChange={e => setContent(e.target.value)}
                        />
                        <button onClick={test} disabled={loading}>
                            {loading ? 'Testing...' : 'Test Perceptor'}
                        </button>
                        {result && (
                            <div className="result">
                                {JSON.stringify(result, null, 2)}
                            </div>
                        )}
                    </div>
                );
            }
            
            ReactDOM.render(<App />, document.getElementById('root'));
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)