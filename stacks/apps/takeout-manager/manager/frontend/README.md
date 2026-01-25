# Takeout Manager Frontend

Vue.js 3 frontend for the Google Photos Takeout Manager.

## Development

### Prerequisites

- Node.js 20+
- npm

### Setup

```bash
# Install dependencies
npm install

# Start development server with hot-reload
npm run dev
```

The development server will start on `http://localhost:5173` with API proxy configured to forward `/api/*` requests to `http://localhost:8000`.

### Building for Production

```bash
# Build for production
npm run build
```

This creates optimized static files in the `dist/` directory, which are copied to the manager's static directory during Docker build.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── CreateJob.vue      # Job creation form
│   │   ├── JobList.vue        # Job listing with stats
│   │   └── JobModal.vue       # Job detail modal
│   ├── App.vue                # Main app component
│   └── main.js                # App entry point
├── index.html                 # HTML template
├── package.json               # Dependencies
└── vite.config.js            # Vite configuration
```

## Features

- **Job Creation**: Form to create new takeout jobs with all required parameters
- **Job Monitoring**: Real-time job status and progress tracking
- **Chunk Visualization**: Visual grid showing status of each archive chunk
- **Cookie Management**: Update expired cookies without recreating jobs
- **Auto-refresh**: Automatic polling for status updates every 5 seconds
