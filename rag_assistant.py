import requests
import json
import os
import subprocess
from typing import List, Dict

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
        self.ollama_url = "http://localhost:11434/api/generate"
        self.prompt_template = self.load_prompt_template(prompt_file)
        
        # Thinking models configuration
        self.thinking_models = {
            'qwen3': True,  # QwQ reasoning models
            'qwq': True,    # Qwen with Questions
            'deepseek-r1': True,  # DeepSeek reasoning
            'o1': True,  # OpenAI o1 style
            'thinking': True,  # Generic thinking model indicator
        }
    
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
            print(f"Error detecting Ollama models: {e}")
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
        context_str = ""
        for i, ctx in enumerate(context):
            source = ctx['metadata'].get('source', 'unknown')
            page = ctx['metadata'].get('page', 'N/A')
            context_str += f"\n[{i+1}] Source: {source}, Page: {page}\n"
            context_str += f"Content: {ctx['text']}\n"
            context_str += "-" * 40 + "\n"
        
        # Replace placeholders in template
        prompt = self.prompt_template.replace('{context}', context_str)
        prompt = prompt.replace('{question}', query)
        
        return prompt
    
    def query(self, question: str, n_results: int = 3) -> Dict:
        """Main query method"""
        
        # Search vector store
        search_results = self.vector_store.search(question, n_results=n_results)
        
        # Prepare context
        context = []
        for i in range(len(search_results['documents'][0])):
            context.append({
                'text': search_results['documents'][0][i],
                'metadata': search_results['metadatas'][0][i],
                'distance': search_results['distances'][0][i]
            })
        
        # Create prompt
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
            response = requests.post(self.ollama_url, json={
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
            'confidence': 1.0 - (sum(ctx['distance'] for ctx in context) / len(context))
        }
    
    def query_stream(self, question: str, n_results: int = 3, stop_event=None):
        """Streaming query method for real-time response"""
        
        # Search vector store
        search_results = self.vector_store.search(question, n_results=n_results)
        
        # Prepare context
        context = []
        for i in range(len(search_results['documents'][0])):
            context.append({
                'text': search_results['documents'][0][i],
                'metadata': search_results['metadatas'][0][i],
                'distance': search_results['distances'][0][i]
            })
        
        # Create prompt
        prompt = self.create_prompt(question, context)
        
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
            response = requests.post(self.ollama_url, json={
                'model': self.model_name,
                'prompt': prompt,
                'stream': True,  # Enable streaming
                'options': {
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'max_tokens': 2000
                }
            }, stream=True, timeout=timeout)
            
            response.raise_for_status()
            
            # Yield chunks as they come
            full_response = ""
            thinking_content = ""
            answer_content = ""
            
            # Tag-aware streaming state for thinking models
            buffer = ""
            in_thinking = False
            thinking_started = False
            
            # First yield model information
            yield {
                'model_name': self.model_name,
                'is_thinking_model': is_thinking,
                'type': 'model_info',
                'done': False
            }
            
            for line in response.iter_lines():
                # Check if stop was requested
                if stop_event and stop_event.is_set():
                    response.close()  # Close the connection
                    yield {
                        'token': '',
                        'done': True,
                        'full_response': full_response,
                        'thinking_content': thinking_content,
                        'answer_content': answer_content,
                        'sources': context,
                        'type': 'final'
                    }
                    return
                    
                if line:
                    try:
                        chunk = json.loads(line)
                        if 'response' in chunk:
                            token = chunk['response']
                            full_response += token
                            
                            # Tag-aware parsing for thinking models
                            if is_thinking:
                                combined = buffer + token
                                
                                # Start when <thinking> or <think> appears
                                if not thinking_started:
                                    if '<thinking>' in combined:
                                        thinking_started = True
                                        in_thinking = True
                                        combined = combined.split('<thinking>', 1)[1]
                                        # Found <thinking> tag
                                    elif '<think>' in combined:
                                        thinking_started = True
                                        in_thinking = True
                                        combined = combined.split('<think>', 1)[1]
                                        # Found <think> tag
                                    else:
                                        # Buffer tokens until we see the tag (or fallback after limit)
                                        if len(combined) > 50:  # Fallback after 50 chars without tags
                                            thinking_started = True
                                            in_thinking = True
                                            thinking_content += combined
                                            yield {
                                                'token': combined,
                                                'done': chunk.get('done', False),
                                                'type': 'thinking',
                                                'sources': context
                                            }
                                            combined = ""
                                        buffer = combined[-20:] if combined else ""
                                        continue
                                
                                # Process tokens after thinking started
                                if thinking_started and combined:
                                    
                                    # Check for closing tags - both formats
                                    if in_thinking and ('</thinking>' in combined or '</think>' in combined):
                                        # Handle both closing tag formats
                                        if '</thinking>' in combined:
                                            before_tag, after_tag = combined.split('</thinking>', 1)
                                        else:
                                            before_tag, after_tag = combined.split('</think>', 1)
                                        
                                        thinking_content += before_tag
                                        
                                        # Yield the thinking content
                                        if before_tag:
                                            yield {
                                                'token': before_tag,
                                                'done': False,
                                                'type': 'thinking',
                                                'sources': context
                                            }
                                        
                                        in_thinking = False
                                        combined = after_tag
                                        
                                        # Process remaining as answer if any
                                        if after_tag:
                                            answer_content += after_tag
                                            yield {
                                                'token': after_tag,
                                                'done': chunk.get('done', False),
                                                'type': 'answer',
                                                'sources': context
                                            }
                                    else:
                                        # No closing tag yet in this combined text
                                        if in_thinking:
                                            thinking_content += combined
                                            content_type = 'thinking'
                                        else:
                                            answer_content += combined
                                            content_type = 'answer'
                                        
                                        yield {
                                            'token': combined,
                                            'done': chunk.get('done', False),
                                            'type': content_type,
                                            'sources': context
                                        }
                                
                                # Keep small buffer for tag detection across token boundaries
                                buffer = combined[-20:] if len(combined) > 20 else ""
                                
                            else:
                                # Non-thinking models: everything is answer
                                answer_content += token
                                yield {
                                    'token': token,
                                    'done': chunk.get('done', False),
                                    'type': 'answer',
                                    'sources': context
                                }
                                continue
                    except json.JSONDecodeError:
                        continue
            
            # Final yield when streaming completes
            yield {
                'token': '',
                'done': True,
                'full_response': full_response,
                'thinking_content': thinking_content,
                'answer_content': answer_content,
                'sources': context,
                'type': 'final'
            }
                        
        except requests.exceptions.ConnectionError:
            yield {
                'error': "Cannot connect to Ollama. Please ensure Ollama is running on http://localhost:11434",
                'done': True
            }
        except requests.exceptions.Timeout:
            yield {
                'error': f"Request timed out after {timeout} seconds. Large models may need more time to load.",
                'done': True
            }
        except Exception as e:
            yield {
                'error': f"Error: {str(e)}",
                'done': True
            }
    
    def explain_grammar(self, grammar_point: str) -> Dict:
        """Specialized method for grammar explanations"""
        query = f"Explain the classical Japanese grammar point: {grammar_point}. Include formation rules, usage, and examples."
        return self.query(query)
    
    def translate_passage(self, passage: str) -> Dict:
        """Translate classical Japanese passage"""
        query = f"Translate and analyze this classical Japanese passage: {passage}"
        return self.query(query)

# Usage
# assistant = ClassicalJapaneseAssistant(vector_store)
# result = assistant.query("What is the difference between ぞ and こそ particles?")
# print(result['answer'])

