# 🎌 Classical Japanese Learning Assistant - Feature Roadmap

## 🎯 Vision
Transform this from a basic RAG assistant into the ultimate Classical Japanese learning platform - think "Duolingo meets Ancient Japan with AI superpowers"

## ✅ Completed Features (Latest Update: 2025-01)
*These have been successfully implemented!*

### **Real-time Response Streaming** ⚡
- ✅ Token-by-token streaming for all model responses
- ✅ No more waiting for complete generation
- ✅ Instant feedback as the AI thinks
- **Status: COMPLETE** - Smooth streaming experience

### **Thinking Mode Visualization** 🧠
- ✅ Support for reasoning models (qwen3, deepseek-r1, etc.)
- ✅ Collapsible accordion shows AI's thought process
- ✅ Clean separation between thinking and answer content
- ✅ Tag-aware parser handles both `<think>` and `<thinking>` formats
- **Status: COMPLETE** - Full thinking/answer separation

### **Code Quality & Cleanup** 🧹
- ✅ Removed excessive debug logging
- ✅ Cleaned up unused imports and variables
- ✅ Simplified settings interface
- ✅ Optimized component routing
- **Status: COMPLETE** - Production-ready code

### **Critical Bug Fixes** 🐛
- ✅ **Missing streamed citations**: Sources now properly appear in final responses
- ✅ **Division by zero protection**: Guards added for empty search results
- ✅ **Empty database handling**: Graceful messages when no documents indexed
- ✅ **Model selection guard**: Clear error when no model selected
- ✅ **Image metadata fix**: Uploaded images get proper source/page information
- ✅ **OCR crash protection**: Blank images no longer crash deskew process
- ✅ **Session isolation**: Stop button races between users eliminated
- ✅ **OCR fallback robustness**: Page-level error handling with quality fallbacks
- ✅ **Performance optimization**: Database stats queries optimized for large datasets
- ✅ **Cleanup precision**: Only deletes PNG files created by current job
- **Status: COMPLETE** - 10 critical issues resolved across stability, safety, and performance

## Priority 1: Core Learning Enhancements 🔥
*These directly improve your learning experience*

### 0. **Hybrid Knowledge System** ⚡ NEW
- Intelligent routing between textbook knowledge and model's classical literature knowledge
- Question classifier detects grammar vs literature vs hybrid queries
- Enhanced responses combining textbook accuracy with real literary examples
- Smart source indicators showing exactly what knowledge was used
- **Impact: VERY HIGH** - Unlocks model's deep classical Japanese training while maintaining textbook accuracy
- **Implementation Plan**: 4-phase rollout with question classification, routing engine, hybrid prompts, and enhanced UI

#### Decision Matrix (Routing)
- **RAG**: Strong textbook hits (Top‑K density high, avg distance ≤ τ) and question is grammar/meta → cite textbooks only.
- **LLM General**: Low textbook hits and question requests literature/examples beyond textbooks → allow general knowledge with clear “General” banner, no textbook citations.
- **Hybrid**: Medium textbook hits or mixed query → combine RAG + general; clearly separate and label each.

#### Guardrails
- Prefer textbook content; do not attach textbook citations to claims derived from general knowledge.
- Label and separate “General Knowledge” content from “Textbook‑grounded” content in the answer.
- Refuse or minimize out‑of‑scope requests when both RAG and general signals are weak; ask for clarifying context.

#### Metrics & Thresholds (Tunable)
- Hit density: fraction of Top‑K with distance ≤ 0.40 (start), adjustable via settings.
- Diversity: distinct sources among Top‑K (≥ 2 preferred for high confidence).
- Router confidence: simple score from density + diversity; shown in UI header.

#### Evaluation
- Log route decision, hit metrics, knowledge mix (e.g., “Textbook 80% / General 20%”).
- Collect thumbs up/down and brief reason; compare by route.
- A/B against RAG‑only baseline to tune thresholds.

#### Phase Breakdown
1) Classifier + Signals: keyword heuristics + retrieval metrics produce route + confidence.
2) Routing + Guardrails: enforce output policy (citations only for textbook claims; “General” banner for others).
3) Hybrid Prompt & UI: prompt sections (Retrieved Context, General Knowledge, Synthesis Policy) and header indicator “Source Mode: RAG | General | Hybrid”.
4) Quality Loop: telemetry, user feedback, threshold tuning and documentation.

### 1. **Interactive Sentence Parser** 
- Click any sentence to see grammatical breakdown
- Color-coded particles, verbs, auxiliaries
- Hover for explanations
- **Impact: HIGH** - Makes texts instantly understandable

### 2. **Spaced Repetition System (SRS)**
- Auto-extract vocabulary/grammar from your readings
- Smart flashcards that know what you struggle with
- Daily review sessions
- **Impact: HIGH** - Proven memory retention

### 3. **Dictionary Integration**
- Hover over any word for instant definition
- Historical etymology included
- Links to grammar explanations
- **Impact: HIGH** - Removes lookup friction

#### 3.a Public Dictionary Integration (JMdict/KANJIDIC2) — Plan
- Data sources:
  - JMdict (EDICT successor) for modern Japanese vocabulary (CC BY‑SA license, via EDRDG)
  - KANJIDIC2 for kanji readings, meanings, stroke counts (CC BY‑SA, via EDRDG)
  - Optional later: classical filters via JMdict misc tags (e.g., “arch” for archaic) and custom classical addenda
- Distribution format:
  - Keep originals in `data/dicts/raw/` (XML)
  - Convert to normalized JSON in `data/dicts/json/` with schema: `headword`, `reading`, `gloss[]`, `pos[]`, `tags[]`, `source`, `licenses`
  - Store LICENSE and attribution alongside converted JSON
- Pipeline:
  - Script `scripts/fetch_dicts.py` downloads latest JMdict_e and KANJIDIC2 from official mirrors
  - Script `scripts/convert_jmdict.py` converts XML → JSON (multi‑sense flattening, POS/tags normalization, classical tag extraction)
  - Versioning with date stamp; do not commit raw XML to repo by default
- App integration:
  - Settings → “Load Public Dictionary”: one‑click fetch + convert + load into memory index (uses existing lookup UI)
  - Toggle: “Classical only” (filters by archaic/older‑kana tags when available)
  - Fuzzy search fallback (optional) when exact/substring misses
- Performance & storage:
  - In‑memory index with NFKC normalization; shard by headword initial for fast prefix search
  - Optional vector index for gloss search reuse (small model; opt‑in)
- Legal & UX:
  - About/Settings page shows CC BY‑SA attribution for EDRDG datasets and links to licenses
  - Respect license on export (include attribution in exported snippets)


### 4. **Progress Tracking Dashboard**
- Study streaks, time spent, passages read
- Grammar points mastered
- Vocabulary growth chart
- **Impact: MEDIUM** - Motivation through gamification

## Priority 2: Beautiful UX/UI 🌸
*Make it a joy to use*

### 5. **Japanese-Inspired Themes**
- Sakura (spring cherry blossoms)
- Sumi-e (ink wash painting)
- Autumn leaves
- Heian court aesthetic
- **Impact: MEDIUM** - Aesthetic pleasure enhances learning

### 6. **Vertical Text Display**
- Toggle between horizontal/vertical
- Authentic classical text experience
- Proper furigana placement
- **Impact: MEDIUM** - Authenticity matters

### 7. **Mobile Responsive Design**
- Study on your phone/tablet
- Swipe through flashcards
- Touch-friendly interface
- **Impact: HIGH** - Learn anywhere

## Priority 3: Advanced Learning Tools 🚀
*Next-level features*

### 8. **AI Practice Generator**
- Generate exercises based on grammar you're learning
- Create similar sentences to ones you're reading
- Difficulty adjustment
- **Impact: HIGH** - Unlimited practice material

### 9. **Furigana Recognition**
- OCR that captures reading aids
- Toggle furigana on/off
- Add your own furigana
- **Impact: MEDIUM** - Better for beginners

### 10. **Side-by-Side Translation**
- Modern Japanese translation
- English translation
- Synchronized scrolling
- **Impact: MEDIUM** - Multiple perspectives

### 11. **Audio Pronunciation**
- Text-to-speech for classical pronunciation
- Record yourself for comparison
- Pitch accent notation
- **Impact: LOW** - Nice to have

## Priority 4: Recovery & Resilience 🔧
*Handle interruptions and failures gracefully*

### 12. **OCR Processing Recovery**
- Resume interrupted OCR processing from last saved state
- Incremental save progress every N pages
- Ability to continue from existing PNG files
- **Impact: HIGH** - Prevents data loss on large PDFs

### 13. **Import Orphaned JSON Files**
- Detect JSON files not in database
- One-click import of processed but not imported files
- Batch import multiple JSON files
- **Impact: MEDIUM** - Useful for recovery scenarios

### 14. **Processing Queue Management**
- Visual queue for multiple document processing
- Pause/resume processing
- Retry failed documents
- **Impact: MEDIUM** - Better UX for bulk imports

## Priority 5: Content & Community 🤝
*Expand beyond your textbook*

### 15. **Pre-loaded Classical Texts**
- Tale of Genji excerpts
- Kokinshū poems
- Heike Monogatari passages
- All public domain, pre-analyzed
- **Impact: HIGH** - Instant content library

### 16. **Community Features**
- Share annotations
- Discussion threads on passages
- Upvote best explanations
- **Impact: LOW** - Requires user base

### 17. **Anki Export**
- One-click export to Anki
- Pre-formatted cards
- Include context sentences
- **Impact: MEDIUM** - Integrates with existing tools

## Priority 6: Specialized Tools 📚
*For serious scholars*

### 18. **Poetry Analysis**
- Meter detection (5-7-5-7-7)
- Kakekotoba (pivot words) highlighting
- Makurakotoba (pillow words) database
- **Impact: LOW** - Niche but powerful

### 19. **Manuscript Viewer**
- Load images of original texts
- Overlay your transcription
- Compare different manuscripts
- **Impact: LOW** - For researchers

### 20. **Grammar Timeline**
- Visualize how grammar evolved
- From Old Japanese to Modern
- Interactive examples
- **Impact: LOW** - Educational but complex

### 21. **Handwriting Practice**
- Draw characters with finger/stylus
- Stroke order guides
- Historical character variants (hentaigana)
- **Impact: LOW** - Specialized skill

## 🎨 UI/UX Overhaul - Modern Japanese-Inspired Design ✅ COMPLETE
*Transform the app into a beautiful, cohesive learning environment*

### **Phase 1: Foundation** 🏗️ ✅ COMPLETE
- ✅ Create custom Gradio theme with Japanese color palette (indigo, cherry blossom pink, gold)
- ✅ Redesign main navigation structure (Learning Hub, Document Management, System)
- ✅ Implement improved typography and spacing with Japanese-optimized fonts
- ✅ Add basic animations and transitions between states
- **Status: COMPLETE** - Dark mode theme with cultural aesthetics

### **Phase 2: Content Enhancement** 📋 ✅ COMPLETE
- ✅ Redesign chat interface with better information hierarchy and bilingual support
- ✅ Create card-based grammar search results with interactive examples
- ✅ Build interactive source viewer with shared sources between chat and grammar tabs
- ✅ Implement dashboard with progress cards (document stats, health checks, backup functions)
- **Status: COMPLETE** - Enhanced content presentation with full functionality

### **Phase 3: Interactive Features** ✨ ✅ COMPLETE
- ✅ Add hover previews and interactive grammar examples
- ✅ Implement micro-animations and loading states with cultural elements
- ✅ Create seasonal theme variations (Sakura, Momiji, Yuki, Natsu)
- ✅ Add cultural flourishes (sakura patterns, traditional Japanese colors)
- **Status: COMPLETE** - Beautiful interactive elements with Japanese aesthetics

### **Phase 4: Polish & Optimization** 🚀 ✅ COMPLETE
- ✅ Mobile responsiveness improvements with overflow controls
- ✅ Performance optimizations and proper error handling
- ✅ Accessibility enhancements (focus indicators, high contrast)
- ✅ User testing completed and all issues resolved
- **Status: COMPLETE** - Production-ready with all functionality working

### **🎌 Implementation Highlights (2025-08-28)**
- **Beautiful Dark Mode**: High contrast theme with Japanese color palette
- **Bilingual Interface**: All text in Japanese and English throughout
- **Consolidated Navigation**: Learning Hub, Document Management, System tabs
- **Enhanced Functionality**: Working stop buttons, PNG management, model indicators
- **Cultural Elements**: Sakura patterns, traditional colors, Japanese typography
- **Responsive Design**: No scroll bar issues, proper mobile support
- **Full Feature Parity**: All original functionality preserved and enhanced

## 🎮 Quick Wins (Do These First!)
1. **Dictionary hover** - Relatively easy, huge impact
2. **Beautiful theme** - CSS changes, instant improvement  
3. **Progress tracking** - Motivational, not too complex
4. **Sentence parser** - Most requested feature
5. **Pre-loaded texts** - Immediate value add

## 🔬 Technical Enhancements Needed
- Switch to PostgreSQL for better performance
- Add Redis for caching
- Implement user authentication system
- Deploy to cloud (Hugging Face Spaces?)
- Add real-time collaboration features

## 💡 "Coolness Factor" Ideas
- **AI Study Buddy**: Conversational partner who speaks in classical Japanese
- **Time Machine Mode**: See how a text would be written in different eras
- **AR Mode**: Point phone at classical text for instant translation overlay
- **Daily Classical Haiku**: AI generates a classical poem based on modern events
- **Virtual Heian Court**: Gamified environment where you "level up" in court ranks

## 📊 Success Metrics
- Daily active usage time
- Vocabulary retention rate
- Grammar points mastered
- User satisfaction score
- Community engagement

## 🚦 Next Steps
1. **Hybrid Knowledge System** - Ready for implementation review
   - Phase 1: Question classifier with keyword detection
   - Phase 2: Knowledge source router with UI controls  
   - Phase 3: Hybrid query engine combining both sources
   - Phase 4: Enhanced source indicators and literature prompts
2. Pick 2-3 additional features from Priority 1
3. Create GitHub issues for each selected feature
4. Set up development branches
5. Build MVP of each feature
6. Get user feedback and iterate

---

## 🧠 Hybrid Knowledge System - Detailed Implementation Plan

### **Technical Architecture**

**New Files to Create**:
- `question_classifier.py` - Classify questions as TEXTBOOK/LITERATURE/HYBRID/AUTO
- `knowledge_router.py` - Route to appropriate knowledge source
- `prompts/literature_expert.md` - Literature-focused prompt template
- `prompts/hybrid_expert.md` - Combined textbook + literature prompt

**Enhanced Files**:
- `rag_assistant.py` - Add hybrid query methods
- `app.py` - UI controls for knowledge source selection
- `ui_components.py` - Enhanced source indicators

### **Phase 1: Question Classification Engine** (Week 1)
```python
# question_classifier.py
class QuestionClassifier:
    LITERARY_KEYWORDS = ['poem', 'poetry', 'genji', 'tale', 'kokin', 'manyou', 'author', 'work']
    GRAMMAR_KEYWORDS = ['particle', 'auxiliary', 'conjugation', 'tense', 'form', 'grammar']
    HYBRID_KEYWORDS = ['example', 'usage', 'appears', 'used in', 'how does', 'literature']
    
    def classify(self, question: str) -> str:
        # Returns: "TEXTBOOK", "LITERATURE", "HYBRID", or "AUTO"
```

### **Phase 2: Knowledge Source Router** (Week 2)  
```python
# Enhanced rag_assistant.py
def query_hybrid_stream(self, message, knowledge_mode="auto"):
    if knowledge_mode == "auto":
        knowledge_mode = self.classifier.classify(message)
    
    if knowledge_mode == "HYBRID":
        return self._query_with_both_sources(message)
    elif knowledge_mode == "LITERATURE": 
        return self._query_model_literature(message)
    else:
        return self._query_textbook_only(message)
```

### **Phase 3: Hybrid Query Engine** (Week 3)
- Two-stage approach: Get textbook context, then enhance with model knowledge
- Literature-aware prompting that encourages classical text citations
- Smart source attribution showing both textbook pages AND literary works

### **Phase 4: Enhanced UI & Indicators** (Week 4)
- Knowledge source selector in chat interface
- Enhanced source display with textbook + literature sections
- Color-coded indicators for different knowledge types

### **Success Criteria**
1. ✅ User asks grammar question → Gets textbook explanation + literary examples
2. ✅ User asks about specific classical work → Gets rich model knowledge response  
3. ✅ User sees clear indication of knowledge sources used
4. ✅ Responses are more comprehensive without losing accuracy

**Ready to proceed with implementation?**
