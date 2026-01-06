import { useEffect, useRef } from 'react'
import { useChat } from '../context/ChatContext'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import EmptyState from './EmptyState'
import { FaExclamationTriangle } from 'react-icons/fa'

const ChatContainer = () => {
  const { currentSession, messages, error, setError } = useChat()
  const containerRef = useRef(null)

  useEffect(() => {
    // Scroll to bottom when messages change
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [messages])

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-gray-50">
      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-red-800">
            <FaExclamationTriangle className="flex-shrink-0" />
            <span className="text-sm font-medium">{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-red-600 hover:text-red-800 font-medium text-sm"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Messages Container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto scrollbar-thin"
      >
        {!currentSession ? (
          <EmptyState />
        ) : messages.length === 0 ? (
          <div className="h-full flex items-center justify-center p-8">
            <div className="text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">💬</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Start a Conversation
              </h3>
              <p className="text-gray-600">
                Ask questions about your documents
              </p>
            </div>
          </div>
        ) : (
          <MessageList messages={messages} />
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 bg-white">
        <MessageInput disabled={!currentSession} />
      </div>
    </div>
  )
}

export default ChatContainer
