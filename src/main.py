import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from rag.pipeline import process_user_question, proceed_input

# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def gradio_app():
    """Enhanced Gradio app to chat with documents using RAG."""
    
    with gr.Blocks(title="Chat with Documents") as interface:
        
        # Header
        gr.Markdown("# 📚 Chat with Your Documents")
        gr.Markdown("Upload documents (PDF, DOCX, XLSX) or enter text, then ask questions!")
        
        # State to persist RAG chain across interactions
        rag_chain_state = gr.State(None)
        
        # Input Section
        with gr.Row():
            with gr.Column(scale=1):
                text_input = gr.Textbox(
                    label="📝 Enter Text (Optional)", 
                    lines=8,
                    placeholder="Paste any text you want to include in the knowledge base..."
                )
                file_upload = gr.File(
                    label="📁 Upload Documents", 
                    file_types=[".xlsx", ".pdf", ".docx"], 
                    file_count="multiple"
                )
                process_btn = gr.Button("🚀 Process Documents", variant="primary", size="lg")
                output_message = gr.Textbox(label="Status", interactive=False)
        
        # Chat Section
        gr.Markdown("### 💬 Chat Interface")
        chatbot = gr.Chatbot(
            elem_id="chatbot",
            scale=1,
            height=400
        )
        
        with gr.Row():
            chat_input = gr.Textbox(
                placeholder="Ask a question about your documents...", 
                show_label=False,
                scale=4
            )
            clear_btn = gr.Button("🗑️ Clear", scale=1)

        def add_message(history, message):
            """Add user message to chat history."""
            if message and message.strip():
                history.append({"role": "user", "content": message})
            return history, gr.Textbox(value="", interactive=False)

        def process_input_gradio(text, files):
            """Process uploaded documents and text."""
            if not files and not text.strip():
                return "⚠️ Please upload files or enter text before processing.", None, []
            
            try:
                rag_chain = proceed_input(text, files)
                return "✅ Documents processed successfully! You can now ask questions.", rag_chain, []
            except Exception as e:
                return f"❌ Error: {str(e)}", None, []

        def bot_response(history, rag_chain_state):
            """Generate bot response."""
            if not history:
                return history
                
            if rag_chain_state is None:
                history.append({
                    "role": "assistant", 
                    "content": "⚠️ Please upload and process documents first."
                })
                return history
            
            # Get the last user message - handle both dict and list formats
            last_message = history[-1]
            if isinstance(last_message, dict):
                user_message = last_message.get("content", "")
            else:
                user_message = str(last_message)
            
            # Ensure user_message is a string
            if isinstance(user_message, list):
                user_message = " ".join(str(item) for item in user_message)
            elif not isinstance(user_message, str):
                user_message = str(user_message)
            
            try:
                # Include recent chat history to improve contextual answers
                answer = process_user_question(user_message, rag_chain_state, history)
                history.append({"role": "assistant", "content": answer})
            except Exception as e:
                history.append({
                    "role": "assistant", 
                    "content": f"❌ Error processing question: {str(e)}"
                })
            
            return history

        # Event handlers
        process_btn.click(
            fn=process_input_gradio, 
            inputs=[text_input, file_upload], 
            outputs=[output_message, rag_chain_state, chatbot]
        )

        # Chat submission
        chat_msg = chat_input.submit(
            fn=add_message, 
            inputs=[chatbot, chat_input], 
            outputs=[chatbot, chat_input]
        )
        bot_msg = chat_msg.then(
            fn=bot_response, 
            inputs=[chatbot, rag_chain_state], 
            outputs=chatbot
        )
        bot_msg.then(lambda: gr.Textbox(interactive=True), None, [chat_input])

        # Clear button
        clear_btn.click(lambda: [], None, chatbot)

    interface.launch(server_name="0.0.0.0", server_port=7000, theme=gr.themes.Soft())


# Run the Gradio app
if __name__ == "__main__":
    # Launch Gradio app with server name and port
    gradio_app()
