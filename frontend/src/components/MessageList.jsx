import { useRef, useEffect, createRef } from 'react'
import Message from './Message'
import TypingIndicator from './TypingIndicator'
import { useChat } from '../context/ChatContext'

const MessageList = ({ messages }) => {
  const { sendingMessage, searchHighlight, setSearchHighlight } = useChat()
  const messageRefs = useRef([])

  const normalize = (text) =>
    (text || '')
      .toString()
      .toLowerCase()
      .replace(/\s+/g, ' ')
      .trim()

  // Initialize refs for each message
  useEffect(() => {
    messageRefs.current = messages.map((_, i) => messageRefs.current[i] || createRef())
  }, [messages])

  // Handle search highlight - scroll to match and clear after 2 seconds
  useEffect(() => {
    if (searchHighlight?.query && searchHighlight?.timestamp) {
      // Prefer exact message timestamp match (from search results)
      let matchIndex = -1
      if (searchHighlight.messageTimestamp) {
        matchIndex = messages.findIndex(
          (msg) => msg.timestamp === searchHighlight.messageTimestamp
        )
      }

      // Fallback: try matching a snippet (strip ellipses)
      if (matchIndex === -1 && searchHighlight.snippet) {
        const snippet = searchHighlight.snippet.replace(/\.\.\./g, '').trim()
        if (snippet) {
          const normalizedSnippet = normalize(snippet)
          matchIndex = messages.findIndex((msg) =>
            normalize(msg.content).includes(normalizedSnippet)
          )
        }
      }

      // Fallback: find first message that contains the search query
      if (matchIndex === -1) {
        const normalizedQuery = normalize(searchHighlight.query)
        matchIndex = messages.findIndex(
          (msg) =>
            normalize(msg.content).includes(normalizedQuery)
        )
      }

      const scrollTimer =
        matchIndex !== -1 && messageRefs.current[matchIndex]?.current
          ? setTimeout(() => {
              messageRefs.current[matchIndex].current?.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
              })
            }, 300)
          : null

      // Clear highlight after 2 seconds
      const clearTimer = setTimeout(() => {
        setSearchHighlight(null)
      }, 2000)

      return () => {
        if (scrollTimer) clearTimeout(scrollTimer)
        clearTimeout(clearTimer)
      }
    }
  }, [searchHighlight?.timestamp, messages, setSearchHighlight])

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {messages.map((message, index) => (
        <Message 
          key={index} 
          message={message}
          ref={messageRefs.current[index]}
          highlightQuery={searchHighlight?.query || null}
        />
      ))}
      
      {sendingMessage && <TypingIndicator />}
    </div>
  )
}

export default MessageList
