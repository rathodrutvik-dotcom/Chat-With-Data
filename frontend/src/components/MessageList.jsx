import Message from './Message'
import TypingIndicator from './TypingIndicator'
import { useChat } from '../context/ChatContext'

const MessageList = ({ messages }) => {
  const { sendingMessage } = useChat()

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {messages.map((message, index) => (
        <Message key={index} message={message} />
      ))}
      
      {sendingMessage && <TypingIndicator />}
    </div>
  )
}

export default MessageList
