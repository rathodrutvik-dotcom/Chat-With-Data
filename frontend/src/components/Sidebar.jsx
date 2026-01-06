import { useState, useRef, useEffect } from 'react'
import { FaPlus, FaTimes, FaTrash, FaFile, FaComments, FaEllipsisV, FaPencilAlt, FaBroom } from 'react-icons/fa'
import { useChat } from '../context/ChatContext'
import FileUpload from './FileUpload'
import { formatDistanceToNow } from 'date-fns'

const Sidebar = ({ isOpen, onClose }) => {
  const { sessions, currentSession, loadSession, deleteSession, newChat, clearChat } = useChat()
  const [showUpload, setShowUpload] = useState(false)
  const [openMenuId, setOpenMenuId] = useState(null)
  const menuRef = useRef(null)

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpenMenuId(null)
      }
    }

    if (openMenuId !== null) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [openMenuId])

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
    setOpenMenuId(null)
  }

  const handleClearChat = async (e, sessionId) => {
    e.stopPropagation()
    if (window.confirm('Are you sure you want to clear the chat history? This will remove all messages but keep the session.')) {
      await clearChat()
    }
    setOpenMenuId(null)
  }

  const toggleMenu = (e, sessionId) => {
    e.stopPropagation()
    setOpenMenuId(openMenuId === sessionId ? null : sessionId)
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
          <button
            onClick={handleNewChat}
            className="w-full flex items-center space-x-3 text-gray-300 hover:bg-gray-800 px-3 py-2.5 rounded-lg font-normal transition-colors mb-4"
          >
            <FaPencilAlt className="w-4 h-4" />
            <span className="text-sm">New chat</span>
          </button>

          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">Your chats</h2>
            <button
              onClick={onClose}
              className="lg:hidden p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <FaTimes />
            </button>
          </div>
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
                  ${currentSession?.session_id === session.session_id
                    ? 'bg-gray-800'
                    : 'hover:bg-gray-800'
                  }
                `}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0 pr-2">
                    <h3 className="text-sm font-normal truncate text-gray-200">
                      {session.document_name}
                    </h3>
                  </div>

                  <div className="relative flex-shrink-0" ref={openMenuId === session.session_id ? menuRef : null}>
                    <button
                      onClick={(e) => toggleMenu(e, session.session_id)}
                      className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-gray-700 rounded transition-all"
                      title="Options"
                    >
                      <FaEllipsisV className="w-3 h-3 text-gray-400" />
                    </button>

                    {/* Dropdown Menu */}
                    {openMenuId === session.session_id && (
                      <div className="absolute right-0 mt-1 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-20 py-1">
                        <button
                          onClick={(e) => handleClearChat(e, session.session_id)}
                          className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
                        >
                          <FaBroom className="w-3 h-3" />
                          <span>Clear Chat</span>
                        </button>
                        <button
                          onClick={(e) => handleDelete(e, session.session_id)}
                          className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-red-400 hover:bg-gray-700 transition-colors"
                        >
                          <FaTrash className="w-3 h-3" />
                          <span>Delete</span>
                        </button>
                      </div>
                    )}
                  </div>
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
