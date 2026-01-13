import { useEffect, useRef, useState } from 'react'
import { useChat } from '../context/ChatContext'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import EmptyState from './EmptyState'
import { FaExclamationTriangle, FaArrowDown } from 'react-icons/fa'

const ChatContainer = () => {
  const { currentSession, messages, error, setError, searchHighlight } = useChat()
  const containerRef = useRef(null)
  const prevMessageCountRef = useRef(0)
  const [showScrollButton, setShowScrollButton] = useState(false)

  const handleScroll = () => {
    if (containerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = containerRef.current
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100
      setShowScrollButton(!isNearBottom)
    }
  }

  const scrollToBottom = () => {
    if (containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }

  useEffect(() => {
    // Only auto-scroll to bottom when NEW messages are added (not on search)
    if (containerRef.current && !searchHighlight) {
      const messageCountIncreased = messages.length > prevMessageCountRef.current
      if (messageCountIncreased) {
        containerRef.current.scrollTop = containerRef.current.scrollHeight
      }
    }
    prevMessageCountRef.current = messages.length
  }, [messages, searchHighlight])

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

      {/* Messages Area Wrapper */}
      <div className="flex-1 relative min-h-0">
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="absolute inset-0 overflow-y-auto scrollbar-thin"
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

        {/* Floating Scroll Button */}
        {showScrollButton && (
          <button
            onClick={scrollToBottom}
            className="absolute bottom-5 left-1/2 transform -translate-x-1/2 bg-white text-gray-500 hover:text-gray-900 rounded-full p-2 shadow-md border border-gray-200 transition-all duration-200 z-10"
            aria-label="Scroll to bottom"
          >
            <FaArrowDown size={14} />
          </button>
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
