import { useMemo, useState } from "react";
import {
  Section,
  Eyebrow,
  GlassCard,
  GradientText,
  ButtonLink,
  TextLink,
} from "@/components/ui/primitives";
import { CASE_STUDIES } from "@/data/caseStudies";
import { cn } from "@/lib/utils";

export default function CaseStudies() {
  const departments = useMemo(() => ["All", ...new Set(CASE_STUDIES.map((c) => c.department))], []);
  const industries = useMemo(() => ["All", ...new Set(CASE_STUDIES.map((c) => c.industry))], []);
  const [department, setDepartment] = useState("All");
  const [industry, setIndustry] = useState("All");

  const filtered = CASE_STUDIES.filter(
    (c) => (department === "All" || c.department === department) && (industry === "All" || c.industry === industry)
  );

  return (
    <>
      <Section className="pt-20 md:pt-28">
        <div className="max-w-3xl space-y-6">
          <Eyebrow>CASE STUDIES</Eyebrow>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tighter text-white leading-[1.02]">
            The proof is <GradientText>in the numbers.</GradientText>
          </h1>
          <p className="text-lg text-zinc-400 leading-relaxed">
            We measure automation by the value it creates — not by how sophisticated the technology sounds.
            Clients stay anonymous; the numbers don't.
          </p>
        </div>
      </Section>

      <Section className="!pt-0">
        <div className="mb-8 flex flex-wrap gap-x-8 gap-y-4">
          <FilterRow label="Department" options={departments} value={department} onChange={setDepartment} />
          <FilterRow label="Industry" options={industries} value={industry} onChange={setIndustry} />
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {filtered.map((c) => (
            <GlassCard key={c.slug} className="flex flex-col">
              <Eyebrow className="mb-3 text-[10px]">{c.tag}</Eyebrow>
              <div className="text-xl font-semibold text-white leading-snug">{c.title}</div>
              <p className="mt-2 text-sm text-zinc-400 leading-relaxed">{c.challenge}</p>
              <div className="mt-5 flex flex-wrap gap-x-8 gap-y-3">
                {c.results.slice(0, 3).map((r) => (
                  <div key={r.label}>
                    <div className="text-lg font-bold tracking-tight text-white">{r.value}</div>
                    <div className="text-xs text-zinc-500">{r.label}</div>
                  </div>
                ))}
              </div>
              <TextLink to={`/case-studies/${c.slug}`} className="mt-6">
                Read the case study
              </TextLink>
            </GlassCard>
          ))}
        </div>
        {filtered.length === 0 && (
          <p className="text-zinc-500">No case studies match those filters yet.</p>
        )}
      </Section>

      <Section className="!pt-0 text-center">
        <h2 className="text-3xl sm:text-4xl font-medium tracking-tighter text-white">Your process could be next.</h2>
        <div className="mt-8 flex justify-center">
          <ButtonLink to="/contact">Book a strategy call</ButtonLink>
        </div>
      </Section>
    </>
  );
}

function FilterRow({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="mr-1 text-xs font-semibold uppercase tracking-wider text-zinc-500">{label}</span>
      {options.map((o) => (
        <button
          key={o}
          onClick={() => onChange(o)}
          className={cn(
            "rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors",
            value === o
              ? "border-white/30 bg-white/10 text-white"
              : "border-white/10 bg-white/5 text-zinc-400 hover:text-white"
          )}
        >
          {o}
        </button>
      ))}
    </div>
  );
}
