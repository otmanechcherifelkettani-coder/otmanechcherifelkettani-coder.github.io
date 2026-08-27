import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { CONTACT } from "@/data/site";
import { SOLUTIONS } from "@/data/solutions";
import { Field } from "@/components/ui/primitives";

const RESOURCE_LINKS = [
  { label: "Guides", to: "/resources" },
  { label: "Case Studies", to: "/case-studies" },
  { label: "Insights", to: "/resources" },
  { label: "Tools", to: "/resources" },
];

const COMPANY_LINKS = [
  { label: "About", to: "/about" },
  { label: "Our Approach", to: "/approach" },
  { label: "Contact", to: "/contact" },
];

export default function Footer() {
  // No backend yet: subscribing opens a pre-filled email to the founder.
  const subscribe = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const email = new FormData(e.currentTarget).get("email");
    window.location.href = `mailto:${CONTACT.email}?subject=${encodeURIComponent("Newsletter subscription")}&body=${encodeURIComponent(`Please add ${email} to the Cadence newsletter.`)}`;
  };

  return (
    <footer className="border-t border-white/5 bg-zinc-950">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">
          <div className="lg:col-span-4 space-y-4">
            <div className="text-lg font-semibold tracking-tight text-white">Cadence</div>
            <p className="text-sm text-zinc-400 leading-relaxed max-w-xs">
              Cadence builds automation that pays for itself. AI and automation systems designed around real
              business outcomes.
            </p>
            <form onSubmit={subscribe} className="pt-2 space-y-2 max-w-xs">
              <div className="text-xs font-medium text-zinc-300">Useful ideas about automation. No spam.</div>
              <div className="flex gap-2">
                <Field type="email" name="email" required placeholder="Your email" className="py-2.5" />
                <button
                  type="submit"
                  className="shrink-0 rounded-2xl bg-white px-4 py-2.5 text-xs font-semibold text-zinc-950 transition-colors hover:bg-zinc-200"
                >
                  Subscribe
                </button>
              </div>
            </form>
          </div>

          <FooterColumn title="Solutions" links={SOLUTIONS.map((s) => ({ label: s.name, to: `/solutions/${s.slug}` }))} />
          <FooterColumn title="Resources" links={RESOURCE_LINKS} />
          <FooterColumn title="Company" links={COMPANY_LINKS} />

          <div className="lg:col-span-2">
            <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-zinc-500">Contact</div>
            <ul className="space-y-2.5 text-sm">
              <li><Link to="/contact" className="text-zinc-400 transition-colors hover:text-white">Book a call</Link></li>
              <li><a href={`mailto:${CONTACT.email}`} className="text-zinc-400 transition-colors hover:text-white">Email</a></li>
              <li><a href={CONTACT.linkedin} target="_blank" rel="noopener" className="text-zinc-400 transition-colors hover:text-white">LinkedIn</a></li>
            </ul>
          </div>
        </div>

        <div className="mt-14 flex flex-col gap-2 border-t border-white/5 pt-6 text-xs text-zinc-600 sm:flex-row sm:justify-between">
          <span>© {new Date().getFullYear()} Cadence. All rights reserved.</span>
          <span>Built in Morocco. Working worldwide.</span>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({ title, links }: { title: string; links: { label: string; to: string }[] }) {
  return (
    <div className="lg:col-span-2">
      <div className="mb-4 text-xs font-semibold uppercase tracking-wider text-zinc-500">{title}</div>
      <ul className="space-y-2.5 text-sm">
        {links.map((l) => (
          <li key={l.label}>
            <Link to={l.to} className="text-zinc-400 transition-colors hover:text-white">
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
