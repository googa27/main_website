import type { Metadata } from "next";
import AboutPage from "../../about/page";

export const metadata: Metadata = {
  title: "Public CV preview",
  description:
    "The curated public CV, with optional JSON Resume and PDF downloads.",
};

function downloadBase(): string | null {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!configured) return null;
  const url = new URL(configured);
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  ) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL must be a public HTTP(S) API base URL",
    );
  }
  return url.href.replace(/\/$/, "");
}

export default function CVPreviewPage() {
  const base = downloadBase();
  return (
    <div className="space-y-10">
      <aside className="rounded-2xl border bg-white p-5 text-center print:hidden">
        <p className="text-sm text-slate-600">
          Preview the curated public CV. You can also print this page from your
          browser.
        </p>
        {base ? (
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            <a
              className="rounded-lg bg-blue-700 px-4 py-2 text-white hover:bg-blue-800"
              href={`${base}/api/cv/pdf`}
            >
              Download PDF
            </a>
            <a
              className="rounded-lg border px-4 py-2 text-slate-800 hover:bg-slate-50"
              href={`${base}/api/cv/resume/download`}
            >
              Download JSON Resume
            </a>
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-500">
            File downloads are available when the CV export service is
            connected.
          </p>
        )}
      </aside>
      <AboutPage />
    </div>
  );
}
