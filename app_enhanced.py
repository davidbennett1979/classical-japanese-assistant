import gradio as gr
from rag_assistant import ClassicalJapaneseAssistant
from vector_store import JapaneseVectorStore
from ocr_pipeline import JapaneseOCR
from database_manager import DatabaseManager
from theme import create_japanese_theme, CUSTOM_CSS, SEASONAL_THEMES, get_seasonal_css
from ui_components import *
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

# Theme configuration
current_theme = create_japanese_theme()
current_season = "sakura"

# Session management
session_stop_events = {}
session_last_used = {}
last_sources = []

def _cleanup_expired_sessions():
    """Remove session events that haven't been used for a while."""
    ttl = max(1, int(getattr(settings, 'session_ttl_minutes', 60))) * 60
    now = time.time()
    expired = [sid for sid, ts in session_last_used.items() if now - ts > ttl]
    for sid in expired:
        session_stop_events.pop(sid, None)
        session_last_used.pop(sid, None)

def get_available_prompts():
    """Dynamically load all .md files from prompts folder"""
    prompt_files = glob.glob("prompts/*.md")
    return sorted(prompt_files) if prompt_files else ["prompts/classical_japanese_tutor.md"]

def enhanced_chat_function(message, history, show_thinking_enabled=True, session_id=None):
    """Enhanced chat interface with streaming support"""
    global last_sources
    
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    _cleanup_expired_sessions()
    if session_id not in session_stop_events:
        session_stop_events[session_id] = threading.Event()
    
    stop_event = session_stop_events[session_id]
    stop_event.clear()
    session_last_used[session_id] = time.time()
    
    history = history or []
    history.append({"role": "user", "content": message})
    
    # Check if a model is selected
    if not assistant.model_name:
        history.append({
            "role": "assistant", 
            "content": "❌ モデルが選択されていません。設定タブでモデルを選択してください。\n\n❌ No model selected. Please select a model in the Settings tab first."
        })
        yield (
            history,
            gr.update(value="", visible=False),
            gr.update(value=""),
            gr.update(visible=False),
            gr.update()
        )
        return
    
    try:
        model_info = ""
        thinking_text = ""
        answer_text = ""
        sources_text = ""
        is_thinking_model = False
        
        # Stream the response with enhanced formatting
        for chunk in assistant.query_stream(message, stop_event=stop_event):
            session_last_used[session_id] = time.time()
            
            if stop_event.is_set():
                if thinking_text:
                    thinking_text += "\n\n*[生成が停止されました • Generation stopped by user]*"
                if answer_text:
                    answer_text += "\n\n*[生成が停止されました • Generation stopped by user]*"
                else:
                    answer_text = "*[生成が停止されました • Generation stopped by user]*"
                
                if is_thinking_model:
                    if len(history) > 1 and history[-1]["role"] == "assistant":
                        history[-1]["content"] = f"📝 応答が停止されました • Response stopped - using {assistant.model_name}"
                    else:
                        history.append({
                            "role": "assistant", 
                            "content": f"📝 応答が停止されました • Response stopped - using {assistant.model_name}"
                        })
                
                yield (
                    history,
                    gr.update(value="", visible=False),
                    gr.update(value=thinking_text),
                    gr.update(visible=bool(thinking_text) and show_thinking_enabled),
                    gr.update(visible=False)
                )
                return
            
            # Process different types of chunks
            if chunk.get('type') == 'model_info':
                is_thinking_model = chunk.get('is_thinking_model', False)
                model_info = f"🤖 モデル: {assistant.model_name} {'(推論モデル • Reasoning Model)' if is_thinking_model else ''}"
                if chunk.get('sources'):
                    last_sources = chunk['sources']
            
            elif chunk.get('type') == 'thinking' and chunk.get('token'):
                thinking_text += chunk['token']
                yield (
                    history,
                    gr.update(value=model_info, visible=bool(model_info)),
                    gr.update(value=thinking_text),
                    gr.update(visible=show_thinking_enabled and is_thinking_model),
                    gr.update(visible=True)
                )
            
            elif chunk.get('type') == 'answer' and chunk.get('token'):
                answer_text += chunk['token']
                
                if len(history) > 0 and history[-1]["role"] == "assistant":
                    history[-1]["content"] = answer_text
                else:
                    history.append({"role": "assistant", "content": answer_text})
                
                yield (
                    history,
                    gr.update(value=model_info, visible=bool(model_info)),
                    gr.update(value=thinking_text),
                    gr.update(visible=show_thinking_enabled and is_thinking_model and bool(thinking_text)),
                    gr.update(visible=True)
                )
            
            elif chunk.get('done'):
                # Final processing
                if chunk.get('sources') and not last_sources:
                    last_sources = chunk['sources']
                
                yield (
                    history,
                    gr.update(value="", visible=False),
                    gr.update(value=thinking_text),
                    gr.update(visible=show_thinking_enabled and is_thinking_model and bool(thinking_text)),
                    gr.update(visible=False)
                )
                break
    
    except Exception as e:
        error_message = f"❌ エラー • Error: {str(e)}"
        history.append({"role": "assistant", "content": error_message})
        yield (
            history,
            gr.update(value="", visible=False),
            gr.update(value=""),
            gr.update(visible=False),
            gr.update(visible=False)
        )

def enhanced_grammar_search(grammar_point, session_id):
    """Enhanced streaming grammar search"""
    if not grammar_point.strip():
        yield (
            "文法項目を入力してください • Please enter a grammar point to search for.", 
            "準備完了 • Ready to search", 
            gr.update(visible=False)
        )
        return
    
    stop_event = threading.Event()
    session_stop_events[session_id] = stop_event
    
    try:
        yield "", "🔍 データベースを検索中... • Searching database...", gr.update(visible=True)
        
        # Use grammar-focused prompt
        original_prompt = assistant.prompt_template
        grammar_prompt = getattr(assistant, 'grammar_prompt_path', 'prompts/grammar_focused.md')
        
        if os.path.exists(grammar_prompt):
            assistant.prompt_template = assistant.load_prompt_template(grammar_prompt)
        
        full_response = ""
        
        # Stream with Japanese status updates
        for chunk in assistant.explain_grammar_stream(grammar_point, stop_event=stop_event):
            if stop_event.is_set():
                full_response += "\n\n*[生成が停止されました • Generation stopped by user]*"
                yield full_response, "⏹️ 停止されました • Stopped", gr.update(visible=False)
                break
            
            if chunk.get('token'):
                full_response += chunk['token']
                yield full_response, "🧠 AIモデルで分析中... • Analyzing with AI model...", gr.update(visible=True)
            
            if chunk.get('done'):
                # Add sources with bilingual labels
                if chunk.get('sources'):
                    full_response += "\n\n**📚 出典 • Sources:**\n"
                    for src in chunk['sources']:
                        source_name = src.get('source', 'Unknown')
                        page_num = src.get('page', 'N/A')
                        full_response += f"- {source_name} (ページ • Page {page_num})\n"
                
                yield full_response, f"✅ '{grammar_point}' の説明を見つけました • Found explanation for '{grammar_point}'", gr.update(visible=False)
        
        # Restore original prompt
        assistant.prompt_template = original_prompt
        
    except Exception as e:
        yield f"❌ エラー • Error: {str(e)}", "エラーが発生しました • Error occurred", gr.update(visible=False)
    finally:
        session_stop_events.pop(session_id, None)

def add_note_function(note_text, topic):
    """Enhanced note adding with bilingual feedback"""
    if not note_text.strip():
        return "ノート内容を入力してください • Please enter note content."
    
    try:
        vector_store.add_note(note_text, topic or "general")
        return f"✅ ノートが追加されました • Note added successfully!\nトピック • Topic: {topic or 'general'}"
    except Exception as e:
        return f"❌ エラー • Error adding note: {str(e)}"

def format_sources_markdown():
    """Enhanced sources formatting with bilingual labels"""
    global last_sources
    if not last_sources:
        return "まだ出典がありません。質問して出典を表示してください。\n\n*No sources yet. Ask a question to populate sources.*"
    
    lines = ["### 📚 出典情報 • Source Information\n"]
    try:
        for i, s in enumerate(last_sources, 1):
            meta = s.get('metadata', {})
            src = meta.get('source', 'unknown')
            page = meta.get('page', 'N/A')
            snippet = (s.get('text') or '')[:150] + "..." if len(s.get('text', '')) > 150 else s.get('text', '')
            
            lines.append(f"**{i}. {src}** (ページ • Page: {page})")
            lines.append(f"   *{snippet}*")
            lines.append("")
        
        return "\n".join(lines)
    except Exception as e:
        return f"出典の表示中にエラーが発生しました • Error displaying sources: {e}"

def process_new_document_enhanced(file, start_page=None, end_page=None, resume_from_json=True):
    """Enhanced document processing with bilingual status updates"""
    if not file:
        yield "ファイルを選択してください • Please select a file."
        return
    
    try:
        yield f"📄 処理開始 • Starting processing: {file.name}"
        
        # Check for existing JSON
        pdf_name = os.path.basename(file.name)
        json_path = os.path.join("processed_docs", f"{pdf_name}.json")
        
        if resume_from_json and os.path.exists(json_path):
            yield f"📥 既存のJSONファイルから読み込み中 • Loading from existing JSON: {json_path}"
            import json
            with open(json_path, 'r', encoding='utf-8') as f:
                ocr_data = json.load(f)
            yield f"✅ JSONから {len(ocr_data)} ページを読み込みました • Loaded {len(ocr_data)} pages from JSON"
        else:
            # OCR processing with progress updates
            yield "🔍 OCRでテキスト抽出中 • Extracting text with OCR..."
            ocr_data = []
            
            for page_data in ocr.process_pdf(file.name, start_page=start_page, end_page=end_page):
                if isinstance(page_data, str) and "Processing" in page_data:
                    # Status update
                    yield f"📖 {page_data}"
                else:
                    # Actual page data
                    ocr_data.append(page_data)
                    yield f"📄 ページ処理完了 • Page processed: {len(ocr_data)} pages done"
        
        # Chunking
        yield f"📝 テキストをチャンク化中 • Chunking text into segments..."
        chunks = vector_store.chunk_text(ocr_data)
        total_chunks = len(chunks)
        yield f"📊 {total_chunks:,} チャンクを作成しました • Created {total_chunks:,} chunks"
        
        # Add to database
        if total_chunks > 1000:
            batch_size = 100
            total_batches = (total_chunks + batch_size - 1) // batch_size
            
            for i in range(0, total_chunks, batch_size):
                batch = chunks[i:i+batch_size]
                batch_num = i // batch_size + 1
                progress_pct = int((batch_num / total_batches) * 100)
                
                yield f"💾 バッチ追加中 • Adding batch {batch_num}/{total_batches} ({progress_pct}%): チャンク • chunks {i+1:,}-{min(i+batch_size, total_chunks):,}..."
                vector_store.add_documents(batch)
        else:
            yield f"💾 {total_chunks:,} チャンクをベクトルデータベースに追加中 • Adding {total_chunks:,} chunks to vector database..."
            vector_store.add_documents(chunks)
        
        # Final success message
        final_count = vector_store.collection.count()
        yield f"""✅ 処理完了 • Processing Complete!

📊 追加されたチャンク数 • Chunks Added: {total_chunks:,}
📚 データベース総文書数 • Total Documents in Database: {final_count:,}
🎉 学習準備完了 • Ready for learning!"""
        
    except Exception as e:
        yield f"❌ 処理中にエラーが発生しました • Error during processing: {str(e)}"

# Create the enhanced Gradio interface
with gr.Blocks(
    title="🎌 Classical Japanese Learning Assistant • 古典日本語学習アシスタント",
    theme=current_theme,
    css=CUSTOM_CSS + get_seasonal_css(current_season)
) as app:
    
    # Beautiful Japanese-inspired header
    with gr.Column(elem_classes=["app-header"]):
        gr.Markdown(
            """
            <div class="app-title">🎌 古典日本語学習アシスタント</div>
            <div class="app-subtitle">Classical Japanese Learning Assistant</div>
            <div class="app-subtitle">AIと教科書の知識で古典日本語を学ぼう • Learn Classical Japanese with AI and textbook knowledge</div>
            """,
            elem_classes=["sakura-pattern"]
        )
    
    # Theme selector
    season_dropdown = create_seasonal_theme_selector()
    
    # Main navigation with enhanced structure
    with gr.Tabs(elem_classes=["tab-nav"]) as main_tabs:
        
        # Learning Hub - Main interface
        with gr.Tab("🎓 学習 • Learning Hub", elem_classes=["content-card"]):
            
            with gr.Tabs() as learning_subtabs:
                
                # Chat Interface
                with gr.Tab("💬 AI対話 • AI Chat"):
                    chat_components = create_enhanced_chat_interface(
                        enhanced_chat_function, None, None, assistant
                    )
                    
                    # Wire up the chat functionality
                    outputs = [
                        chat_components['chatbot'],
                        chat_components['model_display'],
                        chat_components['thinking_content'],
                        chat_components['thinking_accordion'],
                        chat_components['stop_btn']
                    ]
                    
                    # Enhanced sources viewer
                    sources_components = create_enhanced_sources_viewer()
                    
                    # Chat event handlers
                    submit_event = chat_components['msg'].submit(
                        enhanced_chat_function,
                        [
                            chat_components['msg'],
                            chat_components['chatbot'],
                            chat_components['show_thinking'],
                            chat_components['session_id_state']
                        ],
                        outputs,
                        show_progress="minimal"
                    ).then(
                        lambda: gr.update(visible=False), None, chat_components['stop_btn']
                    ).then(
                        lambda: "", None, chat_components['msg']
                    )
                    
                    click_event = chat_components['submit_btn'].click(
                        enhanced_chat_function,
                        [
                            chat_components['msg'],
                            chat_components['chatbot'],
                            chat_components['show_thinking'],
                            chat_components['session_id_state']
                        ],
                        outputs,
                        show_progress="minimal"
                    ).then(
                        lambda: gr.update(visible=False), None, chat_components['stop_btn']
                    ).then(
                        lambda: "", None, chat_components['msg']
                    )
                    
                    # Clear functionality
                    def clear_all():
                        return (
                            [],
                            gr.update(value="", visible=False),
                            gr.update(value=""),
                            gr.update(visible=False),
                            gr.update()
                        )
                    
                    chat_components['clear_btn'].click(clear_all, None, outputs, queue=False)
                    
                    # Sources refresh
                    sources_components['refresh_sources_btn'].click(
                        format_sources_markdown, None, sources_components['sources_md']
                    )
                
                # Grammar Search
                with gr.Tab("📖 文法検索 • Grammar Search"):
                    grammar_components = create_enhanced_grammar_search(enhanced_grammar_search)
                    
                    # Wire up grammar search
                    search_event = grammar_components['search_btn'].click(
                        enhanced_grammar_search,
                        inputs=[grammar_components['grammar_input'], grammar_components['grammar_session_id']],
                        outputs=[
                            grammar_components['grammar_output'],
                            grammar_components['grammar_status'],
                            grammar_components['stop_grammar_btn']
                        ],
                        show_progress="minimal"
                    )
                    
                    # Example button handlers
                    for i, btn in enumerate(grammar_components['example_buttons']):
                        example_text = ["らむ", "べし", "なり", "けり", "つ・ぬ", "む・べし"][i]
                        btn.click(
                            lambda x=example_text: x,
                            None,
                            grammar_components['grammar_input'],
                            queue=False
                        )
                
                # Study Notes
                with gr.Tab("📝 学習ノート • Study Notes"):
                    notes_components = create_notes_interface(add_note_function)
                    
                    notes_components['add_btn'].click(
                        add_note_function,
                        [notes_components['note_input'], notes_components['topic_input']],
                        notes_components['note_output']
                    )
        
        # Document Management
        with gr.Tab("📚 文書管理 • Document Management"):
            
            with gr.Tabs():
                
                # Add Documents
                with gr.Tab("📥 文書追加 • Add Documents"):
                    gr.Markdown(
                        """
                        ### 📄 新しい文書を追加 • Add New Documents
                        Upload PDF files or images to expand your knowledge base.
                        """
                    )
                    
                    file_input = gr.File(
                        label="📎 ファイル選択 • Select File",
                        file_types=[".pdf", ".jpg", ".png"],
                        elem_classes=["enhanced-file-input"]
                    )
                    
                    with gr.Row():
                        start_page_in = gr.Number(
                            label="開始ページ • Start Page",
                            value=None,
                            elem_classes=["enhanced-input"]
                        )
                        end_page_in = gr.Number(
                            label="終了ページ • End Page",
                            value=None,
                            elem_classes=["enhanced-input"]
                        )
                    
                    resume_chk = gr.Checkbox(
                        label="既存のJSONファイルから読み込み • Import from existing JSON if present",
                        value=True,
                        info="JSONファイルが存在する場合、OCRをスキップして読み込みます • If matching JSON exists, skip OCR and import it",
                        elem_classes=["japanese-checkbox"]
                    )
                    
                    process_btn = gr.Button(
                        "🚀 文書処理開始 • Start Processing",
                        variant="primary",
                        elem_classes=["btn-primary", "process-button"]
                    )
                    
                    process_output = gr.Textbox(
                        label="処理状況 • Processing Status",
                        lines=10,
                        elem_classes=["status-display", "process-log"]
                    )
                    
                    process_btn.click(
                        process_new_document_enhanced,
                        [file_input, start_page_in, end_page_in, resume_chk],
                        process_output
                    )
        
        # System & Settings
        with gr.Tab("⚙️ システム • System"):
            
            # Dashboard
            dashboard_components = create_dashboard_interface(None)
            
            gr.Markdown("---")
            
            # Model Settings
            gr.Markdown("### 🤖 モデル設定 • Model Settings")
            
            def get_installed_models():
                """Get list of installed Ollama models"""
                try:
                    import subprocess
                    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            models = []
                            for line in lines[1:]:
                                if line.strip():
                                    parts = line.strip().split()
                                    if parts:
                                        models.append(parts[0])
                            return models if models else []
                    return []
                except Exception as e:
                    logging.getLogger(__name__).warning(f"Error getting models: {e}")
                    return []
            
            installed_models = get_installed_models()
            current_model = assistant.model_name if assistant.model_name in installed_models else (installed_models[0] if installed_models else None)
            
            model_dropdown = gr.Dropdown(
                choices=installed_models,
                value=current_model,
                label="モデル選択 • Select Model",
                info="インストール済みのOllamaモデルから選択 • Choose from installed Ollama models",
                elem_classes=["enhanced-dropdown"]
            )
            
            def switch_model(model_name):
                assistant.model_name = model_name
                return f"モデルを切り替えました • Switched to model: {model_name}"
            
            model_status = gr.Textbox(
                label="モデル状態 • Model Status",
                value=f"現在のモデル • Current: {assistant.model_name}",
                interactive=False,
                elem_classes=["status-display"]
            )
            
            model_dropdown.change(switch_model, model_dropdown, model_status)
            
            refresh_models_btn = gr.Button(
                "🔄 モデルリスト更新 • Refresh Model List",
                elem_classes=["btn-secondary"]
            )
            
            def refresh_models():
                models = get_installed_models()
                if not models:
                    return gr.update(choices=[], value=None), "モデルが見つかりません • No models found. Please install Ollama models."
                
                current_value = assistant.model_name if assistant.model_name in models else models[0]
                return (
                    gr.update(choices=models, value=current_value),
                    f"{len(models)} モデルが見つかりました • Found {len(models)} installed models: {', '.join(models)}"
                )
            
            refresh_models_btn.click(refresh_models, None, [model_dropdown, model_status])

# Launch the enhanced app
if __name__ == "__main__":
    # Enable queuing for streaming
    app.queue()
    # Launch with enhanced configuration
    app.launch(
        server_name=settings.gradio_host,
        server_port=settings.gradio_port,
        share=False,
        show_api=False,
        show_error=True
    )