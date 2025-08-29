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
dictionary_entries = []  # Loaded dictionary entries for lookup

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

def enhanced_chat_function(message, history, show_thinking_enabled=True, knowledge_mode="auto", session_id=None):
    """Enhanced chat interface with streaming support and knowledge source selection"""
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
        stream_start_ts = time.time()
        
        # Stream the response with enhanced formatting using hybrid system
        for chunk in assistant.query_hybrid_stream(message, knowledge_mode=knowledge_mode, stop_event=stop_event):
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
                has_sources = chunk.get('sources') and len(chunk.get('sources', [])) > 0
                route = chunk.get('route', 'AUTO')
                confidence = chunk.get('confidence', 0.0)
                
                # Enhanced model info with routing information
                route_emojis = {
                    'RAG': '📚',
                    'GENERAL': '🧠', 
                    'HYBRID': '🔄',
                    'AUTO': '🤖'
                }
                
                route_descriptions = {
                    'RAG': '教科書のみ • Textbook Only',
                    'GENERAL': 'モデル知識のみ • Model Knowledge Only',
                    'HYBRID': '教科書+モデル知識 • Textbook + Model Knowledge',
                    'AUTO': '自動選択 • Auto-Selected'
                }
                
                route_emoji = route_emojis.get(route, '🤖')
                route_desc = route_descriptions.get(route, 'Unknown')
                
                model_info = f"🤖 モデル: **{assistant.model_name}** {'(推論モデル • Reasoning Model)' if is_thinking_model else ''}\n"
                model_info += f"{route_emoji} **知識ソース • Knowledge Source:** {route_desc}"
                
                if confidence > 0:
                    model_info += f" (信頼度 • Confidence: {confidence:.1%})"
                
                if chunk.get('sources'):
                    last_sources = chunk['sources']
            
            elif chunk.get('type') == 'thinking' and chunk.get('token'):
                thinking_text += chunk['token']
                elapsed = time.time() - stream_start_ts
                metrics_line = f"⏱ {elapsed:.1f}s • 思考 {len(thinking_text)} 文字"
                yield (
                    history,
                    gr.update(value=model_info, visible=bool(model_info)),
                    gr.update(value=f"{metrics_line}\n\n" + thinking_text),
                    gr.update(visible=show_thinking_enabled and is_thinking_model),
                    gr.update(visible=True)
                )
            
            elif chunk.get('type') == 'answer' and chunk.get('token'):
                answer_text += chunk['token']
                elapsed = time.time() - stream_start_ts
                metrics_line = f"⏱ {elapsed:.1f}s • 思考 {len(thinking_text)} 文字 • 応答 {len(answer_text)} 文字"
                
                if len(history) > 0 and history[-1]["role"] == "assistant":
                    history[-1]["content"] = answer_text
                else:
                    history.append({"role": "assistant", "content": answer_text})
                
                yield (
                    history,
                    gr.update(value=model_info, visible=bool(model_info)),
                    gr.update(value=f"{metrics_line}\n\n" + thinking_text),
                    gr.update(visible=show_thinking_enabled and is_thinking_model and bool(thinking_text)),
                    gr.update(visible=True)
                )
            
            elif chunk.get('done'):
                # Final processing
                if chunk.get('sources') and not last_sources:
                    last_sources = chunk['sources']
                
                elapsed = time.time() - stream_start_ts
                metrics_line = f"⏱ {elapsed:.1f}s • 思考 {len(thinking_text)} 文字 • 応答 {len(answer_text)} 文字"
                yield (
                    history,
                    gr.update(value="", visible=False),
                    gr.update(value=f"{metrics_line}\n\n" + thinking_text if thinking_text else ""),
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
    global last_sources
    
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
                # Update global sources for the sources viewer (same as chat)
                if chunk.get('sources'):
                    last_sources = chunk['sources']
                
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
    
    # Simple static header block
    gr.HTML(
        """
        <div class="simple-header">
            <h1 class="header-title">🎌 Classical Japanese Learning Assistant</h1>
            <p class="header-subtitle">古典日本語学習アシスタント • Learn Classical Japanese with AI and textbook knowledge</p>
        </div>
        """,
        elem_classes=["header-container"]
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

                    # Sentence Parser section (small dedicated input)
                    parser_components = create_sentence_parser_section()

                    def analyze_sentence(sentence):
                        """Analyze a Classical Japanese sentence using passage analysis prompt (with immediate feedback)"""
                        if not sentence or not sentence.strip():
                            yield "入力された文がありません • Please enter a sentence."
                            return
                        if not assistant.model_name:
                            yield "❌ モデル未選択 • No model selected in Settings."
                            return
                        yield "🧠 解析中… • Analyzing…"
                        # Temporarily switch to passage analysis prompt
                        original_prompt = assistant.prompt_template
                        passage_prompt = 'prompts/passage_analysis.md'
                        try:
                            if os.path.exists(passage_prompt):
                                assistant.prompt_template = assistant.load_prompt_template(passage_prompt)
                            result = assistant.translate_passage(sentence)
                            yield result.get('answer', 'No analysis produced.')
                        except Exception as e:
                            yield f"❌ 解析中にエラー • Error during analysis: {e}"
                        finally:
                            assistant.prompt_template = original_prompt

                    parser_components['analyze_btn'].click(
                        analyze_sentence,
                        inputs=[parser_components['sentence_input']],
                        outputs=[parser_components['parser_output']],
                        show_progress="minimal"
                    )

                    # Dictionary lookup (click-to-lookup)
                    gr.Markdown("---")
                    gr.Markdown("### 📚 語彙検索 • Dictionary Lookup")
                    lookup_input = gr.Textbox(
                        label="語 • Term",
                        placeholder="語や表現を入力 • Enter a term",
                        elem_classes=["enhanced-input"]
                    )
                    lookup_btn = gr.Button("検索 • Lookup", variant="secondary")
                    lookup_out = gr.Markdown(elem_classes=["explanation-card"]) 

                    def lookup_term(term):
                        import unicodedata
                        term = (term or "").strip()
                        if not term:
                            return "入力がありません • Please enter a term."
                        if not dictionary_entries:
                            return "辞書が読み込まれていません • No dictionary loaded in Settings."
                        q = unicodedata.normalize('NFKC', term)
                        results = []
                        for e in dictionary_entries:
                            hw = e.get('headword') or e.get('term') or e.get('word') or ''
                            rd = e.get('reading') or e.get('yomi') or ''
                            gl = e.get('gloss') or e.get('definition') or e.get('def') or e.get('meaning') or ''
                            if any(q in unicodedata.normalize('NFKC', str(x)) for x in (hw, rd, gl)):
                                results.append((hw, rd, gl, e))
                            if len(results) >= 20:
                                break
                        if not results:
                            return f"該当なし • No matches for: {term}"
                        lines = [f"**🔎 {term} — {len(results)} 件 • matches**\n"]
                        for i, (hw, rd, gl, e) in enumerate(results, 1):
                            pos = e.get('pos') or e.get('品詞') or ''
                            src = e.get('source') or ''
                            line = f"**{i}. {hw}** "
                            if rd:
                                line += f"({rd}) "
                            if pos:
                                line += f"[{pos}] "
                            line += "\n- " + str(gl)
                            if src:
                                line += "\n  _" + str(src) + "_"
                            lines.append(line)
                        return "\n\n".join(lines)

                    lookup_btn.click(lookup_term, inputs=[lookup_input], outputs=[lookup_out], show_progress="minimal")
                    
                    # Chat event handlers
                    submit_event = chat_components['msg'].submit(
                        enhanced_chat_function,
                        [
                            chat_components['msg'],
                            chat_components['chatbot'],
                            chat_components['show_thinking'],
                            chat_components['knowledge_mode'],
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
                            chat_components['knowledge_mode'],
                            chat_components['session_id_state']
                        ],
                        outputs,
                        show_progress="minimal"
                    ).then(
                        lambda: gr.update(visible=False), None, chat_components['stop_btn']
                    ).then(
                        lambda: "", None, chat_components['msg']
                    )
                    
                    # Show stop button during generation
                    chat_components['msg'].submit(lambda: gr.update(visible=True), None, chat_components['stop_btn'], queue=False)
                    chat_components['submit_btn'].click(lambda: gr.update(visible=True), None, chat_components['stop_btn'], queue=False)
                    
                    # Stop button functionality
                    def stop_generation_handler(current_session_id):
                        stop_event = session_stop_events.get(current_session_id)
                        if stop_event:
                            stop_event.set()
                        return gr.update(visible=False)
                    
                    chat_components['stop_btn'].click(
                        stop_generation_handler,
                        inputs=[chat_components['session_id_state']],
                        outputs=[chat_components['stop_btn']],
                        cancels=[submit_event, click_event],
                        queue=False
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
                    
                    # Add sources viewer to grammar tab (same as chat)
                    grammar_sources_components = create_enhanced_sources_viewer()
                    
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
                    
                    # Sources refresh for grammar tab
                    grammar_sources_components['refresh_sources_btn'].click(
                        format_sources_markdown, None, grammar_sources_components['sources_md']
                    )
                    
                    # Grammar stop button functionality
                    def stop_grammar_generation(session_id):
                        """Stop grammar generation for this session"""
                        if session_id in session_stop_events:
                            session_stop_events[session_id].set()
                        return gr.update(visible=False)
                    
                    grammar_components['stop_grammar_btn'].click(
                        stop_grammar_generation,
                        inputs=[grammar_components['grammar_session_id']],
                        outputs=[grammar_components['stop_grammar_btn']],
                        cancels=[search_event],
                        queue=False
                    )
                    
                    # Show stop button during grammar search
                    grammar_components['search_btn'].click(
                        lambda: gr.update(visible=True), 
                        None, 
                        grammar_components['stop_grammar_btn'], 
                        queue=False
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
                
                # Database Management
                with gr.Tab("🗄️ データベース管理 • Database Management"):
                    gr.Markdown(
                        """
                        ### 📊 データベース統計 • Database Statistics
                        View and manage your textbook database.
                        """
                    )
                    
                    # Database statistics
                    db_stats_display = gr.Markdown("Click 'Refresh Stats' to view database information")
                    png_stats_display = gr.Markdown("PNG file information will appear here")
                    refresh_db_stats_btn = gr.Button(
                        "🔄 統計更新 • Refresh Stats",
                        variant="primary",
                        elem_classes=["btn-primary"]
                    )
                    
                    gr.Markdown("---")
                    
                    # Delete textbook section
                    gr.Markdown("### ⚠️ 文書削除 • Delete Documents")
                    gr.Markdown("**警告 • Warning**: 選択した文書のすべてのチャンクが永続的に削除されます • This permanently removes all chunks from the selected textbook")
                    
                    textbook_dropdown = gr.Dropdown(
                        choices=[],
                        label="削除する文書を選択 • Select Document to Delete",
                        info="完全に削除する文書を選択してください • Choose which document to remove completely",
                        elem_classes=["enhanced-dropdown"]
                    )
                    
                    confirm_input = gr.Textbox(
                        label="削除確認 • Confirmation",
                        placeholder="Type 'DELETE filename.pdf' to confirm",
                        info="正確に入力してください • Type exactly: DELETE [document filename]",
                        elem_classes=["enhanced-input"]
                    )
                    
                    delete_btn = gr.Button(
                        "🗑️ 文書削除 • Delete Document",
                        variant="stop",
                        elem_classes=["btn-secondary"]
                    )
                    
                    delete_status = gr.Textbox(
                        label="削除状況 • Deletion Status",
                        interactive=False,
                        elem_classes=["status-display"]
                    )
                    
                    # Database management functions
                    def get_database_stats():
                        """Get current database statistics"""
                        try:
                            stats = db_manager.get_textbook_stats()
                            if 'error' in stats:
                                return f"❌ Error: {stats['error']}", [], ""
                            
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
                            
                            textbook_info = "\\n".join(textbook_list)
                            
                            summary = f"""## データベース概要 • Database Overview
**総文書数 • Total Documents**: {stats['total_documents']:,} chunks
**文書数 • Number of Books**: {len(stats['textbooks'])} documents
**重複 • Duplicates Found**: {stats['duplicates']:,} entries
{png_summary}

### データベース内の文書 • Documents in Database:
{textbook_info}
                            """
                            
                            # Return dropdown options for deletion
                            textbook_options = list(stats['textbooks'].keys())
                            return summary, textbook_options, png_summary
                        except Exception as e:
                            error_msg = f"❌ Error getting stats: {str(e)}"
                            return error_msg, [], error_msg
                    
                    def delete_textbook_func(textbook_name, confirm_text):
                        """Delete a textbook from the database"""
                        if not textbook_name:
                            return "文書を選択してください • Please select a document to delete."
                        
                        if confirm_text != f"DELETE {textbook_name}":
                            return f"❌ 正確に入力してください • Please type exactly: DELETE {textbook_name}"
                        
                        try:
                            result = db_manager.delete_textbook(textbook_name)
                            if result['success']:
                                return f"✅ {result['message']}"
                            else:
                                return f"❌ {result['message']}"
                        except Exception as e:
                            return f"❌ Error deleting document: {str(e)}"
                    
                    # Connect database management functions
                    def refresh_stats():
                        stats_text, textbook_options, png_info = get_database_stats()
                        return stats_text, gr.update(choices=textbook_options), png_info
                    
                    refresh_db_stats_btn.click(
                        refresh_stats,
                        outputs=[db_stats_display, textbook_dropdown, png_stats_display]
                    )
                    
                    delete_btn.click(
                        delete_textbook_func,
                        inputs=[textbook_dropdown, confirm_input],
                        outputs=[delete_status]
                    )
                    
                    gr.Markdown("---")
                    
                    # PNG cleanup section
                    gr.Markdown("### 📁 PNG ファイル削除 • Clean PNG Files")
                    gr.Markdown("**⚠️ 警告 • Warning**: PNGファイルはOCR処理に使用されます。データベースが正常に動作することを確認してから削除してください。")
                    gr.Markdown("**⚠️ Warning**: PNG files are used for OCR processing. Delete only after confirming database is working correctly.")
                    gr.Markdown("これにより、processed_docsフォルダー内のすべてのPNGファイルが削除されます。JSONファイルは復旧のために保持されます。")
                    gr.Markdown("This will delete ALL PNG files in processed_docs folder. JSON files will be preserved for recovery.")
                    
                    # PNG stats are shown above with the main database stats
                    
                    png_confirm_input = gr.Textbox(
                        label="削除確認 • Confirmation Required",
                        placeholder="Type 'DELETE PNGs' to confirm",
                        info="正確に入力してください • Type exactly: DELETE PNGs",
                        elem_classes=["enhanced-input"]
                    )
                    
                    delete_pngs_btn = gr.Button(
                        "🗑️ PNG ファイル削除 • Delete PNG Files",
                        variant="stop",
                        elem_classes=["btn-secondary"]
                    )
                    
                    png_delete_status = gr.Textbox(
                        label="PNG削除状況 • PNG Deletion Status",
                        interactive=False,
                        elem_classes=["status-display"]
                    )
                    
                    def delete_png_files_func(confirm_text):
                        """Delete PNG files after confirmation"""
                        if confirm_text != "DELETE PNGs":
                            return "❌ 'DELETE PNGs' と正確に入力してください • Please type 'DELETE PNGs' exactly to confirm deletion."
                        
                        try:
                            result = db_manager.delete_png_files()
                            if result['success']:
                                return f"✅ {result['message']}"
                            else:
                                return f"❌ {result['message']}"
                        except Exception as e:
                            return f"❌ Error deleting PNG files: {str(e)}"
                    
                    delete_pngs_btn.click(
                        delete_png_files_func,
                        inputs=[png_confirm_input],
                        outputs=[png_delete_status]
                    )

                    gr.Markdown("---")
                    # Orphaned JSON Import
                    gr.Markdown("### 📥 JSON インポート • Import Orphaned JSON")
                    gr.Markdown("processed_docs 内のJSONで、まだデータベースに取り込まれていないものを検出して取り込みます • Scan and import processed JSON files not yet in the database.")
                    scan_json_btn = gr.Button("🔎 JSONスキャン • Scan for JSON Files", variant="secondary")
                    json_list = gr.CheckboxGroup(label="検出されたJSON • Found JSON Files (select to import)")
                    import_selected_btn = gr.Button("📥 選択をインポート • Import Selected", variant="primary")
                    import_all_btn = gr.Button("📥 すべてインポート • Import All", variant="secondary")
                    import_status = gr.Markdown("")

                    def scan_orphaned_json():
                        import glob, json
                        files = sorted(glob.glob('processed_docs/*.json'))
                        orphaned = []
                        for f in files:
                            name = os.path.basename(f)
                            source_key = os.path.splitext(name)[0]
                            try:
                                with open(f, 'r', encoding='utf-8') as jf:
                                    data = json.load(jf)
                                if isinstance(data, list) and data:
                                    sp = data[0].get('source_pdf') or data[0].get('metadata', {}).get('source')
                                    if sp:
                                        source_key = sp
                            except Exception:
                                pass
                            try:
                                count = vector_store.collection.count(where={"source": source_key})
                            except Exception:
                                count = 0
                            if count == 0:
                                orphaned.append(name)
                        return gr.update(choices=orphaned, value=[])

                    def import_json_files(selected):
                        import json
                        if not selected:
                            return "⚠️ ファイルが選択されていません • No files selected"
                        total_added = 0
                        for name in selected:
                            path = os.path.join('processed_docs', name)
                            try:
                                with open(path, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                chunks = vector_store.chunk_text(data)
                                vector_store.add_documents(chunks)
                                total_added += len(chunks)
                            except Exception as e:
                                return f"❌ {name} のインポートに失敗 • Failed on {name}: {e}"
                        return f"✅ {len(selected)} 件のJSONをインポート • Imported {len(selected)} JSON files, 追加 • added ~{total_added:,} チャンク • chunks"

                    scan_json_btn.click(scan_orphaned_json, None, json_list)
                    import_selected_btn.click(import_json_files, json_list, import_status)
                    import_all_btn.click(lambda choices: choices, json_list, json_list).then(import_json_files, json_list, import_status)
        
        # System & Settings
        with gr.Tab("⚙️ システム • System"):
            
            # Dashboard
            dashboard_components = create_dashboard_interface(None)
            
            # Connect dashboard functions
            def update_dashboard_stats():
                """Update dashboard statistics"""
                try:
                    # Get detailed database statistics
                    stats = db_manager.get_textbook_stats()
                    if 'error' in stats:
                        error_msg = f"**❌ Error**\n\n{stats['error']}"
                        return error_msg, error_msg, error_msg
                    
                    # Enhanced document display
                    textbook_list = []
                    for source, count in stats['textbooks'].items():
                        textbook_list.append(f"• **{source}**: {count:,} chunks")
                    
                    if textbook_list:
                        textbook_info = "\\n".join(textbook_list)
                        docs_display = f"""**📚 総文書数 • Total Documents**

**{stats['total_documents']:,}** total chunks
**{len(stats['textbooks'])}** documents

### 文書一覧 • Document Library:
{textbook_info}"""
                    else:
                        docs_display = "**📚 総文書数 • Total Documents**\n\nNo documents in database"
                    
                    # Routing statistics
                    routing_display = get_routing_stats_display()
                    
                    # Grammar points placeholder  
                    grammar_display = "**📖 文法項目 • Grammar Points**\n\nStudied: 0\nMastered: 0"
                    
                    return docs_display, routing_display, grammar_display
                except Exception as e:
                    error_msg = f"**❌ Error**\n\n{str(e)}"
                    return error_msg, error_msg, error_msg
            
            def run_health_checks():
                """Run comprehensive health checks"""
                messages = []
                
                # Ollama check
                try:
                    import subprocess
                    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        models = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] if line.strip()]
                        messages.append(f"✅ Ollama reachable. Models: {', '.join(models) if models else 'none'}")
                    else:
                        messages.append("❌ Ollama not responding to 'ollama list'")
                except Exception as e:
                    messages.append(f"❌ Ollama check failed: {e}")
                
                # Tesseract check
                try:
                    import subprocess
                    result = subprocess.run(['tesseract', '--list-langs'], capture_output=True, text=True)
                    has_jpn = 'jpn' in result.stdout
                    messages.append("✅ Tesseract installed" + (" with 'jpn'" if has_jpn else " (missing 'jpn' language)"))
                except Exception as e:
                    messages.append(f"❌ Tesseract check failed: {e}")
                
                # ChromaDB check
                try:
                    count = vector_store.collection.count()
                    messages.append(f"✅ ChromaDB OK. Documents: {count}")
                except Exception as e:
                    messages.append(f"❌ ChromaDB check failed: {e}")
                
                return "\\n\\n".join(messages)
            
            def get_routing_stats_display():
                """Get hybrid knowledge system routing statistics"""
                try:
                    stats = assistant.get_routing_stats()
                    if stats['total'] == 0:
                        return "📊 **Knowledge Routing Statistics**\\n\\nNo queries processed yet."
                    
                    lines = [
                        f"📊 **Knowledge Routing Statistics**\\n",
                        f"**Total Queries**: {stats['total']}",
                        f"**Average Confidence**: {stats['avg_confidence']:.1%}\\n",
                        "**Route Distribution**:"
                    ]
                    
                    route_emojis = {
                        'RAG': '📚',
                        'GENERAL': '🧠', 
                        'HYBRID': '🔄'
                    }
                    
                    for route, percentage in stats['route_percentages'].items():
                        emoji = route_emojis.get(route, '❓')
                        lines.append(f"- {emoji} **{route}**: {percentage:.1f}%")
                    
                    return "\\n".join(lines)
                
                except Exception as e:
                    return f"❌ Routing stats error: {e}"
            
            def create_backup():
                """Create database backup"""
                try:
                    import shutil
                    import datetime
                    import os
                    
                    os.makedirs('backups', exist_ok=True)
                    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
                    base_name = os.path.join('backups', f'chroma_db-{timestamp}')
                    archive_path = shutil.make_archive(base_name, 'zip', root_dir='.', base_dir='chroma_db')
                    
                    return f"✅ Backup created: {archive_path}"
                except Exception as e:
                    return f"❌ Backup failed: {str(e)}"
            
            # Connect dashboard buttons
            dashboard_components['refresh_stats_btn'].click(
                update_dashboard_stats,
                None,
                [
                    dashboard_components['total_docs_display'],
                    dashboard_components['study_time_display'], 
                    dashboard_components['grammar_points_display']
                ]
            )
            
            dashboard_components['health_check_btn'].click(
                lambda: gr.update(value=run_health_checks()),
                None,
                dashboard_components['total_docs_display']  # Reuse for health check display
            )
            
            dashboard_components['backup_btn'].click(
                lambda: gr.update(value=create_backup()),
                None,
                dashboard_components['study_time_display']  # Reuse for backup status
            )
            
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

            gr.Markdown("---")
            # Dictionary Loader
            gr.Markdown("### 📚 辞書設定 • Dictionary Settings")
            gr.Markdown("ローカル辞書(JSON)を読み込み、チャットで語彙検索ができます • Load a local JSON dictionary for lookups in Chat.")
            dict_file = gr.File(label="辞書ファイル(JSON) • Dictionary JSON", file_types=[".json"])
            load_dict_btn = gr.Button("📥 辞書読み込み • Load Dictionary", variant="secondary")
            dict_status = gr.Markdown("")

            def load_dictionary(file_obj):
                import json, unicodedata
                global dictionary_entries
                if not file_obj:
                    return "⚠️ ファイルが選択されていません • No file selected"
                try:
                    with open(file_obj.name, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    entries = []
                    if isinstance(data, dict):
                        # Map form: headword -> definition
                        for k, v in data.items():
                            entries.append({
                                'headword': unicodedata.normalize('NFKC', str(k)),
                                'gloss': unicodedata.normalize('NFKC', str(v))
                            })
                    elif isinstance(data, list):
                        for it in data:
                            if isinstance(it, dict):
                                # Normalize known fields
                                it = {k: (unicodedata.normalize('NFKC', str(v)) if isinstance(v, str) else v) for k, v in it.items()}
                                entries.append(it)
                    else:
                        return "❌ 未対応のJSON形式 • Unsupported JSON structure"
                    dictionary_entries = entries
                    return f"✅ 辞書を読み込みました • Loaded dictionary with {len(entries):,} entries"
                except Exception as e:
                    return f"❌ 辞書読み込みエラー • Failed to load dictionary: {e}"

            load_dict_btn.click(load_dictionary, inputs=[dict_file], outputs=[dict_status], show_progress="minimal")
            
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
