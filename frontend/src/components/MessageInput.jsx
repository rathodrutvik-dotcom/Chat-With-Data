import { useState } from 'react'
import { FaPaperPlane, FaStop } from 'react-icons/fa'
import { useChat } from '../context/ChatContext'

const MessageInput = ({ disabled }) => {
  const { sendMessage, sendingMessage } = useChat()
  const [input, setInput] = useState('')

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
        <div className="relative flex items-end bg-white border-2 border-gray-300 rounded-2xl shadow-lg focus-within:border-blue-500 transition-colors">
          <textarea
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
            className="flex-1 px-5 py-4 bg-transparent border-none outline-none resize-none max-h-32 min-h-[56px] disabled:cursor-not-allowed disabled:text-gray-400"
            style={{
              scrollbarWidth: 'thin',
            }}
          />

          <div className="flex items-center space-x-2 px-3 pb-3">
            {sendingMessage ? (
              <button
                type="button"
                className="p-3 bg-red-500 hover:bg-red-600 text-white rounded-xl transition-colors"
                title="Stop generation"
              >
                <FaStop className="w-5 h-5" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim() || disabled}
                className="p-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-xl transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-lg"
                title="Send message"
              >
                <FaPaperPlane className="w-5 h-5" />
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
