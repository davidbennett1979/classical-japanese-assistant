# 🎌 Classical Japanese Learning Assistant - Feature Roadmap

## 🎯 **Vision**
Transform this from a basic RAG assistant into the ultimate Classical Japanese learning platform - think **"Duolingo meets Ancient Japan with AI superpowers"**

---

## ✅ **What We've Built** (Production-Ready)

### **🧠 Hybrid Knowledge System** - *The Game Changer*
- **AUTO**: Intelligently routes between textbook and model knowledge
- **RAG**: Pure textbook accuracy with citations
- **GENERAL**: Model's deep classical literature knowledge  
- **HYBRID**: Combined approach with clear separation
- **Analytics**: Route confidence, usage statistics, A/B testing foundation

### **⚡ Core Infrastructure** 
- **Streaming**: Real-time token-by-token responses
- **Thinking Models**: Support for reasoning models with collapsible thought process
- **Beautiful UI**: Dark mode with Japanese aesthetics, seasonal themes
- **Bilingual**: Japanese/English throughout
- **Robust**: 10+ critical bugs fixed, production-ready error handling

---

## 🔥 **High-Priority Features** (Next 3-6 months)

### **1. Interactive Sentence Parser** 
*Click any sentence for instant grammatical breakdown*
- Color-coded particles, verbs, auxiliaries
- Hover explanations with literary context
- **Why**: Makes classical texts instantly understandable

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

### **7. Vertical Text Display**
- Authentic classical reading experience
- Toggle horizontal/vertical
- Proper furigana placement
- **Why**: Cultural authenticity matters

---

## 🚀 **Advanced Features** (Future Vision)

### **Content Library**
- **Pre-loaded Classics**: Tale of Genji, Kokinshū, Heike Monogatari excerpts
- **Audio Pronunciation**: Classical pronunciation with pitch accent
- **Translation Views**: Side-by-side modern Japanese and English

### **Scholarly Tools**
- **Poetry Analysis**: Meter detection, kakekotoba highlighting
- **Manuscript Viewer**: Original text overlays
- **Grammar Evolution**: Historical timeline of language changes

### **Social Learning**
- **Anki Export**: One-click flashcard export
- **Community Features**: Share annotations, discussions (when we have users)

---

## 🔧 **Technical Infrastructure** (As Needed)

### **Performance & Scale**
- PostgreSQL migration (when we outgrow ChromaDB)
- Redis caching layer
- Cloud deployment (Hugging Face Spaces?)

### **Resilience**
- OCR processing recovery (resume interrupted jobs)
- Processing queue management
- Orphaned file recovery (already implemented)

---

## 💡 **"Coolness Factor" Ideas** (Blue Sky)

- **AI Study Buddy**: Conversational partner in classical Japanese
- **Time Machine Mode**: See how text evolved across eras  
- **AR Mode**: Point phone at classical text for instant overlay
- **Virtual Heian Court**: Gamified learning with court ranks
- **Daily Classical Haiku**: AI generates poems about current events

---

## 📊 **Success Metrics**

**Learning Effectiveness**:
- Vocabulary retention rate
- Grammar points mastered per session
- Time to comprehension (sentence → understanding)

**Engagement**:
- Daily active usage time
- Study streak length
- Feature adoption rates

**Quality**:
- Routing accuracy (textbook vs model knowledge)
- User satisfaction scores
- Error rates and crash reports

---

## 🎯 **Next Steps**

**Immediate (Next 2 weeks)**:
1. **Sentence Parser**: Start with basic grammatical tagging
2. **Dictionary Integration**: Implement JMdict loading and hover lookup

**Short-term (Next month)**:
3. **SRS Foundation**: Design vocabulary extraction and scheduling
4. **Practice Generator**: Create grammar-focused exercise templates

**Medium-term (Next 3 months)**:
5. **Progress Dashboard**: Build comprehensive tracking system
6. **Mobile Polish**: Optimize for phone/tablet usage

**Continuous**:
- Monitor hybrid system performance and tune thresholds
- Collect user feedback and iterate
- A/B test new features against baseline

---

## 🏷️ **Current Status**: *Hybrid Knowledge System Complete*
✅ **Production-ready** with intelligent routing between textbook accuracy and model's classical literature knowledge

Ready to tackle the next high-impact feature! 🚀