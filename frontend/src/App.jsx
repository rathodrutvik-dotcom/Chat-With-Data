import { useState } from 'react'
import { ChatProvider } from './context/ChatContext'
import Sidebar from './components/Sidebar'
import ChatContainer from './components/ChatContainer'
import Header from './components/Header'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <ChatProvider>
      <div className="flex h-screen overflow-hidden bg-gray-50">
        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        
        {/* Main Content */}
        <div className="flex flex-col flex-1 overflow-hidden">
          <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
          <ChatContainer />
        </div>
      </div>
    </ChatProvider>
  )
}

export default App
