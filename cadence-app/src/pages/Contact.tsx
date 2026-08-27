import { useState, type FormEvent, type ReactNode } from "react";
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

export default function Contact() {
  const [sent, setSent] = useState(false);

  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const d = new FormData(e.currentTarget);
    const body = [
      `Name: ${d.get("firstName")} ${d.get("lastName")}`,
      `Company: ${d.get("company")}`,
      `Email: ${d.get("email")}`,
      `Phone: ${d.get("phone") || "—"}`,
      `Company size: ${d.get("size") || "—"}`,
      `Preferred meeting time: ${d.get("time") || "—"}`,
      "",
      "What I'd like to discuss:",
      `${d.get("topic")}`,
    ].join("\n");
    window.location.href = `mailto:${CONTACT.email}?subject=${encodeURIComponent(
      `Strategy call — ${d.get("company") || d.get("firstName")}`
    )}&body=${encodeURIComponent(body)}`;
    setSent(true);
  };

  return (
    <>
      <Section className="pt-20 md:pt-28">
        <div className="max-w-3xl space-y-6">
          <Eyebrow>CONTACT</Eyebrow>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tighter text-white leading-[1.02]">
            Let's talk about what's <GradientText>slowing your business down.</GradientText>
          </h1>
          <p className="text-lg text-zinc-400 leading-relaxed">
            Bring us a process, a problem, or simply a question. We'll help you figure out whether automation can
            actually make a difference.
          </p>
        </div>
      </Section>

      <Section className="!pt-0">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          <GlassCard className="lg:col-span-7 p-8 md:p-10">
            {sent ? (
              <div className="space-y-4 py-8 text-center">
                <CheckCircle2 className="mx-auto h-10 w-10 text-[#ffcd75]" />
                <h2 className="text-2xl font-medium tracking-tight text-white">One step left.</h2>
                <p className="mx-auto max-w-md text-zinc-400 leading-relaxed">
                  Your email client should have opened with the details pre-filled — hit send and we'll get back
                  to you with times. If nothing opened, email{" "}
                  <a href={`mailto:${CONTACT.email}`} className="text-white underline underline-offset-4">
                    {CONTACT.email}
                  </a>
                  .
                </p>
              </div>
            ) : (
              <form onSubmit={submit} className="space-y-5">
                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                  <Labeled label="First name" name="firstName">
                    <Field id="firstName" name="firstName" required placeholder="First name" />
                  </Labeled>
                  <Labeled label="Last name" name="lastName">
                    <Field id="lastName" name="lastName" required placeholder="Last name" />
                  </Labeled>
                  <Labeled label="Company" name="company">
                    <Field id="company" name="company" required placeholder="Company" />
                  </Labeled>
                  <Labeled label="Email" name="email">
                    <Field id="email" name="email" type="email" required placeholder="you@company.com" />
                  </Labeled>
                  <Labeled label="Phone" name="phone">
                    <Field id="phone" name="phone" type="tel" placeholder="Optional" />
                  </Labeled>
                  <Labeled label="Estimated company size" name="size">
                    <Select id="size" name="size" defaultValue="">
                      <option value="" disabled>
                        Select…
                      </option>
                      {["1–10", "11–50", "51–200", "201–1000", "1000+"].map((o) => (
                        <option key={o} value={o}>
                          {o}
                        </option>
                      ))}
                    </Select>
                  </Labeled>
                </div>
                <Labeled label="What would you like to discuss?" name="topic">
                  <TextArea id="topic" name="topic" rows={4} required placeholder="A process, a problem, or a question" />
                </Labeled>
                <Labeled label="Preferred meeting time" name="time">
                  <Field id="time" name="time" placeholder="e.g. weekday mornings" />
                </Labeled>
                <button
                  type="submit"
                  className="group inline-flex w-full items-center justify-center gap-2 rounded-full bg-white px-8 py-4 text-sm font-semibold text-zinc-950 transition-all hover:scale-[1.01] hover:bg-zinc-200 active:scale-[0.99]"
                >
                  Book a strategy call
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </button>
                <p className="text-center text-xs text-zinc-500">30 minutes. No commitment.</p>
              </form>
            )}
          </GlassCard>

          <div className="lg:col-span-5">
            <GlassCard className="p-8 lg:sticky lg:top-24">
              <Eyebrow className="mb-5">Direct</Eyebrow>
              <ul className="space-y-4 text-sm">
                <li>
                  <a href={`mailto:${CONTACT.email}`} className="text-zinc-300 transition-colors hover:text-white">
                    {CONTACT.email}
                  </a>
                </li>
                <li>
                  <a href={CONTACT.linkedin} target="_blank" rel="noopener" className="text-zinc-300 transition-colors hover:text-white">
                    LinkedIn
                  </a>
                </li>
              </ul>
              <div className="mt-7 border-t border-white/10 pt-5 text-xs text-zinc-500 leading-relaxed">
                Working in English, Spanish, French, and Arabic.
              </div>
            </GlassCard>
          </div>
        </div>
      </Section>
    </>
  );
}

function Labeled({ label, name, children }: { label: string; name: string; children: ReactNode }) {
  return (
    <div>
      <label htmlFor={name} className="mb-2 block text-sm font-medium text-zinc-300">
        {label}
      </label>
      {children}
    </div>
  );
}
