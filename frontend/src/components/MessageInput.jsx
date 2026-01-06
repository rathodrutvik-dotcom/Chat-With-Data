import { useState, useRef, useEffect } from 'react'
import { FaArrowUp, FaStop } from 'react-icons/fa'
import { useChat } from '../context/ChatContext'

const MessageInput = ({ disabled }) => {
  const { sendMessage, sendingMessage } = useChat()
  const [input, setInput] = useState('')
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 240)}px`
    }
  }, [input])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || sendingMessage || disabled) return

    const message = input.trim()
    setInput('')

    try {
      await sendMessage(message)
    } catch (error) {
      setInput(message) // Restore input on error
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="max-w-4xl mx-auto w-full p-4">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-center bg-white border-2 border-gray-300 rounded-3xl shadow-lg focus-within:border-blue-500 transition-colors">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              disabled
                ? 'Select a session or upload documents to start chatting...'
                : 'Ask a question about your documents...'
            }
            disabled={disabled || sendingMessage}
            rows={1}
            className="flex-1 px-5 py-4 bg-transparent border-none outline-none resize-none overflow-y-auto min-h-[56px] disabled:cursor-not-allowed disabled:text-gray-400"
            style={{
              maxHeight: '240px', // ~10 lines
              scrollbarWidth: 'thin',
              scrollbarColor: '#CBD5E0 transparent',
            }}
          />

          <div className="flex items-center px-3">
            {sendingMessage ? (
              <button
                type="button"
                className="p-3 bg-red-500 hover:bg-red-600 text-white rounded-full transition-all transform hover:scale-105 shadow-md"
                title="Stop generation"
              >
                <FaStop className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim() || disabled}
                className={`p-3 rounded-full transition-all transform shadow-md ${input.trim() && !disabled
                  ? 'bg-black hover:bg-gray-800 text-white hover:scale-105'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  }`}
                title="Send message"
              >
                <FaArrowUp className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between mt-2 px-2 text-xs text-gray-500">
          <span>Press Enter to send, Shift + Enter for new line</span>
          <span>{input.length} characters</span>
        </div>
      </form>
    </div>
  )
}

export default MessageInput
