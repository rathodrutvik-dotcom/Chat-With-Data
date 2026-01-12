import { useState, useRef, useEffect } from 'react'
import { FaPlus, FaTimes, FaTrash, FaFile, FaComments, FaEllipsisV, FaPencilAlt, FaBroom, FaBars } from 'react-icons/fa'
import { useChat } from '../context/ChatContext'
import FileUpload from './FileUpload'
import ConfirmModal from './ConfirmModal'
import { formatDistanceToNow } from 'date-fns'

const Sidebar = ({ isOpen, onClose }) => {
  const { sessions, currentSession, loadSession, deleteSession, renameSession, newChat, clearChat } = useChat()
  const [showUpload, setShowUpload] = useState(false)
  const [openMenuId, setOpenMenuId] = useState(null)
  const [deleteModal, setDeleteModal] = useState({ isOpen: false, sessionId: null })
  const [clearChatModal, setClearChatModal] = useState({ isOpen: false, sessionId: null })
  const [renameModal, setRenameModal] = useState({ isOpen: false, sessionId: null, currentName: '' })
  const [renameName, setRenameName] = useState('')
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

  const handleDelete = (e, sessionId) => {
    e.stopPropagation()
    setDeleteModal({ isOpen: true, sessionId })
    setOpenMenuId(null)
  }

  const handleClearChat = (e, sessionId) => {
    e.stopPropagation()
    setClearChatModal({ isOpen: true, sessionId })
    setOpenMenuId(null)
  }

  const handleRename = (e, session) => {
    e.stopPropagation()
    setRenameModal({ isOpen: true, sessionId: session.session_id, currentName: session.document_name })
    setRenameName(session.document_name)
    setOpenMenuId(null)
  }

  const confirmDelete = async () => {
    if (deleteModal.sessionId) {
      await deleteSession(deleteModal.sessionId)
    }
  }

  const confirmClearChat = async () => {
    if (clearChatModal.sessionId) {
      await clearChat()
    }
  }

  const confirmRename = async () => {
    if (renameModal.sessionId && renameName.trim()) {
      try {
        await renameSession(renameModal.sessionId, renameName)
        setRenameModal({ isOpen: false, sessionId: null, currentName: '' })
        setRenameName('')
      } catch (error) {
        console.error('Failed to rename:', error)
      }
    }
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
          bg-gray-900 text-white
          transition-all duration-300 ease-in-out
          ${isOpen ? 'w-80 translate-x-0' : 'w-80 -translate-x-full lg:translate-x-0 lg:w-16'}
          flex flex-col overflow-hidden
        `}
      >
        {/* Collapsed view - Icon only (Desktop) */}
        <div className={`${isOpen ? 'hidden' : 'hidden lg:flex'} flex-col items-center py-4 space-y-4 w-16`}>
          {/* Toggle button */}
          <button
            onClick={onClose}
            className="p-3 hover:bg-gray-800 rounded-lg transition-colors"
            title="Open sidebar"
          >
            <FaBars className="w-5 h-5 text-gray-400" />
          </button>

          {/* New chat icon */}
          <button
            onClick={handleNewChat}
            className="p-3 hover:bg-gray-800 rounded-lg transition-colors"
            title="New chat"
          >
            <FaPencilAlt className="w-5 h-5 text-gray-400" />
          </button>

          {/* Chats icon - clickable to open sidebar */}
          <button
            onClick={onClose}
            className="p-3 hover:bg-gray-800 rounded-lg transition-colors"
            title="View chats"
          >
            <FaComments className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Expanded view - Full sidebar */}
        <div className={`${isOpen ? 'flex' : 'hidden'} flex-col flex-1 overflow-hidden`}>
          {/* Header */}
          <div className="p-4 border-b border-gray-700">
            {/* New chat button and toggle button row */}
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={handleNewChat}
                className="flex items-center space-x-3 text-gray-300 hover:bg-gray-800 px-3 py-2.5 rounded-lg font-normal transition-colors"
              >
                <FaPencilAlt className="w-4 h-4" />
                <span className="text-sm">New chat</span>
              </button>

              {/* Toggle button */}
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                title="Close sidebar"
              >
                <FaBars className="w-4 h-4 text-gray-400" />
              </button>
            </div>

            {/* Your chats title */}
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold">Your chats</h2>
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
                      <h3 className="text-sm font-normal truncate text-gray-200" title={session.document_name}>
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
                            onClick={(e) => handleRename(e, session)}
                            className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
                          >
                            <FaPencilAlt className="w-3 h-3" />
                            <span>Rename</span>
                          </button>
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
        </div>
      </aside>

      {/* Upload Modal */}
      {showUpload && (
        <FileUpload onClose={() => setShowUpload(false)} />
      )}

      {/* Delete Session Modal */}
      <ConfirmModal
        isOpen={deleteModal.isOpen}
        onClose={() => setDeleteModal({ isOpen: false, sessionId: null })}
        onConfirm={confirmDelete}
        title="Delete chat?"
        message="This will permanently delete this chat and all associated messages. This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        confirmButtonClass="bg-red-600 hover:bg-red-700"
        icon={FaTrash}
      />

      {/* Clear Chat Modal */}
      <ConfirmModal
        isOpen={clearChatModal.isOpen}
        onClose={() => setClearChatModal({ isOpen: false, sessionId: null })}
        onConfirm={confirmClearChat}
        title="Clear chat?"
        message="This will remove all messages from this chat. The session and uploaded documents will be preserved."
        confirmText="Clear"
        cancelText="Cancel"
        confirmButtonClass="bg-orange-600 hover:bg-orange-700"
        icon={FaBroom}
      />

      {/* Rename Modal */}
      {renameModal.isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center mb-4">
              <FaPencilAlt className="w-5 h-5 text-blue-400 mr-3" />
              <h3 className="text-lg font-semibold text-white">Rename Chat</h3>
            </div>
            <input
              type="text"
              value={renameName}
              onChange={(e) => setRenameName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && confirmRename()}
              placeholder="Enter new name"
              className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
              autoFocus
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setRenameModal({ isOpen: false, sessionId: null, currentName: '' })
                  setRenameName('')
                }}
                className="px-4 py-2 text-gray-300 hover:bg-gray-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmRename}
                disabled={!renameName.trim()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Rename
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default Sidebar
