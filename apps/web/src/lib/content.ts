import sourceResume from "@/data/react-folio-resume.json";

export interface ResumeBasics {
  name: string;
  label: string;
  summary: string;
  location: string;
  email?: string;
}

export interface TimelineItem {
  organization: string;
  role: string;
  location?: string;
  summary?: string;
  startDate?: string;
  endDate?: string | null;
}

export interface EducationItem {
  institution: string;
  credential?: string | null;
  area?: string | null;
  startDate?: string;
  endDate?: string;
}

export interface RecognitionItem {
  title: string;
  issuer?: string | null;
  date?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  url?: string | null;
  summary?: string | null;
}

export interface VolunteerItem {
  organization: string;
  role?: string | null;
  summary?: string | null;
}

export interface SkillGroup {
  name: string;
  keywords: string[];
}

export interface PortfolioProject {
  id: string;
  title: string;
  summary: string;
  tags: string[];
  links: {
    github?: string;
    live?: string;
    documentation?: string;
  };
  evidence: string;
  lastVerified: string;
}

interface SourceResume {
  basics: {
    name: string;
    label?: string;
    summary?: string;
    email?: string;
    phone?: string;
    location?: { general?: string; full?: string; raw?: string };
  };
  work?: Array<{
    name?: string;
    company?: string;
    position: string;
    location?: string;
    summary?: string;
    startDate?: string;
    endDate?: string | null;
  }>;
  education?: Array<{
    institution: string;
    studyType?: string | null;
    area?: string | null;
    startDate?: string;
    endDate?: string;
  }>;
  skills?: Array<{ name: string; keywords?: string[] }>;
  languages?: Array<{ language: string; fluency?: string }>;
  awards?: Array<{
    title: string;
    date?: string | null;
    summary?: string | null;
  }>;
  volunteer?: Array<{
    organization: string;
    position?: string | null;
    summary?: string | null;
  }>;
  certificates?: Array<{
    name: string;
    issuer?: string | null;
    url?: string | null;
    startDate?: string | null;
    endDate?: string | null;
  }>;
}

const resume = sourceResume as SourceResume;
function normalizeSkillName(name: string): string {
  const aliases: Record<string, string> = {
    pytorch: "PyTorch",
    "Python (Programming Language)": "Python",
    "Pandas (Software)": "Pandas",
    "React.js": "React",
    "Scikit-Learn": "scikit-learn",
  };
  return aliases[name] ?? name;
}

export const publicResume = {
  basics: {
    name: resume.basics.name,
    label:
      resume.basics.label ??
      "Data Science, AI, Applied Math, and Quantitative Finance",
    summary: resume.basics.summary ?? "",
    location:
      resume.basics.location?.general ??
      resume.basics.location?.full ??
      resume.basics.location?.raw ??
      "Santiago, Chile",
    email: resume.basics.email,
  } satisfies ResumeBasics,
  work: (resume.work ?? []).map((job) => ({
    organization: job.company ?? job.name ?? "Organization",
    role: job.position,
    location: job.location,
    summary: job.summary,
    startDate: job.startDate,
    endDate: job.endDate,
  })) satisfies TimelineItem[],
  education: (resume.education ?? []).slice(0, 4).map((item) => ({
    institution: item.institution,
    credential: item.studyType,
    area: item.area,
    startDate: item.startDate,
    endDate: item.endDate,
  })) satisfies EducationItem[],
  awards: (resume.awards ?? []).map((item) => ({
    title: item.title,
    date: item.date,
    summary: item.summary,
  })) satisfies RecognitionItem[],
  certificates: (resume.certificates ?? []).map((item) => ({
    title: item.name,
    issuer: item.issuer,
    url: item.url,
    startDate: item.startDate,
    endDate: item.endDate,
  })) satisfies RecognitionItem[],
  volunteer: (resume.volunteer ?? []).map((item) => ({
    organization: item.organization,
    role: item.position,
    summary: item.summary,
  })) satisfies VolunteerItem[],
  languages: resume.languages ?? [],
  skills: [
    {
      name: "Migrated React-folio skills",
      keywords: (resume.skills ?? [])
        .map((skill) => skill.name)
        .map(normalizeSkillName),
    },
    {
      name: "Delivery stack",
      keywords: [
        "Python",
        "TypeScript",
        "React",
        "Next.js",
        "Django",
        "REST APIs",
        "PostgreSQL",
        "MLflow",
      ],
    },
  ] satisfies SkillGroup[],
  source: {
    repository: "googa27/cristobal-react-folio",
    path: "src/data/resume.json",
    migration:
      "one-way consolidation into main_website; source repository is retained",
    redactions: [
      "basics.phone is excluded from the checked-in main_website copy and public renderer",
    ],
  },
  social: {
    github: "https://github.com/googa27",
    linkedin: "https://www.linkedin.com/in/cristobal-cortinez-duhalde",
    evidence:
      "React-folio normalizer supplied these profile defaults when basics.profiles was empty.",
  },
} as const;

export const curatedProjects: PortfolioProject[] = [
  {
    id: "finite-difference-options",
    title: "Finite Difference Options Pricing",
    summary:
      "PDE-based derivatives pricing work using finite-difference schemes, convergence checks, Greeks, and risk analysis dashboards.",
    tags: ["Python", "NumPy", "SciPy", "Streamlit", "Quant Finance"],
    links: {
      github: "https://github.com/googa27/finite-difference-options",
      live: "https://finite-diff-options.streamlit.app",
    },
    evidence:
      "Consolidated from main_website FastAPI showcase service and React-folio portfolio content inventory.",
    lastVerified: "2026-07-13",
  },
  {
    id: "django-optimization-app",
    title: "Django Optimization App",
    summary:
      "Web optimization solver for linear-programming style workflows, combining mathematical modeling with a practical Django interface.",
    tags: ["Django", "Python", "Optimization", "Linear Programming"],
    links: {
      github: "https://github.com/googa27/django-optimization-app",
    },
    evidence: "Consolidated from main_website project showcase service.",
    lastVerified: "2026-07-13",
  },
  {
    id: "portfolio-site",
    title: "Static-first Portfolio Site",
    summary:
      "This Next.js portfolio now consumes checked-in, redacted React-folio resume content first; the FastAPI backend remains optional for demonstrably dynamic needs.",
    tags: ["Next.js", "TypeScript", "Static Export", "Content Governance"],
    links: {
      github: "https://github.com/googa27/main_website",
    },
    evidence:
      "Project #24 consolidation: React-folio resume JSON copied into apps/web/src/data and rendered by static pages.",
    lastVerified: "2026-07-13",
  },
];
