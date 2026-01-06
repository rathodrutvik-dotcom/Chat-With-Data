import { FaRobot } from 'react-icons/fa'

const TypingIndicator = () => {
  return (
    <div className="flex items-start space-x-4 animate-fade-in">
      <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
        <FaRobot className="w-5 h-5 text-white" />
      </div>

      <div className="max-w-[80%] bg-white border border-gray-200 rounded-2xl px-5 py-4 shadow-sm">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full loading-dot"></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full loading-dot"></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full loading-dot"></div>
          </div>
          <span className="text-sm text-gray-500">Thinking...</span>
        </div>
      </div>
    </div>
  )
}

export default TypingIndicator
