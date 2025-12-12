"""
Refactored CLI using the new pipeline factory system.

This version uses pipeline factories to create configured pipelines
for flexible ChatGPT export processing.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from apiana import runtime_config
from apiana.types.configuration import Neo4jConfig
import pipelines

logger = logging.getLogger(__name__)


class ProgressPrinter:
    """Simple progress printer for CLI."""

    def __init__(self):
        self.current_stage = ""

    def __call__(self, stage_name: str, current: int, total: int):
        if stage_name != self.current_stage:
            print(f"\n🔄 {stage_name}")
            self.current_stage = stage_name

        if total > 0:
            percent = (current / total) * 100
            print(f"   Progress: {current}/{total} ({percent:.1f}%)", end="\r")

        if current == total:
            print(f"   ✅ {stage_name} complete!")


def create_neo4j_config(args) -> Optional[Neo4jConfig]:
    """Create Neo4j configuration if enabled."""
    if args.no_neo4j:
        return None

    try:
        print("🗄️  Using Neo4j configuration...")
        return runtime_config.neo4j
    except Exception as e:
        print(f"⚠️  Failed to get Neo4j config: {e}")
        if args.require_neo4j:
            sys.exit(1)
        return None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Process ChatGPT export files using modular pipeline system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic processing with chunking
  %(prog)s -i export.json -o output/
  
  # Use local LLM with quantization
  %(prog)s -i export.json -o output/ --local-llm microsoft/DialoGPT-small --quantize-4bit
  
  # Skip Neo4j stores
  %(prog)s -i export.json -o output/ --no-neo4j
  
  # Custom chunk size
  %(prog)s -i export.json -o output/ --max-tokens 3000
        """,
    )

    # Input/output arguments
    parser.add_argument(
        "-i", "--input", required=True, help="Input ChatGPT export JSON file"
    )
    parser.add_argument(
        "-o", "--output", required=True, help="Output directory for processed files"
    )

    # Processing options
    parser.add_argument(
        "--no-chunking", action="store_true", help="Disable conversation chunking"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=5000,
        help="Maximum tokens per conversation chunk (default: 5000)",
    )
    parser.add_argument(
        "--no-plain-text",
        action="store_true",
        help="Skip saving conversations as plain text",
    )

    # LLM provider options
    parser.add_argument(
        "--local-llm",
        help="Use local LLM (transformers model name, e.g., 'microsoft/DialoGPT-small')",
    )
    parser.add_argument(
        "--device", default="auto", help="Device for local LLM (auto, cpu, cuda, mps)"
    )
    parser.add_argument(
        "--quantize-4bit",
        action="store_true",
        help="Use 4-bit quantization for local LLM",
    )
    parser.add_argument(
        "--quantize-8bit",
        action="store_true",
        help="Use 8-bit quantization for local LLM",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.7, help="LLM temperature (default: 0.7)"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=2048,
        help="Maximum sequence length for local LLM (default: 2048)",
    )

    # Storage options
    parser.add_argument("--no-neo4j", action="store_true", help="Skip Neo4j stores")
    parser.add_argument(
        "--require-neo4j", action="store_true", help="Exit if Neo4j connection fails"
    )

    # Logging
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set up logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Validate inputs
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Get Neo4j configuration
        neo4j_config = create_neo4j_config(args)

        # Determine LLM model configuration
        if args.local_llm:
            llm_model = args.local_llm
            llm_device = args.device
            llm_quantization = None
            if args.quantize_4bit:
                llm_quantization = "4bit"
            elif args.quantize_8bit:
                llm_quantization = "8bit"
            print(f"🤖 Using local LLM: {llm_model}")
        else:
            llm_model = runtime_config.summarizer.model_name
            llm_device = "auto"
            llm_quantization = None
            print(f"🤖 Using OpenAI-compatible LLM: {llm_model}")

        # Create pipeline using factory
        print("\n🚀 Starting processing...")
        print(f"   Input: {input_file}")
        print(f"   Output: {output_dir}")
        print(f"   Chunking: {'enabled' if not args.no_chunking else 'disabled'}")
        print(f"   Max tokens: {args.max_tokens}")

        pipeline = pipelines.create_chatgpt_export_pipeline(
            neo4j_config=neo4j_config,
            agent_id="cli_user",  # Default agent for CLI
            llm_model=llm_model,
            llm_device=llm_device,
            llm_quantization=llm_quantization,
            llm_temperature=args.temperature,
            embedding_model=runtime_config.embedding_model_name,
            max_tokens=args.max_tokens,
            chunk_conversations=not args.no_chunking,
            run_name=f"CLI Export Processing: {input_file.name}"
        )

        # Run the pipeline
        result = pipeline.run(str(input_file))

        # Print final statistics
        print("\n✅ Processing complete!")
        print(f"   Success: {result.success}")
        print(f"   Execution time: {result.execution_time_ms:.1f}ms")
        print(f"   Errors: {len(result.errors)}")
        print(f"   Warnings: {len(result.warnings)}")

        if result.errors:
            print("   Error details:")
            for error in result.errors:
                print(f"     - {error}")

        if result.warnings:
            print("   Warning details:")
            for warning in result.warnings:
                print(f"     - {warning}")

        # Save plain text output if requested
        if not args.no_plain_text:
            print(f"\n💾 Saving results to {output_dir}")
            # TODO: Implement plain text output saving from pipeline result

        if not result.success or result.errors:
            print("⚠️  Some errors occurred during processing.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n❌ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception("Processing failed")
        print(f"❌ Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
