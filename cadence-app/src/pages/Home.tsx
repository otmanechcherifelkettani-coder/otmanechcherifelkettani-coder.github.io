import { Link } from "react-router-dom";
import {
  Clock,
  Puzzle,
  ShieldCheck,
  Repeat,
  Unplug,
  CircleDollarSign,
  Search,
  PenTool,
  Wrench,
  TrendingUp,
  BookOpen,
  FileText,
  Lightbulb,
  Calculator,
  CheckCircle2,
} from "lucide-react";
import HeroSection from "@/components/ui/glassmorphism-trust-hero";
import {
  Section,
  SectionHeading,
  Eyebrow,
  GlassCard,
  GradientText,
  ButtonLink,
  TextLink,
  IconBadge,
} from "@/components/ui/primitives";
import { SOLUTIONS } from "@/data/solutions";
import { CASE_STUDIES } from "@/data/caseStudies";
import { RESOURCES } from "@/data/resources";
import { IMPACT_METRICS, CLIENTS, TESTIMONIALS } from "@/data/site";

const PROOF_POINTS = [
  {
    icon: Clock,
    title: "ROI in 4–12 weeks",
    copy: "Measurable impact, not another technology project.",
  },
  {
    icon: Puzzle,
    title: "Built for your business",
    copy: "Solutions designed around your processes, tools, and goals.",
  },
  {
    icon: ShieldCheck,
    title: "Secure & reliable",
    copy: "Enterprise-grade systems built to work in the real world.",
  },
];

const PROBLEMS = [
  {
    icon: Repeat,
    title: "Too much manual work",
    copy: "Repetitive tasks keep talented people busy with work that should happen automatically.",
  },
  {
    icon: Unplug,
    title: "Disconnected processes",
    copy: "Information moves between people, spreadsheets, emails, and systems with too much friction.",
  },
  {
    icon: CircleDollarSign,
    title: "Technology without a business case",
    copy: "Companies invest in tools without knowing whether they will actually create meaningful returns.",
  },
];

const APPROACH_STEPS = [
  {
    icon: Search,
    index: "01",
    name: "Discover",
    title: "Find the opportunity.",
    copy: "We map your processes, understand where time and money are being lost, and identify the opportunities with the highest potential return.",
  },
  {
    icon: PenTool,
    index: "02",
    name: "Design",
    title: "Design the solution.",
    copy: "We define what should be automated, what should remain human, and how the system should work within your existing tools.",
  },
  {
    icon: Wrench,
    index: "03",
    name: "Build",
    title: "Build and integrate.",
    copy: "We develop, integrate, test, and deploy the solution with your team.",
  },
  {
    icon: TrendingUp,
    index: "04",
    name: "Optimize",
    title: "Measure and improve.",
    copy: "We track the impact, improve the system, and identify the next opportunities for automation.",
  },
];

const PRINCIPLES = [
  {
    title: "Business first",
    copy: "We focus on the process, the cost, and the outcome before deciding which technology belongs underneath.",
  },
  {
    title: "Build, don't just advise",
    copy: "You don't receive a 60-page strategy deck and a recommendation to “implement AI.” We design and build the system.",
  },
  {
    title: "Measure the return",
    copy: "Every project has a clear definition of value, measurable KPIs, and a path to proving the investment was worth it.",
  },
];

const RESOURCE_ICONS = { Guides: BookOpen, "Case Studies": FileText, Insights: Lightbulb, Tools: Calculator };

const FINAL_POINTS = [
  { title: "Free opportunity assessment", copy: "Identify your highest-value processes." },
  { title: "ROI estimate", copy: "Understand the potential financial impact." },
  { title: "Clear recommendation", copy: "Know what to automate — and what not to." },
];

export default function Home() {
  const featured = CASE_STUDIES.filter((c) => c.featured);

  return (
    <>
      {/* 1 — Hero */}
      <HeroSection />

      {/* Hero proof points */}
      <Section className="!py-0 -mt-2 md:-mt-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {PROOF_POINTS.map((p) => (
            <GlassCard key={p.title} className="p-6">
              <div className="flex items-start gap-4">
                <IconBadge className="h-10 w-10 rounded-xl shrink-0">
                  <p.icon className="h-5 w-5 text-white" />
                </IconBadge>
                <div>
                  <div className="font-semibold text-white">{p.title}</div>
                  <p className="mt-1 text-sm text-zinc-400 leading-relaxed">{p.copy}</p>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      </Section>

      {/* 2 — Trust / Clients (renders only once real clients exist) */}
      {CLIENTS.length > 0 && (
        <Section className="!pb-0">
          <p className="mb-8 text-center text-sm text-zinc-500">Trusted by ambitious companies in Morocco</p>
          <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6 opacity-60 grayscale">
            {CLIENTS.map((c) =>
              c.logoUrl ? (
                <img key={c.name} src={c.logoUrl} alt={c.name} className="h-8" />
              ) : (
                <span key={c.name} className="text-lg font-bold tracking-tight text-white">{c.name}</span>
              )
            )}
          </div>
        </Section>
      )}

      {/* 3 — The problem */}
      <Section>
        <SectionHeading
          title={
            <>
              Your biggest automation opportunity is probably <GradientText>hiding in plain sight.</GradientText>
            </>
          }
          intro={
            <>
              Every company has processes that consume hours, create unnecessary costs, or depend on people doing
              the same work over and over again. The problem isn't knowing that AI exists.{" "}
              <span className="text-white">The problem is knowing where it actually makes economic sense.</span>
            </>
          }
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {PROBLEMS.map((p) => (
            <GlassCard key={p.title}>
              <IconBadge className="mb-5">
                <p.icon className="h-6 w-6 text-white" />
              </IconBadge>
              <div className="text-lg font-semibold text-white">{p.title}</div>
              <p className="mt-2 text-sm text-zinc-400 leading-relaxed">{p.copy}</p>
            </GlassCard>
          ))}
        </div>
        <p className="mt-10 text-lg font-medium text-white">That's where we come in.</p>
      </Section>

      {/* 4 — Approach */}
      <Section>
        <SectionHeading
          eyebrow="OUR APPROACH"
          title="A clear process. Real impact."
          intro="We don't start with technology. We start with the business problem, identify where value is being lost, and work backwards toward the right solution."
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {APPROACH_STEPS.map((s) => (
            <GlassCard key={s.index}>
              <div className="mb-5 flex items-center justify-between">
                <IconBadge>
                  <s.icon className="h-6 w-6 text-white" />
                </IconBadge>
                <span className="text-sm font-semibold text-zinc-600">{s.index}</span>
              </div>
              <Eyebrow className="mb-1 text-[10px]">{s.name}</Eyebrow>
              <div className="text-lg font-semibold text-white">{s.title}</div>
              <p className="mt-2 text-sm text-zinc-400 leading-relaxed">{s.copy}</p>
            </GlassCard>
          ))}
        </div>
        <div className="mt-10">
          <TextLink to="/approach">Learn about our approach</TextLink>
        </div>
      </Section>

      {/* 5 — Solutions */}
      <Section>
        <SectionHeading
          eyebrow="SOLUTIONS"
          title="Smart automation for every department."
          intro="The best automation doesn't live in a technology department. It lives wherever people spend time doing work that software can do better."
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {SOLUTIONS.map((s) => (
            <GlassCard key={s.slug} className="flex flex-col">
              <IconBadge className="mb-5">
                <s.icon className="h-6 w-6 text-white" />
              </IconBadge>
              <Eyebrow className="mb-1 text-[10px]">{s.name}</Eyebrow>
              <div className="text-lg font-semibold text-white">{s.cardHeadline}</div>
              <p className="mt-2 flex-1 text-sm text-zinc-400 leading-relaxed">{s.cardDescription}</p>
              <TextLink to={`/solutions/${s.slug}`} className="mt-5">
                Explore {s.name}
              </TextLink>
            </GlassCard>
          ))}
        </div>
      </Section>

      {/* 6 — Case studies */}
      <Section>
        <SectionHeading
          eyebrow="CASE STUDIES"
          title="Real results. From real companies."
          intro="Automation only matters when it changes the numbers. Explore how we help businesses reduce costs, save time, and improve performance."
        />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {featured.map((c) => (
            <GlassCard key={c.slug} className="flex flex-col">
              <Eyebrow className="mb-3 text-[10px]">{c.tag}</Eyebrow>
              <div className="text-lg font-semibold text-white leading-snug">{c.title}</div>
              <p className="mt-2 flex-1 text-sm text-zinc-400 leading-relaxed">{c.summary}</p>
              <div className="mt-5 text-2xl font-bold tracking-tight text-white">{c.headline}</div>
              <TextLink to={`/case-studies/${c.slug}`} className="mt-5">
                Read the case study
              </TextLink>
            </GlassCard>
          ))}
        </div>
      </Section>

      {/* 7 — Impact */}
      <Section>
        <SectionHeading
          eyebrow="OUR IMPACT"
          title="We measure what matters."
          intro="Every engagement starts with a business case. Before we build anything, we define what success looks like and how we'll measure it."
        />
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {IMPACT_METRICS.map((m) => (
            <GlassCard key={m.label} className="text-center">
              <div className="text-3xl sm:text-4xl font-bold tracking-tight text-white">{m.value}</div>
              <div className="mt-2 text-sm font-medium text-zinc-300">{m.label}</div>
              <div className="mt-1 text-xs text-zinc-500">{m.note}</div>
            </GlassCard>
          ))}
        </div>
      </Section>

      {/* 8 — Why Cadence */}
      <Section>
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <SectionHeading
              title={
                <>
                  Not another <GradientText>AI consultancy.</GradientText>
                </>
              }
              intro={
                <>
                  We don't come in with a technology looking for somewhere to use it.{" "}
                  <span className="text-white">We start with the economics of the problem.</span>
                </>
              }
            />
          </div>
          <div className="lg:col-span-7 space-y-4">
            {PRINCIPLES.map((p, i) => (
              <GlassCard key={p.title} className="flex gap-6 p-6">
                <span className="text-sm font-semibold text-zinc-600 pt-1">0{i + 1}</span>
                <div>
                  <div className="text-lg font-semibold text-white">{p.title}</div>
                  <p className="mt-1 text-sm text-zinc-400 leading-relaxed">{p.copy}</p>
                </div>
              </GlassCard>
            ))}
          </div>
        </div>
      </Section>

      {/* 9 — Testimonials (renders only once real quotes exist) */}
      {TESTIMONIALS.length > 0 && (
        <Section>
          <SectionHeading eyebrow="CLIENTS SAY IT BEST" title="Built around results." />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {TESTIMONIALS.map((t) => (
              <GlassCard key={t.name}>
                <p className="text-zinc-300 leading-relaxed">&ldquo;{t.quote}&rdquo;</p>
                <div className="mt-6 text-sm font-semibold text-white">{t.name}</div>
                <div className="text-xs text-zinc-500">
                  {t.title}, {t.company}
                </div>
              </GlassCard>
            ))}
          </div>
        </Section>
      )}

      {/* 10 — Resources */}
      <Section>
        <SectionHeading
          eyebrow="RESOURCES"
          title="Think smarter about automation."
          intro="Practical guides, case studies, and ideas for leaders deciding where AI and automation can actually create value."
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {RESOURCES.slice(0, 3).map((r) => {
            const Icon = RESOURCE_ICONS[r.category];
            return (
              <GlassCard key={r.slug} className="flex flex-col">
                <div className="mb-4 flex items-center gap-3">
                  <IconBadge className="h-9 w-9 rounded-xl">
                    <Icon className="h-4 w-4 text-white" />
                  </IconBadge>
                  <Eyebrow className="text-[10px]">{r.category}</Eyebrow>
                </div>
                <div className="text-lg font-semibold text-white leading-snug">{r.title}</div>
                <p className="mt-2 flex-1 text-sm text-zinc-400 leading-relaxed">{r.description}</p>
              </GlassCard>
            );
          })}
        </div>
        <div className="mt-10">
          <TextLink to="/resources">Explore all resources</TextLink>
        </div>
      </Section>

      {/* 11 — Final CTA */}
      <Section>
        <GlassCard className="p-10 md:p-16 text-center">
          <div className="absolute top-0 right-0 -mr-24 -mt-24 h-96 w-96 rounded-full bg-white/5 blur-3xl pointer-events-none" />
          <div className="relative z-10 mx-auto max-w-2xl">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-medium tracking-tighter text-white">
              Find your biggest <GradientText>automation opportunity.</GradientText>
            </h2>
            <p className="mt-5 text-lg text-zinc-400 leading-relaxed">
              In 30 minutes, we'll look at your business, identify where automation could create the most value,
              and tell you whether it's worth building.
            </p>
            <div className="mt-8 grid grid-cols-1 gap-3 text-left sm:grid-cols-3">
              {FINAL_POINTS.map((p) => (
                <div key={p.title} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-white">
                    <CheckCircle2 className="h-4 w-4 text-[#ffcd75]" />
                    {p.title}
                  </div>
                  <p className="mt-1 text-xs text-zinc-400">{p.copy}</p>
                </div>
              ))}
            </div>
            <div className="mt-8 flex justify-center">
              <ButtonLink to="/contact">Book a free strategy call</ButtonLink>
            </div>
            <p className="mt-4 text-xs text-zinc-500">
              No commitment. No sales pitch. Just a practical conversation about what's possible.
            </p>
          </div>
        </GlassCard>
      </Section>

      {/* Secondary path to the assessment */}
      <Section className="!pt-0 text-center">
        <p className="text-sm text-zinc-500">
          Prefer to start async?{" "}
          <Link to="/assessment" className="font-semibold text-white transition-colors hover:text-[#ffcd75]">
            Take the automation opportunity assessment →
          </Link>
        </p>
      </Section>
    </>
  );
}
