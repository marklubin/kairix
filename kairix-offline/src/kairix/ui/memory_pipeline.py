import gradio as gr

from kairix.ui.gpt_loader import load_from_file
from kairix.ui.summary_memory_synth import SummaryMemorySynth



file_import_output = gr.Textbox(
    label="Results", placeholder="This is where the import will be displayed.", lines=20
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
                value="test-convos.json",
                max_height=400,
            )
            gr.Button("Start").click(
                fn=load_from_file, inputs=[file], outputs=[file_import_output]
            )
        with gr.Column():
            gr.Markdown("#### Processing Result")
            file_import_output.render()

    with gr.Row():
        gr.Markdown("### Chunked Summary Memory Synth")
    with gr.Row():
        with gr.Column():
        with gr.Column():
            prompt = gr.FileExplorer(
                label="Select System Prompt File",
                value="./prompts",
            )
        with gr.Column():
            gr.Button("Start").click(
                fn= SummaryMemorySynth
                inputs=[
                    summarizer_model,
                    embedder_model,
                    prompt,
                    max_tokens,
                    temp,
                    chunk_size,
                    overlap,
                ],
                outputs=summarizer_output,
            )
        with gr.Column():
            summarizer_output.render()


def main():
    history_importer.launch(server_name='0.0.0.0')


if __name__ == "__main__":
    main()
