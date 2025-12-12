"""
Local LLM provider using transformers library for inference.
"""

import logging
import time
from typing import Any, Dict, List, Optional

try:
    import torch
    from transformers import (
        AutoModelForCausalLM, 
        AutoTokenizer, 
        GenerationConfig,
        BitsAndBytesConfig
    )
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

from apiana.core.providers.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class LocalTransformersLLM(LLMProvider):
    """
    Local LLM provider using transformers library.
    
    Supports loading models locally with various optimizations like quantization,
    and provides the same interface as remote providers.
    """
    
    def __init__(
        self,
        model_name: str,
        device: str = "auto",
        torch_dtype: str = "auto",
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        max_length: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True,
        **kwargs
    ):
        if not HAS_TRANSFORMERS:
            raise ImportError("transformers library is required for LocalTransformersLLM")
        
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self.generation_config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            max_length=max_length,
            **kwargs
        )
        
        logger.info(f"Loading model {model_name}...")
        
        # Set up quantization if requested
        quantization_config = None
        if load_in_4bit or load_in_8bit:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=load_in_4bit,
                load_in_8bit=load_in_8bit,
                bnb_4bit_compute_dtype=torch.float16 if load_in_4bit else None,
            )
        
        # Determine torch dtype
        if torch_dtype == "auto":
            if torch.cuda.is_available():
                torch_dtype = torch.float16
            else:
                torch_dtype = torch.float32
        elif isinstance(torch_dtype, str):
            torch_dtype = getattr(torch, torch_dtype)
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        
        # Add special tokens if missing
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model
        model_kwargs = {
            "torch_dtype": torch_dtype,
            "trust_remote_code": True,
        }
        
        if quantization_config:
            model_kwargs["quantization_config"] = quantization_config
        elif device != "cpu":
            model_kwargs["device_map"] = device
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            **model_kwargs
        )
        
        # Move to device if not using device_map
        if device == "cpu" or (quantization_config is None and device != "auto"):
            self.model = self.model.to(device)
        
        self.model.eval()
        logger.info(f"Model {model_name} loaded successfully")
    
    def invoke(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None, 
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the local model."""
        start_time = time.time()
        
        # Format prompt with system instruction if provided
        if system_instruction:
            # Use a simple format for now, could be made model-specific
            formatted_prompt = f"System: {system_instruction}\n\nUser: {prompt}\n\nAssistant:"
        else:
            formatted_prompt = prompt
        
        # Tokenize input
        inputs = self.tokenizer(
            formatted_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length - 500  # Leave room for response
        )
        
        # Move to same device as model
        device = next(self.model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Override generation config with any provided kwargs
        generation_config = GenerationConfig(**{
            **self.generation_config.to_dict(),
            **kwargs
        })
        
        # Generate response
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                generation_config=generation_config,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        # Decode response (only the new tokens)
        input_length = inputs["input_ids"].shape[1]
        response_tokens = outputs[0][input_length:]
        response_text = self.tokenizer.decode(response_tokens, skip_special_tokens=True)
        
        # Clean up response
        response_text = response_text.strip()
        
        execution_time = time.time() - start_time
        
        return LLMResponse(
            content=response_text,
            model=self.model_name,
            usage={
                "prompt_tokens": input_length,
                "completion_tokens": len(response_tokens),
                "total_tokens": input_length + len(response_tokens),
            },
            metadata={
                "execution_time": execution_time,
                "device": str(device),
                "generation_config": generation_config.to_dict(),
            }
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        device = next(self.model.parameters()).device
        
        # Calculate approximate model size
        param_count = sum(p.numel() for p in self.model.parameters())
        
        return {
            "model_name": self.model_name,
            "device": str(device),
            "parameter_count": param_count,
            "model_size_mb": param_count * 4 / (1024 * 1024),  # Approximate for float32
            "max_length": self.max_length,
            "vocabulary_size": len(self.tokenizer),
            "torch_dtype": str(next(self.model.parameters()).dtype),
        }
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """
        Chat interface that accepts a list of messages.
        
        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
        """
        # Convert messages to a single prompt
        prompt_parts = []
        system_msg = None
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_msg = content
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt = "\n\n".join(prompt_parts)
        if not prompt.endswith("\n\nAssistant:"):
            prompt += "\n\nAssistant:"
        
        return self.invoke(prompt, system_instruction=system_msg, **kwargs)
    
    def __del__(self):
        """Clean up model when object is destroyed."""
        if hasattr(self, 'model'):
            del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()