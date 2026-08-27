import { Link, Navigate, useParams } from "react-router-dom";
import { ArrowRight, Check } from "lucide-react";
import {
  Section,
  SectionHeading,
  Eyebrow,
  GlassCard,
  GradientText,
  ButtonLink,
  TextLink,
} from "@/components/ui/primitives";
import { getSolution, HOW_IT_WORKS } from "@/data/solutions";
import { getCaseStudy } from "@/data/caseStudies";

export default function SolutionDetail() {
  const { slug } = useParams();
  const solution = slug ? getSolution(slug) : undefined;
  if (!solution) return <Navigate to="/solutions" replace />;

  const related = solution.relatedCaseSlug ? getCaseStudy(solution.relatedCaseSlug) : undefined;

  return (
    <>
      <Section className="pt-20 md:pt-28">
        <div className="max-w-3xl space-y-6">
          <Eyebrow>{solution.name} automation</Eyebrow>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tighter text-white leading-[1.02]">
            <GradientText>{solution.heroLine}</GradientText>
          </h1>
          <ButtonLink to="/contact">Talk to us about your process</ButtonLink>
        </div>
      </Section>

      {/* The problem */}
      <Section className="!pt-0">
        <GlassCard className="p-8 md:p-12">
          <Eyebrow className="mb-4">The problem</Eyebrow>
          <h2 className="max-w-2xl text-2xl sm:text-3xl font-medium tracking-tight text-white">
            {solution.problemHeadline}
          </h2>
          <p className="mt-4 max-w-2xl text-zinc-400 leading-relaxed">{solution.problemCopy}</p>
        </GlassCard>
      </Section>

      {/* What we automate */}
      <Section className="!pt-0">
        <SectionHeading eyebrow="What we automate" title={solution.cardHeadline} />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
          {solution.capabilities.map((c) => (
            <GlassCard key={c} className="p-6">
              <Check className="mb-3 h-5 w-5 text-[#ffcd75]" />
              <div className="text-sm font-semibold text-white">{c}</div>
            </GlassCard>
          ))}
        </div>
      </Section>

      {/* How it works */}
      <Section className="!pt-0">
        <SectionHeading
          eyebrow="How it works"
          title="From incoming work to finished outcome."
          intro="The same six-step pattern sits behind every system we build — what changes is your data, your policies, and your tools."
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {HOW_IT_WORKS.map((h, i) => (
            <GlassCard key={h.step} className="p-6">
              <span className="text-sm font-semibold text-zinc-600">0{i + 1}</span>
              <div className="mt-2 font-semibold text-white">{h.step}</div>
              <p className="mt-1.5 text-sm text-zinc-400 leading-relaxed">{h.detail}</p>
            </GlassCard>
          ))}
        </div>
      </Section>

      {/* Example workflow */}
      <Section className="!pt-0">
        <GlassCard className="p-8 md:p-12">
          <Eyebrow className="mb-6">Example workflow</Eyebrow>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-4">
            {solution.workflow.map((step, i) => (
              <div key={step} className="flex items-center gap-3">
                <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-zinc-200">
                  {step}
                </span>
                {i < solution.workflow.length - 1 && <ArrowRight className="h-4 w-4 shrink-0 text-zinc-600" />}
              </div>
            ))}
          </div>
        </GlassCard>
      </Section>

      {/* Business impact */}
      <Section className="!pt-0">
        <SectionHeading
          eyebrow="Business impact"
          title="What we measure."
          intro="Every engagement defines its KPIs before anything is built. These are the numbers we typically track in this department — your baseline sets the targets."
        />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {solution.impactMeasures.map((m) => (
            <GlassCard key={m.label}>
              <div className="text-lg font-semibold text-white">{m.label}</div>
              <p className="mt-2 text-sm text-zinc-400 leading-relaxed">{m.description}</p>
            </GlassCard>
          ))}
        </div>
      </Section>

      {/* Related case study */}
      {related && (
        <Section className="!pt-0">
          <GlassCard className="p-8 md:p-12">
            <div className="absolute top-0 right-0 -mr-24 -mt-24 h-72 w-72 rounded-full bg-white/5 blur-3xl pointer-events-none" />
            <div className="relative z-10">
              <Eyebrow className="mb-3">Related case study · {related.tag}</Eyebrow>
              <h2 className="max-w-2xl text-2xl sm:text-3xl font-medium tracking-tight text-white">{related.title}</h2>
              <p className="mt-3 max-w-2xl text-zinc-400 leading-relaxed">{related.summary}</p>
              <div className="mt-5 text-2xl font-bold tracking-tight text-white">{related.headline}</div>
              <TextLink to={`/case-studies/${related.slug}`} className="mt-5">
                See how we did it
              </TextLink>
            </div>
          </GlassCard>
        </Section>
      )}

      {/* Final CTA */}
      <Section className="!pt-0 text-center">
        <h2 className="text-3xl sm:text-4xl font-medium tracking-tighter text-white">
          Think this could work for your business?
        </h2>
        <div className="mt-8 flex justify-center">
          <ButtonLink to="/contact">Let's look at the process together</ButtonLink>
        </div>
        <div className="mt-6">
          <Link to="/solutions" className="text-sm text-zinc-500 transition-colors hover:text-white">
            ← All solutions
          </Link>
        </div>
      </Section>
    </>
  );
}
