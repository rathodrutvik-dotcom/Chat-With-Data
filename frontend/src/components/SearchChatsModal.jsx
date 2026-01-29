import { useState, useEffect, useRef } from 'react' // turbo
import { FaSearch, FaTimes, FaComments, FaHistory } from 'react-icons/fa'
import { formatDistanceToNow } from 'date-fns'
import api, { chatAPI } from '../services/api'
import { useChat } from '../context/ChatContext'

const SearchChatsModal = ({ isOpen, onClose }) => {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState([])
    const [loading, setLoading] = useState(false)
    const { loadSession, sessions } = useChat()
    const inputRef = useRef(null)

    // Focus input when modal opens
    useEffect(() => {
        if (isOpen) {
            setTimeout(() => {
                inputRef.current?.focus()
            }, 50)

            setQuery('')
            // Initial state: show recent chats from the context
            setResults(formatRecentSessions(sessions))
        }
    }, [isOpen, sessions])

    const formatRecentSessions = (sessionList) => {
        return sessionList.slice(0, 5).map(s => ({
            session_id: s.session_id,
            display_name: s.document_name, // fallback
            match_type: 'recent',
            timestamp: s.last_updated
        }))
    }

    // Handle search
    useEffect(() => {
        const search = async () => {
            if (!query.trim()) {
                setResults(formatRecentSessions(sessions))
                return
            }

            setLoading(true)
            try {
                const data = await chatAPI.searchChats(query)
                setResults(data)
            } catch (error) {
                console.error("Search failed", error)
            } finally {
                setLoading(false)
            }
        }

        const debounce = setTimeout(search, 300)
        return () => clearTimeout(debounce)
    }, [query, sessions])

    if (!isOpen) return null

    // Highlight matching text helper
    const HighlightText = ({ text, highlight }) => {
        if (!highlight || !text) return <span>{text}</span>

        // Escape regex characters
        const escapeRegExp = (string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
        const regex = new RegExp(`(${escapeRegExp(highlight)})`, 'i')
        const parts = text.split(regex)

        return (
            <span>
                {parts.map((part, i) =>
                    regex.test(part) ? (
                        <span key={i} className="bg-yellow-200 text-gray-900 font-semibold rounded px-0.5">{part}</span>
                    ) : (
                        <span key={i}>{part}</span>
                    )
                )}
            </span>
        )
    }

    return (
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-20 p-4 animate-fade-in">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-white rounded-xl shadow-2xl max-w-2xl w-full overflow-hidden animate-scale-in flex flex-col max-h-[70vh]">

                {/* Header / Search Input */}
                <div className="relative flex items-center p-4 border-b border-gray-100">
                    <FaSearch className="w-5 h-5 text-gray-400 absolute left-6" />
                    <input
                        ref={inputRef}
                        type="text"
                        className="w-full pl-10 pr-12 py-3 bg-gray-50 text-gray-900 rounded-lg border-none focus:ring-2 focus:ring-blue-100 placeholder-gray-400 text-lg sm:text-base font-normal transition-all"
                        placeholder="Search chats..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                    />
                    <button
                        onClick={onClose}
                        className="absolute right-6 p-1 text-gray-400 hover:text-gray-600 bg-gray-100 hover:bg-gray-200 rounded text-xs px-2 py-1 transition-colors"
                    >
                        ESC
                    </button>
                </div>

                {/* Results List */}
                <div className="flex-1 overflow-y-auto p-2">
                    {loading ? (
                        <div className="py-12 text-center text-gray-500 flex flex-col items-center">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-3"></div>
                            <span>Searching...</span>
                        </div>
                    ) : results.length === 0 ? (
                        <div className="py-12 text-center text-gray-500">
                            <p>No results found for "{query}"</p>
                        </div>
                    ) : (
                        <div className="space-y-1">
                            {/* Section Label */}
                            <div className="px-4 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center">
                                {query ? (
                                    <>
                                        <FaSearch className="mr-2" /> Match Results
                                    </>
                                ) : (
                                    <>
                                        <FaHistory className="mr-2" /> Recent Chats
                                    </>
                                )}
                            </div>

                            {results.map((item) => (
                                <button
                                    key={`${item.session_id}-${item.timestamp}`}
                                    onClick={() => {
                                        const trimmedQuery = query.trim()
                                        loadSession(
                                            item.session_id,
                                            trimmedQuery
                                                ? {
                                                    query: trimmedQuery,
                                                    messageTimestamp:
                                                        item.match_type === 'content'
                                                            ? item.message_timestamp || item.timestamp
                                                            : null,
                                                    snippet: item.match_type === 'content' ? item.snippet : null,
                                                    matchType: item.match_type,
                                                }
                                                : null
                                        )
                                        onClose()
                                    }}
                                    className="w-full text-left px-4 py-3 hover:bg-gray-50 rounded-lg group transition-all duration-200 flex flex-col border border-transparent hover:border-gray-100"
                                >
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="font-medium text-gray-800 flex items-center truncate pr-4">
                                            <FaComments className="mr-2.5 text-gray-400 group-hover:text-blue-500 transition-colors flex-shrink-0" />
                                            <span className="truncate">
                                                <HighlightText text={item.display_name} highlight={query} />
                                            </span>
                                        </span>
                                        {item.timestamp && (
                                            <span className="text-xs text-gray-400 flex-shrink-0 whitespace-nowrap">
                                                {formatDistanceToNow(new Date(item.timestamp), { addSuffix: true })}
                                            </span>
                                        )}
                                    </div>

                                    {/* matching snippet */}
                                    {item.snippet && (
                                        <div className="ml-7 text-sm text-gray-500 line-clamp-2 leading-relaxed">
                                            <HighlightText text={item.snippet} highlight={query} />
                                        </div>
                                    )}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer Hint */}
                {results.length > 0 && (
                    <div className="px-4 py-2 bg-gray-50 border-t border-gray-100 text-xs text-gray-400 text-right">
                        {results.length} result{results.length !== 1 && 's'}
                    </div>
                )}
            </div>
        </div>
    )
}

export default SearchChatsModal
