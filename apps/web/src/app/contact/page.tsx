import type { Metadata } from "next";
import { publicResume } from "@/lib/content";

export const metadata: Metadata = {
  title: `Contact | ${publicResume.basics.name}`,
  description:
    "Contact information for collaboration and data science opportunities.",
};

export default function ContactPage() {
  const email = publicResume.basics.email;
  const mailtoHref = email
    ? `mailto:${email}?subject=${encodeURIComponent("Portfolio contact")}`
    : undefined;

  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <header className="text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.25em] text-blue-700">
          Contact
        </p>
        <h1 className="mb-4 text-4xl font-bold text-slate-950">Get in Touch</h1>
        <p className="mx-auto max-w-2xl text-lg leading-8 text-slate-700">
          The static site does not submit messages to a backend by default. Use
          the direct email link for collaboration, data science, ML, or
          quantitative finance opportunities.
        </p>
      </header>
      <section className="rounded-3xl border bg-white p-8 text-center shadow-sm">
        <h2 className="mb-3 text-2xl font-bold text-slate-950">Email</h2>
        {email && mailtoHref ? (
          <a
            href={mailtoHref}
            className="inline-flex rounded-lg bg-blue-700 px-8 py-3 font-semibold text-white transition-colors hover:bg-blue-800"
          >
            {email}
          </a>
        ) : (
          <p className="text-slate-600">
            Contact details are available on request.
          </p>
        )}
        <p className="mt-5 text-sm text-slate-500">
          No message body is stored by this website; your mail client owns the
          submission flow.
        </p>
      </section>
      <section className="rounded-3xl border bg-white p-8 text-center shadow-sm">
        <h2 className="mb-4 text-2xl font-bold text-slate-950">Profiles</h2>
        <div className="flex flex-col justify-center gap-3 sm:flex-row">
          <a
            href={publicResume.social.github}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border px-6 py-3 font-semibold text-slate-700 transition-colors hover:border-blue-700 hover:text-blue-700"
          >
            GitHub
          </a>
          <a
            href={publicResume.social.linkedin}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border px-6 py-3 font-semibold text-slate-700 transition-colors hover:border-blue-700 hover:text-blue-700"
          >
            LinkedIn
          </a>
        </div>
        <p className="mt-5 text-sm text-slate-500">
          {publicResume.social.evidence}
        </p>
      </section>
    </div>
  );
}
