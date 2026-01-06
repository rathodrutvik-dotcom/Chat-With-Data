import { FaBars, FaRobot } from 'react-icons/fa'
import { useChat } from '../context/ChatContext'

const Header = ({ onMenuClick }) => {
  const { currentSession } = useChat()

  return (
    <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shadow-sm">
      <div className="flex items-center space-x-3">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
          aria-label="Toggle menu"
        >
          <FaBars className="w-5 h-5 text-gray-600" />
        </button>
        
        <div className="flex items-center space-x-3">
          <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-2 rounded-lg">
            <FaRobot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">
              {currentSession ? currentSession.document_name : 'Chat with Documents'}
            </h1>
            {currentSession && (
              <p className="text-xs text-gray-500">
                {currentSession.message_count} messages
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <div className="hidden sm:flex items-center space-x-2 text-sm text-gray-600">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span>Online</span>
        </div>
      </div>
    </header>
  )
}

export default Header
