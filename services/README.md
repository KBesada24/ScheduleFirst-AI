# CUNY Schedule Optimizer - Backend Services

Backend MCP (Model Context Protocol) server for the CUNY AI Schedule Optimizer. Built with Python, FastMCP, and integrates with Google Gemini AI.

## 🏗️ Architecture

```
services/
├── mcp_server/          # Main MCP server
│   ├── main.py          # Entry point
│   ├── config.py        # Configuration management
│   ├── models/          # Pydantic data models
│   ├── services/        # Business logic & scrapers
│   ├── tools/           # FastMCP tools
│   └── utils/           # Utilities (logging, cache, validators)
└── background_jobs/     # Scheduled tasks
    ├── scheduler.py     # APScheduler setup
    └── jobs/            # Job definitions
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Poetry (recommended) or pip
- PostgreSQL (or Supabase account)
- Google Gemini API key
- Chrome/Chromium (for web scraping)

### Installation

1. **Clone the repository**
```bash
cd services
```

2. **Install dependencies**
```bash
# Using Poetry (recommended)
poetry install

# Or using pip
pip install -r requirements/base.txt
```

3. **Set up environment variables**
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
GEMINI_API_KEY=your_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_key_here
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
```

4. **Run the MCP server**
```bash
# Using Poetry
poetry run python -m mcp_server.main

# Or directly
python -m mcp_server.main
```

## 📋 Available MCP Tools

The server exposes the following tools via FastMCP:

### 1. `fetch_course_sections`
Fetch available course sections from CUNY database.

**Parameters:**
- `course_codes`: List[str] - Course codes (e.g., ["CSC381", "MATH201"])
- `semester`: str - Semester (e.g., "Fall 2025")
- `university`: Optional[str] - CUNY school name

**Returns:** Course sections with professor, time, location, and enrollment data

### 2. `generate_optimized_schedule`
Generate optimized course schedules based on requirements and preferences.

**Parameters:**
- `required_courses`: List[str] - Required course codes
- `semester`: str - Semester
- `university`: str - CUNY school name
- `preferred_days`: Optional[List[str]] - Preferred days (e.g., ["MWF"])
- `earliest_start_time`: Optional[str] - Earliest class time (HH:MM)
- `latest_end_time`: Optional[str] - Latest class time (HH:MM)
- `min_professor_rating`: Optional[float] - Minimum professor rating
- `max_schedules`: int - Max schedules to return (default: 5)

**Returns:** Ranked optimized schedules with conflict detection

### 3. `get_professor_grade`
Get AI-generated grade (A-F) for a professor based on RateMyProfessors reviews.

**Parameters:**
- `professor_name`: str - Full name of professor
- `university`: str - CUNY school name
- `course_code`: Optional[str] - Course code to filter ratings

**Returns:** Professor grade, metrics, and review analysis

### 4. `compare_professors`
Compare multiple professors side-by-side.

**Parameters:**
- `professor_names`: List[str] - Professor names to compare
- `university`: str - CUNY school name
- `course_code`: Optional[str] - Course context

**Returns:** Comparison data with AI recommendation

### 5. `check_schedule_conflicts`
Check for conflicts in a set of course sections.

**Parameters:**
- `section_ids`: List[str] - Section IDs (UUIDs)

**Returns:** Detected conflicts with severity and suggestions

## 🤖 Background Jobs

Automated tasks run on a schedule:

### Course Sync Job
- **Schedule:** Every Sunday at 2 AM
- **Function:** Scrapes CUNY Global Search for course data
- **Updates:** Courses, sections, enrollment data

### Reviews Scrape Job
- **Schedule:** Every Monday at 3 AM
- **Function:** Scrapes RateMyProfessors for reviews
- **Updates:** Professor reviews and ratings

### Grades Update Job
- **Schedule:** Every Monday at 5 AM
- **Function:** Analyzes reviews and generates professor grades
- **Updates:** Professor composite scores and letter grades

### Running Background Jobs

```bash
# Start the scheduler
python -m background_jobs.scheduler
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_server --cov-report=html

# Run specific test file
pytest mcp_server/tests/test_schedule_optimizer.py
```

## 📊 Data Flow

```
CUNY Global Search → Scraper → PostgreSQL (Supabase)
                                      ↓
RateMyProfessors → Scraper → Review Storage
                                      ↓
                            Sentiment Analysis
                                      ↓
                            Professor Grades
                                      ↓
User Request → MCP Server → Gemini AI → Optimized Schedule
```

## 🔧 Configuration

All configuration is managed via environment variables in `.env`:

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `LOG_LEVEL` | Logging level (INFO, DEBUG, etc.) | No |
| `SCRAPER_REQUEST_DELAY` | Delay between scraper requests (seconds) | No |

## 📝 Logging

Logs are written to:
- **Console:** Structured JSON logs (production) or text (development)
- **Files:** 
  - `logs/app.log` - All logs (production only)
  - `logs/error.log` - Error logs only

Configure via:
```env
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## 🐛 Debugging

Enable debug mode:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

View detailed logs:
```bash
tail -f logs/app.log
```

## 🚢 Deployment

### Railway / Fly.io

1. **Set environment variables** in the dashboard
2. **Deploy:**
```bash
# Railway
railway up

# Fly.io
fly deploy
```

### Docker

```bash
# Build image
docker build -t cuny-mcp-server .

# Run container
docker run -p 8000:8000 --env-file .env cuny-mcp-server
```

## 📚 Additional Documentation

- [API Documentation](../docs/API.md)
- [Architecture Guide](../docs/ARCHITECTURE.md)
- [Database Schema](../docs/DATABASE.md)
- [MCP Tools Reference](../docs/MCP_TOOLS.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Support

- Issues: [GitHub Issues](https://github.com/your-repo/issues)
- Email: support@cunyschedule.com
- Discord: [Join our server](https://discord.gg/your-invite)

---

**Built with ❤️ for CUNY students**
