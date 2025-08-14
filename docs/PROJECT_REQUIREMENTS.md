# Project Requirements & Configuration

## Project Overview
This document captures all project requirements, decisions, and configurations for the personal portfolio website.

## Content Strategy
### Projects to Highlight
- [x] Financial Options Pricing Model (Python, PyTorch)
- [ ] Django Optimization Web App

### Design Preferences
- [ ] Add design system preferences
- [ ] Include brand colors/fonts if any

## Technical Configuration
### Deployment
- Frontend Host: Vercel
- Backend Host: 
- Custom Domain: 

### Analytics
- [ ] Google Analytics ID:
- [ ] Other tracking:

## Feature Priorities
### MVP Features
- [x] Project showcase
- [x] Contact form
- [ ] Blog section
- [ ] AI features

### Future Features
- [ ] User authentication
- [ ] Content management system
- [ ] Monetization options

## Technical Decisions
### Styling
- Primary CSS: Tailwind CSS
- Component Library: shadcn/ui (if needed)

### State Management
- Frontend: React Context + useState/useReducer
- Backend: 

## Testing Requirements
- [ ] Unit test coverage goal: %
- [ ] E2E test critical paths
- [ ] Performance budget:

## Accessibility
- [ ] WCAG Level: (A/AA/AAA)
- [ ] Screen reader testing needed: [ ]
- [ ] Keyboard navigation testing needed: [ ]

## Content Management
- [ ] Headless CMS: [Yes/No]
- [ ] Preferred CMS if yes:
- [ ] Content update workflow:

## API Endpoints
### Projects
- `GET /api/projects` - List all projects
- `GET /api/projects/{id}` - Get project details
- `POST /api/contact` - Submit contact form

## Environment Variables
Required environment variables are listed in `.env.example`.

## Development Setup
### Prerequisites
- Node.js v18+
- Python 3.9+
- pnpm

### Getting Started
1. Clone the repository
2. Install dependencies:
   ```bash
   # Frontend
   cd apps/web
   pnpm install
   
   # Backend
   cd ../../apps/api
   pip install -e .[dev]
   ```
3. Copy `.env.example` to `.env` and configure
4. Start development servers:
   ```bash
   # Frontend
   cd apps/web
   pnpm dev
   
   # Backend
   cd ../api
   uvicorn app.main:app --reload
   ```

## Open Questions
### Content
1. What specific projects should be highlighted in the portfolio?
2. Are there any specific design systems or themes to follow?

### Technical
1. Preferred database for future scaling?
2. Any specific performance requirements?

### Deployment
1. Preferred backend hosting provider?
2. Need CI/CD pipeline setup?

## Change Log
- 2025-08-13: Initial document created
