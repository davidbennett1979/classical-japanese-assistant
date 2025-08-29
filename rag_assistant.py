import requests
import json
import os
import subprocess
from typing import List, Dict, Optional, Generator
import logging
from config import settings
from question_classifier import QuestionClassifier, ClassificationResult

class ClassicalJapaneseAssistant:
    def __init__(self, vector_store, model_name=None, prompt_file="prompts/classical_japanese_tutor.md"):
        self.vector_store = vector_store
        
        # If no model specified, try to get the first available model
        if model_name is None:
            model_name = self.get_first_available_model()
            if model_name:
                print(f"Using detected model: {model_name}")
            else:
                print("Warning: No Ollama models detected. Please install a model.")
        
        self.model_name = model_name
        self.ollama_url = settings.ollama_url
        self.session = requests.Session()
        self.prompt_template = self.load_prompt_template(prompt_file)
        
        # Thinking models configuration
        self.thinking_models = {
            'qwen3': True,  # QwQ reasoning models
            'qwq': True,    # Qwen with Questions
            'deepseek-r1': True,  # DeepSeek reasoning
            'o1': True,  # OpenAI o1 style
            'thinking': True,  # Generic thinking model indicator
        }
        
        # Initialize hybrid knowledge system
        self.classifier = QuestionClassifier()
        self.route_telemetry = []  # Log routing decisions for analysis
    
    def is_thinking_model(self, model_name=None):
        """Check if the current or specified model is a thinking/reasoning model"""
        name_to_check = (model_name or self.model_name or '').lower()
        for key in self.thinking_models:
            if key in name_to_check:
                return True
        return False
    
    def get_first_available_model(self):
        """Get the first available Ollama model"""
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header
                    # Get first model name from first data line
                    first_line = lines[1].strip()
                    if first_line:
                        model_name = first_line.split()[0]
                        return model_name
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error detecting Ollama models: {e}")
        return None
    
    def load_prompt_template(self, prompt_file: str) -> str:
        """Load prompt template from external file"""
        if os.path.exists(prompt_file):
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Fallback to basic prompt if file not found
            return self.get_default_prompt()
    
    def get_default_prompt(self) -> str:
        """Fallback prompt if external file not found"""
        return """You are an expert Classical Japanese tutor.

## Retrieved Context
{context}

## Question
{question}

## Response
Provide a clear, educational response with citations."""
        
    def create_prompt(self, query: str, context: List[Dict]) -> str:
        """Create a detailed prompt with retrieved context"""
        
        # Format context section
        if context:
            context_str = ""
            for i, ctx in enumerate(context):
                source = ctx['metadata'].get('source', 'unknown')
                page = ctx['metadata'].get('page', 'N/A')
                context_str += f"\n[{i+1}] Source: {source}, Page: {page}\n"
                context_str += f"Content: {ctx['text']}\n"
                context_str += "-" * 40 + "\n"
        else:
            # No database context available
            context_str = "\n[No documents in database - using general knowledge only]\n"
        
        # Replace placeholders in template
        prompt = self.prompt_template.replace('{context}', context_str)
        prompt = prompt.replace('{question}', query)
        
        return prompt
    
    def query(self, question: str, n_results: int = 3) -> Dict:
        """Main query method"""
        
        # Search vector store
        search_results = self.vector_store.search(question, n_results=n_results)
        
        # Check for empty results and prepare context
        context = []
        has_database_results = search_results['documents'] and search_results['documents'][0]
        
        if has_database_results:
            # Prepare context from database results
            for i in range(len(search_results['documents'][0])):
                context.append({
                    'text': search_results['documents'][0][i],
                    'metadata': search_results['metadatas'][0][i],
                    'distance': search_results['distances'][0][i]
                })
        
        # Create prompt (with or without context)
        prompt = self.create_prompt(question, context)
        
        # Determine timeout based on model size
        # Larger models need more time for initial loading and generation
        timeout = 30  # default
        if self.model_name:
            if '70b' in self.model_name or '72b' in self.model_name:
                timeout = 120  # 2 minutes for 70B+ models
            elif '30b' in self.model_name or '32b' in self.model_name or '35b' in self.model_name:
                timeout = 90  # 1.5 minutes for 30B+ models
            elif '13b' in self.model_name or '14b' in self.model_name:
                timeout = 60  # 1 minute for 13B+ models
        
        # Call Ollama
        try:
            response = self.session.post(self.ollama_url, json={
                'model': self.model_name,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'max_tokens': 2000
                }
            }, timeout=timeout)
            
            response.raise_for_status()  # Raise an exception for bad status codes
            result = response.json()
            
            # Check if the response contains an error
            if 'error' in result:
                raise Exception(f"Ollama API error: {result['error']}")
                
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to Ollama. Please ensure Ollama is running on http://localhost:11434")
        except requests.exceptions.Timeout:
            raise Exception(f"Request timed out after {timeout} seconds. Large models like {self.model_name} may need more time to load initially. Please try again - subsequent requests should be faster.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("Invalid response from Ollama API")
        
        # Structure the response
        return {
            'question': question,
            'answer': result['response'],
            'sources': [
                {
                    'text': ctx['text'][:200] + '...' if len(ctx['text']) > 200 else ctx['text'],
                    'source': ctx['metadata'].get('source'),
                    'page': ctx['metadata'].get('page')
                }
                for ctx in context
            ],
            'confidence': 1.0 - (sum(ctx['distance'] for ctx in context) / len(context)) if context else 0.0
        }
    
    def query_hybrid_stream(self, question: str, knowledge_mode: str = "auto", n_results: int = 3, stop_event=None):
        """Hybrid knowledge system streaming query with intelligent routing"""
        
        # Search vector store for all modes (needed for classification)
        search_results = self.vector_store.search(question, n_results=n_results)
        
        # Prepare search results for classifier
        classifier_results = []
        if search_results['documents'] and search_results['documents'][0]:
            for i in range(len(search_results['documents'][0])):
                classifier_results.append({
                    'text': search_results['documents'][0][i],
                    'metadata': search_results['metadatas'][0][i], 
                    'distance': search_results['distances'][0][i]
                })
        
        # Classify question if auto mode
        if knowledge_mode == "auto":
            classification = self.classifier.classify_with_retrieval(question, classifier_results)
            knowledge_mode = classification.route
        else:
            # Manual mode - still get classification for telemetry
            classification = self.classifier.classify_with_retrieval(question, classifier_results)
            classification.route = knowledge_mode  # Override with manual selection
        
        # Log telemetry
        telemetry_entry = {
            'question': question[:100],  # Truncated for privacy
            'route': classification.route,
            'confidence': classification.confidence,
            'manual_override': knowledge_mode != classification.route,
            'retrieval_metrics': classification.retrieval_metrics,
            'keyword_signals': classification.keyword_signals
        }
        self.route_telemetry.append(telemetry_entry)
        
        # Route to appropriate method
        if classification.route == "RAG":
            return self._query_rag_only_stream(question, classifier_results, classification, stop_event)
        elif classification.route == "GENERAL":
            return self._query_general_stream(question, classification, stop_event)
        else:  # HYBRID
            return self._query_hybrid_combined_stream(question, classifier_results, classification, stop_event)
    
    def _query_rag_only_stream(self, question: str, search_results: List[Dict], classification: ClassificationResult, stop_event=None):
        """RAG-only streaming - textbook knowledge with citations only"""
        
        # Use existing logic but with explicit textbook-only prompt
        context = search_results
        prompt = self.create_prompt(question, context)
        
        # Add explicit instruction to stick to textbook content
        rag_instruction = """
IMPORTANT: Base your answer ONLY on the provided textbook context. Do not add information from your general knowledge. 
If the textbook context doesn't contain sufficient information, acknowledge this limitation rather than speculating.
"""
        prompt = rag_instruction + "\n\n" + prompt
        
        return self._stream_with_context(question, context, prompt, "RAG", classification, stop_event)
    
    def _query_general_stream(self, question: str, classification: ClassificationResult, stop_event=None):
        """General knowledge streaming - model's literary/cultural knowledge"""
        
        # Create literature-focused prompt without textbook context
        general_prompt = f"""You are an expert in Classical Japanese literature, poetry, and culture. 
Answer this question using your knowledge of classical works like Tale of Genji, Kokinshū, Man'yōshū, 
Heike Monogatari, Sei Shōnagon's Pillow Book, and other classical Japanese texts.

Provide specific examples from classical works when possible. Focus on cultural context, 
historical background, and literary significance.

Question: {question}

Answer based on your knowledge of classical Japanese literature and culture:"""

        return self._stream_with_context(question, [], general_prompt, "GENERAL", classification, stop_event)
        
    def _query_hybrid_combined_stream(self, question: str, search_results: List[Dict], classification: ClassificationResult, stop_event=None):
        """Hybrid streaming - combine textbook + general knowledge with clear separation"""
        
        context = search_results
        
        # Create hybrid prompt that encourages both sources with clear separation
        hybrid_prompt = f"""You are a Classical Japanese expert with access to both textbook knowledge and deep knowledge of classical literature.

**TEXTBOOK CONTEXT:**
{self._format_context_for_prompt(context)}

**INSTRUCTIONS:**
1. Use the textbook context for grammatical accuracy and structured explanations
2. Enhance with examples from classical works you know (Genji, Kokinshū, Man'yōshū, etc.)
3. Clearly separate textbook-grounded content from general literary knowledge
4. Use section headers to organize your response:
   - **📚 Textbook Explanation** (cite textbook sources)
   - **📖 Literary Examples** (from your knowledge of classical texts)
   - **🔍 Analysis** (synthesis of both sources)

**QUESTION:** {question}

Provide a comprehensive answer using both textbook accuracy and classical literature examples:"""

        return self._stream_with_context(question, context, hybrid_prompt, "HYBRID", classification, stop_event)
    
    def _format_context_for_prompt(self, context: List[Dict]) -> str:
        """Format context for hybrid prompts"""
        if not context:
            return "No textbook context available."
        
        formatted = []
        for i, ctx in enumerate(context, 1):
            source = ctx.get('metadata', {}).get('source', 'Unknown')
            page = ctx.get('metadata', {}).get('page', 'N/A') 
            text = ctx.get('text', '')
            formatted.append(f"[{i}] {source}, Page {page}:\n{text}")
        
        return "\n\n".join(formatted)
    
    def _stream_with_context(self, question: str, context: List[Dict], prompt: str, route: str, classification: ClassificationResult, stop_event=None):
        """Common streaming logic with route information"""
        
        # Check if this is a thinking model
        is_thinking = self.is_thinking_model()
        
        # For thinking models, enforce explicit tags for reliable parsing
        if is_thinking:
            prompt = (
                "Please enclose internal reasoning in <think>...</think> and output only "
                "the final answer after </think>. "
                "Do not repeat the reasoning outside these tags.\n\n"
            ) + prompt
        
        # Determine timeout based on model size
        timeout = 30
        if self.model_name:
            if '70b' in self.model_name or '72b' in self.model_name:
                timeout = 120
            elif '30b' in self.model_name or '32b' in self.model_name or '35b' in self.model_name:
                timeout = 90
            elif '13b' in self.model_name or '14b' in self.model_name:
                timeout = 60
        
        try:
            # Make streaming request
            response = self.session.post(self.ollama_url, json={
                'model': self.model_name,
                'prompt': prompt,
                'stream': True,
                'options': {
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'max_tokens': 2000
                }
            }, stream=True, timeout=timeout)
            
            response.raise_for_status()
            
            # Yield chunks with route information
            full_response = ""
            thinking_content = ""
            answer_content = ""
            
            # Tag-aware streaming state for thinking models
            buffer = ""
            in_thinking = False
            thinking_started = False
            
            # First yield model information with route details
            yield {
                'model_name': self.model_name,
                'is_thinking_model': is_thinking,
                'type': 'model_info',
                'sources': context,
                'route': route,
                'confidence': classification.confidence,
                'classification': classification,
                'done': False
            }
            
            # Continue with existing streaming logic...
            for line in response.iter_lines():
                # Check if stop was requested
                if stop_event and stop_event.is_set():
                    response.close()
                    yield {
                        'token': '',
                        'done': True,
                        'full_response': full_response,
                        'thinking_content': thinking_content,
                        'answer_content': answer_content,
                        'sources': context,
                        'route': route,
                        'type': 'final'
                    }
                    return
                
                if line:
                    try:
                        chunk = json.loads(line)
                        if chunk.get('response'):
                            token = chunk['response']
                            buffer += token
                            
                            # Handle thinking models with tag awareness
                            if is_thinking:
                                # Process buffer for thinking tags
                                while True:
                                    if not in_thinking and '<think>' in buffer:
                                        # Found start of thinking
                                        before, after = buffer.split('<think>', 1)
                                        if before:
                                            # Yield any content before thinking as answer
                                            for char in before:
                                                answer_content += char
                                                yield {
                                                    'token': char,
                                                    'type': 'answer',
                                                    'done': False
                                                }
                                        buffer = after
                                        in_thinking = True
                                        thinking_started = True
                                        continue
                                    elif in_thinking and '</think>' in buffer:
                                        # Found end of thinking
                                        thinking, after = buffer.split('</think>', 1)
                                        thinking_content += thinking
                                        yield {
                                            'token': thinking,
                                            'type': 'thinking', 
                                            'done': False
                                        }
                                        buffer = after
                                        in_thinking = False
                                        continue
                                    else:
                                        break
                                
                                # Yield buffer content based on current state
                                if buffer:
                                    if in_thinking:
                                        thinking_content += buffer
                                        yield {
                                            'token': buffer,
                                            'type': 'thinking',
                                            'done': False
                                        }
                                    else:
                                        answer_content += buffer
                                        yield {
                                            'token': buffer,
                                            'type': 'answer',
                                            'done': False
                                        }
                                    buffer = ""
                            else:
                                # Non-thinking model: stream as answer directly
                                answer_content += token
                                yield {
                                    'token': token,
                                    'type': 'answer',
                                    'done': False
                                }
                            
                            full_response += token
                        
                        if chunk.get('done'):
                            yield {
                                'done': True,
                                'full_response': full_response,
                                'thinking_content': thinking_content,
                                'answer_content': answer_content,
                                'sources': context,
                                'route': route,
                                'classification': classification,
                                'type': 'final'
                            }
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logging.error(f"Error in hybrid streaming: {e}")
            yield {
                'error': str(e),
                'done': True,
                'route': route
            }
    
    def query_stream(self, question: str, n_results: int = 3, stop_event=None):
        """Streaming query method for real-time response (legacy - now routes to hybrid)"""
        
        # Route through hybrid system with auto classification
        return self.query_hybrid_stream(question, "auto", n_results, stop_event)
    
    def explain_grammar(self, grammar_point: str) -> Dict:
        """Specialized method for grammar explanations"""
        query = f"Explain the classical Japanese grammar point: {grammar_point}. Include formation rules, usage, and examples."
        return self.query(query)
    
    def explain_grammar_stream(self, grammar_point: str, stop_event=None):
        """Streaming version of explain_grammar"""
        query = f"Explain the classical Japanese grammar point: {grammar_point}. Include formation rules, usage, and examples."
        yield from self.query_stream(query, stop_event=stop_event)
    
    def translate_passage(self, passage: str) -> Dict:
        """Translate classical Japanese passage"""
        query = f"Translate and analyze this classical Japanese passage: {passage}"
        return self.query(query)
    
    def get_routing_telemetry(self, limit: int = 50) -> List[Dict]:
        """Get recent routing decisions for analysis"""
        return self.route_telemetry[-limit:]
    
    def get_routing_stats(self) -> Dict:
        """Get routing statistics"""
        if not self.route_telemetry:
            return {"total": 0, "routes": {}, "avg_confidence": 0.0}
        
        total = len(self.route_telemetry)
        routes = {}
        confidences = []
        
        for entry in self.route_telemetry:
            route = entry['route']
            routes[route] = routes.get(route, 0) + 1
            confidences.append(entry['confidence'])
        
        return {
            "total": total,
            "routes": routes,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0,
            "route_percentages": {k: (v / total * 100) for k, v in routes.items()}
        }
    
    def update_classifier_thresholds(self, **kwargs):
        """Update classifier thresholds for tuning"""
        self.classifier.update_thresholds(**kwargs)

# Usage
# assistant = ClassicalJapaneseAssistant(vector_store)
# result = assistant.query("What is the difference between ぞ and こそ particles?")
# print(result['answer'])
