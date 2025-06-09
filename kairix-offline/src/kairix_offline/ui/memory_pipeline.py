import hashlib
import uuid

import gradio as gr
from kairix_core.types import Agent, Embedding, MemoryShard, SourceDocument, Summary

from kairix_offline.processing import (
    initialize_processing,
    load_sources_from_gpt_export,
    synth_memories,
)


def create_and_embed_shard_text(agent_name: str,
                                input_text: str,
                                source_label: str):
    """Create a memory shard directly from input text without chunking."""
    try:
        # Validate inputs
        if not agent_name or not agent_name.strip():
            return "Error: Agent name is required"
        if not input_text or not input_text.strip():
            return "Error: Input text is required"
        if not source_label or not source_label.strip():
            return "Error: Source label is required"

        # Get or create agent
        agent = Agent.nodes.first_or_none(name=agent_name)
        if agent is None:
            agent = Agent(name=agent_name)
            agent.save()

        # Create unique ID for this entry
        doc_uid = str(uuid.uuid4().hex)

        # Create and save source document
        doc = SourceDocument(
            uid=doc_uid,
            source_label=source_label,
            content=input_text,
            source_type='mem-ui-manual-entry'
        )
        doc.save()

        # Generate idempotency key based on content hash
        content_hash = hashlib.sha256(input_text.encode()).hexdigest()
        idempotency_key = f"manual-{agent_name}-{content_hash[:16]}"

        # Check if this exact content already exists
        existing_shard = MemoryShard.get_or_none(idempotency_key)
        if existing_shard:
            return f"✓ Memory shard already exists with ID: {idempotency_key}"

        # Get embedder from the global processing environment
        from kairix_offline.processing import _initialized, summary_memory_synthezier
        if not _initialized or not summary_memory_synthezier:
            return "Error: Processing environment not initialized. Please restart the application."

        embedder = summary_memory_synthezier.embedder

        # Generate embedding
        numpy_array = embedder.encode(input_text)
        vector = numpy_array.tolist()

        # Create and save embedding
        embedding = Embedding(
            uid=idempotency_key,
            embedding_model=embedder.model_card_data.model_name,
            vector=vector,
        )
        embedding.save()

        # Create summary (for manual entries, the summary is the input text itself)
        summary = Summary(
            uid=idempotency_key,
            summary_text=input_text
        )
        summary.save()

        # Create memory shard
        shard = MemoryShard(
            uid=idempotency_key,
            shard_contents=input_text,
            vector_address=vector,
        )
        shard.save()

        # Connect relationships
        shard.embedding.connect(embedding)
        shard.summary.connect(summary)
        shard.source_document.connect(doc)
        shard.agent.connect(agent)

        return f"""✓ Successfully created memory shard!

Agent: {agent_name}
Shard ID: {idempotency_key}
Source Label: {source_label}
Text Length: {len(input_text)} characters
Embedding Model: {embedder.model_card_data.model_name}
Vector Dimensions: {len(vector)}"""

    except Exception as e:
        return f"Error creating memory shard: {e!s}"

theme = gr.themes.Monochrome(
    primary_hue="slate",
    secondary_hue="zinc",
    neutral_hue="gray",
    text_size="md",
    radius_size="md",
    spacing_size="md",
).set(
    body_background_fill="*neutral_950",
    body_background_fill_dark="*neutral_950",
    body_text_color="*neutral_100",
    body_text_color_dark="*neutral_100",
    body_text_color_subdued="*neutral_400",
    body_text_weight="400",
    background_fill_secondary="*neutral_900",
    background_fill_primary="*neutral_800",
    border_color_accent="*primary_600",
    border_color_primary="*neutral_700",
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_hover="*primary_500",
    button_primary_text_color="white",
    button_secondary_background_fill="*neutral_800",
    button_secondary_background_fill_hover="*neutral_700",
    button_secondary_text_color="*neutral_100",
    block_background_fill="*neutral_900",
    block_border_color="*neutral_800",
    block_label_text_color="*neutral_300",
    input_background_fill="*neutral_800",
    input_border_color="*neutral_700",
    input_border_color_focus="*primary_600",
)

with gr.Blocks(theme=theme, css="""
    .gradio-container {
        background-color: #0a0a0a !important;
    }
    h1 {
        background: linear-gradient(45deg, #4338ca, #6366f1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin-bottom: 1rem;
    }
    h2 {
        color: #e2e8f0;
        font-weight: 600;
        border-bottom: 2px solid #1e293b;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    .gr-button-primary {
        background: linear-gradient(45deg, #4338ca, #6366f1) !important;
        border: none !important;
        font-weight: 600 !important;
    }
    .gr-button-primary:hover {
        background: linear-gradient(45deg, #3730a3, #4f46e5) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }
    .gr-button-secondary {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
    }
    .gr-button-secondary:hover {
        background-color: #334155 !important;
    }
    .gr-box {
        border-radius: 8px !important;
        border-color: #1e293b !important;
        background-color: #0f172a !important;
    }
""") as history_importer:
    with gr.Column():
        gr.Markdown("# 🧠 Kairix Memory Architecture Pipeline")
        gr.Markdown("Advanced memory synthesis and management system", elem_classes=["subtitle"])

    with gr.Tabs() as tabs:
        # Tab 1: Manual Memory Entry
        with gr.Tab("📝 Manual Memory Entry", id=0):
            gr.Markdown("## Direct Memory Shard Creation")
            gr.Markdown("Create memory shards directly from text input without chunking.")

            with gr.Row():
                with gr.Column(scale=1):
                    manual_agent_name = gr.Textbox(
                        label="Agent Name",
                        placeholder="Enter agent name (e.g., ResearchAssistant)",
                        info="The agent that will own this memory"
                    )
                    manual_source_label = gr.Textbox(
                        label="Source Label",
                        placeholder="Enter a descriptive label",
                        info="A brief description of this memory's origin"
                    )
                    manual_text = gr.Textbox(
                        label="Memory Content",
                        placeholder="Enter the text content to embed and store as a memory shard...",
                        lines=10,
                        info="This text will be embedded and stored directly as a memory shard"
                    )
                    manual_submit_btn = gr.Button("🚀 Create Memory Shard", variant="primary", size="lg")

                with gr.Column(scale=1):
                    manual_output = gr.Textbox(
                        label="Creation Status",
                        placeholder="Results will appear here...",
                        lines=14,
                        interactive=False
                    )

        # Tab 2: ChatGPT Import
        with gr.Tab("📥 ChatGPT Import", id=1):
            gr.Markdown("## Import ChatGPT Conversations")
            gr.Markdown("Process exported ChatGPT conversations into source documents.")

            with gr.Row():
                with gr.Column(scale=1):
                    file = gr.FileExplorer(
                        label="Select ChatGPT Export File",
                        root_dir="../",
                        max_height=400,
                        glob="*.json",
                        info="Browse for your ChatGPT export JSON file"
                    )
                    import_btn = gr.Button("📤 Import Conversations", variant="primary", size="lg")

                with gr.Column(scale=1):
                    file_import_output = gr.Textbox(
                        label="Import Results",
                        placeholder="Import status will appear here...",
                        lines=16,
                        interactive=False
                    )

        # Tab 3: Memory Synthesis
        with gr.Tab("⚡ Memory Synthesis", id=2):
            gr.Markdown("## Synthesize Memories from Documents")
            gr.Markdown("Process source documents into chunked, summarized memory shards.")

            with gr.Row():
                with gr.Column(scale=1):
                    synth_agent_name = gr.Textbox(
                        label="Agent Name",
                        placeholder="Enter agent name",
                        info="The agent that will own these memories"
                    )
                    run_id = gr.Textbox(
                        label="Run ID",
                        placeholder="Enter a unique run identifier",
                        info="Unique identifier for this synthesis run"
                    )
                    synth_btn = gr.Button("⚙️ Synthesize Memories", variant="primary", size="lg")

                with gr.Column(scale=1):
                    summarizer_output = gr.Textbox(
                        label="Synthesis Results",
                        placeholder="Synthesis progress will appear here...",
                        lines=10,
                        interactive=False
                    )

    # Wire up the manual entry functionality
    manual_submit_btn.click(
        fn=create_and_embed_shard_text,
        inputs=[manual_agent_name, manual_text, manual_source_label],
        outputs=[manual_output],
    )

    # Wire up the import functionality
    import_btn.click(
        fn=load_sources_from_gpt_export,
        inputs=[file],
        outputs=[file_import_output],
    )

    # Wire up the synthesis functionality
    synth_btn.click(
        fn=synth_memories,
        inputs=[synth_agent_name, run_id],
        outputs=[summarizer_output],
    )


def main():
    # Initialize the processing environment before launching UI
    initialize_processing()
    history_importer.launch(server_name="0.0.0.0")


if __name__ == "__main__":
    main()
