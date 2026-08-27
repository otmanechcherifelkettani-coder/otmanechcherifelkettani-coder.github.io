export type Resource = {
  slug: string;
  category: "Guides" | "Case Studies" | "Insights" | "Tools";
  title: string;
  description: string;
  comingSoon?: boolean;
};

export const RESOURCE_CATEGORIES = [
  { name: "Guides", description: "Long-form educational content." },
  { name: "Case studies", description: "Detailed breakdowns of real projects." },
  { name: "Insights", description: "Short opinions and perspectives." },
  { name: "Tools", description: "Practical calculators, assessments, and frameworks." },
];

// Planned editorial pipeline. Articles ship one by one; keep comingSoon
// until the piece is actually published.
export const RESOURCES: Resource[] = [
  {
    slug: "20-processes-you-can-automate",
    category: "Guides",
    title: "20 Processes You Can Automate Right Now",
    description: "A department-by-department list of the processes most companies can automate today, and what each one is worth.",
    comingSoon: true,
  },
  {
    slug: "cfo-guide-automation-roi",
    category: "Guides",
    title: "The CFO's Guide to Automation ROI",
    description: "How to build the business case for automation: costs to count, returns to measure, and traps to avoid.",
    comingSoon: true,
  },
  {
    slug: "ai-in-customer-service",
    category: "Insights",
    title: "Where AI Actually Makes Sense in Customer Service",
    description: "What to automate, what to keep human, and how to tell the difference — from someone who ran it at global scale.",
    comingSoon: true,
  },
  {
    slug: "ai-vs-automation",
    category: "Insights",
    title: "AI vs. Automation: What Should You Build?",
    description: "Most problems don't need AI. Some do. A practical way to decide which one you're looking at.",
    comingSoon: true,
  },
  {
    slug: "find-your-highest-value-opportunity",
    category: "Tools",
    title: "How to Find Your Highest-Value Automation Opportunity",
    description: "The framework we use in discovery: mapping processes, pricing the waste, and ranking what to build first.",
    comingSoon: true,
  },
];
