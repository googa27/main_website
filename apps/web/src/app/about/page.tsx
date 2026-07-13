import type { Metadata } from "next";
import { publicResume } from "@/lib/content";

export const metadata: Metadata = {
  title: `About | ${publicResume.basics.name}`,
  description: "Resume, work history, education, and technical focus areas.",
};

function formatDate(value?: string | null): string {
  return value ?? "Present";
}

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-14">
      <header className="text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.25em] text-blue-700">
          Resume
        </p>
        <h1 className="mb-4 text-4xl font-bold text-slate-950">
          About {publicResume.basics.name}
        </h1>
        <p className="mx-auto max-w-3xl text-lg leading-8 text-slate-700">
          {publicResume.basics.summary}
        </p>
        <p className="mt-4 text-sm text-slate-500">
          {publicResume.basics.location}
        </p>
      </header>

      <section>
        <h2 className="mb-6 text-2xl font-bold text-slate-950">
          Professional Experience
        </h2>
        <div className="space-y-5">
          {publicResume.work.map((job, index) => (
            <article
              key={`${job.organization}-${job.role}-${index}`}
              className="rounded-2xl border bg-white p-6 shadow-sm"
            >
              <div className="flex flex-col justify-between gap-2 md:flex-row md:items-start">
                <div>
                  <h3 className="text-xl font-semibold text-slate-950">
                    {job.role}
                  </h3>
                  <p className="font-medium text-blue-700">
                    {job.organization}
                  </p>
                  {job.location && (
                    <p className="text-sm text-slate-500">{job.location}</p>
                  )}
                </div>
                <p className="text-sm font-medium text-slate-500">
                  {formatDate(job.startDate)} – {formatDate(job.endDate)}
                </p>
              </div>
              {job.summary && (
                <p className="mt-4 leading-7 text-slate-700">{job.summary}</p>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="grid gap-8 md:grid-cols-2">
        <div>
          <h2 className="mb-6 text-2xl font-bold text-slate-950">Education</h2>
          <div className="space-y-4">
            {publicResume.education.map((item, index) => (
              <article
                key={`${item.institution}-${index}`}
                className="rounded-2xl border bg-white p-5 shadow-sm"
              >
                <h3 className="font-semibold text-slate-950">
                  {item.institution}
                </h3>
                <p className="text-sm text-slate-700">
                  {[item.credential, item.area].filter(Boolean).join(" — ")}
                </p>
                <p className="mt-2 text-sm text-slate-500">
                  {formatDate(item.startDate)} – {formatDate(item.endDate)}
                </p>
              </article>
            ))}
          </div>
        </div>
        <div>
          <h2 className="mb-6 text-2xl font-bold text-slate-950">
            Skills and Languages
          </h2>
          <div className="space-y-4">
            <article className="rounded-2xl border bg-white p-5 shadow-sm">
              <h3 className="mb-3 font-semibold text-slate-950">Awards</h3>
              <ul className="space-y-2 text-sm text-slate-700">
                {publicResume.awards.map((award) => (
                  <li key={award.title}>
                    <span className="font-medium">{award.title}</span>
                    {award.date ? ` — ${formatDate(award.date)}` : ""}
                  </li>
                ))}
              </ul>
            </article>
            <article className="rounded-2xl border bg-white p-5 shadow-sm">
              <h3 className="mb-3 font-semibold text-slate-950">
                Certificates
              </h3>
              <ul className="space-y-2 text-sm text-slate-700">
                {publicResume.certificates.map((certificate) => (
                  <li key={certificate.title}>
                    {certificate.url ? (
                      <a
                        href={certificate.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-blue-700 hover:text-blue-900"
                      >
                        {certificate.title}
                      </a>
                    ) : (
                      <span className="font-medium">{certificate.title}</span>
                    )}
                    {certificate.issuer ? ` — ${certificate.issuer}` : ""}
                    {certificate.startDate
                      ? ` (${formatDate(certificate.startDate)}${certificate.endDate ? `–${formatDate(certificate.endDate)}` : ""})`
                      : ""}
                  </li>
                ))}
              </ul>
            </article>
            <article className="rounded-2xl border bg-white p-5 shadow-sm">
              <h3 className="mb-3 font-semibold text-slate-950">Volunteer</h3>
              <ul className="space-y-2 text-sm text-slate-700">
                {publicResume.volunteer.map((item) => (
                  <li key={item.organization}>
                    <span className="font-medium">{item.organization}</span>
                    {item.role ? ` — ${item.role}` : ""}
                  </li>
                ))}
              </ul>
            </article>
            {publicResume.skills.map((group) => (
              <article
                key={group.name}
                className="rounded-2xl border bg-white p-5 shadow-sm"
              >
                <h3 className="mb-3 font-semibold text-slate-950">
                  {group.name}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {group.keywords.map((skill, index) => (
                    <span
                      key={`${group.name}-${skill}-${index}`}
                      className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </article>
            ))}
            <article className="rounded-2xl border bg-white p-5 shadow-sm">
              <h3 className="mb-3 font-semibold text-slate-950">Languages</h3>
              <ul className="space-y-2 text-sm text-slate-700">
                {publicResume.languages.map((language) => (
                  <li key={language.language}>
                    <span className="font-medium">{language.language}</span>
                    {language.fluency ? ` — ${language.fluency}` : ""}
                  </li>
                ))}
              </ul>
            </article>
          </div>
        </div>
      </section>
    </div>
  );
}
