import requests
import json
import os
from typing import List, Dict

class ClassicalJapaneseAssistant:
    def __init__(self, vector_store, model_name="qwen2.5:72b", prompt_file="prompts/classical_japanese_tutor.md"):
        self.vector_store = vector_store
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/generate"
        self.prompt_template = self.load_prompt_template(prompt_file)
    
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
    
    def query(self, question: str, n_results: int = 5) -> Dict:
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
        
        # Call Ollama
        response = requests.post(self.ollama_url, json={
            'model': self.model_name,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.7,
                'top_p': 0.9,
                'max_tokens': 2000
            }
        })
        
        result = response.json()
        
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

