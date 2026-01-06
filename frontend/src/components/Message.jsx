import { FaUser, FaRobot } from 'react-icons/fa'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

const Message = ({ message }) => {
  const isUser = message.role === 'user'

  return (
    <div
      className={`flex items-start space-x-4 animate-fade-in ${
        isUser ? 'justify-end' : 'justify-start'
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
          ${
            isUser
              ? 'bg-gradient-to-br from-blue-600 to-purple-600 text-white'
              : 'bg-white border border-gray-200 text-gray-900'
          }
        `}
      >
        {isUser ? (
          <p className="text-base leading-relaxed whitespace-pre-wrap">
            {message.content}
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
                      {children}
                    </code>
                  )
                },
                p({ children }) {
                  return <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
                },
                ul({ children }) {
                  return <ul className="list-disc ml-4 mb-2 space-y-1">{children}</ul>
                },
                ol({ children }) {
                  return <ol className="list-decimal ml-4 mb-2 space-y-1">{children}</ol>
                },
                li({ children }) {
                  return <li className="leading-relaxed">{children}</li>
                },
                strong({ children }) {
                  return <strong className="font-semibold">{children}</strong>
                },
                em({ children }) {
                  return <em className="italic">{children}</em>
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center shadow-lg">
          <FaUser className="w-5 h-5 text-gray-700" />
        </div>
      )}
    </div>
  )
}

export default Message
