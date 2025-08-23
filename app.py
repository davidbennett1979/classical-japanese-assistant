import gradio as gr
from rag_assistant import ClassicalJapaneseAssistant
from vector_store import JapaneseVectorStore
from ocr_pipeline import JapaneseOCR
import json
import os
import glob

# Initialize components
vector_store = JapaneseVectorStore()
assistant = ClassicalJapaneseAssistant(vector_store)
ocr = JapaneseOCR()

# Load available prompts dynamically
def get_available_prompts():
    """Dynamically load all .md files from prompts folder"""
    prompt_files = glob.glob("prompts/*.md")
    return sorted(prompt_files) if prompt_files else ["prompts/classical_japanese_tutor.md"]

def chat_function(message, history):
    """Main chat interface"""
    result = assistant.query(message)
    
    # Format response with citations
    response = result['answer'] + "\n\n**Sources:**\n"
    for i, source in enumerate(result['sources']):
        response += f"- [{i+1}] {source['source']}, Page {source['page']}\n"
    
    # Return in the correct format for Gradio Chatbot (append to history)
    history = history or []
    history.append((message, response))
    return history

def add_note_function(note_text, topic):
    """Add personal note"""
    vector_store.add_note(note_text, topic)
    return "Note added successfully!"

def process_new_document(file):
    """Process uploaded PDF or image"""
    if file.name.endswith('.pdf'):
        # PDF processing returns pre-chunked data
        processed_chunks = ocr.process_pdf(file.name)
        
        # Convert to vector store format
        chunks = []
        for chunk in processed_chunks:
            chunks.append({
                'text': chunk.get('text', ''),
                'metadata': {
                    'page': chunk.get('page_number', 0),
                    'source': chunk.get('source_pdf', 'unknown'),
                    'type': chunk.get('type', 'text')
                }
            })
    else:
        # Single image processing - needs chunking
        text_data = ocr.extract_text_with_coordinates(file.name)
        chunks = vector_store.chunk_text(text_data)
    
    # Add to vector store in batches to handle large documents
    batch_size = 5000
    total_chunks = len(chunks)
    
    for i in range(0, total_chunks, batch_size):
        batch = chunks[i:i+batch_size]
        vector_store.add_documents(batch)
    
    return f"Processed and added {total_chunks:,} text chunks to database"

def search_examples(grammar_point):
    """Search for examples of specific grammar"""
    # Use grammar-focused prompt for this tab
    original_prompt = assistant.prompt_template
    grammar_prompt = getattr(assistant, 'grammar_prompt_path', 'prompts/grammar_focused.md')
    
    if os.path.exists(grammar_prompt):
        assistant.prompt_template = assistant.load_prompt_template(grammar_prompt)
    
    result = assistant.explain_grammar(grammar_point)
    
    # Restore original prompt
    assistant.prompt_template = original_prompt
    return result['answer']

# Create Gradio interface
with gr.Blocks(title="Classical Japanese Learning Assistant") as app:
    gr.Markdown("# 📚 Classical Japanese Learning Assistant")
    gr.Markdown("Powered by local AI with your textbook knowledge")
    
    with gr.Tab("Chat"):
        chatbot = gr.Chatbot(height=500)
        msg = gr.Textbox(
            label="Ask a question",
            placeholder="E.g., 'Explain the べし auxiliary verb' or 'What are the uses of particle ぞ?'"
        )
        clear = gr.Button("Clear")
        
        msg.submit(chat_function, [msg, chatbot], [chatbot]).then(
            lambda: "", None, msg  # Clear the input after sending
        )
        clear.click(lambda: [], None, chatbot, queue=False)
    
    with gr.Tab("Add Notes"):
        note_input = gr.Textbox(
            label="Note Content",
            lines=5,
            placeholder="Add your study notes here..."
        )
        topic_input = gr.Textbox(
            label="Topic/Category",
            placeholder="E.g., 'particles', 'verb conjugation', 'keigo'"
        )
        add_btn = gr.Button("Add Note")
        note_output = gr.Textbox(label="Status")
        
        add_btn.click(add_note_function, [note_input, topic_input], note_output)
    
    with gr.Tab("Grammar Search"):
        grammar_input = gr.Textbox(
            label="Grammar Point",
            placeholder="Enter a grammar point (e.g., らむ, べし, なり)"
        )
        search_btn = gr.Button("Search & Explain")
        grammar_output = gr.Markdown()
        
        search_btn.click(search_examples, grammar_input, grammar_output)
    
    with gr.Tab("Add Documents"):
        file_input = gr.File(
            label="Upload PDF or Image",
            file_types=[".pdf", ".jpg", ".png"]
        )
        process_btn = gr.Button("Process Document")
        process_output = gr.Textbox(label="Processing Status")
        
        process_btn.click(process_new_document, file_input, process_output)
    
    with gr.Tab("Settings"):
        gr.Markdown("### Model Settings")
        
        # Get available models from Ollama
        def get_installed_models():
            try:
                import subprocess
                result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header
                    models = [line.split()[0] for line in lines if line]
                    return models if models else ["qwen2.5:72b"]
            except:
                return ["qwen2.5:72b"]
        
        installed_models = get_installed_models()
        suggested_models = [
            "qwen2.5:72b",
            "llama3.1:70b", 
            "llama3.1:70b-instruct",
            "deepseek-coder-v2:16b",
            "command-r:35b",
            "mixtral:8x7b"
        ]
        
        model_dropdown = gr.Dropdown(
            choices=installed_models,
            value=installed_models[0] if installed_models else "qwen2.5:72b",
            label="Select Model",
            info="Choose from installed models"
        )
        
        def switch_model(model_name):
            assistant.model_name = model_name
            return f"Switched to model: {model_name}"
        
        model_status = gr.Textbox(label="Model Status", interactive=False, value=f"Current: {assistant.model_name}")
        model_dropdown.change(switch_model, model_dropdown, model_status)
        
        gr.Markdown("""#### 📦 Recommended Models for Your System (192GB RAM):
        - **qwen2.5:72b** (47GB) - Current, excellent for Japanese
        - **llama3.1:70b** (40GB) - Very strong general model
        - **command-r:35b** (20GB) - Good for RAG tasks
        - **deepseek-coder-v2:16b** (9GB) - If analyzing code
        - **mixtral:8x7b** (26GB) - Fast, good quality
        
        To install: `ollama pull model_name`
        """)
        
        gr.Markdown("### Prompt Settings")
        gr.Markdown("Configure which prompts to use for each section:")
        
        with gr.Row():
            with gr.Column():
                chat_prompt_dropdown = gr.Dropdown(
                    choices=get_available_prompts(),
                    value="prompts/classical_japanese_tutor.md",
                    label="Chat Tab Prompt",
                    interactive=True
                )
                
            with gr.Column():
                grammar_prompt_dropdown = gr.Dropdown(
                    choices=get_available_prompts(),
                    value="prompts/grammar_focused.md" if "prompts/grammar_focused.md" in get_available_prompts() else get_available_prompts()[0],
                    label="Grammar Search Prompt",
                    interactive=True
                )
        
        refresh_prompts_btn = gr.Button("🔄 Refresh Prompt List")
        prompt_status = gr.Textbox(label="Status", interactive=False, value="Prompts loaded")
        
        def update_chat_prompt(prompt_file):
            assistant.prompt_template = assistant.load_prompt_template(prompt_file)
            return f"Chat prompt updated to: {os.path.basename(prompt_file)}"
        
        def update_grammar_prompt(prompt_file):
            # Store grammar prompt path for use in search_examples
            assistant.grammar_prompt_path = prompt_file
            return f"Grammar prompt updated to: {os.path.basename(prompt_file)}"
        
        def refresh_prompt_list():
            prompts = get_available_prompts()
            return (
                gr.update(choices=prompts),
                gr.update(choices=prompts),
                f"Found {len(prompts)} prompt files"
            )
        
        chat_prompt_dropdown.change(update_chat_prompt, chat_prompt_dropdown, prompt_status)
        grammar_prompt_dropdown.change(update_grammar_prompt, grammar_prompt_dropdown, prompt_status)
        refresh_prompts_btn.click(refresh_prompt_list, None, [chat_prompt_dropdown, grammar_prompt_dropdown, prompt_status])
        
        # Add model refresh button
        refresh_models_btn = gr.Button("🔄 Refresh Model List")
        
        def refresh_models():
            models = get_installed_models()
            return gr.update(choices=models), f"Found {len(models)} installed models"
        
        refresh_models_btn.click(refresh_models, None, [model_dropdown, model_status])
        
        gr.Markdown("### Database Info")
        stats_box = gr.Textbox(
            value="Click 'Refresh Stats' to update",
            label="Statistics",
            interactive=False
        )
        refresh_btn = gr.Button("Refresh Stats")
        
        def update_stats():
            count = vector_store.collection.count()
            return f"Documents in database: {count:,}"
        
        refresh_btn.click(update_stats, None, stats_box)

# Launch the app
if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)

