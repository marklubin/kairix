"""Reusable UI components for Kairix applications."""

from collections.abc import Callable
from typing import Any

import gradio as gr


def create_slideout_toolbar(
    model_options: list[str] = None,
    default_model: str = None,
    on_model_change: Callable[[str], Any] = None,
    additional_components: list[gr.components.Component] = None
) -> gr.Group:
    """
    Create a slide-out toolbar with model selection and expandable for other components.
    
    Args:
        model_options: List of available model names
        default_model: Default selected model
        on_model_change: Callback when model selection changes
        additional_components: Additional Gradio components to include in toolbar
        
    Returns:
        gr.Group containing the toolbar
    """
    
    # Default model options if none provided
    if model_options is None:
        model_options = [
            "gpt-4",
            "gpt-3.5-turbo", 
            "claude-3-opus",
            "claude-3-sonnet",
            "llama-3-70b",
            "mixtral-8x7b"
        ]
    
    if default_model is None:
        default_model = model_options[0]
    
    # Create the toolbar HTML/CSS
    toolbar_css = """
    <style>
    .toolbar-container {
        position: fixed;
        right: -300px;
        top: 50%;
        transform: translateY(-50%);
        width: 300px;
        background: rgba(30, 30, 30, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 12px 0 0 12px;
        box-shadow: -4px 0 20px rgba(0, 0, 0, 0.3);
        transition: right 0.3s ease-in-out;
        z-index: 1000;
        padding: 20px;
    }
    
    .toolbar-container:hover,
    .toolbar-container.active {
        right: 0;
    }
    
    .toolbar-tab {
        position: absolute;
        left: -40px;
        top: 50%;
        transform: translateY(-50%);
        width: 40px;
        height: 80px;
        background: rgba(30, 30, 30, 0.9);
        border-radius: 12px 0 0 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .toolbar-tab:hover {
        width: 50px;
        left: -50px;
        background: rgba(40, 40, 40, 0.95);
    }
    
    .toolbar-tab svg {
        width: 24px;
        height: 24px;
        fill: #888;
        transition: fill 0.3s ease;
    }
    
    .toolbar-tab:hover svg {
        fill: #fff;
    }
    
    .toolbar-content {
        color: #fff;
    }
    
    .toolbar-section {
        margin-bottom: 20px;
    }
    
    .toolbar-section h3 {
        font-size: 14px;
        color: #888;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .model-selector {
        background: rgba(50, 50, 50, 0.5);
        border: 1px solid rgba(100, 100, 100, 0.3);
        border-radius: 8px;
        padding: 10px;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .model-selector:hover {
        background: rgba(60, 60, 60, 0.7);
        border-color: rgba(150, 150, 150, 0.5);
    }
    
    .model-icon {
        width: 20px;
        height: 20px;
        opacity: 0.7;
    }
    </style>
    """
    
    toolbar_html = """
    <div class="toolbar-container" id="slideout-toolbar">
        <div class="toolbar-tab" onclick="document.getElementById('slideout-toolbar').classList.toggle('active')">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
        </div>
        <div class="toolbar-content">
            <div class="toolbar-section">
                <h3>Model Selection</h3>
                <div id="model-selector-container"></div>
            </div>
        </div>
    </div>
    """
    
    with gr.Group() as toolbar_group:
        # Add CSS and HTML
        gr.HTML(toolbar_css + toolbar_html)
        
        # Model dropdown (hidden, controlled by JavaScript)
        model_dropdown = gr.Dropdown(
            choices=model_options,
            value=default_model,
            label="Model",
            visible=False,
            elem_id="hidden-model-dropdown"
        )
        
        # JavaScript to connect the custom UI to Gradio components
        gr.HTML("""
        <script>
        (function() {
            // Wait for Gradio to initialize
            setTimeout(() => {
                const modelDropdown = document.querySelector('#hidden-model-dropdown input');
                const modelContainer = document.getElementById('model-selector-container');
                
                if (modelDropdown && modelContainer) {
                    // Create custom model selector
                    const selector = document.createElement('div');
                    selector.className = 'model-selector';
                    selector.innerHTML = `
                        <svg class="model-icon" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/>
                        </svg>
                        <span>${modelDropdown.value || 'Select Model'}</span>
                    `;
                    
                    selector.onclick = () => {
                        // Trigger Gradio dropdown
                        modelDropdown.click();
                        modelDropdown.focus();
                    };
                    
                    modelContainer.appendChild(selector);
                    
                    // Update selector when model changes
                    const observer = new MutationObserver(() => {
                        selector.querySelector('span').textContent = modelDropdown.value || 'Select Model';
                    });
                    
                    observer.observe(modelDropdown, {
                        attributes: true,
                        attributeFilter: ['value']
                    });
                }
            }, 1000);
        })();
        </script>
        """)
        
        # Handle model changes
        if on_model_change:
            model_dropdown.change(
                fn=on_model_change,
                inputs=[model_dropdown],
                outputs=[]
            )
        
        # Add any additional components
        if additional_components:
            with gr.Column(visible=False):  # Hidden container for additional components
                for component in additional_components:
                    component
    
    return toolbar_group, model_dropdown


# Example usage function
def demo_toolbar():
    """Demo app showing the toolbar in action."""
    
    with gr.Blocks(title="Toolbar Demo") as demo:
        gr.Markdown("# Slide-out Toolbar Demo")
        gr.Markdown("Hover over the right edge to reveal the toolbar")
        
        # State to track selected model
        current_model = gr.State("gpt-4")
        
        # Create toolbar
        def on_model_change(model):
            print(f"Model changed to: {model}")
            return f"Selected model: {model}"
        
        toolbar, model_selector = create_slideout_toolbar(
            on_model_change=on_model_change
        )
        
        # Main content area
        with gr.Row():
            with gr.Column():
                output = gr.Textbox(
                    label="Current Selection",
                    value="Selected model: gpt-4",
                    interactive=False
                )
        
        # Connect model changes to output
        model_selector.change(
            fn=lambda m: f"Selected model: {m}",
            inputs=[model_selector],
            outputs=[output]
        )
    
    return demo


if __name__ == "__main__":
    demo = demo_toolbar()
    demo.launch()