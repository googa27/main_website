import type { Metadata } from "next";
import ProjectCard from "@/components/ProjectCard";
import { curatedProjects } from "@/lib/content";

export const metadata: Metadata = {
  title: "Projects | Cristobal Cortinez Duhalde",
  description:
    "Curated quantitative engineering, data science, and portfolio projects.",
};

export default function ProjectsPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-10">
      <header className="text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.25em] text-blue-700">
          Static project evidence
        </p>
        <h1 className="mb-4 text-4xl font-bold text-slate-950">Projects</h1>
        <p className="mx-auto max-w-3xl text-lg leading-8 text-slate-700">
          These cards are rendered from local, reviewed content so builds do not
          depend on a live backend or stale third-party API cache.
        </p>
      </header>
      <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
        {curatedProjects.map((project) => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </div>
  );
}
