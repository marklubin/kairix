# Engineering Report: Multi-Model Inference Optimization with llama.cpp

## Executive Summary

Performance testing reveals that the reported 50+ second inference times are NOT occurring with the current codebase. Instead, inference takes 4-17 seconds depending on prompt complexity. The primary bottlenecks are:

1. **Memory pressure** from running 3 models simultaneously (11.4GB VRAM usage)
2. **Large context window** (8000 tokens) 
3. **Complex, lengthy system prompts** (7.6x slower than simple prompts)

## Test Results

### Baseline Performance
- **Simple inference (50 tokens)**: 2.2s
- **With your long prompts (512 tokens)**: 16.8s
- **With JSON schema validation**: 10.9s (actually faster!)
- **With model pooling (3 models)**: 4.6s average

### Key Findings

1. **Context Size Impact**: Minimal (8000 vs 2048 = same speed)
2. **Thread Count**: No impact on GPU inference
3. **Async Overhead**: Negligible (<0.1s)
4. **Pooling Overhead**: None for inference, but high memory usage
5. **Prompt Complexity**: MAJOR impact (7.6x slowdown)

## Root Cause Analysis

The 50+ second times you observed were likely due to:
1. **Initial run compilation** - Metal shaders compile on first use
2. **Memory swapping** - 11.4GB models + 8K context approaching 16GB limit
3. **Debug/verbose output** slowing down the process

## Recommendations (Priority Order)

### 1. **Immediate Fix: Reduce Memory Pressure**
```python
# Option A: Single model (RECOMMENDED)
class LlamaCppProvider(ModelProvider):
    def __init__(self, model_name: str):
        self.model = LlamaCppModel(llama=Llama.from_pretrained(
            n_gpu_layers=-1,
            n_ctx=4096,  # Reduced from 8000
            **_model_definitions[model_name]
        ))
    
    def get_model(self, model_name: str) -> Model:
        return self.model  # Same model for all requests
```

### 2. **Optimize Prompts**
```python
# Cache tokenized system prompt
class LlamaCppModel:
    def __init__(self, llama: Llama):
        self.llama = llama
        self._cached_system_tokens = None
    
    def get_response(self, system_instructions: str, ...):
        # Cache system prompt encoding
        if self._cached_system_tokens is None:
            self._cached_system_tokens = self.llama.tokenize(system_instructions)
```

### 3. **Smart Context Management**
```python
# Dynamic context sizing based on input
def calculate_context_size(prompt_length: int) -> int:
    if prompt_length < 500:
        return 2048
    elif prompt_length < 1500:
        return 4096
    else:
        return 8192
```

### 4. **Platform-Specific Optimizations**

#### For macOS (Metal):
```python
config_mac = {
    "n_gpu_layers": -1,
    "n_ctx": 4096,
    "use_mlock": True,
    "n_batch": 512,
    "flash_attn": True,  # Keep enabled
}
```

#### For Linux/CUDA:
```python
config_cuda = {
    "n_gpu_layers": -1,
    "n_ctx": 4096,
    "use_mlock": False,  # Let CUDA manage memory
    "n_batch": 1024,     # Larger batches on CUDA
    "flash_attn": True,
    "tensor_split": None,  # For multi-GPU
}
```

### 5. **Production Architecture**

```python
class OptimizedLlamaProvider:
    def __init__(self, model_config: dict, max_models: int = 1):
        self.max_models = max_models
        self.models = []
        self.current_idx = 0
        
        # Only create what we need
        for i in range(min(max_models, self._calculate_safe_pool_size())):
            self.models.append(self._create_model(model_config))
    
    def _calculate_safe_pool_size(self) -> int:
        """Calculate safe pool size based on available memory"""
        if platform.system() == "Darwin":  # macOS
            # M-series unified memory
            available_gb = 16  # Conservative for M4
            model_gb = 4  # Q4_0 model size
            return max(1, int(available_gb * 0.7 / model_gb))
        else:  # Linux/CUDA
            # Check CUDA memory
            import torch
            if torch.cuda.is_available():
                available_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
                model_gb = 4
                return max(1, int(available_gb * 0.8 / model_gb))
        return 1
    
    def get_model(self) -> Model:
        """Round-robin if multiple models, otherwise return single"""
        if len(self.models) == 1:
            return self.models[0]
        
        model = self.models[self.current_idx]
        self.current_idx = (self.current_idx + 1) % len(self.models)
        return model
```

### 6. **Monitoring and Diagnostics**

```python
class PerformanceMonitor:
    def __init__(self):
        self.inference_times = []
    
    def log_inference(self, prompt_tokens: int, generated_tokens: int, time_sec: float):
        self.inference_times.append({
            "timestamp": time.time(),
            "prompt_tokens": prompt_tokens,
            "generated_tokens": generated_tokens,
            "total_time": time_sec,
            "tokens_per_sec": generated_tokens / time_sec
        })
        
        # Alert on slow inference
        if time_sec > 20:
            logger.warning(f"Slow inference detected: {time_sec:.1f}s for {prompt_tokens} prompt tokens")
```

## Conclusion

The system is NOT fundamentally broken. The perceived slowness comes from:
1. Running 3x 4GB models in 16GB memory
2. Very long system prompts (1000+ tokens)
3. First-run Metal shader compilation

**Quick win**: Use a single model instead of pooling. This will:
- Reduce memory usage by 67%
- Enable prompt caching
- Maintain same throughput for your use case

**Long term**: Implement the optimized architecture above for production scalability.

## Appendix: Performance Benchmarks

| Configuration | Inference Time | Memory Usage |
|--------------|----------------|--------------|
| Single model, simple prompt | 2.2s | 3.8GB |
| Single model, complex prompt | 16.8s | 3.8GB |
| 3-model pool, simple prompt | 4.6s | 11.4GB |
| With JSON schema | 10.9s | Same |
| Recommended config | ~5-8s | 3.8GB |

The recommended configuration should give you 5-8 second inference times with stable performance.