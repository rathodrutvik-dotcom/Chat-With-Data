# Chat with Documents - React Frontend

A modern, ChatGPT-style React frontend for the RAG-powered document chat application.

## 🎨 Features

- **ChatGPT-like Interface**: Modern, intuitive UI with smooth animations
- **Real-time Chat**: Instant responses with typing indicators
- **Session Management**: Create, switch, and manage multiple document sessions
- **Document Upload**: Drag-and-drop support for PDF, DOCX, and XLSX files
- **Markdown Support**: Rich text rendering with code syntax highlighting
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Persistent History**: All chats are automatically saved

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.8+ (for backend)
- Running FastAPI backend server

### Installation

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Create environment file (optional):**
   ```bash
   echo "VITE_API_URL=http://localhost:8000/api" > .env
   ```

### Running the Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

### Preview Production Build

```bash
npm run preview
```

## 📁 Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── components/      # React components
│   │   ├── ChatContainer.jsx     # Main chat interface
│   │   ├── Message.jsx           # Individual message component
│   │   ├── MessageList.jsx       # Messages list
│   │   ├── MessageInput.jsx      # Chat input box
│   │   ├── Sidebar.jsx           # Sessions sidebar
│   │   ├── Header.jsx            # Top header
│   │   ├── FileUpload.jsx        # File upload modal
│   │   ├── EmptyState.jsx        # Landing page
│   │   └── TypingIndicator.jsx   # Loading animation
│   ├── context/         # React Context
│   │   └── ChatContext.jsx       # Global state management
│   ├── services/        # API services
│   │   └── api.js               # API client
│   ├── App.jsx          # Main app component
│   ├── main.jsx         # Entry point
│   └── index.css        # Global styles
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## 🔌 API Integration

The frontend communicates with the FastAPI backend through REST APIs:

### Endpoints Used

- `GET /api/sessions` - Get all sessions
- `GET /api/sessions/{id}/messages` - Get chat history
- `POST /api/upload` - Upload documents
- `POST /api/chat` - Send message
- `DELETE /api/sessions/{id}` - Delete session
- `POST /api/sessions/{id}/clear` - Clear chat history

## 🎨 Customization

### Colors & Theme

Edit `tailwind.config.js` to customize colors:

```js
theme: {
  extend: {
    colors: {
      primary: { ... },
      dark: { ... }
    }
  }
}
```

### API URL

Set the backend URL in `.env`:

```env
VITE_API_URL=http://your-backend-url:8000/api
```

## 🛠️ Technologies

- **React 18** - UI framework
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **React Markdown** - Markdown rendering
- **React Syntax Highlighter** - Code highlighting
- **React Icons** - Icon library
- **date-fns** - Date formatting

## 📱 Responsive Design

The app is fully responsive and works on:
- Desktop (1024px+)
- Tablet (768px - 1023px)
- Mobile (< 768px)

## 🐛 Troubleshooting

### Port Already in Use

If port 5173 is already in use, edit `vite.config.js`:

```js
server: {
  port: 3000, // Change to your preferred port
}
```

### API Connection Issues

1. Check if backend is running on port 8000
2. Verify CORS settings in backend
3. Check browser console for errors

### Build Errors

Clear node_modules and reinstall:

```bash
rm -rf node_modules package-lock.json
npm install
```

## 📝 Development Tips

### Hot Reload

Vite provides instant hot reload. Just save your files and see changes immediately.

### ESLint

Run linter:
```bash
npm run lint
```

### Component Development

- Keep components small and focused
- Use Context for global state
- Follow React best practices
- Add PropTypes or TypeScript for type safety

## 🤝 Contributing

1. Follow the existing code style
2. Use meaningful component and variable names
3. Add comments for complex logic
4. Test on multiple devices

## 📄 License

Same as parent project

## 🆘 Support

For issues or questions, check the main project README or create an issue.
