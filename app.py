import gradio as gr
from rag_assistant import ClassicalJapaneseAssistant
from vector_store import JapaneseVectorStore
from ocr_pipeline import JapaneseOCR
from database_manager import DatabaseManager
import os
import glob
import threading
import logging
import uuid
import time
from config import settings

# Initialize components
vector_store = JapaneseVectorStore()
assistant = ClassicalJapaneseAssistant(vector_store)
ocr = JapaneseOCR()
db_manager = DatabaseManager()

# Session-based stop events to prevent interference between users
session_stop_events = {}
session_last_used = {}
last_sources = []  # Stores last retrieved sources for Source Viewer

def _cleanup_expired_sessions():
    """Remove session events that haven't been used for a while."""
    ttl = max(1, int(getattr(settings, 'session_ttl_minutes', 60))) * 60
    now = time.time()
    expired = [sid for sid, ts in session_last_used.items() if now - ts > ttl]
    for sid in expired:
        session_stop_events.pop(sid, None)
        session_last_used.pop(sid, None)

# Load available prompts dynamically
def get_available_prompts():
    """Dynamically load all .md files from prompts folder"""
    prompt_files = glob.glob("prompts/*.md")
    return sorted(prompt_files) if prompt_files else ["prompts/classical_japanese_tutor.md"]

def chat_function(message, history, show_thinking_enabled=True, session_id=None):
    """Main chat interface with streaming support - returns multiple outputs for different UI components"""
    global last_sources
    # Create or get session-specific stop event
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    _cleanup_expired_sessions()
    if session_id not in session_stop_events:
        session_stop_events[session_id] = threading.Event()
    
    stop_event = session_stop_events[session_id]
    stop_event.clear()  # Reset stop flag
    session_last_used[session_id] = time.time()
    
    
    history = history or []
    history.append({"role": "user", "content": message})
    
    # Check if a model is selected
    if not assistant.model_name:
        history.append({"role": "assistant", "content": "❌ No model selected. Please select a model in the Settings tab first."})
        yield (
            history,
            gr.update(value="", visible=False),
            gr.update(value=""),
            gr.update(visible=False),
            gr.update()
        )
        return
    
    try:
        # Initialize components
        model_info = ""
        thinking_text = ""
        answer_text = ""
        sources_text = ""
        is_thinking_model = False
        
        # Stream the response
        for chunk in assistant.query_stream(message, stop_event=stop_event):
            session_last_used[session_id] = time.time()
            # Check if stop was requested
            if stop_event.is_set():
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
                # Show short markers for sources if available
                if 'sources' in chunk and chunk['sources']:
                    try:
                        pages = []
                        for i, s in enumerate(chunk['sources'][:5], 1):
                            pg = s.get('metadata', {}).get('page', 'N/A')
                            pages.append(f"[{i}:p{pg}]")
                        if pages:
                            model_info += " | Sources: " + " ".join(pages)
                        # Update global last_sources for viewer
                        last_sources = chunk['sources']
                    except Exception:
                        pass
                continue
            
            # Handle final chunk with sources (may not have token)
            if chunk.get('done') and not sources_text and 'sources' in chunk:
                sources_text = "\n\n**Sources:**\n"
                for i, source in enumerate(chunk['sources']):
                    source_text = source['metadata'].get('source', 'unknown')
                    page = source['metadata'].get('page', 'N/A')
                    sources_text += f"- [{i+1}] {source_text}, Page {page}\n"
                # Update last_sources at completion too
                try:
                    last_sources = chunk['sources']
                except Exception:
                    pass
                
                # Update final message with sources for both model types
                if is_thinking_model and answer_text:
                    # For thinking models, update the answer in chatbot with sources
                    assistant_message = f"📝 **Response using {assistant.model_name}**\n\n{answer_text}{sources_text}"
                    if len(history) > 1 and history[-1]["role"] == "assistant":
                        history[-1]["content"] = assistant_message
                    else:
                        history.append({"role": "assistant", "content": assistant_message})
                    
                    thinking_display = thinking_text if show_thinking_enabled else f"*Thinking hidden ({len(thinking_text)} chars)*"
                    yield (
                        history,
                        gr.update(value=model_info, visible=True),
                        gr.update(value=thinking_display),
                        gr.update(visible=bool(thinking_text)),
                        gr.update()
                    )
                elif not is_thinking_model:
                    # For non-thinking models, update with sources
                    assistant_message = f"📝 **Response generated using {assistant.model_name}**\n\n{answer_text}{sources_text}"
                    if len(history) > 1 and history[-1]["role"] == "assistant":
                        history[-1]["content"] = assistant_message
                    
                    yield (
                        history,
                        gr.update(value="", visible=False),
                        gr.update(value=""),
                        gr.update(visible=False),
                        gr.update()
                    )
            
            # Update content based on chunk type
            if 'token' in chunk:
                # Route tokens based on model type and chunk type
                if is_thinking_model:
                    # THINKING MODELS: Route based on chunk type
                    if chunk.get('type') == 'thinking':
                        thinking_text += chunk['token']
                        # Update thinking accordion in real-time
                        thinking_display = thinking_text if show_thinking_enabled else f"*Thinking hidden ({len(thinking_text)} chars)*"
                        thinking_visible = bool(thinking_text) and bool(show_thinking_enabled)
                        yield (
                            history,  # [0] chatbot - no change during thinking
                            gr.update(value=model_info, visible=True),  # [1] model_display
                            gr.update(value=thinking_display),  # [2] thinking_content - show thinking in accordion
                            gr.update(visible=thinking_visible),  # [3] thinking_accordion - visible
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
                        thinking_visible = bool(thinking_text) and bool(show_thinking_enabled)
                        yield (
                            history,  # [0] chatbot - gets streaming answer
                            gr.update(value=model_info, visible=True),  # [1] model_display
                            gr.update(value=thinking_display),  # [2] thinking_content - keep thinking content
                            gr.update(visible=thinking_visible),  # [3] thinking_accordion - visible if thinking exists and allowed
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
                        gr.update(value=model_info, visible=True),  # [1] model_display now used for sources too
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

def process_new_document(file, start_page=None, end_page=None, resume_from_json=True):
    """Process uploaded PDF or image with progress updates"""
    import glob
    from pdf2image import convert_from_path
    
    if file.name.endswith('.pdf'):
        # If resume requested and existing JSON found, import it directly
        json_path = os.path.join('processed_docs', os.path.basename(file.name) + '.json')
        if resume_from_json and os.path.exists(json_path):
            try:
                import json as _json
                yield f"📥 Found existing JSON. Importing {os.path.basename(json_path)}..."
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = _json.load(f)
                chunks = vector_store.chunk_text(data)
                yield f"💾 Adding {len(chunks):,} chunks to vector database..."
                vector_store.add_documents(chunks)
                final_count = vector_store.collection.count()
                return f"✅ Imported JSON successfully! Added {len(chunks):,} chunks. Total: {final_count:,}"
            except Exception as e:
                yield f"❌ Failed to import existing JSON: {e}. Falling back to OCR..."

        # First, get page count for accurate progress
        try:
            yield "📄 Analyzing PDF structure..."
            kwargs = {}
            if start_page:
                kwargs['first_page'] = int(start_page)
            if end_page:
                kwargs['last_page'] = int(end_page)
            images = convert_from_path(file.name, 300, **kwargs)
            total_pages = len(images)
            yield f"📄 Found {total_pages} pages. Starting OCR processing..."
            
            # Process with page-by-page updates
            processed_chunks = []
            failed_pages = []
            created_png_files = []  # Track files created by this job
            for i, image in enumerate(images, 1):
                progress_pct = int((i / total_pages) * 100)
                yield f"📄 Processing page {i}/{total_pages} ({progress_pct}%)..."
                
                try:
                    # Save temporary image
                    page_path = f"processed_docs/page_{i:04d}.png"
                    image.save(page_path, 'PNG')
                    created_png_files.append(page_path)  # Track this file
                    
                    # Extract text
                    text_data = ocr.extract_text_with_coordinates(page_path)
                    for item in text_data:
                        item['source_pdf'] = os.path.basename(file.name)
                        item['page_number'] = i
                    processed_chunks.extend(text_data)
                except Exception as page_error:
                    failed_pages.append(i)
                    logging.getLogger(__name__).warning(f"Failed to process page {i}: {page_error}")
                    continue
            
            if failed_pages and len(failed_pages) < total_pages:
                yield f"⚠️ Warning: {len(failed_pages)} pages failed, but processed {total_pages - len(failed_pages)} successfully"
            
            yield f"✅ OCR complete! Processed {len(processed_chunks):,} text chunks from {total_pages - len(failed_pages)} pages"
            
        except Exception as pdf_error:
            # If entire PDF fails, try a different approach with lower DPI
            yield f"📄 PDF processing failed, trying with lower quality..."
            created_png_files = []  # Initialize in case first try failed
            try:
                images = convert_from_path(file.name, 150, **kwargs)  # Lower DPI
                processed_chunks = []
                for i, image in enumerate(images, 1):
                    page_path = f"processed_docs/page_{i:04d}.png"
                    image.save(page_path, 'PNG')
                    created_png_files.append(page_path)
                    text_data = ocr.extract_text_with_coordinates(page_path)
                    for item in text_data:
                        item['source_pdf'] = os.path.basename(file.name)
                        item['page_number'] = i
                    processed_chunks.extend(text_data)
                yield f"✅ OCR complete with fallback! Processed {len(processed_chunks):,} text chunks..."
            except Exception:
                yield f"❌ PDF processing failed completely. Error: {str(pdf_error)}"
                return
        
        # Save structured JSON for resume/import
        try:
            import json as _json
            os.makedirs('processed_docs', exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as f:
                _json.dump(processed_chunks, f, ensure_ascii=False)
            yield f"💾 Saved OCR JSON to {os.path.basename(json_path)}"
        except Exception as e:
            yield f"⚠️ Warning: Failed to save JSON: {e}"

        # Convert to vector store format using chunker for consistency
        chunks = vector_store.chunk_text(processed_chunks)
    else:
        # Single image processing - needs chunking
        yield "🖼️ Processing image with OCR..."
        text_data = ocr.extract_text_with_coordinates(file.name)
        
        # Add metadata to text_data before chunking
        for item in text_data:
            item['source_pdf'] = os.path.basename(file.name)
            item['page_number'] = 1
        
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
    
    # Clean up only PNG files created by this job
    if file.name.endswith('.pdf') and 'created_png_files' in locals() and created_png_files:
        yield "🧹 Cleaning up temporary image files..."
        removed_count = 0
        for png_file in created_png_files:
            try:
                os.remove(png_file)
                removed_count += 1
            except:
                pass  # Ignore errors
        yield f"🧹 Removed {removed_count} temporary PNG files from this job"
    
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
            open=False,
            visible=False
        )
        with thinking_accordion:
            thinking_content = gr.Markdown("", elem_id="thinking-content")

        # Sources viewer panel
        sources_accordion = gr.Accordion(
            "🔎 Sources (Last Response)",
            open=False,
            visible=True
        )
        with sources_accordion:
            with gr.Row():
                refresh_sources_btn = gr.Button("Refresh Sources", variant="secondary")
            sources_md = gr.Markdown("No sources yet. Ask a question to populate.")
        
        def format_sources_markdown():
            """Format the global last_sources into a readable Markdown list"""
            global last_sources
            if not last_sources:
                return "No sources yet. Ask a question to populate."
            lines = ["**Sources for last answer:**"]
            try:
                for i, s in enumerate(last_sources, 1):
                    meta = s.get('metadata', {})
                    src = meta.get('source', 'unknown')
                    page = meta.get('page', 'N/A')
                    snippet = (s.get('text') or '')
                    if len(snippet) > 120:
                        snippet = snippet[:117] + '...'
                    lines.append(f"- [{i}] {src} (p. {page})\n  \n  > {snippet}")
            except Exception as e:
                return f"⚠️ Could not render sources: {e}"
            return "\n".join(lines)

        refresh_sources_btn.click(lambda: format_sources_markdown(), None, sources_md)
        
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

        # Per-user session state for precise stop control
        session_id_state = gr.State(str(uuid.uuid4()))
        
        submit_event = msg.submit(
            chat_function, 
            [msg, chatbot, show_thinking, session_id_state], 
            outputs,
            show_progress="minimal"
        ).then(
            lambda: gr.update(visible=False), None, stop_btn
        ).then(
            lambda: "", None, msg  # Clear input after sending
        )
        
        click_event = submit_btn.click(
            chat_function,
            [msg, chatbot, show_thinking, session_id_state],
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
        def stop_generation_handler(current_session_id):
            # Stop only the current session
            stop_event = session_stop_events.get(current_session_id)
            if stop_event:
                stop_event.set()
            return gr.update(visible=False)
        
        stop_btn.click(
            stop_generation_handler,
            inputs=[session_id_state],
            outputs=[stop_btn],
            queue=False
        )
        
        # Clear function for all components
        def clear_all():
            # Reset to initial 5-component state (no answer_section used)
            return (
                [],  # chatbot
                gr.update(value="", visible=False),  # model_display
                gr.update(value=""),  # thinking_content
                gr.update(visible=False),  # thinking_accordion
                gr.update()   # show_thinking checkbox - leave as-is
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
        
        with gr.Row():
            search_btn = gr.Button("Search & Explain", variant="primary")
            stop_grammar_btn = gr.Button("Stop", variant="stop", visible=False)
        
        with gr.Row():
            with gr.Column():
                grammar_status = gr.Textbox(
                    label="Status", 
                    value="Ready to search", 
                    interactive=False,
                    max_lines=1
                )
        
        grammar_output = gr.Markdown(label="Grammar Explanation")
        
        # Session state for grammar search
        grammar_session_id = gr.State(str(uuid.uuid4()))
        
        def search_with_streaming(grammar_point, session_id):
            """Streaming version of grammar search"""
            if not grammar_point.strip():
                yield "Please enter a grammar point to search for.", "Ready to search", gr.update(visible=False)
                return
            
            # Create session-specific stop event
            stop_event = threading.Event()
            session_stop_events[session_id] = stop_event
            
            try:
                # Update status
                yield "", "🔍 Searching database...", gr.update(visible=True)
                
                # Use grammar-focused prompt for this tab
                original_prompt = assistant.prompt_template
                grammar_prompt = getattr(assistant, 'grammar_prompt_path', 'prompts/grammar_focused.md')
                
                if os.path.exists(grammar_prompt):
                    assistant.prompt_template = assistant.load_prompt_template(grammar_prompt)
                
                # Initialize response
                full_response = ""
                
                # Stream the grammar explanation
                for chunk in assistant.explain_grammar_stream(grammar_point, stop_event=stop_event):
                    if stop_event.is_set():
                        full_response += "\n\n*[Generation stopped by user]*"
                        yield full_response, "⏹️ Stopped", gr.update(visible=False)
                        break
                    
                    if chunk.get('token'):
                        full_response += chunk['token']
                        yield full_response, "🧠 Analyzing with AI model...", gr.update(visible=True)
                    
                    if chunk.get('done'):
                        # Add sources if available
                        if chunk.get('sources'):
                            full_response += "\n\n**Sources:**\n"
                            for src in chunk['sources']:
                                full_response += f"- {src.get('source', 'Unknown')} (Page {src.get('page', 'N/A')})\n"
                        
                        yield full_response, f"✅ Found explanation for '{grammar_point}'", gr.update(visible=False)
                
                # Restore original prompt
                assistant.prompt_template = original_prompt
                
            except Exception as e:
                yield f"❌ Error: {str(e)}", "Error occurred", gr.update(visible=False)
            finally:
                # Clean up session
                session_stop_events.pop(session_id, None)
        
        def stop_grammar_generation(session_id):
            """Stop grammar generation for this session"""
            if session_id in session_stop_events:
                session_stop_events[session_id].set()
            return gr.update(visible=False)
        
        search_event = search_btn.click(
            search_with_streaming, 
            inputs=[grammar_input, grammar_session_id], 
            outputs=[grammar_output, grammar_status, stop_grammar_btn],
            show_progress="minimal"
        )
        
        stop_grammar_btn.click(
            stop_grammar_generation,
            inputs=[grammar_session_id],
            outputs=[stop_grammar_btn],
            cancels=[search_event]
        )
        
        # Also allow Enter key to trigger search
        submit_event = grammar_input.submit(
            search_with_streaming, 
            inputs=[grammar_input, grammar_session_id], 
            outputs=[grammar_output, grammar_status, stop_grammar_btn],
            show_progress="minimal"
        )
        
        stop_grammar_btn.click(
            stop_grammar_generation,
            inputs=[grammar_session_id],
            outputs=[stop_grammar_btn],
            cancels=[submit_event]
        )
    
    with gr.Tab("Add Documents"):
        file_input = gr.File(
            label="Upload PDF or Image",
            file_types=[".pdf", ".jpg", ".png"]
        )
        with gr.Row():
            start_page_in = gr.Number(label="Start Page", value=None)
            end_page_in = gr.Number(label="End Page", value=None)
        resume_chk = gr.Checkbox(label="Import from existing JSON if present", value=True,
                                 info="If a matching JSON exists in processed_docs, skip OCR and import it")
        process_btn = gr.Button("Process Document")
        process_output = gr.Textbox(label="Processing Status")
        
        def process_new_document_wrapper(file, start_page, end_page, resume):
            # Wrapper to pass extra parameters
            for update in process_new_document(file, start_page=start_page, end_page=end_page, resume_from_json=resume):
                yield update
        
        process_btn.click(process_new_document_wrapper, [file_input, start_page_in, end_page_in, resume_chk], process_output)
    
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
        
        # Orphaned JSON import
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 📥 Import Orphaned JSON Files")
                gr.Markdown("Scan for processed JSON files not in the database and import them.")
                scan_json_btn = gr.Button("Scan for JSON Files")
                json_list = gr.CheckboxGroup(label="Found JSON Files (select to import)")
                import_selected_btn = gr.Button("Import Selected JSON", variant="primary")
                import_all_btn = gr.Button("Import All JSON", variant="secondary")
                import_status = gr.Textbox(label="Import Status", interactive=False)

                def scan_orphaned_json():
                    import glob, json
                    files = sorted(glob.glob('processed_docs/*.json'))
                    orphaned = []
                    for f in files:
                        name = os.path.basename(f)
                        # Heuristic: count docs with this source
                        try:
                            count = db_manager.vector_store.collection.count(where={"source": name})
                        except Exception:
                            count = 0
                        if count == 0:
                            orphaned.append(name)
                    return gr.update(choices=orphaned, value=[])

                def import_json_files(selected):
                    import json
                    if not selected:
                        return "No files selected"
                    total_added = 0
                    for name in selected:
                        path = os.path.join('processed_docs', name)
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            # Convert into vector_store format and add
                            chunks = vector_store.chunk_text(data)
                            vector_store.add_documents(chunks)
                            total_added += len(chunks)
                        except Exception as e:
                            return f"❌ Failed on {name}: {e}"
                    return f"✅ Imported {len(selected)} JSON files, added ~{total_added:,} chunks"

                scan_json_btn.click(scan_orphaned_json, None, json_list)
                import_selected_btn.click(import_json_files, json_list, import_status)
                import_all_btn.click(lambda choices: choices, json_list, json_list).then(import_json_files, json_list, import_status)

        # Backups
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 💾 Backups")
                gr.Markdown("Create and restore backups of the Chroma database.")
                create_backup_btn = gr.Button("Create Backup Archive")
                backup_file = gr.File(label="Download Backup", interactive=False)
                list_backups_btn = gr.Button("List Backups")
                backups_dropdown = gr.Dropdown(label="Available Backups", choices=[])
                restore_confirm = gr.Textbox(label="Confirmation", placeholder="Type RESTORE to confirm")
                restore_btn = gr.Button("Restore Selected Backup", variant="stop")
                restore_status = gr.Textbox(label="Restore Status", interactive=False)

                def create_backup():
                    import os, shutil, datetime
                    os.makedirs('backups', exist_ok=True)
                    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
                    base = os.path.join('backups', f'chroma_db-{ts}')
                    archive = shutil.make_archive(base, 'zip', root_dir='.', base_dir='chroma_db')
                    return archive

                def list_backups():
                    import glob
                    files = sorted(glob.glob('backups/chroma_db-*.zip'))
                    return gr.update(choices=files, value=files[-1] if files else None)

                def restore_backup(path, confirm):
                    import shutil
                    import os
                    if not path:
                        return "Select a backup first"
                    if confirm != 'RESTORE':
                        return "Type RESTORE to confirm"
                    try:
                        # Remove existing DB (dangerous) then extract
                        if os.path.exists('chroma_db'):
                            shutil.rmtree('chroma_db')
                        os.makedirs('chroma_db', exist_ok=True)
                        shutil.unpack_archive(path, '.')
                        return "✅ Restored backup successfully. Restart app to reload DB."
                    except Exception as e:
                        return f"❌ Restore failed: {e}"

                create_backup_btn.click(create_backup, None, backup_file)
                list_backups_btn.click(list_backups, None, backups_dropdown)
                restore_btn.click(restore_backup, [backups_dropdown, restore_confirm], restore_status)

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
                logging.getLogger(__name__).warning(f"Error getting models: {e}")
                return []
        
        # Get installed models on startup
        installed_models = get_installed_models()
        
        # Set initial model - use current model or first available
        if not installed_models:
            logging.getLogger(__name__).warning("No Ollama models found. Please install at least one model.")
            current_model = assistant.model_name
        else:
            # Check if current model is in the list, otherwise use first available
            if assistant.model_name in installed_models:
                current_model = assistant.model_name
            else:
                current_model = installed_models[0]
                assistant.model_name = current_model  # Update assistant with first available model
                logging.getLogger(__name__).info(f"Switched to available model: {current_model}")
        
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
        
        # Add model refresh button right after model settings
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
        
        prompt_status = gr.Textbox(label="Prompt Status", interactive=False, value="Prompts loaded")
        refresh_prompts_btn = gr.Button("🔄 Refresh Prompt List")
        
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

        gr.Markdown("### Health Checks")
        health_btn = gr.Button("Run Health Checks")
        health_out = gr.Markdown("Click to run basic environment checks")

        def run_health_checks():
            messages = []
            # Ollama
            try:
                import subprocess
                r = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=10)
                if r.returncode == 0:
                    models = [ln.split()[0] for ln in r.stdout.strip().split('\n')[1:] if ln.strip()]
                    messages.append(f"✅ Ollama reachable. Models: {', '.join(models) if models else 'none'}")
                else:
                    messages.append("❌ Ollama not responding to 'ollama list'")
            except Exception as e:
                messages.append(f"❌ Ollama check failed: {e}")
            # Tesseract
            try:
                import pytesseract  # noqa: F401
                import subprocess
                langs = subprocess.run(['tesseract','--list-langs'], capture_output=True, text=True)
                has_jpn = 'jpn' in langs.stdout
                messages.append("✅ Tesseract installed" + (" with 'jpn'" if has_jpn else " (missing 'jpn' language)"))
            except Exception as e:
                messages.append(f"❌ Tesseract check failed: {e}")
            # Chroma
            try:
                count = vector_store.collection.count()
                messages.append(f"✅ ChromaDB OK. Documents: {count}")
            except Exception as e:
                messages.append(f"❌ ChromaDB check failed: {e}")
            return "\n\n".join(messages)

        health_btn.click(run_health_checks, None, health_out)

        gr.Markdown("### OCR Settings")
        with gr.Row():
            ocr_langs = gr.Textbox(label="OCR Languages", value=settings.ocr_langs, info="e.g., jpn+eng")
            ocr_psm = gr.Textbox(label="OCR PSM", value=str(settings.ocr_psm), info="Tesseract page segmentation mode")
            ocr_min_conf = gr.Slider(label="Min Token Confidence", minimum=0, maximum=100, step=1, value=int(settings.ocr_min_conf))
        save_ocr_status = gr.Textbox(label="OCR Status", interactive=False, value="Current settings loaded")
        save_ocr_btn = gr.Button("💾 Save OCR Settings")

        def _update_env_vars(updates: dict):
            env_path = ".env"
            existing = {}
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            k, v = line.strip().split('=', 1)
                            existing[k] = v
            existing.update({k: str(v) for k, v in updates.items()})
            with open(env_path, 'w', encoding='utf-8') as f:
                for k, v in existing.items():
                    f.write(f"{k}={v}\n")

        def save_ocr_settings(langs, psm, min_conf):
            # Update in-memory settings
            settings.ocr_langs = langs.strip() or settings.ocr_langs
            settings.ocr_psm = str(psm).strip() or settings.ocr_psm
            settings.ocr_min_conf = int(min_conf)
            # Persist to .env
            try:
                _update_env_vars({
                    'OCR_LANGS': settings.ocr_langs,
                    'OCR_PSM': settings.ocr_psm,
                    'OCR_MIN_CONF': settings.ocr_min_conf,
                })
                return "Saved OCR settings to .env"
            except Exception as e:
                return f"Failed to save: {e}"

        save_ocr_btn.click(save_ocr_settings, inputs=[ocr_langs, ocr_psm, ocr_min_conf], outputs=[save_ocr_status])

# Launch the app
if __name__ == "__main__":
    # Enable queuing for streaming; omit concurrency kwarg for current Gradio version
    app.queue()
    # Bind host/port from settings with a safer default host
    app.launch(server_name=settings.gradio_host, server_port=settings.gradio_port, share=False)
