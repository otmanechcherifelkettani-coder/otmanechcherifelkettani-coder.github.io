import {
  Section,
  SectionHeading,
  Eyebrow,
  GlassCard,
  GradientText,
  ButtonLink,
} from "@/components/ui/primitives";
import { CONTACT } from "@/data/site";

const THINKING = [
  { title: "Start with the problem", copy: "Technology comes second." },
  { title: "Focus on leverage", copy: "Automate work where it creates meaningful economic value." },
  { title: "Keep humans where they matter", copy: "Not everything should be automated." },
  { title: "Build for reality", copy: "Systems need to work with the tools, constraints, and people already inside the business." },
  { title: "Prove the value", copy: "If we can't explain the return, we shouldn't build it." },
];

const CHAPTERS = [
  {
    period: "2017 – 2020",
    role: "Strategy consultant — international consultancy, Madrid",
    copy: "Bottom-up financial and costing models for four major telecom operators; market evaluation informing 5G strategy across two GCC countries. Where the analytical rigor comes from.",
  },
  {
    period: "2020 – 2021",
    role: "Product & operations manager — consumer fintech, Madrid",
    copy: "Launched a point-of-sale lending product end to end (+10% revenue), cut acquisition cost 5% through data strategy, grew cross-selling 15% in four months. Where the operator instinct comes from.",
  },
  {
    period: "2021 – now",
    role: "Global product & operations lead — food delivery platform, Amsterdam",
    copy: "Led post-order support automation from rule-based workflows to LLM-driven systems: ~$15M/yr in cost savings, ~$20M/yr in incremental bookings, +20% CSAT. Hands-on across system design, prompting, evals, and experimentation. Where the builder credibility comes from.",
  },
];

export default function About() {
  return (
    <>
      <Section className="pt-20 md:pt-28">
        <div className="max-w-3xl space-y-6">
          <Eyebrow>ABOUT</Eyebrow>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tighter text-white leading-[1.02]">
            Automation should create <GradientText>value, not complexity.</GradientText>
          </h1>
          <p className="text-lg text-zinc-400 leading-relaxed">
            Cadence was built around a simple idea: businesses shouldn't invest in technology because it's new.
            They should invest because it makes the business better.
          </p>
        </div>
      </Section>

      {/* What we do */}
      <Section className="!pt-0">
        <GlassCard className="p-8 md:p-12">
          <Eyebrow className="mb-4">What we do</Eyebrow>
          <p className="max-w-2xl text-xl text-zinc-300 leading-relaxed">
            We combine business thinking, automation engineering, and AI to solve operational problems.
          </p>
        </GlassCard>
      </Section>

      {/* How we think */}
      <Section className="!pt-0">
        <SectionHeading eyebrow="HOW WE THINK" title="Five rules we don't break." />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {THINKING.map((t, i) => (
            <GlassCard key={t.title} className="p-6">
              <span className="text-sm font-semibold text-zinc-600">0{i + 1}</span>
              <div className="mt-2 text-lg font-semibold text-white">{t.title}</div>
              <p className="mt-1 text-sm text-zinc-400 leading-relaxed">{t.copy}</p>
            </GlassCard>
          ))}
        </div>
      </Section>

      {/* Founder */}
      <Section className="!pt-0">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <SectionHeading
              eyebrow="FOUNDER"
              title="Otman Kettani"
              intro={
                <>
                  Strategy consultant turned operator turned builder. Eight-plus years across product, operations,
                  and strategy in tech and fintech — most recently leading global customer-support automation
                  through the LLM shift at one of the world's largest delivery platforms.
                  <br />
                  <br />
                  <span className="text-white">
                    The through-line: I don't stop at the recommendation. I build the system, measure it against a
                    baseline, and hand it over working.
                  </span>
                </>
              }
            />
            <div className="flex flex-wrap gap-4">
              <ButtonLink to={`mailto:${CONTACT.email}`}>Email me</ButtonLink>
              <ButtonLink to={CONTACT.linkedin} variant="ghost">
                LinkedIn
              </ButtonLink>
            </div>
          </div>
          <div className="lg:col-span-7 space-y-4">
            {CHAPTERS.map((c) => (
              <GlassCard key={c.period} className="p-6">
                <Eyebrow className="mb-2 text-[10px]">{c.period}</Eyebrow>
                <div className="font-semibold text-white">{c.role}</div>
                <p className="mt-1.5 text-sm text-zinc-400 leading-relaxed">{c.copy}</p>
              </GlassCard>
            ))}
          </div>
        </div>
      </Section>

      {/* Why Cadence exists / market */}
      <Section className="!pt-0">
        <GlassCard className="p-8 md:p-12">
          <div className="absolute top-0 right-0 -mr-24 -mt-24 h-72 w-72 rounded-full bg-white/5 blur-3xl pointer-events-none" />
          <div className="relative z-10 max-w-2xl space-y-4">
            <Eyebrow>Why Cadence</Eyebrow>
            <h2 className="text-2xl sm:text-3xl font-medium tracking-tight text-white">
              Built in Morocco. Designed for ambitious businesses.
            </h2>
            <p className="text-zinc-400 leading-relaxed">
              Inside large companies, I watched automation create tens of millions in measured value — and watched
              how rarely that capability reaches everyone else. Most businesses can't hire this skill set
              in-house, and most agencies sell them technology instead of outcomes.
            </p>
            <p className="text-zinc-400 leading-relaxed">
              Cadence focuses on Moroccan companies first: ambitious businesses where the automation opportunity
              is large and largely untouched. The same systems, rigor, and measurement — available without
              building an internal team. And we work with international clients too; the engagements run in
              English, Spanish, French, and Arabic.
            </p>
          </div>
        </GlassCard>
      </Section>

      <Section className="!pt-0 text-center">
        <h2 className="text-3xl sm:text-4xl font-medium tracking-tighter text-white">Let's talk.</h2>
        <div className="mt-8 flex justify-center">
          <ButtonLink to="/contact">Book a strategy call</ButtonLink>
        </div>
      </Section>
    </>
  );
}
