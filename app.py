import gradio as gr
from rag_assistant import ClassicalJapaneseAssistant
from vector_store import JapaneseVectorStore
from ocr_pipeline import JapaneseOCR
from database_manager import DatabaseManager
import json
import os
import glob

# Initialize components
vector_store = JapaneseVectorStore()
assistant = ClassicalJapaneseAssistant(vector_store)
ocr = JapaneseOCR()
db_manager = DatabaseManager()

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
    
    # Return in the correct format for Gradio Chatbot messages format
    history = history or []
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
    return history

def add_note_function(note_text, topic):
    """Add personal note"""
    vector_store.add_note(note_text, topic)
    return "Note added successfully!"

def process_new_document(file):
    """Process uploaded PDF or image with progress updates"""
    import glob
    from pdf2image import convert_from_path
    
    if file.name.endswith('.pdf'):
        # First, get page count for accurate progress
        try:
            yield "📄 Analyzing PDF structure..."
            images = convert_from_path(file.name, 300)
            total_pages = len(images)
            yield f"📄 Found {total_pages} pages. Starting OCR processing..."
            
            # Process with page-by-page updates
            processed_chunks = []
            for i, image in enumerate(images, 1):
                progress_pct = int((i / total_pages) * 100)
                yield f"📄 Processing page {i}/{total_pages} ({progress_pct}%)..."
                
                # Save temporary image
                page_path = f"processed_docs/page_{i:04d}.png"
                image.save(page_path, 'PNG')
                
                # Extract text
                text_data = ocr.extract_text_with_coordinates(page_path)
                for item in text_data:
                    item['source_pdf'] = os.path.basename(file.name)
                    item['page_number'] = i
                processed_chunks.extend(text_data)
            
            yield f"✅ OCR complete! Processed {len(processed_chunks):,} text chunks from {total_pages} pages"
            
        except Exception as e:
            # Fallback to original method
            yield f"📄 Processing PDF (using fallback method)..."
            processed_chunks = ocr.process_pdf(file.name)
            yield f"✅ OCR complete! Processing {len(processed_chunks):,} text chunks..."
        
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
        yield "🖼️ Processing image with OCR..."
        text_data = ocr.extract_text_with_coordinates(file.name)
        chunks = vector_store.chunk_text(text_data)
        yield f"✅ OCR complete! Processing {len(chunks):,} text chunks..."
    
    # Add to vector store in batches to handle large documents
    batch_size = 5000
    total_chunks = len(chunks)
    
    if total_chunks > batch_size:
        total_batches = (total_chunks + batch_size - 1) // batch_size
        yield f"💾 Adding {total_chunks:,} chunks to vector database in {total_batches} batches..."
        
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i+batch_size]
            batch_num = i // batch_size + 1
            progress_pct = int((batch_num / total_batches) * 100)
            
            yield f"💾 Adding batch {batch_num}/{total_batches} ({progress_pct}%): chunks {i+1:,}-{min(i+batch_size, total_chunks):,}..."
            vector_store.add_documents(batch)
    else:
        yield f"💾 Adding {total_chunks:,} chunks to vector database..."
        vector_store.add_documents(chunks)
    
    # Clean up PNG files automatically
    yield "🧹 Cleaning up temporary image files..."
    png_files = glob.glob("processed_docs/*.png")
    if png_files:
        for png_file in png_files:
            try:
                os.remove(png_file)
            except:
                pass  # Ignore errors
        yield f"🧹 Removed {len(png_files)} temporary PNG files"
    
    # Final success message
    final_count = vector_store.collection.count()
    return f"✅ Successfully processed and added {total_chunks:,} text chunks!\n📚 Total documents in database: {final_count:,}"

def search_examples(grammar_point):
    """Search for examples of specific grammar"""
    if not grammar_point.strip():
        return "Please enter a grammar point to search for."
    
    # Use grammar-focused prompt for this tab
    original_prompt = assistant.prompt_template
    grammar_prompt = getattr(assistant, 'grammar_prompt_path', 'prompts/grammar_focused.md')
    
    if os.path.exists(grammar_prompt):
        assistant.prompt_template = assistant.load_prompt_template(grammar_prompt)
    
    result = assistant.explain_grammar(grammar_point)
    
    # Restore original prompt
    assistant.prompt_template = original_prompt
    return result['answer']

# Database management functions
def get_database_stats():
    """Get current database statistics"""
    stats = db_manager.get_textbook_stats()
    if 'error' in stats:
        return f"❌ Error: {stats['error']}", ""
    
    # Format textbook list
    textbook_list = []
    for source, count in stats['textbooks'].items():
        textbook_list.append(f"📚 **{source}**: {count:,} chunks")
    
    textbook_info = "\n".join(textbook_list)
    
    summary = f"""## Database Overview
**Total Documents**: {stats['total_documents']:,} chunks
**Textbooks**: {len(stats['textbooks'])} books
**Duplicates Found**: {stats['duplicates']:,} entries need cleanup

### Textbooks in Database:
{textbook_info}
    """
    
    # Create dropdown options for deletion
    textbook_options = list(stats['textbooks'].keys())
    return summary, textbook_options

def delete_textbook_func(textbook_name, confirm_text):
    """Delete a textbook from the database"""
    if not textbook_name:
        return "Please select a textbook to delete."
    
    if confirm_text != f"DELETE {textbook_name}":
        return f"❌ Please type exactly: DELETE {textbook_name}"
    
    result = db_manager.delete_textbook(textbook_name)
    if result['success']:
        return f"✅ {result['message']}"
    else:
        return f"❌ {result['message']}"

def clean_duplicates_func():
    """Clean up duplicate entries"""
    result = db_manager.clean_duplicates()
    if result['success']:
        return f"✅ {result['message']}"
    else:
        return f"❌ {result['message']}"

# Create Gradio interface
with gr.Blocks(title="Classical Japanese Learning Assistant", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 📚 Classical Japanese Learning Assistant")
    gr.Markdown("Powered by local AI with your textbook knowledge")
    
    with gr.Tab("Chat"):
        chatbot = gr.Chatbot(height=500, elem_id="main-chatbot", show_copy_button=True, type="messages")
        msg = gr.Textbox(
            label="Ask a question",
            placeholder="E.g., 'Explain the べし auxiliary verb' or 'What are the uses of particle ぞ?'",
            elem_id="chat-input"
        )
        clear = gr.Button("Clear", variant="secondary")
        
        msg.submit(chat_function, [msg, chatbot], [chatbot], show_progress="minimal").then(
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
        search_btn = gr.Button("Search & Explain", variant="primary")
        
        with gr.Row():
            with gr.Column():
                grammar_status = gr.Textbox(
                    label="Status", 
                    value="Ready to search", 
                    interactive=False,
                    max_lines=1
                )
        
        grammar_output = gr.Markdown(label="Grammar Explanation")
        
        def search_with_feedback(grammar_point):
            if not grammar_point.strip():
                return "Please enter a grammar point to search for.", "Ready to search"
            
            # Show that we're starting the search
            import time
            
            # Update status immediately
            yield "Searching vector database...", "🔍 Searching database..."
            time.sleep(0.1)  # Brief pause for UI update
            
            # Update status for AI processing
            yield "Searching vector database...", "🧠 Analyzing with AI model..."
            
            # Perform the actual search
            result = search_examples(grammar_point)
            
            # Return final result
            yield result, f"✅ Found explanation for '{grammar_point}'"
        
        search_btn.click(
            search_with_feedback, 
            inputs=[grammar_input], 
            outputs=[grammar_output, grammar_status],
            show_progress="minimal"
        )
        
        # Also allow Enter key to trigger search
        grammar_input.submit(
            search_with_feedback, 
            inputs=[grammar_input], 
            outputs=[grammar_output, grammar_status],
            show_progress="minimal"
        )
    
    with gr.Tab("Add Documents"):
        file_input = gr.File(
            label="Upload PDF or Image",
            file_types=[".pdf", ".jpg", ".png"]
        )
        process_btn = gr.Button("Process Document")
        process_output = gr.Textbox(label="Processing Status")
        
        process_btn.click(process_new_document, file_input, process_output)
    
    with gr.Tab("Database"):
        gr.Markdown("### 🗄️ Database Management")
        gr.Markdown("View, manage, and clean your textbook database")
        
        # Statistics section
        with gr.Row():
            with gr.Column():
                db_stats = gr.Markdown("Click 'Refresh Stats' to view database information")
                refresh_stats_btn = gr.Button("🔄 Refresh Stats", variant="primary")
        
        # Duplicate cleanup section
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 🧹 Clean Duplicates")
                gr.Markdown("Remove duplicate page entries (keeps first occurrence)")
                clean_dups_btn = gr.Button("Clean Duplicates", variant="secondary")
                clean_status = gr.Textbox(label="Cleanup Status", interactive=False)
        
        # Delete textbook section  
        with gr.Row():
            with gr.Column():
                gr.Markdown("### ⚠️ Delete Textbook")
                gr.Markdown("**Warning**: This permanently removes all chunks from the selected textbook")
                
                textbook_dropdown = gr.Dropdown(
                    choices=[],
                    label="Select Textbook to Delete",
                    info="Choose which textbook to remove completely"
                )
                
                confirm_input = gr.Textbox(
                    label="Confirmation",
                    placeholder="Type 'DELETE filename.pdf' to confirm",
                    info="Type exactly: DELETE [textbook filename]"
                )
                
                delete_btn = gr.Button("🗑️ Delete Textbook", variant="stop")
                delete_status = gr.Textbox(label="Deletion Status", interactive=False)
        
        # Wire up the functions
        def refresh_stats():
            stats_text, textbook_options = get_database_stats()
            return stats_text, gr.update(choices=textbook_options)
        
        refresh_stats_btn.click(
            refresh_stats,
            outputs=[db_stats, textbook_dropdown]
        )
        
        clean_dups_btn.click(
            clean_duplicates_func,
            outputs=[clean_status]
        )
        
        delete_btn.click(
            delete_textbook_func,
            inputs=[textbook_dropdown, confirm_input],
            outputs=[delete_status]
        )
    
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

