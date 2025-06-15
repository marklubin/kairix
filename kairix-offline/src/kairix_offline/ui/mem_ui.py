import hashlib
import uuid
from threading import Thread
import subprocess

import gradio as gr
from kairix_core.thread_runner import LogStreamingThreadRuner
from kairix_core.types import Agent, Embedding, MemoryShard, SourceDocument, Summary

from kairix_offline.processing import (
    initialize_processing,
    load_sources_from_gpt_export,
    synth_memories,
)
from kairix_offline.ui import kairirx_log_stream
from kairix_offline.stores.sqlite import ConversationStore


def with_streaming_logs(fn):
    return lambda *args, **kwargs: LogStreamingThreadRuner(
        kairirx_log_stream,
        Thread(target=fn, args=args, kwargs=kwargs),
    ).start()


def create_and_embed_shard_text(agent_name: str, input_text: str, source_label: str):
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
            source_type="mem-ui-manual-entry",
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
            embedding_model=embedder.model_card_data.base_model,
            vector=vector,
        )
        embedding.save()

        # Create summary (for manual entries, the summary is the input text itself)
        summary = Summary(uid=idempotency_key, summary_text=input_text)
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

        return f"""<pre style='font-family: Courier New, monospace; color: #1a237e;'><span class="blink">✓ Successfully created memory shard!</span>

Agent: <span class="blink">{agent_name}</span>
Shard ID: <span class="blink">{idempotency_key}</span>
Source Label: {source_label}
Text Length: {len(input_text)} characters
Embedding Model: {embedder.model_card_data.model_name}
Vector Dimensions: {len(vector)}</pre>"""

    except Exception as e:
        return f"<pre style='font-family: Courier New, monospace; color: #d32f2f;'>Error creating memory shard: {e!s}</pre>"


def direct_inference_query(input_text: str):
    """Submit a query directly to the configured inference provider."""
    try:
        # Validate input
        if not input_text or not input_text.strip():
            return "Error: Input text is required"

        # Get the synthesizer instance
        from kairix_offline.processing import _initialized, summary_memory_synthezier

        if not _initialized or not summary_memory_synthezier:
            return "Error: Processing environment not initialized. Please restart the application."

        # Get the inference parameters from the synthesizer
        inference_params = summary_memory_synthezier.inference_parameters

        # Call the inference provider directly
        result = summary_memory_synthezier.inference_provider.predict(
            input_text, inference_params
        )

        # Format the response with metadata
        return f"""<pre style='font-family: Courier New, monospace; color: #1a237e;'><span class="blink">✓ Inference completed successfully!</span>

Input Length: <span class="blink">{len(input_text)}</span> characters
Output Length: <span class="blink">{len(result)}</span> characters

Inference Parameters:
- Max Tokens: <span class="blink">{inference_params.get("requested_tokens", "N/A")}</span>
- Temperature: {inference_params.get("temperature", "N/A")}
- Template: {inference_params.get("chat_template", "N/A")}

Result:
---
{result}
</pre>"""

    except Exception as e:
        return f"<pre style='font-family: Courier New, monospace; color: #d32f2f;'>Error during inference: {e!s}</pre>"


def get_cron_job_history():
    """Get recent cron job history"""
    try:
        store = ConversationStore()
        jobs = store.get_job_history(limit=20)
        
        if not jobs:
            return "<pre style='font-family: Courier New, monospace; color: #666;'>No job history found</pre>"
        
        html = "<div style='font-family: Courier New, monospace;'>"
        html += "<table style='width: 100%; border-collapse: collapse;'>"
        html += "<tr style='border-bottom: 2px solid #000;'>"
        html += "<th style='text-align: left; padding: 8px;'>Job ID</th>"
        html += "<th style='text-align: left; padding: 8px;'>Start Time</th>"
        html += "<th style='text-align: left; padding: 8px;'>Status</th>"
        html += "<th style='text-align: left; padding: 8px;'>Files</th>"
        html += "<th style='text-align: left; padding: 8px;'>Errors</th>"
        html += "</tr>"
        
        for job in jobs:
            status_color = {
                'running': '#ff6f00',
                'completed': '#00897b',
                'completed_with_errors': '#ffa000',
                'failed': '#d32f2f'
            }.get(job['status'], '#666')
            
            html += "<tr style='border-bottom: 1px solid #ddd;'>"
            html += f"<td style='padding: 8px;'>{job['id'][:8]}...</td>"
            html += f"<td style='padding: 8px;'>{job['start_time'].strftime('%Y-%m-%d %H:%M')}</td>"
            html += f"<td style='padding: 8px; color: {status_color}; font-weight: bold;'>{job['status']}</td>"
            html += f"<td style='padding: 8px;'>{job['files_processed']}/{job['files_found']}</td>"
            html += f"<td style='padding: 8px; color: {'#d32f2f' if job['errors_count'] else '#00897b'};'>{job['errors_count']}</td>"
            html += "</tr>"
        
        html += "</table></div>"
        return html
        
    except Exception as e:
        return f"<pre style='font-family: Courier New, monospace; color: #d32f2f;'>Error loading job history: {e!s}</pre>"


def run_cron_job_manually():
    """Manually trigger the cron job"""
    try:
        # Run the cron job script
        result = subprocess.run(
            ['python', 'scripts/conversation_ingestion_cron.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        output = result.stdout if result.returncode == 0 else result.stderr
        status = "✓ Job completed successfully" if result.returncode == 0 else "✗ Job failed"
        
        return f"""<pre style='font-family: Courier New, monospace; color: {'#00897b' if result.returncode == 0 else '#d32f2f'}'>
{status}

Output:
{output}
</pre>"""
        
    except subprocess.TimeoutExpired:
        return "<pre style='font-family: Courier New, monospace; color: #d32f2f;'>Error: Job timed out after 5 minutes</pre>"
    except Exception as e:
        return f"<pre style='font-family: Courier New, monospace; color: #d32f2f;'>Error running job: {e!s}</pre>"


theme = gr.themes.Base(
    primary_hue="emerald",
    secondary_hue="purple",
    neutral_hue="stone",
    text_size="md",
    radius_size="none",  # Sharp angular shapes
    spacing_size="md",
    font=["Georgia", "Times New Roman", "serif"],  # Serif fonts
    font_mono=["Courier New", "monospace"],
).set(
    # Pale green background
    body_background_fill="#e8f5e9",
    body_background_fill_dark="#e8f5e9",
    # Dark saturated text colors
    body_text_color="#1a237e",  # Deep indigo
    body_text_color_dark="#1a237e",
    body_text_color_subdued="#4527a0",  # Deep purple
    body_text_weight="300",  # Thin font weight
    # Vibrant background colors for components
    background_fill_secondary="#bbdefb",  # Light blue
    background_fill_primary="#c5e1a5",  # Light green
    # Saturated vibrant borders
    border_color_accent="#ff6f00",  # Deep orange
    border_color_primary="#00897b",  # Teal
    # Vibrant saturated buttons
    button_primary_background_fill="#d32f2f",  # Deep red
    button_primary_background_fill_hover="#c62828",  # Darker red
    button_primary_text_color="#ffffff",
    button_secondary_background_fill="#7b1fa2",  # Deep purple
    button_secondary_background_fill_hover="#6a1b9a",  # Darker purple
    button_secondary_text_color="#ffffff",
    # Component backgrounds
    block_background_fill="#f3e5f5",  # Light purple
    block_border_color="#4a148c",  # Deep purple border
    block_label_text_color="#1a237e",  # Deep indigo
    # Input fields
    input_background_fill="#fff9c4",  # Pale yellow
    input_border_color="#f57c00",  # Orange
    input_border_color_focus="#d84315",  # Deep orange focus
    # Additional retro colors
    table_border_color="#00695c",
    table_odd_background_fill="#e1f5fe",  # Light cyan
    table_even_background_fill="#f3e5f5",  # Light purple
)

with gr.Blocks(
    theme=theme,
    css="""
    /* Blinking animation */
    @keyframes blink {
        0% { opacity: 1; }
        50% { opacity: 0; }
        100% { opacity: 1; }
    }

    /* Cursor blink animation */
    @keyframes cursor-blink {
        0% { border-right-color: #d32f2f; }
        50% { border-right-color: transparent; }
        100% { border-right-color: #d32f2f; }
    }

    /* Custom cursor for entire container */
    .gradio-container {
        background-color: #e8f5e9 !important;
        font-family: Georgia, 'Times New Roman', serif !important;
        cursor: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20"><polygon points="0,0 0,16 4,12 8,20 10,19 6,11 12,11" fill="%23d32f2f" stroke="%237b1fa2" stroke-width="1"/></svg>'), auto !important;
    }

    /* Custom cursor for clickable elements */
    button, a, input, textarea, .gr-button {
        cursor: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20"><rect x="0" y="0" width="20" height="20" fill="%23ff6f00" stroke="%234a148c" stroke-width="2"/><rect x="4" y="4" width="12" height="12" fill="%237b1fa2"/></svg>') 10 10, pointer !important;
    }

    /* Blinking cursor for inputs */
    input:focus, textarea:focus {
        animation: cursor-blink 1s infinite;
        border-right: 4px solid #d32f2f !important;
        padding-right: 8px !important;
    }
    h1 {
        background: linear-gradient(135deg, #d32f2f, #ff6f00, #7b1fa2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 300;
        font-size: 3rem;
        letter-spacing: -2px;
        margin-bottom: 1rem;
        text-transform: uppercase;
        font-family: Georgia, serif;
    }
    h2 {
        color: #1a237e;
        font-weight: 300;
        border-bottom: 4px solid #d32f2f;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-family: Georgia, serif;
    }
    .gr-button-primary {
        background: #d32f2f !important;
        border: 3px solid #b71c1c !important;
        font-weight: 300 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        box-shadow: 5px 5px 0px #7b1fa2 !important;
        border-radius: 0 !important;
        font-family: Georgia, serif !important;
    }
    .gr-button-primary:hover {
        background: #c62828 !important;
        transform: translate(-2px, -2px);
        box-shadow: 7px 7px 0px #7b1fa2 !important;
    }
    .gr-button-secondary {
        background-color: #7b1fa2 !important;
        border: 3px solid #4a148c !important;
        box-shadow: 5px 5px 0px #ff6f00 !important;
        border-radius: 0 !important;
        text-transform: uppercase !important;
        font-family: Georgia, serif !important;
    }
    .gr-button-secondary:hover {
        background-color: #6a1b9a !important;
        transform: translate(-2px, -2px);
        box-shadow: 7px 7px 0px #ff6f00 !important;
    }
    .gr-box {
        border-radius: 0 !important;
        border: 3px solid #00897b !important;
        background-color: #f3e5f5 !important;
        box-shadow: 6px 6px 0px #4a148c !important;
    }
    input, textarea {
        border-radius: 0 !important;
        border-width: 3px !important;
        font-family: 'Courier New', monospace !important;
        font-weight: 300 !important;
    }
    .gr-tab-nav {
        border-radius: 0 !important;
        border: 3px solid #00897b !important;
        background: #bbdefb !important;
    }
    .gr-tab-nav button {
        border-radius: 0 !important;
        font-family: Georgia, serif !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-weight: 300 !important;
    }
    .gr-tab-nav button.selected {
        background: #d32f2f !important;
        color: white !important;
        border: 3px solid #b71c1c !important;
    }
    .gradio-container label {
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-weight: 300 !important;
        font-family: Georgia, serif !important;
    }

    /* Blinking text for important info */
    .blink {
        animation: blink 1.5s infinite;
        color: #d32f2f !important;
        font-weight: bold !important;
    }

    /* Status output styling with potential blinking elements */
    .gr-textbox[data-testid="textbox"] pre {
        font-family: 'Courier New', monospace !important;
    }

    /* Make success checkmarks blink */
    .gr-textbox[data-testid="textbox"] pre:has(✓) {
        color: #00897b !important;
    }
""",
) as history_importer:
    with gr.Column():
        gr.Markdown("## 🧠 Kairix Memory Architecture Pipeline")
        gr.Markdown(
            "Advanced memory synthesis and management system", elem_classes=["subtitle"]
        )

    with gr.Tabs() as tabs:
        # Tab 1: Manual Memory Entry
        with gr.Tab("📝 Manual Memory Entry", id=0):
            gr.Markdown("### Direct Memory Shard Creation")
            gr.Markdown(
                "Create memory shards directly from text input without chunking."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    manual_agent_name = gr.Textbox(
                        label="Agent Name",
                        placeholder="Enter agent name (e.g., ResearchAssistant)",
                        info="The agent that will own this memory",
                    )
                    manual_source_label = gr.Textbox(
                        label="Source Label",
                        placeholder="Enter a descriptive label",
                        info="A brief description of this memory's origin",
                    )
                    manual_text = gr.Textbox(
                        label="Memory Content",
                        placeholder="Enter the text content to embed and store as a memory shard...",
                        lines=10,
                        info="This text will be embedded and stored directly as a memory shard",
                    )
                    manual_submit_btn = gr.Button(
                        "🚀 Create Memory Shard", variant="primary", size="lg"
                    )

                with gr.Column(scale=1):
                    manual_output = gr.HTML(
                        label="Creation Status",
                        value="<pre style='font-family: Courier New, monospace; color: #1a237e;'>Results will appear here...</pre>",
                    )

        # Tab 2: ChatGPT Import
        with gr.Tab("📥 ChatGPT Import", id=1):
            gr.Markdown("### Import ChatGPT Conversations")
            gr.Markdown("Process exported ChatGPT conversations into source documents.")

            with gr.Row():
                with gr.Column(scale=1):
                    import_agent_name = gr.Textbox(
                        label="Agent Name",
                        placeholder="Enter agent name",
                    )
                    file = gr.File(
                        label="Select ChatGPT Export File",
                    )
                    import_btn = gr.Button(
                        "📤 Import Conversations",
                        variant="primary",
                        size="lg",
                    )

                with gr.Column(scale=1):
                    file_import_output = gr.Textbox(
                        label="Import Results",
                        placeholder="Import status will appear here...",
                        lines=16,
                        interactive=False,
                    )

        # Tab 3: Memory Synthesis
        with gr.Tab("⚡ Memory Synthesis", id=2):
            gr.Markdown("### Synthesize Memories from Documents")
            gr.Markdown(
                "Process source documents into chunked, summarized memory shards."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    synth_agent_name = gr.Textbox(
                        label="Agent Name",
                        placeholder="Enter agent name",
                        info="The agent that will own these memories",
                    )
                    run_id = gr.Textbox(
                        label="Run ID",
                        placeholder="Enter a unique run identifier",
                        info="Unique identifier for this synthesis run",
                    )
                    synth_btn = gr.Button(
                        "⚙️ Synthesize Memories", variant="primary", size="lg"
                    )

                with gr.Column(scale=1):
                    summarizer_output = gr.Textbox(
                        label="Synthesis Results",
                        placeholder="Synthesis progress will appear here...",
                        lines=10,
                        interactive=False,
                    )

        # Tab 4: Direct Inference
        with gr.Tab("🤖 Direct Inference", id=3):
            gr.Markdown("### Direct Inference Query")
            gr.Markdown(
                "Submit queries directly to the configured inference provider using the same parameters as the synthesizer."
            )

            with gr.Row():
                with gr.Column(scale=1):
                    inference_input = gr.Textbox(
                        label="Query Input",
                        placeholder="Enter your query or text to process...",
                        lines=10,
                        info="This text will be sent to the inference provider",
                    )
                    inference_submit_btn = gr.Button(
                        "🚀 Submit Query", variant="primary", size="lg"
                    )

                with gr.Column(scale=1):
                    inference_output = gr.HTML(
                        label="Inference Result",
                        value="<pre style='font-family: Courier New, monospace; color: #1a237e;'>Results will appear here...</pre>",
                    )

        # Tab 5: Cron Job Monitoring
        with gr.Tab("📊 Cron Monitoring", id=4):
            gr.Markdown("### Conversation Ingestion Jobs")
            gr.Markdown(
                "Monitor and manage the automated conversation ingestion cron jobs."
            )

            with gr.Row():
                with gr.Column(scale=3):
                    job_history = gr.HTML(
                        label="Job History",
                        value=get_cron_job_history(),
                    )
                    refresh_btn = gr.Button(
                        "🔄 Refresh History", variant="secondary"
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### Manual Controls")
                    manual_run_btn = gr.Button(
                        "▶️ Run Job Now", variant="primary", size="lg"
                    )
                    job_output = gr.HTML(
                        label="Job Output",
                        value="<pre style='font-family: Courier New, monospace; color: #666;'>Click 'Run Job Now' to start...</pre>",
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
        inputs=[import_agent_name, file],
        outputs=[file_import_output],
    )

    # Wire up the synthesis functionality
    synth_btn.click(
        fn=synth_memories,
        inputs=[synth_agent_name, run_id],
        outputs=[summarizer_output],
    )

    # Wire up the direct inference functionality
    inference_submit_btn.click(
        fn=direct_inference_query,
        inputs=[inference_input],
        outputs=[inference_output],
    )

    # Wire up the cron monitoring functionality
    refresh_btn.click(
        fn=get_cron_job_history,
        inputs=[],
        outputs=[job_history],
    )
    
    manual_run_btn.click(
        fn=run_cron_job_manually,
        inputs=[],
        outputs=[job_output],
    )


def main():
    # Initialize the processing environment before launching UI
    initialize_processing()
    history_importer.launch(server_name="0.0.0.0")


if __name__ == "__main__":
    main()
