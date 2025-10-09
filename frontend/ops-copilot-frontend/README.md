# OEE Co-Pilot Frontend

A modern, responsive Angular frontend for the OEE Co-Pilot chatbot that converts natural language queries to SQL and displays results with interactive charts.

## Features

- 🤖 **Intelligent Chat Interface**: Natural language to SQL conversion
- 📊 **Interactive Charts**: ECharts integration for data visualization
- 📱 **Responsive Design**: Works seamlessly on desktop and mobile
- 💾 **Chat History**: Persistent conversation storage
- 🔄 **Real-time Updates**: Live connection status monitoring
- 🎨 **Modern UI**: Beautiful gradient design with smooth animations

## Technology Stack

- **Angular 20**: Latest Angular framework with standalone components
- **ECharts**: Interactive charting library via ngx-echarts
- **SCSS**: Enhanced styling with modern CSS features
- **RxJS**: Reactive programming for API communication
- **TypeScript**: Type-safe development

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Angular CLI 20+
- Backend API running on http://localhost:8000

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start development server:**
   ```bash
   npm start
   ```

3. **Open your browser:**
   Navigate to http://localhost:4200

### Using the Development Script

From the project root directory:
```bash
./start_dev.sh
```

This script will:
- Start the FastAPI backend
- Start the Angular frontend
- Handle cleanup on exit

## Project Structure

```
src/
├── app/
│   ├── components/
│   │   └── chat/           # Main chat interface
│   │       ├── chat.ts     # Chat component logic
│   │       ├── chat.html   # Chat template
│   │       └── chat.scss   # Chat styles
│   ├── services/
│   │   ├── api.ts          # Backend API service
│   │   └── chat-history.ts # Chat persistence service
│   ├── app.ts              # Main app component
│   └── app.html            # App template
├── environments/           # Environment configurations
└── styles.scss            # Global styles
```

## Key Components

### Chat Component (`chat.ts`)

The main chat interface that handles:
- Message display and formatting
- SQL query visualization
- Chart rendering with ECharts
- Data table pagination
- Copy-to-clipboard functionality

### API Service (`api.ts`)

Enhanced HTTP service with:
- Error handling and retry logic
- Connection status monitoring
- Request/response interceptors
- Type-safe interfaces

### Chat History Service (`chat-history.ts`)

Local storage management for:
- Conversation persistence
- Session management
- Message history

## Features in Detail

### Natural Language Processing

The frontend seamlessly integrates with the backend's LangChain agent to:
- Convert natural language to SQL queries
- Display generated SQL with syntax highlighting
- Show execution metadata (time, result count)

### Data Visualization

Interactive charts powered by ECharts:
- **Pie Charts**: For distribution analysis
- **Line Charts**: For trend visualization
- **Bar Charts**: For comparisons
- **Heatmaps**: For correlation analysis
- **Pareto Charts**: For 80/20 analysis

### Responsive Design

- **Desktop**: Full-featured interface with sidebars
- **Tablet**: Optimized layout with collapsible elements
- **Mobile**: Touch-friendly interface with simplified navigation

### Real-time Features

- Connection status indicator
- Typing animations
- Smooth message transitions
- Auto-scroll to latest messages

## API Integration

The frontend communicates with the backend through these endpoints:

- `POST /api/query` - Process natural language queries
- `GET /api/suggestions` - Get query suggestions
- `GET /api/schema` - Get database schema
- `GET /health` - Health check

## Styling

The application uses a modern design system with:
- **Color Palette**: Gradient backgrounds with semantic colors
- **Typography**: Inter font family for readability
- **Spacing**: Consistent 8px grid system
- **Animations**: Smooth transitions and micro-interactions
- **Dark Mode**: Ready for future dark theme implementation

## Development

### Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run unit tests
- `npm run watch` - Build and watch for changes

### Code Style

The project follows Angular best practices:
- Standalone components
- Type-safe interfaces
- Reactive programming with RxJS
- SCSS for styling
- ESLint for code quality

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Performance

- Lazy loading for components
- OnPush change detection strategy
- Optimized bundle size
- Efficient chart rendering
- Minimal re-renders

## Security

- XSS protection through Angular's sanitization
- CORS configuration for API calls
- Input validation and sanitization
- Secure local storage usage

## Troubleshooting

### Common Issues

1. **Backend Connection Failed**
   - Ensure backend is running on port 8000
   - Check CORS configuration
   - Verify API endpoints

2. **Charts Not Rendering**
   - Check ECharts library installation
   - Verify chart data format
   - Check browser console for errors

3. **Styling Issues**
   - Clear browser cache
   - Check SCSS compilation
   - Verify font loading

### Debug Mode

Enable debug logging in the browser console:
```typescript
// In chat.ts
console.log('Chart spec:', chartSpec);
console.log('API response:', response);
```

## Contributing

1. Follow Angular style guide
2. Write unit tests for new features
3. Update documentation
4. Test on multiple browsers
5. Ensure responsive design

## License

This project is part of the OEE Co-Pilot system for mining operations analytics.