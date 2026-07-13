import type { PortfolioProject } from "@/lib/content";

interface ProjectCardProps {
  project: PortfolioProject;
}

const ProjectCard = ({ project }: ProjectCardProps) => {
  return (
    <article className="flex h-full flex-col rounded-2xl border bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex-1">
        <h3 className="mb-3 text-xl font-semibold text-slate-950">
          {project.title}
        </h3>
        <p className="mb-5 leading-7 text-slate-700">{project.summary}</p>
        <div className="mb-5 flex flex-wrap gap-2">
          {project.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-blue-50 px-3 py-1 text-sm font-medium text-blue-800"
            >
              {tag}
            </span>
          ))}
        </div>
        <p className="mb-5 rounded-lg bg-slate-50 p-3 text-xs leading-5 text-slate-500">
          Evidence: {project.evidence} Last verified: {project.lastVerified}.
        </p>
      </div>
      <div className="flex flex-wrap gap-3 border-t pt-4">
        {project.links.github && (
          <a
            href={project.links.github}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-slate-700 transition-colors hover:text-blue-700"
          >
            Code
          </a>
        )}
        {project.links.live && (
          <a
            href={project.links.live}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-slate-700 transition-colors hover:text-blue-700"
          >
            Live
          </a>
        )}
        {project.links.documentation && (
          <a
            href={project.links.documentation}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-slate-700 transition-colors hover:text-blue-700"
          >
            Docs
          </a>
        )}
      </div>
    </article>
  );
};

export default ProjectCard;
