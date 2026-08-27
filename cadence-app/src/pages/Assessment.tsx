import { useState, type FormEvent } from "react";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import {
  Section,
  Eyebrow,
  GlassCard,
  GradientText,
  Field,
  TextArea,
  Select,
} from "@/components/ui/primitives";
import { CONTACT } from "@/data/site";

// The 10 assessment questions. Answers are compiled into a structured email
// to the founder — swap for a real backend/CRM when one exists.
const QUESTIONS = [
  { name: "company", label: "Company", type: "text", placeholder: "Company name" },
  { name: "industry", label: "Industry", type: "text", placeholder: "e.g. retail, logistics, services" },
  {
    name: "size",
    label: "Company size",
    type: "select",
    options: ["1–10", "11–50", "51–200", "201–1000", "1000+"],
  },
  {
    name: "department",
    label: "Main department concerned",
    type: "select",
    options: ["Customer Service", "Operations", "Marketing", "Finance", "E-commerce", "HR", "Other"],
  },
  {
    name: "challenge",
    label: "Biggest operational challenge",
    type: "textarea",
    placeholder: "Describe the process or problem slowing your team down",
  },
  { name: "people", label: "Number of people involved in this process", type: "text", placeholder: "e.g. 4" },
  { name: "hours", label: "Approximate hours spent per week", type: "text", placeholder: "e.g. 30" },
  { name: "tools", label: "Current tools / software", type: "text", placeholder: "e.g. Excel, Odoo, Gmail, WhatsApp" },
  { name: "tried", label: "What have you already tried?", type: "textarea", placeholder: "Tools, hires, workarounds…" },
  { name: "success", label: "What would success look like?", type: "textarea", placeholder: "e.g. same output with half the manual work" },
] as const;

const RESULT_POINTS = [
  { label: "Your biggest opportunity", detail: "The process where automation would create the most value, and why." },
  { label: "Potential impact", detail: "An order-of-magnitude estimate of yearly value, based on the hours and costs you describe." },
  { label: "Estimated time saved", detail: "Hours per month your team gets back if the automation ships." },
  { label: "Automation complexity", detail: "Low / medium / high — how hard this is to build with your current tools." },
  { label: "Recommended next step", detail: "Usually a strategy call. Sometimes: don't automate this." },
];

export default function Assessment() {
  const [sent, setSent] = useState(false);

  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const body = QUESTIONS.map((q) => `${q.label}:\n${data.get(q.name) || "—"}`).join("\n\n");
    window.location.href = `mailto:${CONTACT.email}?subject=${encodeURIComponent(
      `Automation opportunity assessment — ${data.get("company") || "unnamed company"}`
    )}&body=${encodeURIComponent(body)}`;
    setSent(true);
  };

  return (
    <>
      <Section className="pt-20 md:pt-28">
        <div className="max-w-3xl space-y-6">
          <Eyebrow>OPPORTUNITY ASSESSMENT</Eyebrow>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tighter text-white leading-[1.02]">
            Where could automation create the <GradientText>most value</GradientText> in your business?
          </h1>
          <p className="text-lg text-zinc-400 leading-relaxed">
            Tell us a little about your business and the processes slowing your team down. We'll identify the
            areas most worth exploring.
          </p>
        </div>
      </Section>

      <Section className="!pt-0">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* Form */}
          <GlassCard className="lg:col-span-7 p-8 md:p-10">
            {sent ? (
              <div className="space-y-4 py-8 text-center">
                <CheckCircle2 className="mx-auto h-10 w-10 text-[#ffcd75]" />
                <h2 className="text-2xl font-medium tracking-tight text-white">Almost there.</h2>
                <p className="mx-auto max-w-md text-zinc-400 leading-relaxed">
                  Your email client should have opened with your answers pre-filled — hit send and we'll come
                  back with your assessment. If nothing opened, email us directly at{" "}
                  <a href={`mailto:${CONTACT.email}`} className="text-white underline underline-offset-4">
                    {CONTACT.email}
                  </a>
                  .
                </p>
              </div>
            ) : (
              <form onSubmit={submit} className="space-y-5">
                {QUESTIONS.map((q, i) => (
                  <div key={q.name}>
                    <label htmlFor={q.name} className="mb-2 block text-sm font-medium text-zinc-300">
                      <span className="mr-2 text-zinc-600">{String(i + 1).padStart(2, "0")}</span>
                      {q.label}
                    </label>
                    {q.type === "textarea" ? (
                      <TextArea id={q.name} name={q.name} rows={3} placeholder={q.placeholder} />
                    ) : q.type === "select" ? (
                      <Select id={q.name} name={q.name} defaultValue="">
                        <option value="" disabled>
                          Select…
                        </option>
                        {q.options.map((o) => (
                          <option key={o} value={o}>
                            {o}
                          </option>
                        ))}
                      </Select>
                    ) : (
                      <Field id={q.name} name={q.name} type="text" placeholder={q.placeholder} />
                    )}
                  </div>
                ))}
                <button
                  type="submit"
                  className="group inline-flex w-full items-center justify-center gap-2 rounded-full bg-white px-8 py-4 text-sm font-semibold text-zinc-950 transition-all hover:scale-[1.01] hover:bg-zinc-200 active:scale-[0.99]"
                >
                  Discuss this opportunity with Cadence
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </button>
              </form>
            )}
          </GlassCard>

          {/* What you get back */}
          <div className="lg:col-span-5">
            <GlassCard className="p-8 lg:sticky lg:top-24">
              <Eyebrow className="mb-5">What you get back</Eyebrow>
              <ul className="space-y-5">
                {RESULT_POINTS.map((p) => (
                  <li key={p.label}>
                    <div className="flex items-center gap-2 text-sm font-semibold text-white">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-[#ffcd75]" />
                      {p.label}
                    </div>
                    <p className="mt-1 pl-6 text-xs text-zinc-400 leading-relaxed">{p.detail}</p>
                  </li>
                ))}
              </ul>
              <div className="mt-7 border-t border-white/10 pt-5 text-xs text-zinc-500">
                Free. No commitment. Reviewed personally, not by a lead-scoring bot.
              </div>
            </GlassCard>
          </div>
        </div>
      </Section>
    </>
  );
}
