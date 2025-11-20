# ScheduleFirst AI

An intelligent course scheduling application for CUNY students, powered by AI and built with modern web technologies.

## Features

### 🎯 Core Functionality
- **Smart Course Search**: Search courses with advanced filters (department, modality, time slots)
- **AI-Powered Optimization**: Generate optimal schedules based on your preferences
- **Conflict Detection**: Automatic detection and prevention of schedule conflicts
- **Interactive Calendar**: Visual schedule grid with drag-and-drop support
- **Professor Ratings**: View and compare professor ratings and reviews
- **Real-time Updates**: Instant UI updates with optimistic rendering

### 🔐 Authentication & Security
- Secure authentication with Supabase
- Protected routes with automatic redirects
- Session management and token refresh
- Row-level security (RLS) for data access

### ♿ Accessibility
- WCAG 2.1 AA compliant
- Full keyboard navigation support
- Screen reader compatible
- High contrast colors
- Responsive design for all devices

### ⚡ Performance
- Debounced search (300ms)
- Cached API responses (5 minutes)
- Memoized calculations
- Lazy loading for images and content
- Code splitting for faster loads

## Tech Stack

### Frontend
- **React 18** - UI library with concurrent features
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **React Router** - Client-side routing
- **Tailwind CSS** - Utility-first styling
- **Radix UI** - Accessible component primitives
- **Framer Motion** - Smooth animations

### Backend
- **Supabase** - PostgreSQL database with real-time capabilities
- **FastAPI** - Python backend for AI features
- **Google Gemini AI** - AI-powered schedule optimization

### Development Tools
- **TypeScript** - Static type checking
- **SWC** - Fast TypeScript/JavaScript compiler
- **PostCSS** - CSS processing

## Getting Started

### Prerequisites
- Node.js 18+ and npm
- Supabase account
- Google Gemini API key (for AI features)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/KBesada24/ScheduleFirst-AI.git
cd ScheduleFirst-AI
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```env
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

4. Start the development server:
```bash
npm run dev
```

5. Open [http://localhost:5173](http://localhost:5173) in your browser

### Backend Setup

See `services/README.md` for backend setup instructions.

## Project Structure

```
├── src/
│   ├── components/        # React components
│   │   ├── auth/         # Authentication components
│   │   ├── schedule/     # Schedule-related components
│   │   └── ui/           # Reusable UI components
│   ├── hooks/            # Custom React hooks
│   ├── lib/              # Utility functions and helpers
│   ├── types/            # TypeScript type definitions
│   └── App.tsx           # Main application component
├── services/             # Backend services
│   ├── mcp_server/       # MCP server for AI integration
│   └── background_jobs/  # Scheduled tasks
├── docs/                 # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── ACCESSIBILITY.md
│   ├── PERFORMANCE_OPTIMIZATION.md
│   └── INTEGRATION_TESTING.md
└── supabase/             # Database migrations and config
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run types:supabase` - Generate TypeScript types from Supabase

## Documentation

- [API Documentation](docs/API_DOCUMENTATION.md) - Complete API reference
- [Accessibility Guide](docs/ACCESSIBILITY.md) - Accessibility features and compliance
- [Performance Optimization](docs/PERFORMANCE_OPTIMIZATION.md) - Performance strategies
- [Integration Testing](docs/INTEGRATION_TESTING.md) - Testing approach and results
- [Button Audit](docs/BUTTON_AUDIT.md) - Button component inventory
- [Supabase Guide](SUPABASE_GUIDE.md) - Database setup and queries

## Key Features Implementation

### Form Validation
All forms use centralized validation with the `useFormSubmission` hook:
```typescript
const { values, errors, handleSubmit } = useFormSubmission(
  { email: "", password: "" },
  {
    validationRules: {
      email: combine(required, email),
      password: combine(required, minLength(8)),
    },
    onSubmit: async (values) => await signIn(values.email, values.password),
  }
);
```

### Course Search with Caching
Search results are automatically cached and debounced:
```typescript
const { courses, loading, search } = useCourseSearch();
search("Computer Science", { department: "csc" }); // Debounced 300ms
```

### Schedule Optimization
AI-powered schedule generation with constraints:
```typescript
<OptimizeButton
  courseCodes={["CSC 101", "MATH 201"]}
  constraints={{
    earliestStartTime: "09:00",
    latestEndTime: "17:00",
    minProfessorRating: 4.0
  }}
  onOptimized={(schedules) => setSchedules(schedules)}
/>
```

## Performance Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Button click response | < 50ms | ~10ms | ✅ |
| API call initiation | < 100ms | ~20ms | ✅ |
| DOM update | < 100ms | ~50ms | ✅ |
| Calendar render | < 200ms | ~120ms | ✅ |
| Page navigation | < 300ms | ~150ms | ✅ |

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Acknowledgments

- CUNY for course data
- Supabase for backend infrastructure
- Google Gemini for AI capabilities
- Radix UI for accessible components
- Tailwind CSS for styling utilities

## Support

For issues and questions:
- Open an issue on GitHub
- Contact: [your-email@example.com]

## Roadmap

- [ ] Mobile app (React Native)
- [ ] Email notifications for schedule changes
- [ ] Course recommendations based on major
- [ ] Study group finder
- [ ] Grade prediction
- [ ] Multi-semester planning
