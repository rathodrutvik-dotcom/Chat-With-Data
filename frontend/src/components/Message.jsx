import { FaUser, FaRobot, FaPaperclip } from 'react-icons/fa'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { forwardRef } from 'react'

const Message = forwardRef(({ message, highlightQuery = null }, ref) => {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  // Helper function to highlight text
  const HighlightText = ({ text }) => {
    if (!highlightQuery || !text) return <span>{text}</span>

    const escapeRegExp = (string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const regex = new RegExp(`(${escapeRegExp(highlightQuery)})`, 'i')
    const parts = text.split(regex)

    return (
      <>
        {parts.map((part, i) =>
          regex.test(part) ? (
            <mark key={i} className="bg-yellow-300 text-gray-900 rounded px-0.5 animate-pulse">{part}</mark>
          ) : (
            part
          )
        )}
      </>
    )
  }

  // Helper to wrap children with highlighting
  const wrapWithHighlight = (children) => {
    if (!highlightQuery) return children
    
    if (typeof children === 'string') {
      return <HighlightText text={children} />
    }
    
    if (Array.isArray(children)) {
      return children.map((child, i) => 
        typeof child === 'string' ? <HighlightText key={i} text={child} /> : child
      )
    }
    
    return children
  }

  // System messages (document additions, etc.)
  if (isSystem) {
    return (
      <div ref={ref} className="flex justify-center my-4 animate-fade-in">
        <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-200 rounded-full text-sm text-blue-700">
          <FaPaperclip className="w-3 h-3" />
          <span><HighlightText text={message.content} /></span>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={ref}
      className={`flex items-start space-x-4 animate-fade-in ${isUser ? 'justify-end' : 'justify-start'
        }`}
    >
      {!isUser && (
        <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
          <FaRobot className="w-5 h-5 text-white" />
        </div>
      )}

      <div
        className={`
          max-w-[80%] rounded-2xl px-5 py-3 shadow-sm
          ${isUser
            ? 'bg-gradient-to-br from-blue-600 to-purple-600 text-white'
            : 'bg-white border border-gray-200 text-gray-900'
          }
        `}
      >
        {isUser ? (
          <p className="text-base leading-relaxed whitespace-pre-wrap">
            <HighlightText text={message.content} />
          </p>
        ) : (
          <div className="message-content prose prose-sm max-w-none">
            <ReactMarkdown
              components={{
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '')
                  return !inline && match ? (
                    <SyntaxHighlighter
                      style={vscDarkPlus}
                      language={match[1]}
                      PreTag="div"
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>
                      {wrapWithHighlight(children)}
                    </code>
                  )
                },
                a({ href, children }) {
                  // Make links open in new tab with proper styling
                  return (
                    <a 
                      href={href} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 underline font-medium"
                    >
                      {children}
                    </a>
                  )
                },
                p({ children }) {
                  return <p className="mb-2 last:mb-0 leading-relaxed">{wrapWithHighlight(children)}</p>
                },
                ul({ children }) {
                  return <ul className="list-disc ml-4 mb-2 space-y-1">{children}</ul>
                },
                ol({ children }) {
                  return <ol className="list-decimal ml-4 mb-2 space-y-1">{children}</ol>
                },
                li({ children }) {
                  return <li className="leading-relaxed">{wrapWithHighlight(children)}</li>
                },
                strong({ children }) {
                  return <strong className="font-semibold">{wrapWithHighlight(children)}</strong>
                },
                em({ children }) {
                  return <em className="italic">{wrapWithHighlight(children)}</em>
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center shadow-lg text-xl">
          🧑
        </div>
      )}
    </div>
  )
})

Message.displayName = 'Message'

export default Message
