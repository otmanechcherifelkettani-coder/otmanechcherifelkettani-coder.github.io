import { Navigate, useParams } from "react-router-dom";
import {
  Section,
  Eyebrow,
  GlassCard,
  GradientText,
  ButtonLink,
  TextLink,
} from "@/components/ui/primitives";
import { CASE_STUDIES, getCaseStudy } from "@/data/caseStudies";

export default function CaseStudyDetail() {
  const { slug } = useParams();
  const cs = slug ? getCaseStudy(slug) : undefined;
  if (!cs) return <Navigate to="/case-studies" replace />;

  const related = CASE_STUDIES.filter((c) => c.slug !== cs.slug).slice(0, 3);

  return (
    <>
      <Section className="pt-20 md:pt-28">
        <div className="max-w-3xl space-y-6">
          <Eyebrow>{cs.tag}</Eyebrow>
          <h1 className="text-4xl sm:text-5xl font-medium tracking-tighter text-white leading-[1.05]">
            <GradientText>{cs.title}</GradientText>
          </h1>
          <p className="text-lg text-zinc-400 leading-relaxed">{cs.summary}</p>
        </div>
      </Section>

      {/* Results up front */}
      <Section className="!pt-0">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {cs.results.map((r) => (
            <GlassCard key={r.label} className="text-center">
              <div className="text-2xl sm:text-3xl font-bold tracking-tight text-white">{r.value}</div>
              <div className="mt-2 text-xs sm:text-sm text-zinc-400">{r.label}</div>
            </GlassCard>
          ))}
        </div>
      </Section>

      <Section className="!pt-0">
        <div className="space-y-6 max-w-4xl">
          <Block label="The challenge" copy={cs.challenge} />
          <Block label="The opportunity" copy={cs.opportunity} />
          <Block label="What we built" copy={cs.built} />
        </div>
      </Section>

      {/* Before / After */}
      <Section className="!pt-0">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <GlassCard>
            <Eyebrow className="mb-3">Before</Eyebrow>
            <p className="text-zinc-400 leading-relaxed">{cs.before}</p>
          </GlassCard>
          <GlassCard className="border-[#ffcd75]/20">
            <Eyebrow className="mb-3 text-[#ffcd75]">After</Eyebrow>
            <p className="text-zinc-300 leading-relaxed">{cs.after}</p>
          </GlassCard>
        </div>
      </Section>

      {/* Related cases */}
      <Section className="!pt-0">
        <Eyebrow className="mb-6">More cases</Eyebrow>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {related.map((c) => (
            <GlassCard key={c.slug} className="flex flex-col">
              <Eyebrow className="mb-3 text-[10px]">{c.tag}</Eyebrow>
              <div className="flex-1 font-semibold text-white leading-snug">{c.title}</div>
              <div className="mt-4 text-lg font-bold tracking-tight text-white">{c.headline}</div>
              <TextLink to={`/case-studies/${c.slug}`} className="mt-4 text-xs">
                Read the case study
              </TextLink>
            </GlassCard>
          ))}
        </div>
      </Section>

      <Section className="!pt-0 text-center">
        <h2 className="text-3xl sm:text-4xl font-medium tracking-tighter text-white">
          Have a process like this in your business?
        </h2>
        <div className="mt-8 flex justify-center">
          <ButtonLink to="/contact">Talk to Cadence</ButtonLink>
        </div>
      </Section>
    </>
  );
}

function Block({ label, copy }: { label: string; copy: string }) {
  return (
    <GlassCard className="p-8">
      <Eyebrow className="mb-3">{label}</Eyebrow>
      <p className="text-zinc-300 leading-relaxed">{copy}</p>
    </GlassCard>
  );
}
