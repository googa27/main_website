import Link from "next/link";
import { curatedProjects, publicResume } from "@/lib/content";

export default function HomePage() {
  const featuredProjects = curatedProjects.slice(0, 3);
  const skillPreview = publicResume.skills
    .flatMap((group) => group.keywords)
    .slice(0, 8);

  return (
    <div className="space-y-16">
      <section className="rounded-3xl bg-gradient-to-br from-slate-950 via-blue-950 to-slate-900 px-6 py-20 text-center text-white shadow-xl">
        <p className="mb-4 text-sm font-semibold uppercase tracking-[0.3em] text-blue-200">
          Data Science • AI • Applied Math
        </p>
        <h1 className="mx-auto mb-6 max-w-4xl text-5xl font-bold leading-tight md:text-6xl">
          {publicResume.basics.name}
        </h1>
        <p className="mx-auto mb-8 max-w-3xl text-xl text-blue-100">
          {publicResume.basics.label}
        </p>
        <p className="mx-auto mb-10 max-w-4xl text-base leading-8 text-slate-200 md:text-lg">
          {publicResume.basics.summary}
        </p>
        <div className="flex flex-col justify-center gap-4 sm:flex-row">
          <Link
            href="/projects"
            className="rounded-lg bg-white px-8 py-3 font-semibold text-slate-950 transition-colors hover:bg-blue-50"
          >
            View Projects
          </Link>
          <Link
            href="/contact"
            className="rounded-lg border border-white/60 px-8 py-3 font-semibold text-white transition-colors hover:bg-white/10"
          >
            Get in Touch
          </Link>
        </div>
      </section>

      <section>
        <div className="mb-10 text-center">
          <h2 className="text-3xl font-bold text-slate-950">Technical Focus</h2>
          <p className="mt-3 text-slate-600">
            A static-first view of the curated React-folio resume content.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {skillPreview.map((skill, index) => (
            <div
              key={`${skill}-${index}`}
              className="rounded-2xl border bg-white p-5 text-center shadow-sm"
            >
              <div className="font-semibold text-slate-900">{skill}</div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="mb-10 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <h2 className="text-3xl font-bold text-slate-950">
              Featured Projects
            </h2>
            <p className="mt-3 max-w-2xl text-slate-600">
              Curated project evidence is now rendered from checked-in content
              before any optional backend integration.
            </p>
          </div>
          <Link
            href="/projects"
            className="font-semibold text-blue-700 hover:text-blue-900"
          >
            See all projects →
          </Link>
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          {featuredProjects.map((project) => (
            <article
              key={project.id}
              className="rounded-2xl border bg-white p-6 shadow-sm"
            >
              <h3 className="mb-3 text-xl font-bold text-slate-950">
                {project.title}
              </h3>
              <p className="mb-5 text-sm leading-6 text-slate-600">
                {project.summary}
              </p>
              <div className="flex flex-wrap gap-2">
                {project.tags.slice(0, 4).map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-800"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-3xl bg-blue-50 p-10 text-center">
        <h2 className="mb-4 text-3xl font-bold text-slate-950">
          Static-first by default
        </h2>
        <p className="mx-auto mb-8 max-w-2xl text-slate-700">
          The public site now builds from local typed content. Backend APIs
          remain available only where a dynamic feature is explicitly justified
          and tested.
        </p>
        <Link
          href="/about"
          className="inline-flex rounded-lg bg-blue-700 px-8 py-3 font-semibold text-white transition-colors hover:bg-blue-800"
        >
          Read the resume
        </Link>
      </section>
    </div>
  );
}
