import gradio as gr

from kairix_offline.processing import (
    initialize_processing,
    load_sources_from_gpt_export,
    synth_memories,
)

file_import_output = gr.Textbox(
    label="Results",
    placeholder="This is where the import output will be displayed.",
    lines=20,
)
summarizer_output = gr.Textbox(
    label="Results",
    placeholder="This is where the summarizer output will be displayed.",
    lines=20,
)
with gr.Blocks(theme="shivi/calm_seafoam") as history_importer:
    gr.Markdown("# Kairix Memory Architecture Pipline")
    with gr.Row():
        gr.Markdown("### ChatGPT History Importer")
    with gr.Row():
        with gr.Column():
            file = gr.FileExplorer(
                label="Select ChatGPT export file",
                root_dir="../data",
                value="test-convos.json",
                max_height=400,
            )
            gr.Button("Start").click(
                fn=load_sources_from_gpt_export,
                inputs=[file],
                outputs=[file_import_output],
            )
        with gr.Column():
            gr.Markdown("#### Processing Result")
            file_import_output.render()

    with gr.Row():
        gr.Markdown("### Chunked Summary Memory Synth")
    with gr.Row():
        with gr.Column():
            agent_name = gr.Textbox("Agent Name")
            run_id = gr.Textbox("Run ID")
            gr.Button("Start").click(
                fn=synth_memories,
                inputs=[agent_name, run_id],
                outputs=summarizer_output,
            )
        with gr.Column():
            summarizer_output.render()


def main():
    # Initialize the processing environment before launching UI
    initialize_processing()
    history_importer.launch(server_name="0.0.0.0")


if __name__ == "__main__":
    main()
