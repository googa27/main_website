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
  skills: (resume.skills ?? []).map((skill) => ({
    name: skill.name,
    keywords: (skill.keywords ?? [skill.name]).map(normalizeSkillName),
  })) satisfies SkillGroup[],
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
      "Professional background on LinkedIn; source code and project documentation on GitHub.",
  },
} as const;

export const curatedProjects: PortfolioProject[] = [
  {
    id: "finite-element-options",
    title: "Finite Element Options Pricing",
    summary:
      "Scientific Python software for option-pricing PDEs, with convergence checks, analytical price/Greek comparisons and experiments in reduced-order modelling.",
    tags: ["Python", "Finite Elements", "Numerical PDEs", "Model Validation"],
    links: {
      github: "https://github.com/googa27/finite_element_options",
      documentation:
        "https://github.com/googa27/finite_element_options/blob/master/docs/BLACK_SCHOLES_PYMOR_ROM.md",
    },
    evidence:
      "Repository benchmark: 28.6x median online speedup on six synthetic Black-Scholes holdout cases. Offline preparation is excluded; accuracy gates and parameter limits are documented. Experimental integrations are not general production claims.",
    lastVerified: "2026-09-06",
  },
  {
    id: "finite-difference-options",
    title: "Finite Difference Options Pricing",
    summary:
      "Numerical option pricing and sensitivities with Black-Scholes analytical checks, Rannacher smoothing and one-dimensional early-exercise reference cases.",
    tags: ["Python", "NumPy", "SciPy", "Streamlit", "Quant Finance"],
    links: {
      github: "https://github.com/googa27/finite_difference_options",
    },
    evidence:
      "Public repository documents validation cases and the limits of experimental model support.",
    lastVerified: "2026-09-06",
  },
  {
    id: "django-optimization-app",
    title: "Django Optimization App",
    summary:
      "An educational application connecting a continuous linear-programming model to a Django interface, with PuLP and CSV input/output.",
    tags: ["Django", "Python", "Optimization", "Linear Programming"],
    links: {
      github: "https://github.com/googa27/django-optimization-app",
    },
    evidence:
      "Small educational model and implementation example, not an enterprise optimisation platform.",
    lastVerified: "2026-09-06",
  },
  {
    id: "portfolio-site",
    title: "Static-first Portfolio Site",
    summary:
      "A personal portfolio presenting professional experience, selected projects and their documented limitations.",
    tags: ["Next.js", "TypeScript", "Static Export", "Content Governance"],
    links: {
      github: "https://github.com/googa27/main_website",
    },
    evidence:
      "Built with Next.js and TypeScript. Public contact details and project links are curated separately from private career notes.",
    lastVerified: "2026-09-06",
  },
];
