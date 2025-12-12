#!/usr/bin/env python3
"""
Dynamic Modelfile generator that loads system prompts from external files
"""
import argparse
from pathlib import Path

class ModelfileGenerator:
    def __init__(self, system_prompts_dir="./system-prompts", output_dir="./modelfiles"):
        self.system_prompts_dir = Path(system_prompts_dir)
        self.output_dir = Path(output_dir)
        
        # Create directories
        self.system_prompts_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
    
    def load_system_prompt(self, prompt_file):
        """Load system prompt from file"""
        prompt_path = self.system_prompts_dir / prompt_file
        if not prompt_path.exists():
            raise FileNotFoundError(f"System prompt file not found: {prompt_path}")
        
        return prompt_path.read_text().strip()
    
    def generate_modelfile(self, model_name, base_model, system_prompt_file, **params):
        """Generate a Modelfile with external system prompt"""
        
        # Load system prompt
        system_prompt = self.load_system_prompt(system_prompt_file)
        
        # Default parameters
        default_params = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "num_ctx": 4096,
            "num_predict": 512
        }
        default_params.update(params)
        
        # Generate Modelfile content
        modelfile_content = f"""# Auto-generated Modelfile for {model_name}
# System prompt loaded from: {system_prompt_file}
FROM {base_model}

SYSTEM \"\"\"{system_prompt}\"\"\"

# Parameters
"""
        
        # Add parameters
        for param, value in default_params.items():
            modelfile_content += f"PARAMETER {param} {value}\n"
        
        # Add template
        modelfile_content += '''
# Template for ChatML format
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
{{ end }}{{ .Response }}<|im_end|>
"""

# Stop tokens
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
'''
        
        # Write Modelfile
        output_path = self.output_dir / f"{model_name}.Modelfile"
        output_path.write_text(modelfile_content)
        
        print(f"✓ Generated {output_path}")
        return output_path
    
    def create_sample_prompts(self):
        """Create sample system prompt files"""
        samples = {
            "coding-assistant.txt": """You are an expert programmer and software architect.

Guidelines:
- Write clean, efficient, well-documented code
- Follow language-specific best practices
- Include error handling and edge cases
- Explain complex algorithms and design decisions
- Suggest optimizations and alternatives when relevant

Always prioritize code clarity, maintainability, and performance.""",
            
            "data-scientist.txt": """You are a senior data scientist with expertise in machine learning, statistics, and data analysis.

Your approach:
- Ask clarifying questions about the data and business problem
- Suggest appropriate ML algorithms and statistical methods
- Consider data quality, bias, and ethical implications
- Explain model performance and limitations clearly
- Provide actionable insights from data analysis
- Use Python/R code examples when helpful

Focus on practical, business-relevant solutions.""",
            
            "creative-writer.txt": """You are a creative writer with expertise in storytelling, character development, and narrative structure.

Your writing style:
- Engaging and vivid descriptions
- Strong character development
- Compelling dialogue
- Varied sentence structure and pacing
- Rich imagery and sensory details
- Appropriate tone for the genre and audience

Help users develop plots, characters, and improve their writing craft.""",
            
            "research-assistant.txt": """You are a research assistant with strong analytical and critical thinking skills.

Your methodology:
- Identify key research questions and hypotheses
- Suggest appropriate research methods and sources
- Evaluate source credibility and bias
- Synthesize information from multiple sources
- Present findings clearly with proper citations
- Acknowledge limitations and areas for further research

Maintain academic rigor while being accessible to your audience."""
        }
        
        for filename, content in samples.items():
            file_path = self.system_prompts_dir / filename
            if not file_path.exists():
                file_path.write_text(content)
                print(f"✓ Created sample prompt: {file_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate Ollama Modelfiles with external system prompts")
    parser.add_argument("--create-samples", action="store_true", help="Create sample system prompt files")
    parser.add_argument("--model-name", help="Name for the new model")
    parser.add_argument("--base-model", help="Base model path")
    parser.add_argument("--system-prompt", help="System prompt file name")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature parameter")
    parser.add_argument("--max-tokens", type=int, default=512, help="Max tokens to generate")
    
    args = parser.parse_args()
    
    generator = ModelfileGenerator()
    
    if args.create_samples:
        generator.create_sample_prompts()
        print("\nSample system prompts created. You can now generate models:")
        print("python modelfile_generator.py --model-name mistral-coder --base-model ./mistralai_Mistral-7B-merged --system-prompt coding-assistant.txt")
        return
    
    if args.model_name and args.base_model and args.system_prompt:
        try:
            output_path = generator.generate_modelfile(
                args.model_name,
                args.base_model,
                args.system_prompt,
                temperature=args.temperature,
                num_predict=args.max_tokens
            )
            print("\nTo create the model, run:")
            print(f"ollama create {args.model_name} -f {output_path}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage:")
        print("1. Create samples: python modelfile_generator.py --create-samples")
        print("2. Generate model: python modelfile_generator.py --model-name NAME --base-model PATH --system-prompt FILE")

if __name__ == "__main__":
    main()