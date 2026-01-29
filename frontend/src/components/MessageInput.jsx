import { useState, useRef, useEffect } from 'react'
import { FaArrowUp, FaStop, FaPlus, FaPaperclip, FaUpload, FaGlobe } from 'react-icons/fa'
import { useChat } from '../context/ChatContext'
import URLUpload from './URLUpload'

const MessageInput = ({ disabled }) => {
  const { sendMessage, sendingMessage, addDocumentsToSession, uploading, currentSession } = useChat()
  const [input, setInput] = useState('')
  const [showURLUpload, setShowURLUpload] = useState(false)
  const [showAddMenu, setShowAddMenu] = useState(false)
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)
  const addMenuRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 240)}px`
    }
  }, [input])

  // Close add menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (addMenuRef.current && !addMenuRef.current.contains(event.target)) {
        setShowAddMenu(false)
      }
    }

    if (showAddMenu) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [showAddMenu])

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

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files)
    if (files.length === 0) return

    try {
      await addDocumentsToSession(files)
      setShowAddMenu(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (error) {
      console.error('Failed to add documents:', error)
    }
  }

  const triggerFileUpload = () => {
    setShowAddMenu(false)
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  const handleAddURLs = () => {
    setShowAddMenu(false)
    setShowURLUpload(true)
  }

  return (
    <div className="max-w-4xl mx-auto w-full p-4">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-center bg-white border-2 border-gray-300 rounded-3xl shadow-lg focus-within:border-blue-500 transition-colors">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.xlsx"
            onChange={handleFileSelect}
            className="hidden"
          />
          
          {/* Add content button with dropdown menu - only show when session is active */}
          {currentSession && !disabled && (
            <div className="relative ml-3" ref={addMenuRef}>
              <button
                type="button"
                onClick={() => setShowAddMenu(!showAddMenu)}
                disabled={uploading || sendingMessage}
                className={`p-2 rounded-full transition-all ${
                  uploading || sendingMessage
                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-600 hover:text-gray-800'
                }`}
                title="Add content to conversation"
              >
                <FaPlus className="w-4 h-4" />
              </button>

              {/* Dropdown Menu */}
              {showAddMenu && (
                <div className="absolute bottom-full left-0 mb-2 bg-white rounded-lg shadow-xl border border-gray-200 overflow-hidden z-10 min-w-[200px]">
                  <button
                    type="button"
                    onClick={triggerFileUpload}
                    className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-blue-50 text-gray-700 hover:text-blue-700 transition-colors text-left"
                  >
                    <FaUpload className="w-4 h-4 text-blue-500" />
                    <span className="text-sm font-medium">Upload Documents</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleAddURLs}
                    className="w-full flex items-center space-x-3 px-4 py-3 hover:bg-green-50 text-gray-700 hover:text-green-700 transition-colors text-left border-t border-gray-100"
                  >
                    <FaGlobe className="w-4 h-4 text-green-500" />
                    <span className="text-sm font-medium">Add URLs</span>
                  </button>
                </div>
              )}
            </div>
          )}
          
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
          <span>
            {currentSession 
              ? 'Press Enter to send, Shift + Enter for new line'
              : 'Select a session or upload documents to start'
            }
          </span>
          <span>{input.length} characters</span>
        </div>
        
        {/* Upload progress indicator */}
        {uploading && (
          <div className="mt-2 px-2">
            <div className="flex items-center gap-2 text-sm text-blue-600">
              <FaPaperclip className="animate-pulse" />
              <span>Adding content to conversation...</span>
            </div>
          </div>
        )}
      </form>

      {/* URL Upload Modal */}
      {showURLUpload && <URLUpload onClose={() => setShowURLUpload(false)} />}
    </div>
  )
}

export default MessageInput
