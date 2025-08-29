import gradio as gr

# Dark Mode Japanese-inspired color palette
JAPANESE_COLORS = {
    # Primary colors - adjusted for dark mode
    "indigo": "#6366f1",      # Brighter indigo for dark backgrounds
    "sakura": "#f472b6",      # Vibrant pink for visibility
    "gold": "#fbbf24",        # Bright gold accent
    
    # Dark mode backgrounds
    "dark_primary": "#0f0f23",    # Very dark blue-black
    "dark_secondary": "#1a1a2e",  # Dark blue-gray
    "dark_surface": "#16213e",    # Card surfaces
    "dark_elevated": "#233253",   # Elevated surfaces
    
    # Text colors for dark mode
    "text_primary": "#f8fafc",    # Almost white
    "text_secondary": "#cbd5e1",  # Light gray
    "text_muted": "#94a3b8",      # Muted gray
    "text_accent": "#f472b6",     # Pink accent text
    
    # Supporting colors
    "deep_blue": "#3b82f6",       # Bright blue
    "light_sakura": "#fda4af",    # Lighter pink
    "white": "#ffffff",
    
    # Semantic colors - brighter for dark mode
    "success": "#10b981",         # Bright green
    "warning": "#f59e0b",         # Bright orange
    "error": "#ef4444",           # Bright red
    "info": "#3b82f6",            # Bright blue
    
    # Traditional colors adjusted
    "autumn": "#f59e0b",          # Bright autumn gold
    "moss": "#84cc16",            # Bright moss green
    "plum": "#c084fc",            # Bright plum
}

# Custom CSS for Dark Mode Japanese-inspired design
CUSTOM_CSS = f"""
/* Import Japanese font */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400;500;600;700&display=swap');

/* Root variables - Dark Mode */
:root {{
    --primary-color: {JAPANESE_COLORS['indigo']};
    --secondary-color: {JAPANESE_COLORS['sakura']};
    --accent-color: {JAPANESE_COLORS['gold']};
    --background-color: {JAPANESE_COLORS['dark_primary']};
    --surface-color: {JAPANESE_COLORS['dark_surface']};
    --elevated-color: {JAPANESE_COLORS['dark_elevated']};
    --text-primary: {JAPANESE_COLORS['text_primary']};
    --text-secondary: {JAPANESE_COLORS['text_secondary']};
    --text-muted: {JAPANESE_COLORS['text_muted']};
    --border-color: #374151;
    --border-radius: 0.5rem;
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    --shadow-elevated: 0 8px 15px -3px rgba(0, 0, 0, 0.4);
    --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}

/* Global styles - Dark Mode (handled below with overflow fixes) */

/* Override Gradio's default styles for dark mode */
.gradio-container .gr-textbox input,
.gradio-container .gr-textbox textarea,
.gradio-container .gr-dropdown,
.gradio-container .gr-number input,
.gradio-container .gr-file,
.gradio-container .gr-checkbox input {{
    background: var(--surface-color) !important;
    border: 2px solid var(--border-color) !important;
    color: var(--text-primary) !important;
}}

.gradio-container .gr-textbox input::placeholder,
.gradio-container .gr-textbox textarea::placeholder {{
    color: var(--text-muted) !important;
}}

.gradio-container .gr-textbox input:focus,
.gradio-container .gr-textbox textarea:focus {{
    border-color: var(--primary-color) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
}}

/* Additional dark mode overrides */
.gradio-container .gr-button,
.gradio-container button {{
    background: var(--surface-color) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-color) !important;
}}

.gradio-container .gr-button.primary,
.gradio-container button.primary {{
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color)) !important;
    color: {JAPANESE_COLORS['text_primary']} !important;
    border: none !important;
}}

.gradio-container .gr-markdown,
.gradio-container .markdown {{
    color: var(--text-primary) !important;
}}

.gradio-container .gr-accordion,
.gradio-container .accordion {{
    background: var(--surface-color) !important;
    border: 1px solid var(--border-color) !important;
}}

/* Tabs styling */
.gradio-container .gr-tab-nav,
.gradio-container .tab-nav {{
    background: var(--surface-color) !important;
    border: 1px solid var(--border-color) !important;
}}

.gradio-container .gr-tab-nav button,
.gradio-container .tab-nav button {{
    color: var(--text-secondary) !important;
    background: transparent !important;
}}

.gradio-container .gr-tab-nav button.selected,
.gradio-container .tab-nav button.selected {{
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color)) !important;
    color: {JAPANESE_COLORS['text_primary']} !important;
}}

/* Simple Static Header Block */
.header-container {{
    margin-bottom: 2rem;
}}

.simple-header {{
    background: linear-gradient(135deg, {JAPANESE_COLORS['indigo']}, {JAPANESE_COLORS['deep_blue']});
    padding: 2rem;
    text-align: center;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
    position: relative;
    display: block;
    width: 100%;
    box-sizing: border-box;
}}

.header-title {{
    font-family: 'Noto Serif JP', serif !important;
    font-size: 2rem !important;
    font-weight: 600 !important;
    margin: 0 0 0.5rem 0 !important;
    color: {JAPANESE_COLORS['text_primary']} !important;
    text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.5);
    line-height: 1.2 !important;
}}

.header-subtitle {{
    font-family: 'Noto Sans JP', sans-serif !important;
    font-size: 1.1rem !important;
    margin: 0 !important;
    color: {JAPANESE_COLORS['text_secondary']} !important;
    opacity: 0.9;
    font-weight: 300 !important;
    line-height: 1.4 !important;
}}

/* Ensure clean container without overflow issues */
.gradio-container {{
    font-family: 'Noto Sans JP', sans-serif !important;
    background: linear-gradient(135deg, {JAPANESE_COLORS['dark_primary']} 0%, {JAPANESE_COLORS['dark_secondary']} 100%);
    min-height: 100vh;
    color: var(--text-primary) !important;
    overflow-x: hidden !important;
}}

/* Clean up all elements */
* {{
    color: var(--text-primary) !important;
    box-sizing: border-box !important;
}}

/* Prevent weird iframe-like behavior */
.header-container, .simple-header {{
    position: static !important;
    height: auto !important;
    min-height: auto !important;
    overflow: visible !important;
}}

/* Tab styling - Dark Mode */
.tab-nav {{
    background: var(--surface-color);
    border-radius: var(--border-radius);
    padding: 0.25rem;
    margin-bottom: 1.5rem;
    box-shadow: var(--shadow-elevated);
    border: 1px solid var(--border-color);
}}

.tab-nav button {{
    background: transparent;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: calc(var(--border-radius) - 0.25rem);
    font-family: 'Noto Sans JP', sans-serif;
    font-weight: 500;
    color: var(--text-secondary) !important;
    transition: var(--transition);
    position: relative;
}}

.tab-nav button.selected {{
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    color: {JAPANESE_COLORS['text_primary']} !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
}}

.tab-nav button:hover:not(.selected) {{
    background: var(--elevated-color);
    color: var(--primary-color) !important;
}}

/* Card-based layout - Dark Mode */
.content-card {{
    background: var(--surface-color);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
    transition: var(--transition);
    color: var(--text-primary) !important;
}}

.content-card:hover {{
    box-shadow: var(--shadow-elevated);
    transform: translateY(-2px);
    border-color: var(--primary-color);
}}

/* Button styling - Dark Mode */
.btn-primary {{
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color)) !important;
    color: {JAPANESE_COLORS['text_primary']} !important;
    border: none !important;
    padding: 0.75rem 1.5rem;
    border-radius: var(--border-radius);
    font-family: 'Noto Sans JP', sans-serif;
    font-weight: 500;
    cursor: pointer;
    transition: var(--transition);
    box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
}}

.btn-primary:hover {{
    box-shadow: 0 4px 8px rgba(0,0,0,0.4) !important;
    transform: translateY(-1px);
}}

.btn-secondary {{
    background: var(--surface-color) !important;
    color: var(--primary-color) !important;
    border: 1px solid var(--primary-color) !important;
    padding: 0.75rem 1.5rem;
    border-radius: var(--border-radius);
    font-family: 'Noto Sans JP', sans-serif;
    font-weight: 500;
    cursor: pointer;
    transition: var(--transition);
}}

.btn-secondary:hover {{
    background: var(--primary-color) !important;
    color: {JAPANESE_COLORS['text_primary']} !important;
}}

/* Input field styling - Dark Mode (handled above in override section) */

/* Chat interface styling - Dark Mode */
.chat-container {{
    background: var(--surface-color);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    min-height: 400px;
    box-shadow: var(--shadow);
    border: 1px solid var(--border-color);
}}

.chat-message {{
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: var(--border-radius);
    animation: slideIn 0.3s ease-out;
}}

.chat-message.user {{
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    color: {JAPANESE_COLORS['text_primary']} !important;
    margin-left: 2rem;
}}

.chat-message.assistant {{
    background: var(--elevated-color);
    color: var(--text-primary) !important;
    margin-right: 2rem;
    border: 1px solid var(--border-color);
}}

/* Accordion styling for thinking content - Dark Mode */
.thinking-accordion {{
    background: var(--surface-color);
    border: 1px solid var(--secondary-color);
    border-radius: var(--border-radius);
    margin: 1rem 0;
}}

.thinking-header {{
    background: var(--secondary-color);
    color: {JAPANESE_COLORS['text_primary']} !important;
    padding: 0.75rem 1rem;
    font-weight: 500;
    cursor: pointer;
    border-radius: calc(var(--border-radius) - 1px);
}}

.thinking-content {{
    padding: 1rem;
    font-family: 'Noto Sans JP', monospace;
    font-size: 0.9rem;
    line-height: 1.6;
    color: var(--text-primary) !important;
    background: var(--elevated-color);
}}

/* Source citations - Dark Mode */
.source-card {{
    background: var(--surface-color);
    border: 1px solid var(--secondary-color);
    border-radius: var(--border-radius);
    padding: 1rem;
    margin: 0.5rem 0;
    transition: var(--transition);
}}

.source-card:hover {{
    border-color: var(--primary-color);
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
}}

.source-title {{
    font-weight: 600;
    color: var(--primary-color) !important;
    margin-bottom: 0.5rem;
}}

.source-text {{
    color: var(--text-secondary) !important;
    font-size: 0.9rem;
    line-height: 1.5;
}}

/* Progress indicators - Dark Mode */
.progress-ring {{
    width: 60px;
    height: 60px;
    border-radius: 50%;
    border: 3px solid var(--border-color);
    border-top-color: var(--primary-color);
    animation: spin 1s linear infinite;
    display: inline-block;
    margin: 0 auto;
}}

/* Cultural flourishes - Dark Mode */
.sakura-pattern {{
    position: relative;
    overflow: hidden;
}}

.sakura-pattern::before {{
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background-image: 
        radial-gradient(circle at 25% 25%, {JAPANESE_COLORS['light_sakura']}20 2px, transparent 2px),
        radial-gradient(circle at 75% 75%, {JAPANESE_COLORS['light_sakura']}20 1px, transparent 1px);
    background-size: 100px 100px, 50px 50px;
    opacity: 0.1;
    pointer-events: none;
    animation: float 20s linear infinite;
}}

/* Animations */
@keyframes slideIn {{
    from {{
        opacity: 0;
        transform: translateY(20px);
    }}
    to {{
        opacity: 1;
        transform: translateY(0);
    }}
}}

@keyframes spin {{
    to {{
        transform: rotate(360deg);
    }}
}}

@keyframes float {{
    from {{
        transform: translateY(100vh) rotate(0deg);
    }}
    to {{
        transform: translateY(-100vh) rotate(360deg);
    }}
}}

/* Responsive design */
@media (max-width: 768px) {{
    .app-title {{
        font-size: 2rem;
    }}
    
    .content-card {{
        padding: 1rem;
        margin-bottom: 1rem;
    }}
    
    .chat-message.user {{
        margin-left: 0;
    }}
    
    .chat-message.assistant {{
        margin-right: 0;
    }}
}}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }}
}}

/* Focus indicators for keyboard navigation */
button:focus, input:focus, textarea:focus {{
    outline: 3px solid {JAPANESE_COLORS['sakura']};
    outline-offset: 2px;
}}
"""

def create_japanese_theme():
    """Create a dark mode Gradio theme with Japanese aesthetics"""
    
    # Use dark theme as base with Japanese colors
    theme = gr.themes.Glass(
        primary_hue=gr.themes.colors.indigo,
        secondary_hue=gr.themes.colors.pink,
        neutral_hue=gr.themes.colors.slate,
    )
    
    return theme

# Seasonal theme variations
SEASONAL_THEMES = {
    "sakura": {
        "name": "🌸 Spring Sakura",
        "primary": "#ffb7c5",
        "secondary": "#ffd1dc", 
        "accent": "#ff69b4",
        "background": "#fef7f0"
    },
    "momiji": {
        "name": "🍂 Autumn Leaves", 
        "primary": "#d2691e",
        "secondary": "#daa520",
        "accent": "#cd853f",
        "background": "#fdf6e3"
    },
    "yuki": {
        "name": "❄️ Winter Snow",
        "primary": "#4682b4",
        "secondary": "#87ceeb", 
        "accent": "#1e90ff",
        "background": "#f8f9fa"
    },
    "natsu": {
        "name": "🌿 Summer Green",
        "primary": "#228b22",
        "secondary": "#90ee90",
        "accent": "#32cd32", 
        "background": "#f0fff0"
    }
}

def get_seasonal_css(season="sakura"):
    """Generate CSS for seasonal theme variations"""
    theme_colors = SEASONAL_THEMES.get(season, SEASONAL_THEMES["sakura"])
    
    return f"""
    :root {{
        --seasonal-primary: {theme_colors['primary']};
        --seasonal-secondary: {theme_colors['secondary']};
        --seasonal-accent: {theme_colors['accent']};
        --seasonal-background: {theme_colors['background']};
    }}
    
    .seasonal-theme {{
        background: linear-gradient(135deg, var(--seasonal-background) 0%, var(--seasonal-secondary)15 100%);
    }}
    
    .seasonal-accent {{
        color: var(--seasonal-primary);
    }}
    
    .seasonal-button {{
        background: linear-gradient(135deg, var(--seasonal-primary), var(--seasonal-secondary));
    }}
    
    /* Knowledge selector styles */
    .knowledge-selector .gradio-radio {{
        background: var(--surface-color);
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius);
        padding: 0.75rem;
    }}
    
    .knowledge-selector .gradio-radio label {{
        color: var(--text-primary);
        font-size: 13px;
        margin: 4px 0;
        cursor: pointer;
    }}
    
    .knowledge-selector .gradio-radio input[type="radio"]:checked + label {{
        color: var(--primary-color);
        font-weight: 600;
    }}
    
    .compact-radio {{
        max-height: 140px;
        overflow-y: auto;
    }}
    
    /* Radio button styling */
    .knowledge-selector input[type="radio"] {{
        accent-color: var(--primary-color);
        margin-right: 8px;
    }}
    """