import { useState, useRef } from 'react'
import { FaPlus, FaTimes, FaTrash, FaFile, FaComments } from 'react-icons/fa'
import { useChat } from '../context/ChatContext'
import FileUpload from './FileUpload'
import { formatDistanceToNow } from 'date-fns'

const Sidebar = ({ isOpen, onClose }) => {
  const { sessions, currentSession, loadSession, deleteSession, newChat } = useChat()
  const [showUpload, setShowUpload] = useState(false)

  const handleSessionClick = (session) => {
    loadSession(session.session_id)
    if (window.innerWidth < 1024) {
      onClose()
    }
  }

  const handleDelete = async (e, sessionId) => {
    e.stopPropagation()
    if (window.confirm('Are you sure you want to delete this session?')) {
      await deleteSession(sessionId)
    }
  }

  const handleNewChat = () => {
    newChat()
    setShowUpload(true)
  }

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:relative inset-y-0 left-0 z-50
          w-80 bg-gray-900 text-white
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
          flex flex-col
        `}
      >
        {/* Header */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">Chat Sessions</h2>
            <button
              onClick={onClose}
              className="lg:hidden p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <FaTimes />
            </button>
          </div>

          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center space-x-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-4 py-3 rounded-lg font-medium transition-all transform hover:scale-105"
          >
            <FaPlus />
            <span>New Chat</span>
          </button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-2">
          {sessions.length === 0 ? (
            <div className="text-center py-12 px-4">
              <FaComments className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">No sessions yet</p>
              <p className="text-gray-500 text-xs mt-1">
                Upload documents to start chatting
              </p>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.session_id}
                onClick={() => handleSessionClick(session)}
                className={`
                  group relative p-3 rounded-lg cursor-pointer transition-all
                  ${
                    currentSession?.session_id === session.session_id
                      ? 'bg-gray-700 ring-2 ring-blue-500'
                      : 'bg-gray-800 hover:bg-gray-700'
                  }
                `}
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 mt-1">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                      <FaFile className="w-4 h-4 text-white" />
                    </div>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium truncate text-white">
                      {session.document_name}
                    </h3>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-xs text-gray-400">
                        {session.message_count} messages
                      </span>
                      <span className="text-gray-600">•</span>
                      <span className="text-xs text-gray-400">
                        {formatDistanceToNow(new Date(session.last_updated), {
                          addSuffix: true,
                        })}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={(e) => handleDelete(e, session.session_id)}
                    className="opacity-0 group-hover:opacity-100 p-2 hover:bg-red-600 rounded transition-all"
                    title="Delete session"
                  >
                    <FaTrash className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700">
          <div className="text-xs text-gray-400 text-center">
            <p>RAG-powered Document Chat</p>
            <p className="mt-1">Built with React & FastAPI</p>
          </div>
        </div>
      </aside>

      {/* Upload Modal */}
      {showUpload && (
        <FileUpload onClose={() => setShowUpload(false)} />
      )}
    </>
  )
}

export default Sidebar
