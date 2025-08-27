import gradio as gr
from rag_assistant import ClassicalJapaneseAssistant
from vector_store import JapaneseVectorStore
from ocr_pipeline import JapaneseOCR
from database_manager import DatabaseManager
import os
import glob
import threading

# Initialize components
vector_store = JapaneseVectorStore()
assistant = ClassicalJapaneseAssistant(vector_store)
ocr = JapaneseOCR()
db_manager = DatabaseManager()

# Global stop flag for cancellation
stop_generation = threading.Event()

# Load available prompts dynamically
def get_available_prompts():
    """Dynamically load all .md files from prompts folder"""
    prompt_files = glob.glob("prompts/*.md")
    return sorted(prompt_files) if prompt_files else ["prompts/classical_japanese_tutor.md"]

def chat_function(message, history, show_thinking_enabled=True):
    """Main chat interface with streaming support - returns multiple outputs for different UI components"""
    global stop_generation
    stop_generation.clear()  # Reset stop flag
    
    
    history = history or []
    history.append({"role": "user", "content": message})
    
    try:
        # Initialize components
        model_info = ""
        thinking_text = ""
        answer_text = ""
        sources_text = ""
        is_thinking_model = False
        
        # Stream the response
        for chunk in assistant.query_stream(message, stop_event=stop_generation):
            # Check if stop was requested
            if stop_generation.is_set():
                if thinking_text:
                    thinking_text += "\n\n*[Generation stopped by user]*"
                if answer_text:
                    answer_text += "\n\n*[Generation stopped by user]*"
                else:
                    answer_text = "*[Generation stopped by user]*"
                
                # For thinking models, add to history only at the end
                if is_thinking_model:
                    if len(history) > 1 and history[-1]["role"] == "assistant":
                        history[-1]["content"] = f"📝 Response stopped - using {assistant.model_name}"
                    else:
                        history.append({"role": "assistant", "content": f"📝 Response stopped - using {assistant.model_name}"})
                
                # DISABLED: This was conflicting with our simplified test
                # Return final states
                # yield (
                #     history,  # chatbot
                #     gr.update(value=f"🤖 **Model:** {assistant.model_name}", visible=is_thinking_model),  # model_display  
                #     gr.update(value=thinking_text if show_thinking_enabled else "Thinking hidden"),  # thinking_content
                #     gr.update(value=answer_text + sources_text, visible=is_thinking_model),  # answer_section
                #     gr.update(visible=is_thinking_model),  # thinking_accordion
                #     gr.update()   # show_thinking checkbox - always visible
                # )
                return
                
            if 'error' in chunk:
                history.append({"role": "assistant", "content": f"❌ Error: {chunk['error']}"})
                yield (
                    history,
                    gr.update(value="", visible=False),
                    gr.update(value=""),
                    gr.update(value="", visible=False),
                    gr.update(visible=False),
                    gr.update()  # show_thinking checkbox - always visible
                )
                return
            
            # Handle model info
            if chunk.get('type') == 'model_info':
                model_info = f"🤖 **Model:** {chunk['model_name']}"
                is_thinking_model = chunk.get('is_thinking_model', False)
                if is_thinking_model:
                    model_info += " 💭 *(Reasoning Model)*"
                continue
            
            # Update content based on chunk type
            if 'token' in chunk:
                # Route tokens based on model type and chunk type
                if is_thinking_model:
                    # THINKING MODELS: Route based on chunk type
                    if chunk.get('type') == 'thinking':
                        thinking_text += chunk['token']
                        # Update thinking accordion in real-time
                        thinking_display = thinking_text if show_thinking_enabled else f"*Thinking hidden ({len(thinking_text)} chars)*"
                        yield (
                            history,  # [0] chatbot - no change during thinking
                            gr.update(value=model_info, visible=True),  # [1] model_display
                            gr.update(value=thinking_display),  # [2] thinking_content - show thinking in accordion
                            gr.update(visible=True),  # [3] thinking_accordion - visible
                            gr.update()   # [4] show_thinking checkbox
                        )
                    elif chunk.get('type') == 'answer':
                        answer_text += chunk['token']
                        # Stream answer to chatbot in real-time
                        assistant_message = f"📝 **Response using {assistant.model_name}**\n\n{answer_text}"
                        if len(history) > 1 and history[-1]["role"] == "assistant":
                            history[-1]["content"] = assistant_message
                        else:
                            history.append({"role": "assistant", "content": assistant_message})
                        
                        # Update chatbot with streaming answer, keep thinking accordion visible
                        thinking_display = thinking_text if show_thinking_enabled else f"*Thinking hidden ({len(thinking_text)} chars)*"
                        yield (
                            history,  # [0] chatbot - gets streaming answer
                            gr.update(value=model_info, visible=True),  # [1] model_display
                            gr.update(value=thinking_display),  # [2] thinking_content - keep thinking content
                            gr.update(visible=bool(thinking_text)),  # [3] thinking_accordion - visible if thinking exists
                            gr.update()   # [4] show_thinking checkbox
                        )
                else:
                    # NON-THINKING MODELS: Stream everything as answer to chatbot
                    answer_text += chunk['token']
                    assistant_message = f"📝 **Response generated using {assistant.model_name}**\n\n{answer_text}"
                    if len(history) > 1 and history[-1]["role"] == "assistant":
                        history[-1]["content"] = assistant_message
                    else:
                        history.append({"role": "assistant", "content": assistant_message})
                    
                    # Stream to chatbot, hide thinking components
                    yield (
                        history,  # [0] chatbot - gets real-time streaming
                        gr.update(value="", visible=False),  # [1] model_display (hidden)
                        gr.update(value=""),  # [2] thinking_content (empty)
                        gr.update(visible=False),  # [3] thinking_accordion (hidden)
                        gr.update()   # [4] show_thinking checkbox
                    )
                
                # Add sources when done
                if chunk['done'] and not sources_text:
                    sources_text = "\n\n**Sources:**\n"
                    for i, source in enumerate(chunk['sources']):
                        source_text = source['metadata'].get('source', 'unknown')
                        page = source['metadata'].get('page', 'N/A')
                        sources_text += f"- [{i+1}] {source_text}, Page {page}\n"
                    
                    # For NON-THINKING models: update final message with sources
                    if not is_thinking_model:
                        assistant_message = f"📝 **Response generated using {assistant.model_name}**\n\n{answer_text}{sources_text}"
                        if len(history) > 1 and history[-1]["role"] == "assistant":
                            history[-1]["content"] = assistant_message
                        
                        # Final update with sources
                        yield (
                            history,  # [0] chatbot - gets final message with sources
                            gr.update(value="", visible=False),  # [1] model_display (hidden)
                            gr.update(value=""),  # [2] thinking_content (empty)
                            gr.update(visible=False),  # [3] thinking_accordion (hidden)
                            gr.update()   # [4] show_thinking checkbox
                        )
                
    except Exception as e:
        history.append({"role": "assistant", "content": f"❌ Error: {str(e)}"})
        # ERROR: Use new 5-component format
        yield (
            history,  # [0] chatbot
            gr.update(value="", visible=False),  # [1] model_display
            gr.update(value=""),  # [2] thinking_content
            gr.update(visible=False),  # [3] thinking_accordion
            gr.update()  # [4] show_thinking checkbox
        )

def chat_function_non_streaming(message, history):
    """Fallback non-streaming chat for compatibility"""
    try:
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
        
    except Exception as e:
        # Return error message in chat format
        history = history or []
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": f"❌ Error: {str(e)}\n\nPlease try again or check the model settings."})
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
            
        except Exception:
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
        return f"❌ Error: {stats['error']}", "", ""
    
    # Get PNG statistics
    png_info = db_manager.get_png_stats()
    png_summary = ""
    if png_info['count'] > 0:
        size_display = f"{png_info['size_gb']} GB" if png_info['size_gb'] >= 1 else f"{png_info['size_mb']} MB"
        png_summary = f"📁 **PNG Files**: {png_info['count']} files ({size_display} total)"
    else:
        png_summary = "📁 **PNG Files**: No PNG files found"
    
    # Format textbook list
    textbook_list = []
    for source, count in stats['textbooks'].items():
        textbook_list.append(f"📚 **{source}**: {count:,} chunks")
    
    textbook_info = "\n".join(textbook_list)
    
    summary = f"""## Database Overview
**Total Documents**: {stats['total_documents']:,} chunks
**Textbooks**: {len(stats['textbooks'])} books
**Duplicates Found**: {stats['duplicates']:,} entries need cleanup
{png_summary}

### Textbooks in Database:
{textbook_info}
    """
    
    # Create dropdown options for deletion
    textbook_options = list(stats['textbooks'].keys())
    return summary, textbook_options, png_summary

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
        # Model and thinking display info
        model_display = gr.Markdown("", visible=False)
        
        # FIXED: Move thinking_content INSIDE accordion where it belongs
        thinking_accordion = gr.Accordion(
            "🧠 Thinking Process", 
            open=True, 
            visible=True  # TEMPORARY: Always visible for testing
        )
        with thinking_accordion:
            thinking_content = gr.Markdown("", elem_id="thinking-content")
        
        # Answer section for thinking models - COMPLETELY DISABLED for testing
        # answer_section = gr.Markdown("", visible=False, label="Answer")
        
        # Regular chatbot for non-thinking models and conversation history
        chatbot = gr.Chatbot(
            height=400, 
            elem_id="main-chatbot", 
            show_copy_button=True, 
            type="messages",
            label="Conversation"
        )
        
        msg = gr.Textbox(
            label="Ask a question",
            placeholder="E.g., 'Explain the べし auxiliary verb' or 'What are the uses of particle ぞ?'",
            elem_id="chat-input"
        )
        with gr.Row():
            submit_btn = gr.Button("Send", variant="primary")
            stop_btn = gr.Button("Stop", variant="stop", visible=False)
            clear_btn = gr.Button("Clear", variant="secondary")
        
        with gr.Row():
            with gr.Column(scale=1):
                show_thinking = gr.Checkbox(
                    label="Show Thinking Process", 
                    value=True,
                    info="Display reasoning steps for thinking models",
                    visible=True  # Always visible
                )
        
        # Handle streaming with proper UI updates
        # FIXED: Match your targeted behavior - no answer_section
        outputs = [chatbot, model_display, thinking_content, thinking_accordion, show_thinking]
        
        submit_event = msg.submit(
            chat_function, 
            [msg, chatbot, show_thinking], 
            outputs,
            show_progress="minimal"
        ).then(
            lambda: gr.update(visible=False), None, stop_btn
        ).then(
            lambda: "", None, msg  # Clear input after sending
        )
        
        click_event = submit_btn.click(
            chat_function,
            [msg, chatbot, show_thinking],
            outputs,
            show_progress="minimal"
        ).then(
            lambda: gr.update(visible=False), None, stop_btn
        ).then(
            lambda: "", None, msg  # Clear input after sending
        )
        
        # Show stop button during generation
        msg.submit(lambda: gr.update(visible=True), None, stop_btn, queue=False)
        submit_btn.click(lambda: gr.update(visible=True), None, stop_btn, queue=False)
        
        # Stop button sets the stop flag and hides itself
        def stop_generation_handler():
            global stop_generation
            stop_generation.set()  # Signal to stop generation
            return gr.update(visible=False)
        
        stop_btn.click(
            stop_generation_handler,
            None,
            stop_btn,
            queue=False
        )
        
        # Clear function for all components
        def clear_all():
            return (
                [],  # chatbot
                gr.update(value="", visible=False),  # model_display
                gr.update(value=""),  # thinking_content
                gr.update(value="", visible=False),  # answer_section
                gr.update(visible=False),  # thinking_accordion
                gr.update()   # show_thinking checkbox - always visible, don't change
            )
        
        clear_btn.click(clear_all, None, outputs, queue=False)
    
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
        
        # PNG cleanup section
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 📁 Clean PNG Files")
                gr.Markdown("**⚠️ PNG files are used for OCR processing. Delete only after confirming database is working correctly.**")
                gr.Markdown("This will delete ALL PNG files in processed_docs folder. JSON files will be preserved for recovery.")
                
                png_stats = gr.Markdown("Click 'Refresh Stats' above to view PNG file information")
                
                png_confirm_input = gr.Textbox(
                    label="Confirmation Required",
                    placeholder="Type 'DELETE PNGs' to confirm",
                    info="Type exactly: DELETE PNGs"
                )
                
                delete_pngs_btn = gr.Button("🗑️ Delete PNG Files", variant="stop")
                png_delete_status = gr.Textbox(label="PNG Deletion Status", interactive=False)
        
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
            stats_text, textbook_options, png_info = get_database_stats()
            return stats_text, gr.update(choices=textbook_options), png_info
        
        def delete_png_files_func(confirm_text):
            """Delete PNG files after confirmation"""
            if confirm_text != "DELETE PNGs":
                return "❌ Please type 'DELETE PNGs' exactly to confirm deletion."
            
            result = db_manager.delete_png_files()
            if result['success']:
                return f"✅ {result['message']}"
            else:
                return f"❌ {result['message']}"
        
        refresh_stats_btn.click(
            refresh_stats,
            outputs=[db_stats, textbook_dropdown, png_stats]
        )
        
        delete_pngs_btn.click(
            delete_png_files_func,
            inputs=[png_confirm_input],
            outputs=[png_delete_status]
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
            """Get list of installed Ollama models"""
            try:
                import subprocess
                result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:  # Skip header line
                        models = []
                        for line in lines[1:]:
                            if line.strip():
                                # Model name is the first column (before the first space)
                                parts = line.strip().split()
                                if parts:
                                    models.append(parts[0])
                        return models if models else []
                return []
            except Exception as e:
                print(f"Error getting models: {e}")
                return []
        
        # Get installed models on startup
        installed_models = get_installed_models()
        
        # Set initial model - use current model or first available
        if not installed_models:
            print("Warning: No Ollama models found. Please install at least one model.")
            current_model = assistant.model_name
        else:
            # Check if current model is in the list, otherwise use first available
            if assistant.model_name in installed_models:
                current_model = assistant.model_name
            else:
                current_model = installed_models[0]
                assistant.model_name = current_model  # Update assistant with first available model
                print(f"Switched to available model: {current_model}")
        
        model_dropdown = gr.Dropdown(
            choices=installed_models,
            value=current_model if installed_models else None,
            label="Select Model",
            info="Choose from installed Ollama models"
        )
        
        def switch_model(model_name):
            assistant.model_name = model_name
            return f"Switched to model: {model_name}"
        
        model_status = gr.Textbox(label="Model Status", interactive=False, value=f"Current: {assistant.model_name}")
        model_dropdown.change(switch_model, model_dropdown, model_status)
        
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
            """Refresh the list of available models"""
            models = get_installed_models()
            if not models:
                return gr.update(choices=[], value=None), "No models found. Please install Ollama models."
            
            # Keep current selection if it's still available
            current_value = assistant.model_name if assistant.model_name in models else models[0]
            return gr.update(choices=models, value=current_value), f"Found {len(models)} installed models: {', '.join(models)}"
        
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
    app.queue()  # Enable queuing for streaming
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)

