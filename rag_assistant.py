import requests
import json
from typing import List, Dict

class ClassicalJapaneseAssistant:
    def __init__(self, vector_store, model_name="qwen2.5:72b"):
        self.vector_store = vector_store
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/generate"
        
    def create_prompt(self, query: str, context: List[Dict]) -> str:
        """Create a detailed prompt with retrieved context"""
        
        prompt = f"""You are an expert Classical Japanese tutor with deep knowledge of grammar, vocabulary, and classical texts.

## Retrieved Context from Textbook:
"""
        for i, ctx in enumerate(context):
            source = ctx['metadata'].get('source', 'unknown')
            page = ctx['metadata'].get('page', 'N/A')
            prompt += f"\n[{i+1}] Source: {source}, Page: {page}\n"
            prompt += f"Content: {ctx['text']}\n"
            prompt += "-" * 40
        
        prompt += f"""

## Student Question:
{query}

## Instructions:
1. Answer the question using the context provided above
2. Explain any grammatical terms clearly
3. Provide examples when helpful
4. Always cite sources using [number] format when referencing the context
5. If the context doesn't contain enough information, state that clearly
6. Use both Japanese characters and romanization when discussing specific words

## Response:"""
        
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

