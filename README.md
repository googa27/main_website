# Portfolio Monorepo

A modern, recruiter-friendly portfolio website built with Next.js, FastAPI, and TypeScript. This monorepo demonstrates full-stack development skills with a clean, scalable architecture.

## 🚀 Features

- **Frontend**: Next.js 15 with App Router, TypeScript, and Tailwind CSS
- **Backend**: FastAPI with Python, Pydantic models, and RESTful APIs
- **Monorepo**: Turborepo + pnpm for efficient development
- **Code Quality**: ESLint, Prettier, Ruff, and MyPy with pre-commit hooks
- **Deterministic Installs**: `pnpm-lock.yaml` ensures consistent dependencies
- **Responsive Design**: Mobile-first approach with modern UI/UX
- **SEO Optimized**: Meta tags, semantic HTML, and accessibility features

## 📁 Project Structure

```
├── apps/
│   ├── web/                 # Next.js frontend
│   │   ├── src/
│   │   │   ├── app/        # App Router pages
│   │   │   ├── components/ # React components
│   │   │   └── lib/        # Utilities and API client
│   │   └── public/         # Static assets
│   └── api/                # FastAPI backend
│       ├── app/
│       │   ├── routers/    # API endpoints
│       │   ├── models/     # Pydantic models
│       │   └── core/       # Configuration
│       └── data/           # Sample data
├── packages/
│   ├── config/             # Shared ESLint/Prettier/TS configs
│   └── ui/                 # Future shared React components
├── docs/                   # Project documentation
└── scripts/                # Development utilities
```

## 🛠️ Tech Stack

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React hooks
- **Build Tool**: Turbopack

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.12+
- **Validation**: Pydantic
- **CORS**: Built-in middleware
- **Server**: Uvicorn

### Development
- **Package Manager**: pnpm
- **Monorepo**: Turborepo
- **Linting**: ESLint + Ruff
- **Formatting**: Prettier + Ruff
- **Type Checking**: TypeScript + MyPy
- **Hooks**: Pre-commit + Husky

## 🚀 Quick Start

### Prerequisites

- **Node.js**: 22+
- **Python**: 3.12+
- **pnpm**: 10+

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd portfolio-monorepo
   ```

2. **Install pnpm** (if not installed)
   ```bash
   npm install -g pnpm@10
   ```

3. **Install dependencies** (uses the included `pnpm-lock.yaml`)
   ```bash
   pnpm install
   ```

4. **Set up environment variables**
   ```bash
   # Copy example files
   cp apps/web/.env.example apps/web/.env.local
   cp apps/api/.env.example apps/api/.env
   
   # Edit with your values
   # apps/web/.env.local
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   
   # apps/api/.env
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```

### Development

1. **Start both apps concurrently**
   ```bash
   pnpm dev
   ```
   
   This starts:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000

2. **Or start individually**
   ```bash
   # Frontend only
   pnpm --filter web dev
   
   # Backend only
   pnpm --filter api dev
   ```

### Available Scripts

```bash
# Root level (runs across all apps)
pnpm dev          # Start development servers
pnpm build        # Build all apps
pnpm lint         # Lint all code
pnpm typecheck    # Type check all code
pnpm format       # Format all code
pnpm test         # Run tests

# Individual app scripts
pnpm --filter web dev      # Start frontend
pnpm --filter api dev      # Start backend
pnpm --filter web build    # Build frontend
pnpm --filter api build    # Build backend
```

## 📱 Pages

- **Home** (`/`): Hero section, skills overview, and call-to-action
- **About** (`/about`): Personal background, experience, and education
- **Projects** (`/projects`): Portfolio showcase with project details
- **Contact** (`/contact`): Contact form and social links

## 🔌 API Endpoints

### Projects
- `GET /api/projects` - Retrieve all projects

### Contact
- `POST /api/contact` - Submit contact form

## 🧪 Code Quality

### Pre-commit Hooks
The repository includes pre-commit hooks that run automatically:

- **Ruff**: Python linting and formatting
- **MyPy**: Python type checking
- **ESLint**: JavaScript/TypeScript linting
- **Prettier**: Code formatting

### Manual Quality Checks
```bash
# Python (Backend)
pnpm --filter api lint      # Ruff linting
pnpm --filter api format    # Ruff formatting
pnpm --filter api typecheck # MyPy type checking

# TypeScript (Frontend)
pnpm --filter web lint      # ESLint
pnpm --filter web format    # Prettier
pnpm --filter web typecheck # TypeScript compiler
```

### Automated Dependency Updates
Dependabot monitors the npm workspaces in `apps/web` and `packages/ui` as well as Python dependencies in `apps/api`. It runs weekly and opens pull requests that trigger the full CI pipeline to test and lint updates automatically.

## 🚀 Deployment

### Frontend (Vercel)
1. Connect your GitHub repository to Vercel
2. Set environment variables:
   - `NEXT_PUBLIC_API_BASE_URL`: Your backend API URL
3. Deploy automatically on push to main branch

### Backend (Railway/Render/Heroku)
1. Set environment variables for production
2. Update CORS origins in `apps/api/app/core/config.py`
3. Deploy using your preferred platform

## 🔧 Customization

### Personal Information
- Update personal details in `apps/web/src/app/page.tsx`
- Modify experience in `apps/web/src/app/about/page.tsx`
- Add your projects to `apps/api/data/projects.json`
- Update social links in `apps/web/src/app/contact/page.tsx`

### Styling
- Modify Tailwind classes in component files
- Update color scheme in `tailwind.config.js`
- Add custom CSS in `apps/web/src/app/globals.css`

### Backend
- Add new API endpoints in `apps/api/app/routers/`
- Create new models in `apps/api/app/models/`
- Implement database integration when ready

## 📚 Learning Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Turborepo Documentation](https://turbo.build/repo)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run quality checks: `pnpm lint && pnpm typecheck`
5. Commit with conventional commits
6. Push and create a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

If you encounter any issues:

1. Check the [Issues](../../issues) page
2. Review the documentation
3. Create a new issue with detailed information

---

**Built with ❤️ using modern web technologies**
