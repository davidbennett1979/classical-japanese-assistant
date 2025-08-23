import gradio as gr
from rag_assistant import ClassicalJapaneseAssistant
from vector_store import JapaneseVectorStore
from ocr_pipeline import JapaneseOCR
import json

# Initialize components
vector_store = JapaneseVectorStore()
assistant = ClassicalJapaneseAssistant(vector_store)
ocr = JapaneseOCR()

def chat_function(message, history):
    """Main chat interface"""
    result = assistant.query(message)
    
    # Format response with citations
    response = result['answer'] + "\n\n**Sources:**\n"
    for i, source in enumerate(result['sources']):
        response += f"- [{i+1}] {source['source']}, Page {source['page']}\n"
    
    return response

def add_note_function(note_text, topic):
    """Add personal note"""
    vector_store.add_note(note_text, topic)
    return "Note added successfully!"

def process_new_document(file):
    """Process uploaded PDF or image"""
    if file.name.endswith('.pdf'):
        text_data = ocr.process_pdf(file.name)
    else:
        text_data = ocr.extract_text_with_coordinates(file.name)
    
    chunks = vector_store.chunk_text(text_data)
    vector_store.add_documents(chunks)
    
    return f"Processed and added {len(chunks)} text chunks to database"

def search_examples(grammar_point):
    """Search for examples of specific grammar"""
    result = assistant.explain_grammar(grammar_point)
    return result['answer']

# Create Gradio interface
with gr.Blocks(title="Classical Japanese Learning Assistant") as app:
    gr.Markdown("# 📚 Classical Japanese Learning Assistant")
    gr.Markdown("Powered by local AI with your textbook knowledge")
    
    with gr.Tab("Chat"):
        chatbot = gr.Chatbot(height=500)
        msg = gr.Textbox(
            label="Ask a question",
            placeholder="E.g., 'Explain the べし auxiliary verb' or 'What are the uses of particle ぞ?'"
        )
        clear = gr.Button("Clear")
        
        msg.submit(chat_function, [msg, chatbot], [chatbot])
        clear.click(lambda: None, None, chatbot, queue=False)
    
    with gr.Tab("Add Notes"):
        note_input = gr.Textbox(
            label="Note Content",
            lines=5,
            placeholder="Add your study notes here..."
        )
        topic_input = gr.Textbox(
            label="Topic/Category",
            placeholder="E.g., 'particles', 'verb conjugation', 'keigo'"
        )
        add_btn = gr.Button("Add Note")
        note_output = gr.Textbox(label="Status")
        
        add_btn.click(add_note_function, [note_input, topic_input], note_output)
    
    with gr.Tab("Grammar Search"):
        grammar_input = gr.Textbox(
            label="Grammar Point",
            placeholder="Enter a grammar point (e.g., らむ, べし, なり)"
        )
        search_btn = gr.Button("Search & Explain")
        grammar_output = gr.Markdown()
        
        search_btn.click(search_examples, grammar_input, grammar_output)
    
    with gr.Tab("Add Documents"):
        file_input = gr.File(
            label="Upload PDF or Image",
            file_types=[".pdf", ".jpg", ".png"]
        )
        process_btn = gr.Button("Process Document")
        process_output = gr.Textbox(label="Processing Status")
        
        process_btn.click(process_new_document, file_input, process_output)
    
    with gr.Tab("Settings"):
        gr.Markdown("### Model Settings")
        model_dropdown = gr.Dropdown(
            choices=["qwen2.5:72b", "llama3.1:70b"],
            value="qwen2.5:72b",
            label="Select Model"
        )
        
        gr.Markdown("### Database Info")
        gr.Textbox(
            value=f"Documents in database: {vector_store.collection.count()}",
            label="Statistics",
            interactive=False
        )

# Launch the app
if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)

