import { FaUpload, FaRocket, FaShieldAlt, FaFileAlt } from 'react-icons/fa'
import { useState } from 'react'
import FileUpload from './FileUpload'

const EmptyState = () => {
  const [showUpload, setShowUpload] = useState(false)

  const features = [
    {
      icon: <FaFileAlt className="w-6 h-6" />,
      title: 'Multiple Formats',
      description: 'Upload PDF, DOCX, and XLSX files',
    },
    {
      icon: <FaRocket className="w-6 h-6" />,
      title: 'Powered by AI',
      description: 'Advanced RAG with semantic search',
    },
    {
      icon: <FaShieldAlt className="w-6 h-6" />,
      title: 'Session Management',
      description: 'Persistent chat history',
    },
  ]

  return (
    <>
      <div className="h-full flex items-center justify-center p-8">
        <div className="max-w-2xl w-full text-center space-y-8">
          {/* Hero Section */}
          <div className="space-y-4">
            <div className="flex justify-center">
              <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
                <span className="text-5xl">📚</span>
              </div>
            </div>
            <h1 className="text-4xl font-bold text-gray-900">
              Chat with Your Documents
            </h1>
            <p className="text-xl text-gray-600 max-w-lg mx-auto">
              Upload your documents and start asking questions. Get instant, intelligent answers powered by advanced AI.
            </p>
          </div>

          {/* CTA Button */}
          <div>
            <button
              onClick={() => setShowUpload(true)}
              className="inline-flex items-center space-x-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-4 rounded-xl font-semibold text-lg transition-all transform hover:scale-105 shadow-lg"
            >
              <FaUpload className="w-5 h-5" />
              <span>Upload Documents</span>
            </button>
          </div>

          {/* Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
            {features.map((feature, index) => (
              <div
                key={index}
                className="bg-white p-6 rounded-xl border border-gray-200 hover:border-blue-300 hover:shadow-lg transition-all"
              >
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600 mb-4 mx-auto">
                  {feature.icon}
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-gray-600">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>

          {/* Info Text */}
          <div className="text-sm text-gray-500 max-w-md mx-auto pt-4">
            <p>
              Your documents are processed securely and stored locally. Chat history is automatically saved for each session.
            </p>
          </div>
        </div>
      </div>

      {showUpload && <FileUpload onClose={() => setShowUpload(false)} />}
    </>
  )
}

export default EmptyState
