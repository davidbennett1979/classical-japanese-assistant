"""
Question Classification and Routing for Hybrid Knowledge System

Classifies user questions to route between:
- RAG: Strong textbook hits for grammar/structured content
- General: Model knowledge for literature/cultural content  
- Hybrid: Combined approach with clear separation
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    """Results of question classification"""
    route: str  # "RAG", "GENERAL", "HYBRID"
    confidence: float  # 0.0-1.0
    keyword_signals: Dict[str, List[str]]  # matched keywords by category
    retrieval_metrics: Optional[Dict[str, float]] = None  # hit density, diversity, etc.
    explanation: str = ""  # human-readable reasoning

class QuestionClassifier:
    """Hybrid knowledge system question classifier"""
    
    # Keyword categories for classification
    GRAMMAR_KEYWORDS = [
        'particle', 'auxiliary', 'conjugation', 'tense', 'form', 'grammar', 'rule',
        'ending', 'suffix', 'prefix', 'inflection', 'case', 'aspect', 'mood',
        '助詞', '助動詞', '活用', '語尾', '文法', 'けり', 'なり', 'たり', 'ぬ', 'つ'
    ]
    
    LITERATURE_KEYWORDS = [
        'poem', 'poetry', 'genji', 'tale', 'kokin', 'manyou', 'author', 'work',
        'heian', 'kamakura', 'court', 'culture', 'emperor', 'empress', 'novel',
        'chronicle', 'diary', 'sei shonagon', 'murasaki', 'basho', 'issa',
        '歌', '詩', '物語', '日記', '源氏', '枕草子', '万葉', '古今', '新古今',
        '作者', '天皇', '中宮', '宮廷', '文化', '平安', '鎌倉'
    ]
    
    HYBRID_KEYWORDS = [
        'example', 'usage', 'appears', 'used in', 'how does', 'literature', 'context',
        'meaning', 'interpretation', 'analysis', 'compare', 'difference', 'similar',
        'explain', 'clarify', 'demonstrate', 'illustrate', 'show me',
        '例', '使用', '用法', '意味', '解釈', '分析', '説明', '例示', '違い', '比較'
    ]
    
    # Patterns that suggest need for general knowledge
    GENERAL_PATTERNS = [
        r'tell me about',
        r'what do you know about',
        r'background of',
        r'history of',
        r'who (was|is)',
        r'when (was|did)',
        r'cultural significance',
        r'influence of'
    ]
    
    def __init__(self, 
                 hit_density_threshold: float = 0.40,
                 diversity_min_sources: int = 2,
                 distance_threshold: float = 0.40):
        """Initialize classifier with tunable thresholds"""
        self.hit_density_threshold = hit_density_threshold
        self.diversity_min_sources = diversity_min_sources  
        self.distance_threshold = distance_threshold
        
    def classify_keywords(self, question: str) -> Dict[str, List[str]]:
        """Classify question based on keyword matching"""
        question_lower = question.lower()
        
        signals = {
            'grammar': [],
            'literature': [], 
            'hybrid': [],
            'general_patterns': []
        }
        
        # Check grammar keywords
        for keyword in self.GRAMMAR_KEYWORDS:
            if keyword.lower() in question_lower:
                signals['grammar'].append(keyword)
                
        # Check literature keywords  
        for keyword in self.LITERATURE_KEYWORDS:
            if keyword.lower() in question_lower:
                signals['literature'].append(keyword)
                
        # Check hybrid keywords
        for keyword in self.HYBRID_KEYWORDS:
            if keyword.lower() in question_lower:
                signals['hybrid'].append(keyword)
                
        # Check general patterns
        for pattern in self.GENERAL_PATTERNS:
            if re.search(pattern, question_lower):
                signals['general_patterns'].append(pattern)
                
        return signals
    
    def calculate_retrieval_metrics(self, search_results: List[Dict]) -> Dict[str, float]:
        """Calculate retrieval quality metrics"""
        if not search_results:
            return {
                'hit_density': 0.0,
                'avg_distance': 1.0,
                'source_diversity': 0.0,
                'top_k_count': 0
            }
            
        # Calculate hit density (fraction with distance ≤ threshold)
        good_hits = [r for r in search_results if r.get('distance', 1.0) <= self.distance_threshold]
        hit_density = len(good_hits) / len(search_results)
        
        # Calculate average distance
        distances = [r.get('distance', 1.0) for r in search_results]
        avg_distance = sum(distances) / len(distances)
        
        # Calculate source diversity (distinct sources)
        sources = set()
        for result in search_results:
            metadata = result.get('metadata', {})
            source = metadata.get('source', 'unknown')
            sources.add(source)
        source_diversity = len(sources)
        
        return {
            'hit_density': hit_density,
            'avg_distance': avg_distance, 
            'source_diversity': source_diversity,
            'top_k_count': len(search_results)
        }
    
    def classify_with_retrieval(self, 
                               question: str, 
                               search_results: List[Dict] = None) -> ClassificationResult:
        """Main classification method combining keywords and retrieval metrics"""
        
        # Get keyword signals
        keyword_signals = self.classify_keywords(question)
        
        # Calculate retrieval metrics if provided
        retrieval_metrics = {}
        if search_results is not None:
            retrieval_metrics = self.calculate_retrieval_metrics(search_results)
        
        # Classification logic based on your decision matrix
        route, confidence, explanation = self._route_decision(
            keyword_signals, retrieval_metrics
        )
        
        return ClassificationResult(
            route=route,
            confidence=confidence,
            keyword_signals=keyword_signals,
            retrieval_metrics=retrieval_metrics,
            explanation=explanation
        )
    
    def _route_decision(self, 
                       keyword_signals: Dict[str, List[str]], 
                       retrieval_metrics: Dict[str, float]) -> Tuple[str, float, str]:
        """Decision matrix implementation"""
        
        # Extract metrics with defaults
        hit_density = retrieval_metrics.get('hit_density', 0.0)
        source_diversity = retrieval_metrics.get('source_diversity', 0.0)
        avg_distance = retrieval_metrics.get('avg_distance', 1.0)
        
        # Count keyword signals
        grammar_signals = len(keyword_signals.get('grammar', []))
        literature_signals = len(keyword_signals.get('literature', []))
        hybrid_signals = len(keyword_signals.get('hybrid', []))
        general_patterns = len(keyword_signals.get('general_patterns', []))
        
        # Decision matrix logic
        
        # RAG: Strong textbook hits + grammar focus
        if (hit_density >= self.hit_density_threshold and 
            source_diversity >= self.diversity_min_sources and
            grammar_signals > 0 and
            general_patterns == 0):
            
            confidence = min(0.9, 0.5 + hit_density * 0.4 + min(grammar_signals, 3) * 0.1)
            explanation = f"Strong textbook hits ({hit_density:.2f} density, {source_diversity} sources) + grammar focus"
            return "RAG", confidence, explanation
            
        # GENERAL: Low textbook hits + literature/cultural request
        elif (hit_density < 0.2 and 
              (literature_signals > 0 or general_patterns > 0)):
            
            confidence = min(0.8, 0.4 + (literature_signals + general_patterns) * 0.15)
            explanation = f"Low textbook relevance ({hit_density:.2f} density) + literature/cultural focus"
            return "GENERAL", confidence, explanation
            
        # HYBRID: Medium hits OR mixed signals OR explicit hybrid keywords
        elif (hybrid_signals > 0 or
              (0.2 <= hit_density < self.hit_density_threshold) or
              (grammar_signals > 0 and literature_signals > 0)):
            
            confidence = 0.3 + hit_density * 0.3 + hybrid_signals * 0.1
            explanation = f"Mixed signals or medium textbook relevance ({hit_density:.2f} density)"
            return "HYBRID", confidence, explanation
            
        # Fallback: Default to HYBRID with low confidence
        else:
            confidence = 0.2 + hit_density * 0.2
            explanation = f"Unclear signals, defaulting to hybrid approach"
            return "HYBRID", confidence, explanation
    
    def update_thresholds(self, 
                         hit_density_threshold: float = None,
                         diversity_min_sources: int = None, 
                         distance_threshold: float = None):
        """Update classification thresholds (for tuning)"""
        if hit_density_threshold is not None:
            self.hit_density_threshold = hit_density_threshold
        if diversity_min_sources is not None:
            self.diversity_min_sources = diversity_min_sources
        if distance_threshold is not None:
            self.distance_threshold = distance_threshold
            
        logger.info(f"Updated thresholds: density={self.hit_density_threshold}, "
                   f"diversity={self.diversity_min_sources}, distance={self.distance_threshold}")