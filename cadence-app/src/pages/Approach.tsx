import { Search, PenTool, Wrench, TrendingUp, Ban } from "lucide-react";
import {
  Section,
  SectionHeading,
  Eyebrow,
  GlassCard,
  GradientText,
  ButtonLink,
  IconBadge,
} from "@/components/ui/primitives";

const STAGES = [
  {
    icon: Search,
    index: "01",
    name: "Discover",
    copy: "We sit with the people doing the work, map the processes end to end, and price the waste: hours spent, errors made, opportunities missed. Then we rank every candidate by potential return and effort — not by how interesting the technology would be.",
    deliverable: "Automation Opportunity Map",
  },
  {
    icon: PenTool,
    index: "02",
    name: "Design",
    copy: "We redesign the process before automating it — often the process itself is the problem. Then we define the solution: what gets automated, what stays human, which tools it connects to, and exactly how success will be measured.",
    deliverable: "Automation Blueprint",
  },
  {
    icon: Wrench,
    index: "03",
    name: "Build",
    copy: "We develop the system, integrate it with your existing tools, and test it against real cases with your team. Deployment is gradual and measured — no big-bang launches on processes your business depends on.",
    deliverable: "Working Automation System",
  },
  {
    icon: TrendingUp,
    index: "04",
    name: "Optimize",
    copy: "We track the KPIs defined in design against the baseline, tune the system where reality differs from plan, and identify the next opportunities the first project uncovered.",
    deliverable: "Impact Dashboard + Optimization Plan",
  },
];

export default function Approach() {
  return (
    <>
      <Section className="pt-20 md:pt-28">
        <div className="max-w-3xl space-y-6">
          <Eyebrow>OUR APPROACH</Eyebrow>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tighter text-white leading-[1.02]">
            From business problem to <GradientText>measurable impact.</GradientText>
          </h1>
          <p className="text-lg text-zinc-400 leading-relaxed">
            Four stages, each with a concrete deliverable. You know what you're getting at every step — and you
            can stop at any of them with something useful in hand.
          </p>
        </div>
      </Section>

      <Section className="!pt-0">
        <div className="space-y-6">
          {STAGES.map((s) => (
            <GlassCard key={s.index} className="p-8 md:p-10">
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
                <div className="flex items-center gap-4 lg:col-span-3">
                  <IconBadge>
                    <s.icon className="h-6 w-6 text-white" />
                  </IconBadge>
                  <div>
                    <span className="text-sm font-semibold text-zinc-600">{s.index}</span>
                    <div className="text-xl font-semibold text-white">{s.name}</div>
                  </div>
                </div>
                <p className="text-zinc-400 leading-relaxed lg:col-span-6">{s.copy}</p>
                <div className="lg:col-span-3">
                  <Eyebrow className="mb-2 text-[10px]">Deliverable</Eyebrow>
                  <div className="rounded-2xl border border-[#ffcd75]/20 bg-[#ffcd75]/5 px-4 py-3 text-sm font-semibold text-[#ffcd75]">
                    {s.deliverable}
                  </div>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      </Section>

      {/* What NOT to automate */}
      <Section className="!pt-0">
        <GlassCard className="p-8 md:p-12">
          <div className="absolute top-0 right-0 -mr-24 -mt-24 h-72 w-72 rounded-full bg-white/5 blur-3xl pointer-events-none" />
          <div className="relative z-10 max-w-2xl">
            <IconBadge className="mb-5">
              <Ban className="h-6 w-6 text-white" />
            </IconBadge>
            <h2 className="text-2xl sm:text-3xl font-medium tracking-tight text-white">
              We also tell you what <GradientText>NOT</GradientText> to automate.
            </h2>
            <p className="mt-4 text-zinc-400 leading-relaxed">
              Automation isn't always the answer. Sometimes the best solution is to simplify the process, change
              the workflow, or leave it alone. If the numbers don't support building something, we'll say so —
              that recommendation is part of the deliverable, not a failed engagement.
            </p>
          </div>
        </GlassCard>
      </Section>

      <Section className="!pt-0">
        <SectionHeading
          center
          title="Start with Discover."
          intro="One conversation is enough to tell whether there's a discovery worth running."
        />
        <div className="flex justify-center">
          <ButtonLink to="/contact">Book a strategy call</ButtonLink>
        </div>
      </Section>
    </>
  );
}
