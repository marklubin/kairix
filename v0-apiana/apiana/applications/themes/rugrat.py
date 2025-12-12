import gradio as gr

RugRat = gr.themes.Monochrome(
    primary_hue="indigo",
    secondary_hue="orange",
    neutral_hue="lime",
    text_size="lg",
    font=[
        gr.themes.GoogleFont("courier-new"),
        gr.themes.GoogleFont("courier-new"),
        gr.themes.GoogleFont("courier-new"),
        gr.themes.GoogleFont("courier-new"),
    ],
).set(
    background_fill_primary="*primary_100",
    background_fill_primary_dark="*neutral_300",
    background_fill_secondary="*secondary_50",
    background_fill_secondary_dark="*neutral_300",
    border_color_accent="*secondary_900",
    border_color_primary="*primary_500",
    border_color_primary_dark="*secondary_600",
    color_accent="*body_text_color",
    link_text_color="*neutral_600",
    prose_text_size="*text_lg",
    prose_text_weight="800",
    code_background_fill="*secondary_200",
)
