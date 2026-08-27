import { Check } from "lucide-react";
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

export default function Solutions() {
  return (
    <>
      <Section className="pt-20 md:pt-28">
        <div className="max-w-3xl space-y-6">
          <Eyebrow>SOLUTIONS</Eyebrow>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tighter text-white leading-[1.02]">
            Automate the work that <GradientText>shouldn't require a person.</GradientText>
          </h1>
          <p className="text-lg text-zinc-400 leading-relaxed">
            From customer service to finance, we build systems that remove repetitive work, connect your
            processes, and give your teams more time to focus on higher-value work.
          </p>
          <ButtonLink to="/assessment">Find an opportunity</ButtonLink>
        </div>
      </Section>

      <Section className="!pt-0">
        <div className="space-y-6">
          {SOLUTIONS.map((s, i) => (
            <GlassCard key={s.slug} className="p-8 md:p-10">
              <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
                <div className="lg:col-span-5 space-y-4">
                  <div className="flex items-center gap-4">
                    <IconBadge>
                      <s.icon className="h-6 w-6 text-white" />
                    </IconBadge>
                    <span className="text-sm font-semibold text-zinc-600">0{i + 1}</span>
                  </div>
                  <h2 className="text-2xl sm:text-3xl font-medium tracking-tight text-white">{s.name}</h2>
                  <p className="text-zinc-400 leading-relaxed">{s.overviewLine}</p>
                  <TextLink to={`/solutions/${s.slug}`}>Explore {s.name}</TextLink>
                </div>
                <div className="lg:col-span-7">
                  <Eyebrow className="mb-4 text-[10px]">Capabilities</Eyebrow>
                  <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    {s.capabilities.map((c) => (
                      <li key={c} className="flex items-center gap-2.5 text-sm text-zinc-300">
                        <Check className="h-4 w-4 shrink-0 text-[#ffcd75]" />
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      </Section>

      <Section className="!pt-0">
        <SectionHeading
          center
          title="Not sure where to start?"
          intro="Tell us about your processes and we'll point you at the highest-value opportunity — even if it's not one of the six above."
        />
        <div className="flex justify-center">
          <ButtonLink to="/assessment">Take the assessment</ButtonLink>
        </div>
      </Section>
    </>
  );
}
