import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from models.session_manager import get_session_manager
from rag.pipeline import process_user_question, proceed_input

# Load environment variables
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")  # Gemini uses GOOGLE_API_KEY

# Initialize session manager
session_manager = get_session_manager()


def gradio_app():
    """Enhanced Gradio app to chat with documents using RAG with persistent sessions."""
    
    with gr.Blocks(title="Chat with Documents") as interface:
        
        # Header
        gr.Markdown("# 📚 Chat with Your Documents")
        gr.Markdown("Upload documents (PDF, DOCX, XLSX), then ask questions! Your conversations are saved automatically.")
        
        # State variables
        current_session_id = gr.State(None)
        
        # Session Management Section
        with gr.Row():
            with gr.Column(scale=2):
                session_dropdown = gr.Dropdown(
                    label="📋 Document Sessions",
                    choices=[],
                    value=None,
                    interactive=True,
                    info="Select a previous document session to continue chatting"
                )
            with gr.Column(scale=1):
                refresh_sessions_btn = gr.Button("🔄 Refresh", size="sm")
                delete_session_btn = gr.Button("🗑️ Delete Session", size="sm", variant="stop")
        
        # Input Section
        with gr.Row():
            with gr.Column(scale=1):
                file_upload = gr.File(
                    label="📁 Upload New Documents", 
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
            clear_chat_btn = gr.Button("🗑️ Clear Chat", scale=1)

        def refresh_session_list():
            """Refresh the list of available sessions."""
            sessions = session_manager.get_all_sessions()
            choices = [doc_name for session_id, doc_name, _ in sessions]
            session_map = {
                doc_name: session_id
                for session_id, doc_name, _ in sessions
            }
            return gr.Dropdown(choices=choices), session_map

        def get_session_id_from_display(display_value, session_map):
            """Extract session_id from display value."""
            return session_map.get(display_value)

        def load_session_chat(display_value, session_map):
            """Load chat history when a session is selected."""
            if not display_value:
                return [], None, "Select a session to continue chatting"
            
            session_id = session_map.get(display_value)
            if not session_id:
                return [], None, "⚠️ Session not found in map. Try refreshing."
            
            # Check if RAG session exists in memory
            rag_session = session_manager.get_session(session_id)
            if not rag_session:
                return [], None, f"⚠️ Session expired. Please reprocess the documents to restore this session."
            
            # Load chat history from storage
            messages = session_manager.load_chat_history(session_id)
            chat_history = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ]
            
            # Get session info
            session_info = session_manager.get_session_info(session_id)
            if session_info:
                status = f"✅ Loaded session: {session_info['document_name']} ({len(chat_history)} messages)"
            else:
                status = "✅ Session loaded"
            
            return chat_history, session_id, status

        def process_input_gradio(files):
            """Process uploaded documents and create a new session."""
            if not files:
                return "⚠️ Please upload files before processing.", None, [], None, gr.Dropdown()
            
            try:
                # Process documents (document name is auto-generated)
                result = proceed_input(files)
                
                # Create new session
                session_id = session_manager.create_session(
                    result.rag_session, 
                    result.document_name,
                    result.collection_name
                )
                
                # Refresh session list
                sessions = session_manager.get_all_sessions()
                choices = [doc_name for sid, doc_name, _ in sessions]
                
                display_value = result.document_name
                
                return (
                    f"✅ Documents processed successfully! Session: {result.document_name}",
                    session_id,
                    [],
                    display_value,
                    gr.Dropdown(choices=choices, value=display_value)
                )
            except Exception as e:
                return f"❌ Error: {str(e)}", None, [], None, gr.Dropdown()

        def add_message(history, message, session_id):
            """Add user message to chat history."""
            if not message or not message.strip():
                return history, gr.Textbox(value="", interactive=True)
            
            if not session_id:
                # Don't add duplicate warnings
                if not history or history[-1].get("content") != "⚠️ Please select or create a document session first.":
                    history.append({
                        "role": "assistant",
                        "content": "⚠️ Please select or create a document session first."
                    })
                return history, gr.Textbox(value="", interactive=True)
            
            # Add to display history
            history.append({"role": "user", "content": message})
            
            # Save to database
            session_manager.save_message(session_id, "user", message)
            
            return history, gr.Textbox(value="", interactive=False)

        def bot_response(history, session_id):
            """Generate bot response."""
            if not history:
                return history
            
            if not session_id:
                history.append({
                    "role": "assistant", 
                    "content": "⚠️ Please select or create a document session first."
                })
                return history
            
            # Get RAG session
            rag_session = session_manager.get_session(session_id)
            if not rag_session:
                history.append({
                    "role": "assistant", 
                    "content": "⚠️ Session expired. Please process documents again."
                })
                return history
            
            # Get the last user message
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
                # Get answer from RAG
                response_data = process_user_question(user_message, rag_session, history)
                
                if isinstance(response_data, dict):
                    answer = response_data.get("answer", "")
                    # Optionally append sources or rely on inline citations
                    # sources = response_data.get("sources", [])
                else:
                    answer = str(response_data)
                
                history.append({"role": "assistant", "content": answer})
                
                # Save to database
                session_manager.save_message(session_id, "assistant", answer)
            except Exception as e:
                error_msg = f"❌ Error processing question: {str(e)}"
                history.append({"role": "assistant", "content": error_msg})
                session_manager.save_message(session_id, "assistant", error_msg)
            
            return history

        def clear_current_chat(session_id):
            """Clear chat for current session."""
            if session_id:
                session_manager.clear_session_chat(session_id)
                return [], "✅ Chat cleared"
            return [], "⚠️ No active session"

        def delete_current_session(display_value, session_map):
            """Delete the currently selected session."""
            if not display_value:
                return [], None, "⚠️ No session selected", gr.Dropdown()
            
            session_id = session_map.get(display_value)
            if session_id:
                session_manager.delete_session(session_id)
                
                # Refresh session list
                sessions = session_manager.get_all_sessions()
                choices = [doc_name for sid, doc_name, _ in sessions]
                
                return [], None, f"✅ Session deleted", gr.Dropdown(choices=choices, value=None)
            
            return [], None, "⚠️ Session not found", gr.Dropdown()

        # Store session map in state
        session_map_state = gr.State({})

        # Event handlers
        interface.load(
            fn=refresh_session_list,
            outputs=[session_dropdown, session_map_state]
        )

        refresh_sessions_btn.click(
            fn=refresh_session_list,
            outputs=[session_dropdown, session_map_state]
        )

        session_dropdown.select(
            fn=load_session_chat,
            inputs=[session_dropdown, session_map_state],
            outputs=[chatbot, current_session_id, output_message]
        )

        process_btn.click(
            fn=process_input_gradio, 
            inputs=[file_upload], 
            outputs=[output_message, current_session_id, chatbot, session_dropdown, session_dropdown]
        ).then(
            fn=refresh_session_list,
            outputs=[session_dropdown, session_map_state]
        )

        # Chat submission
        chat_msg = chat_input.submit(
            fn=add_message, 
            inputs=[chatbot, chat_input, current_session_id], 
            outputs=[chatbot, chat_input]
        )
        bot_msg = chat_msg.then(
            fn=bot_response, 
            inputs=[chatbot, current_session_id], 
            outputs=chatbot
        )
        bot_msg.then(lambda: gr.Textbox(interactive=True), None, [chat_input])

        # Clear chat button
        clear_chat_btn.click(
            fn=clear_current_chat,
            inputs=[current_session_id],
            outputs=[chatbot, output_message]
        )

        # Delete session button
        delete_session_btn.click(
            fn=delete_current_session,
            inputs=[session_dropdown, session_map_state],
            outputs=[chatbot, current_session_id, output_message, session_dropdown]
        ).then(
            fn=refresh_session_list,
            outputs=[session_dropdown, session_map_state]
        )

    interface.launch(server_name="0.0.0.0", server_port=7000, theme=gr.themes.Soft())


# Run the Gradio app
if __name__ == "__main__":
    # Launch Gradio app with server name and port
    gradio_app()
