// Real, shipped engagements from the founder's track record — the same five
// cases documented on the original Cadence Work page. Clients stay anonymous;
// the numbers don't. Do not add entries here without validated results.

export type CaseStudy = {
  slug: string;
  tag: string;
  industry: string;
  department: string;
  title: string;
  headline: string; // short metric-style headline for cards
  summary: string;
  challenge: string;
  opportunity: string;
  built: string;
  before: string;
  after: string;
  results: { value: string; label: string }[];
  featured?: boolean;
};

export const CASE_STUDIES: CaseStudy[] = [
  {
    slug: "support-automation",
    tag: "CUSTOMER SUPPORT · GLOBAL FOOD DELIVERY PLATFORM",
    industry: "Food Delivery",
    department: "Customer Service",
    title: "From workflows to LLMs: automating post-order support at global scale",
    headline: "~$15M/yr saved",
    summary:
      "Millions of post-order customer issues, moved from agents and rigid rules to LLM-driven resolution — with quality going up, not down.",
    challenge:
      "A global food delivery platform handled millions of post-order customer issues through agents and rigid rule-based flows. Cost per contact was high, resolution quality inconsistent, and legacy intent detection couldn't keep up with how customers actually described problems.",
    opportunity:
      "The highest-volume issue types followed predictable patterns — but the decisioning behind them (refund policy, fraud checks, incentives) was where the money was. Automating resolution and redesigning the policies together was the real lever.",
    built:
      "Two phases. First, automated resolution flows for the highest-volume issue types, validated through 20+ cost- and engagement-focused experiments on refund policy, fraud detection, and incentive design. Then a full LLM rebuild: an LLM-based planner unifying all support entry points, LLM-driven resolution workflows, and policy redesigns enabling flexible, data-driven decisioning.",
    before: "Agents and static rule-based flows handling every contact; rigid intent menus customers had to fit themselves into.",
    after: "An LLM planner understands the issue as the customer describes it, resolves eligible cases end to end, and hands agents only the exceptions — with full context.",
    results: [
      { value: "~$15M/yr", label: "cost savings from automation" },
      { value: "+$20M/yr", label: "incremental gross bookings" },
      { value: "+20%", label: "CSAT after the LLM rebuild" },
      { value: "+8%", label: "issue discoverability vs. static baseline" },
    ],
    featured: true,
  },
  {
    slug: "capacity-planning",
    tag: "CAPACITY PLANNING · $2B APPAREL RETAILER",
    industry: "Retail / E-commerce",
    department: "Operations",
    title: "A planning tool that retired the Excel files",
    headline: "manual → internal tool",
    summary:
      "Capacity planning for $2B of annual sales, moved from a chain of spreadsheets to a single internal tool the planning team owns.",
    challenge:
      "A retailer selling $2B of clothing a year ran capacity planning on outdated Excel files and manual processes — slow to update, error-prone, and dependent on a few people who knew where the bodies were buried.",
    opportunity:
      "The planning logic itself was sound; the leverage was in removing the manual assembly and making the real decision drivers explicit in one system.",
    built:
      "Mapped the planning process end to end, identified what actually drove decisions, and built an internal capacity planning tool around those drivers — replacing the spreadsheet chain with a single source of truth the planning team owns.",
    before: "A chain of Excel files, manually updated, understood by a handful of people.",
    after: "One internal tool: current data, explicit drivers, a planning cycle measured in hours.",
    results: [
      { value: "1 tool", label: "replaced a chain of Excel files" },
      { value: "days → hours", label: "planning cycle time" },
      { value: "owned in-house", label: "no new SaaS contract" },
    ],
    featured: true,
  },
  {
    slug: "saas-audit",
    tag: "SAAS AUDIT · COMPANIES OF MULTIPLE SIZES",
    industry: "Cross-industry",
    department: "Finance",
    title: "Full-stack SaaS audits: cut, keep, or rebuild",
    headline: "build vs. buy, quantified",
    summary:
      "Tool-by-tool audits of full SaaS stacks, with a business case behind every verdict — including whether to rebuild internally.",
    challenge:
      "Companies accumulate SaaS faster than they retire it. Across businesses of different sizes, stacks were full of overlapping tools, unused seats, and subscriptions priced for capabilities nobody touched.",
    opportunity:
      "LLMs have collapsed the cost of building internal software — which changes the build-vs-buy math for a large share of a typical stack. Most audits never ask that question.",
    built:
      "Audited each stack tool by tool: real usage vs. contract, switching costs, and whether a simpler internal tool could replace it. Every tool got a verdict — cut, keep, or rebuild — with the business case attached.",
    before: "Renewals approved by default; nobody owns the full picture of spend vs. usage.",
    after: "A quantified verdict per tool and a recurring-savings plan, not a one-off cleanup.",
    results: [
      { value: "full stack", label: "audited per company" },
      { value: "cut / keep / rebuild", label: "verdict with business case per tool" },
      { value: "recurring", label: "savings, not one-off" },
    ],
    featured: true,
  },
  {
    slug: "marketing-automation",
    tag: "MARKETING AUTOMATION · B2C SUPPLEMENT BRAND",
    industry: "Consumer Goods",
    department: "Marketing",
    title: "Automating marketing production end to end",
    headline: "production at scale",
    summary:
      "An LLM production pipeline that turns one campaign brief into full multi-channel output, with human review only where it matters.",
    challenge:
      "A B2C supplement brand's growth was throttled by marketing production: every campaign needed manual copywriting, asset creation, and channel adaptation.",
    opportunity:
      "Production, not ideas, was the bottleneck — the kind of structured, repetitive creative work an LLM pipeline handles well under brand guardrails.",
    built:
      "An LLM-driven production pipeline generating campaign copy and asset variants from a single brief, with brand guardrails and human review at the decision points that matter — not every step.",
    before: "Every campaign hand-produced: copy, assets, and channel adaptations one by one.",
    after: "One brief in, a full campaign out — variants generated, guardrailed, and reviewed in minutes.",
    results: [
      { value: "1 brief", label: "in — full campaign out" },
      { value: "hours → minutes", label: "per campaign variant" },
      { value: "consistent", label: "brand voice across channels" },
    ],
  },
  {
    slug: "student-marketplace",
    tag: "MARKETPLACE · STUDENT EMPLOYMENT",
    industry: "Talent",
    department: "HR",
    title: "Launching a platform connecting students with jobs",
    headline: "zero → launch",
    summary:
      "A two-sided marketplace taken from concept to launch: product, matching logic, and the operational playbook to keep both sides balanced.",
    challenge:
      "Students struggle to find flexible work; employers struggle to find them. No platform served the match well in the target market.",
    opportunity:
      "A structured matching problem with clear supply and demand — the kind of marketplace where good operational design decides whether it works.",
    built:
      "Took the marketplace from concept to launch: product definition, matching logic, supply and demand acquisition, and the operational playbook to keep both sides balanced.",
    before: "No platform serving the match; students and employers finding each other ad hoc.",
    after: "A live two-sided marketplace with students and employers onboarded.",
    results: [
      { value: "0 → 1", label: "shipped to market" },
      { value: "two-sided", label: "students and employers onboarded" },
    ],
  },
];

export function getCaseStudy(slug: string): CaseStudy | undefined {
  return CASE_STUDIES.find((c) => c.slug === slug);
}
