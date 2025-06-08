import gradio as gr

from kairix_offline.processing import (
    initialize_processing,
    load_sources_from_gpt_export,
    synth_memories,
)

theme = gr.themes.Citrus(
    primary_hue="orange",
    secondary_hue="lime",
    neutral_hue="cyan",
    text_size="lg",
    radius_size="lg",
).set(
    body_background_fill="*neutral_100",
    body_text_color="*neutral_950",
    body_text_color_dark="*neutral_950",
    body_text_color_subdued="*secondary_800",
    body_text_weight="600",
    background_fill_secondary="*primary_300",
    border_color_accent="*secondary_200",
    border_color_primary="*neutral_500",
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
with gr.Blocks(theme=theme) as history_importer:
    gr.Markdown("# Kairix Memory Architecture Pipline")
    with gr.Row():
        gr.Markdown("### ChatGPT History Importer")
    with gr.Row():
        with gr.Column(min_width=400):
            file = gr.FileExplorer(
                label="Select ChatGPT export file",
                root_dir="../",
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
        with gr.Column(min_width=400):
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
