import gradio as gr
from theme import CUSTOM_CSS, SEASONAL_THEMES, get_seasonal_css
import uuid

def create_enhanced_chat_interface(
    chat_function, 
    stop_generation_handler,
    clear_all_handler,
    assistant
):
    """Create enhanced chat interface with Japanese aesthetics"""
    
    # Chat components with enhanced styling
    chatbot = gr.Chatbot(
        label="💬 対話 • Conversation",
        show_label=True,
        elem_classes=["chat-container"],
        height=500,
        bubble_full_width=False,
        type='messages',  # Use modern message format
        avatar_images=(
            "https://cdn-icons-png.flaticon.com/512/149/149071.png",  # User
            "https://cdn-icons-png.flaticon.com/512/4712/4712139.png"   # Assistant
        )
    )
    
    # Enhanced input with Japanese placeholder
    msg = gr.Textbox(
        label="質問 • Your Question",
        placeholder="古典日本語について質問してください • Ask about Classical Japanese...",
        lines=2,
        elem_classes=["enhanced-input"],
        max_lines=5
    )
    
    # Stylized control buttons
    with gr.Row():
        with gr.Column(scale=1):
            submit_btn = gr.Button(
                "送信 • Send", 
                variant="primary",
                elem_classes=["btn-primary", "japanese-button"]
            )
        with gr.Column(scale=1):
            clear_btn = gr.Button(
                "クリア • Clear",
                variant="secondary", 
                elem_classes=["btn-secondary"]
            )
        with gr.Column(scale=1):
            stop_btn = gr.Button(
                "停止 • Stop", 
                variant="stop",
                visible=False,
                elem_classes=["btn-stop"]
            )
    
    # Enhanced thinking display with cultural elements
    thinking_accordion = gr.Accordion(
        "🧠 思考過程 • AI Thinking Process",
        open=False,
        visible=False,
        elem_classes=["thinking-accordion", "cultural-card"]
    )
    
    with thinking_accordion:
        thinking_content = gr.Markdown(
            "",
            elem_classes=["thinking-content", "monospace-japanese"]
        )
    
    # Knowledge source selector
    with gr.Row():
        with gr.Column(scale=1):
            knowledge_mode = gr.Radio(
                choices=[
                    ("🤖 自動 • Auto", "auto"),
                    ("📚 教科書 • Textbook", "RAG"),
                    ("🧠 モデル • Model", "GENERAL"),
                    ("🔄 混合 • Hybrid", "HYBRID")
                ],
                value="auto",
                label="💡 知識ソース • Knowledge Source",
                elem_classes=["knowledge-selector", "compact-radio"]
            )
        with gr.Column(scale=1):
            # Show/Hide thinking toggle with Japanese text
            show_thinking = gr.Checkbox(
                label="思考過程を表示 • Show thinking process",
                value=True,
                elem_classes=["japanese-checkbox"]
            )
    
    # Model status with enhanced design
    model_display = gr.Markdown(
        "",
        visible=False,
        elem_classes=["model-status", "info-card"]
    )
    
    # Session management
    session_id_state = gr.State(str(uuid.uuid4()))
    
    return {
        'chatbot': chatbot,
        'msg': msg,
        'submit_btn': submit_btn,
        'clear_btn': clear_btn,
        'stop_btn': stop_btn,
        'thinking_accordion': thinking_accordion,
        'thinking_content': thinking_content,
        'show_thinking': show_thinking,
        'knowledge_mode': knowledge_mode,
        'model_display': model_display,
        'session_id_state': session_id_state
    }

def create_enhanced_grammar_search(search_with_streaming):
    """Create enhanced grammar search interface"""
    
    with gr.Column(elem_classes=["grammar-search-container", "content-card"]):
        gr.Markdown(
            """
            ### 📖 文法検索 • Grammar Search
            Search and learn about Classical Japanese grammar points with AI-powered explanations.
            """,
            elem_classes=["section-header"]
        )
        
        # Enhanced grammar input
        grammar_input = gr.Textbox(
            label="文法項目 • Grammar Point",
            placeholder="例：らむ、べし、なり • e.g., らむ, べし, なり",
            elem_classes=["enhanced-input", "grammar-input"]
        )
        
        # Interactive examples with hover preview
        with gr.Row():
            gr.Markdown("**Quick Examples:**")
        
        with gr.Row():
            example_buttons = []
            examples = ["らむ", "べし", "なり", "けり", "つ・ぬ", "む・べし"]
            for example in examples:
                btn = gr.Button(
                    example,
                    variant="secondary",
                    scale=1,
                    elem_classes=["example-button", "hover-preview"]
                )
                example_buttons.append(btn)
        
        # Search controls with enhanced styling
        with gr.Row():
            search_btn = gr.Button(
                "🔍 検索・説明 • Search & Explain",
                variant="primary",
                elem_classes=["btn-primary", "search-button"]
            )
            stop_grammar_btn = gr.Button(
                "停止 • Stop",
                variant="stop",
                visible=False,
                elem_classes=["btn-stop"]
            )
        
        # Status with progress indicator
        grammar_status = gr.Textbox(
            label="状態 • Status",
            value="準備完了 • Ready to search",
            interactive=False,
            elem_classes=["status-display"]
        )
        
        # Enhanced output with card styling
        grammar_output = gr.Markdown(
            label="文法説明 • Grammar Explanation",
            elem_classes=["grammar-output", "explanation-card"]
        )
        
        # Session management
        grammar_session_id = gr.State(str(uuid.uuid4()))
        
        return {
            'grammar_input': grammar_input,
            'example_buttons': example_buttons,
            'search_btn': search_btn,
            'stop_grammar_btn': stop_grammar_btn,
            'grammar_status': grammar_status,
            'grammar_output': grammar_output,
            'grammar_session_id': grammar_session_id
        }

def create_enhanced_sources_viewer():
    """Create enhanced sources viewer with preview capabilities"""
    
    sources_accordion = gr.Accordion(
        "📚 出典 • Sources & References",
        open=False,
        visible=True,
        elem_classes=["sources-accordion", "cultural-card"]
    )
    
    with sources_accordion:
        with gr.Row():
            refresh_sources_btn = gr.Button(
                "🔄 出典更新 • Refresh Sources",
                variant="secondary",
                elem_classes=["btn-secondary"]
            )
            export_sources_btn = gr.Button(
                "📥 エクスポート • Export",
                variant="secondary",
                elem_classes=["btn-secondary"]
            )
        
        sources_md = gr.Markdown(
            "まだ出典がありません。質問して出典を表示してください。\n\n*No sources yet. Ask a question to populate sources.*",
            elem_classes=["sources-content", "bilingual-text"]
        )
    
    return {
        'sources_accordion': sources_accordion,
        'refresh_sources_btn': refresh_sources_btn,
        'export_sources_btn': export_sources_btn,
        'sources_md': sources_md
    }

def create_sentence_parser_section():
    """Create a small sentence parser input section for the Chat tab"""
    with gr.Column(elem_classes=["content-card"]):
        gr.Markdown(
            """
            ### 🔍 文解析 • Sentence Parser
            Paste a Classical Japanese sentence to get a morphological breakdown, particles/auxiliaries, and brief translation.
            """,
            elem_classes=["section-header"]
        )
        sentence_input = gr.Textbox(
            label="文 • Sentence",
            placeholder="例：花の色は移りにけりないたづらに",
            lines=2,
            elem_classes=["enhanced-input"]
        )
        with gr.Row():
            analyze_btn = gr.Button(
                "解析 • Analyze",
                variant="primary",
                elem_classes=["btn-primary"]
            )
        parser_output = gr.Markdown(
            label="解析結果 • Analysis",
            elem_classes=["explanation-card"]
        )
    return {
        'sentence_input': sentence_input,
        'analyze_btn': analyze_btn,
        'parser_output': parser_output
    }

def create_notes_interface(add_note_function):
    """Create enhanced notes interface"""
    
    with gr.Column(elem_classes=["notes-container", "content-card"]):
        gr.Markdown(
            """
            ### 📝 学習ノート • Study Notes
            Add personal notes and observations about your Classical Japanese studies.
            """,
            elem_classes=["section-header"]
        )
        
        note_input = gr.Textbox(
            label="ノート内容 • Note Content",
            lines=4,
            placeholder="ここに学習ノートを追加してください • Add your study notes here...",
            elem_classes=["enhanced-textarea"]
        )
        
        topic_input = gr.Textbox(
            label="トピック・カテゴリ • Topic/Category",
            placeholder="例：助詞、動詞活用、敬語 • e.g., particles, verb conjugation, keigo",
            elem_classes=["enhanced-input"]
        )
        
        add_btn = gr.Button(
            "📝 ノート追加 • Add Note",
            variant="primary",
            elem_classes=["btn-primary"]
        )
        
        note_output = gr.Textbox(
            label="状態 • Status",
            elem_classes=["status-display"]
        )
        
        return {
            'note_input': note_input,
            'topic_input': topic_input,
            'add_btn': add_btn,
            'note_output': note_output
        }

def create_dashboard_interface(get_database_stats):
    """Create progress tracking dashboard"""
    
    with gr.Column(elem_classes=["dashboard-container"]):
        gr.Markdown(
            """
            # 📊 学習ダッシュボード • Learning Dashboard
            Track your progress and manage your study materials.
            """,
            elem_classes=["dashboard-header"]
        )
        
        # Statistics cards
        with gr.Row(equal_height=True):
            with gr.Column(elem_classes=["stat-card"]):
                total_docs_display = gr.Markdown(
                    "**📚 総文書数 • Total Documents**\n\nLoading...",
                    elem_classes=["stat-content"]
                )
            
            with gr.Column(elem_classes=["stat-card"]):
                study_time_display = gr.Markdown(
                    "**⏰ 学習時間 • Study Time**\n\nToday: 0 min\nTotal: 0 min",
                    elem_classes=["stat-content"]
                )
            
            with gr.Column(elem_classes=["stat-card"]):
                grammar_points_display = gr.Markdown(
                    "**📖 文法項目 • Grammar Points**\n\nStudied: 0\nMastered: 0",
                    elem_classes=["stat-content"]
                )
        
        # Quick actions
        with gr.Row():
            gr.Markdown("### 🚀 クイックアクション • Quick Actions")
        
        with gr.Row():
            refresh_stats_btn = gr.Button(
                "🔄 統計更新 • Refresh Stats",
                variant="primary",
                elem_classes=["btn-primary"]
            )
            backup_btn = gr.Button(
                "💾 バックアップ • Backup",
                variant="secondary",
                elem_classes=["btn-secondary"]
            )
            health_check_btn = gr.Button(
                "🏥 ヘルスチェック • Health Check",
                variant="secondary",
                elem_classes=["btn-secondary"]
            )
        
        return {
            'total_docs_display': total_docs_display,
            'study_time_display': study_time_display,
            'grammar_points_display': grammar_points_display,
            'refresh_stats_btn': refresh_stats_btn,
            'backup_btn': backup_btn,
            'health_check_btn': health_check_btn
        }

def create_seasonal_theme_selector():
    """Create seasonal theme selector with preview"""
    
    with gr.Row():
        with gr.Column(scale=8):
            pass  # Spacer
        with gr.Column(scale=2):
            theme_dropdown = gr.Dropdown(
                choices=[f"{data['name']}" for data in SEASONAL_THEMES.values()],
                value="🌸 Spring Sakura",
                label="🎨 季節テーマ • Seasonal Theme",
                elem_classes=["theme-selector"]
            )
    
    return theme_dropdown
