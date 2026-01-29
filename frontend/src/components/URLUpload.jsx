import { useState } from 'react'
import { FaTimes, FaGlobe, FaLink, FaCheckCircle, FaExclamationTriangle } from 'react-icons/fa'
import { useChat } from '../context/ChatContext'

const URLUpload = ({ onClose }) => {
  const { uploadURLs, uploading, uploadProgress } = useChat()
  const [urlText, setUrlText] = useState('')
  const [urls, setUrls] = useState([])
  const [error, setError] = useState('')

  const validateURL = (url) => {
    try {
      // Add https:// if no protocol specified
      const urlToValidate = url.match(/^https?:\/\//) ? url : `https://${url}`
      new URL(urlToValidate)
      return true
    } catch {
      return false
    }
  }

  const parseURLs = () => {
    setError('')
    
    // Split by newlines and filter empty lines
    const lines = urlText.split('\n').map(line => line.trim()).filter(line => line)
    
    if (lines.length === 0) {
      setError('Please enter at least one URL')
      return
    }

    const validUrls = []
    const invalidUrls = []

    lines.forEach(line => {
      if (validateURL(line)) {
        validUrls.push(line)
      } else {
        invalidUrls.push(line)
      }
    })

    if (invalidUrls.length > 0) {
      setError(`Invalid URL(s): ${invalidUrls.join(', ')}`)
      return
    }

    setUrls(validUrls)
    setUrlText('')
  }

  const removeUrl = (index) => {
    setUrls(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (urls.length === 0) return

    try {
      setError('')
      await uploadURLs(urls)
      onClose()
    } catch (error) {
      setError(error.message || 'Failed to process URLs. Please try again.')
      console.error('URL upload error:', error)
    }
  }

  const extractDomain = (url) => {
    try {
      const urlObj = new URL(url.match(/^https?:\/\//) ? url : `https://${url}`)
      return urlObj.hostname.replace('www.', '')
    } catch {
      return url
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-teal-600 rounded-full flex items-center justify-center">
              <FaGlobe className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Add URLs</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            disabled={uploading}
          >
            <FaTimes className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
          {/* URL Input Area */}
          {urls.length === 0 && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Enter URLs (one per line)
                </label>
                <textarea
                  value={urlText}
                  onChange={(e) => setUrlText(e.target.value)}
                  placeholder="https://example.com&#10;https://docs.example.com&#10;https://blog.example.com"
                  className="w-full h-40 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none font-mono text-sm"
                  disabled={uploading}
                />
                <p className="text-xs text-gray-500 mt-2">
                  Each URL will be crawled along with its linked pages (up to 10 pages per URL)
                </p>
              </div>

              <button
                onClick={parseURLs}
                disabled={!urlText.trim() || uploading}
                className="w-full px-6 py-3 bg-gradient-to-r from-green-600 to-teal-600 hover:from-green-700 hover:to-teal-700 text-white rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                <FaLink className="w-4 h-4" />
                <span>Add URLs</span>
              </button>
            </div>
          )}

          {/* URLs List */}
          {urls.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-gray-900">
                  URLs to Process ({urls.length})
                </h3>
                {!uploading && (
                  <button
                    onClick={() => setUrls([])}
                    className="text-sm text-gray-600 hover:text-gray-900"
                  >
                    Clear All
                  </button>
                )}
              </div>

              <div className="space-y-2 max-h-60 overflow-y-auto">
                {urls.map((url, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-gradient-to-r from-green-50 to-teal-50 rounded-lg border border-green-200"
                  >
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      <FaGlobe className="w-5 h-5 text-green-600 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {extractDomain(url)}
                        </p>
                        <p className="text-xs text-gray-600 truncate">
                          {url}
                        </p>
                      </div>
                    </div>
                    {!uploading && (
                      <button
                        onClick={() => removeUrl(index)}
                        className="p-2 hover:bg-white hover:bg-opacity-50 rounded-lg transition-colors"
                      >
                        <FaTimes className="w-4 h-4 text-gray-500" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="flex items-start space-x-2">
                  <FaCheckCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-blue-900">
                    <p className="font-medium">What happens next?</p>
                    <ul className="mt-1 space-y-1 text-xs text-blue-800">
                      <li>• Each URL will be fetched and validated (3s timeout)</li>
                      <li>• Navigation links will be followed (up to 10 pages per URL)</li>
                      <li>• Duplicate pages will be automatically skipped</li>
                      <li>• Content will be processed and ready for chat</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <FaExclamationTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-red-900">
                  <p className="font-medium">Error</p>
                  <p className="mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Upload Progress */}
          {uploading && (
            <div className="mt-6 space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Processing URLs...</span>
                <span className="font-medium text-green-600">{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-green-500 to-teal-600 h-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-xs text-gray-500 text-center">
                Fetching and processing web content... This may take a moment.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-6 py-2 text-gray-700 hover:bg-gray-200 rounded-lg font-medium transition-colors"
            disabled={uploading}
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={urls.length === 0 || uploading}
            className="px-6 py-2 bg-gradient-to-r from-green-600 to-teal-600 hover:from-green-700 hover:to-teal-700 text-white rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {uploading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <FaGlobe className="w-4 h-4" />
                <span>Start Chat</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default URLUpload
