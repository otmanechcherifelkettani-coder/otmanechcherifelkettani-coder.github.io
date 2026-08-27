import { BookOpen, FileText, Lightbulb, Calculator } from "lucide-react";
import {
  Section,
  SectionHeading,
  Eyebrow,
  GlassCard,
  GradientText,
  ButtonLink,
  IconBadge,
  Pill,
} from "@/components/ui/primitives";
import { RESOURCES, RESOURCE_CATEGORIES } from "@/data/resources";

const CATEGORY_ICONS: Record<string, typeof BookOpen> = {
  Guides: BookOpen,
  "Case studies": FileText,
  Insights: Lightbulb,
  Tools: Calculator,
};

export default function Resources() {
  return (
    <>
      <Section className="pt-20 md:pt-28">
        <div className="max-w-3xl space-y-6">
          <Eyebrow>RESOURCES</Eyebrow>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-medium tracking-tighter text-white leading-[1.02]">
            Ideas for building a <GradientText>more efficient business.</GradientText>
          </h1>
          <p className="text-lg text-zinc-400 leading-relaxed">
            Practical guides, case studies, and ideas for leaders deciding where AI and automation can actually
            create value.
          </p>
        </div>
      </Section>

      <Section className="!pt-0">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {RESOURCE_CATEGORIES.map((c) => {
            const Icon = CATEGORY_ICONS[c.name];
            return (
              <GlassCard key={c.name} className="p-6">
                <IconBadge className="mb-4 h-10 w-10 rounded-xl">
                  <Icon className="h-5 w-5 text-white" />
                </IconBadge>
                <div className="font-semibold text-white">{c.name}</div>
                <p className="mt-1 text-xs text-zinc-400">{c.description}</p>
              </GlassCard>
            );
          })}
        </div>
      </Section>

      <Section className="!pt-0">
        <SectionHeading eyebrow="IN THE PIPELINE" title="First up." />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {RESOURCES.map((r) => (
            <GlassCard key={r.slug} className="flex flex-col">
              <div className="mb-4 flex items-center justify-between gap-3">
                <Eyebrow className="text-[10px]">{r.category}</Eyebrow>
                {r.comingSoon && <Pill>COMING SOON</Pill>}
              </div>
              <div className="text-lg font-semibold text-white leading-snug">{r.title}</div>
              <p className="mt-2 flex-1 text-sm text-zinc-400 leading-relaxed">{r.description}</p>
            </GlassCard>
          ))}
        </div>
        <p className="mt-8 text-sm text-zinc-500">
          Articles publish here as they're written. Subscribe in the footer to get them by email.
        </p>
      </Section>

      <Section className="!pt-0 text-center">
        <h2 className="text-3xl sm:text-4xl font-medium tracking-tighter text-white">
          Rather talk it through than read about it?
        </h2>
        <div className="mt-8 flex justify-center">
          <ButtonLink to="/contact">Book a strategy call</ButtonLink>
        </div>
      </Section>
    </>
  );
}
