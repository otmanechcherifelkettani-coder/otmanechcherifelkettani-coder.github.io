import {
  Headset,
  Settings,
  Megaphone,
  Calculator,
  ShoppingCart,
  Users,
  type LucideIcon,
} from "lucide-react";

export type Solution = {
  slug: string;
  name: string;
  icon: LucideIcon;
  // Home-page card
  cardHeadline: string;
  cardDescription: string;
  // Solutions overview page
  overviewLine: string;
  capabilities: string[];
  // Individual solution page
  heroLine: string;
  problemHeadline: string;
  problemCopy: string;
  workflow: string[];
  // What we measure on engagements in this department (definitions, not claims)
  impactMeasures: { label: string; description: string }[];
  relatedCaseSlug?: string;
};

export const HOW_IT_WORKS = [
  { step: "Understand the request", detail: "The system reads the incoming work item and identifies what is actually being asked." },
  { step: "Retrieve the information", detail: "It pulls the relevant records, documents, and context from your existing tools." },
  { step: "Make a decision", detail: "Clear rules and policies decide what can be handled automatically and what cannot." },
  { step: "Take the action", detail: "The system executes: responds, updates records, routes, or completes the task." },
  { step: "Escalate when needed", detail: "Anything ambiguous or high-stakes goes to a person, with full context attached." },
  { step: "Learn from the outcome", detail: "Every resolution feeds back into measurement, so the system improves over time." },
];

export const SOLUTIONS: Solution[] = [
  {
    slug: "customer-service",
    name: "Customer Service",
    icon: Headset,
    cardHeadline: "Automate the work behind great customer service.",
    cardDescription:
      "Automate repetitive requests, ticket routing, follow-ups, knowledge retrieval, and support workflows so your team can focus on customers.",
    overviewLine: "Automate repetitive customer interactions without compromising the customer experience.",
    capabilities: [
      "Ticket classification",
      "Automated responses",
      "Knowledge retrieval",
      "Escalation workflows",
      "Customer follow-ups",
      "Quality monitoring",
    ],
    heroLine: "Give your team fewer tickets to handle and more time to spend with customers.",
    problemHeadline: "Your team shouldn't spend its day answering the same question in ten different ways.",
    problemCopy:
      "Most support queues are dominated by a small number of request types: order status, refunds, account changes, basic product questions. Handling them manually is slow for customers, expensive for the business, and demoralizing for good agents. The volume also hides the conversations that actually need a human.",
    workflow: [
      "Customer submits request",
      "System understands intent",
      "Retrieves order information",
      "Checks eligibility",
      "Resolves request",
      "Updates CRM",
      "Escalates exceptions",
    ],
    impactMeasures: [
      { label: "Resolution time", description: "How much faster eligible requests are resolved end to end." },
      { label: "Contact automation rate", description: "The share of volume handled without an agent touch." },
      { label: "Customer satisfaction", description: "CSAT on automated resolutions vs. the manual baseline." },
    ],
    relatedCaseSlug: "support-automation",
  },
  {
    slug: "operations",
    name: "Operations",
    icon: Settings,
    cardHeadline: "Make your operations run themselves.",
    cardDescription:
      "Eliminate repetitive administrative work, automate workflows, connect systems, and give your teams time back.",
    overviewLine: "Remove repetitive operational work and connect the systems your teams rely on.",
    capabilities: [
      "Workflow automation",
      "Data entry",
      "Approvals",
      "Reporting",
      "Notifications",
      "System integrations",
    ],
    heroLine: "Remove the repetitive work between your systems, and the errors that come with it.",
    problemHeadline: "Your processes work — they just depend on people copying things between systems.",
    problemCopy:
      "Operational work accumulates in the gaps between tools: data re-entered from one system into another, approvals chased over email, reports assembled by hand every week. Each step is small; together they consume real headcount and introduce errors nobody catches until they cost money.",
    workflow: [
      "Work item arrives",
      "System captures and validates the data",
      "Routes it for approval when required",
      "Updates every connected system once",
      "Notifies the people who need to know",
      "Logs the outcome for reporting",
    ],
    impactMeasures: [
      { label: "Hours returned", description: "Manual processing time removed per week, measured before and after." },
      { label: "Cycle time", description: "How long a process takes end to end, from request to done." },
      { label: "Error rate", description: "Rework and corrections caused by manual handling." },
    ],
    relatedCaseSlug: "capacity-planning",
  },
  {
    slug: "marketing",
    name: "Marketing",
    icon: Megaphone,
    cardHeadline: "Turn repetitive marketing work into automated workflows.",
    cardDescription:
      "Automate campaign operations, lead management, reporting, content workflows, and customer communications.",
    overviewLine: "Automate the operational side of marketing so your team can focus on growth.",
    capabilities: [
      "Lead routing",
      "Campaign workflows",
      "CRM automation",
      "Reporting",
      "Email workflows",
      "Content operations",
    ],
    heroLine: "Let your marketers spend their time on strategy and creative — not production and admin.",
    problemHeadline: "Most marketing time isn't spent on marketing.",
    problemCopy:
      "Campaign production, channel adaptation, list hygiene, weekly reporting, lead handoffs — the operational layer of marketing quietly eats the calendar. Output becomes limited by how fast the team can produce and coordinate, not by how good the ideas are.",
    workflow: [
      "Campaign brief is written once",
      "System generates copy and asset variants",
      "Brand guardrails check every output",
      "Human reviews at the decision points that matter",
      "Campaign ships across channels",
      "Results flow into one report automatically",
    ],
    impactMeasures: [
      { label: "Production time", description: "Time from brief to shipped campaign, per variant." },
      { label: "Output volume", description: "Campaigns and variants shipped per month with the same team." },
      { label: "Lead response time", description: "How fast inbound leads are routed and followed up." },
    ],
    relatedCaseSlug: "marketing-automation",
  },
  {
    slug: "finance",
    name: "Finance",
    icon: Calculator,
    cardHeadline: "Automate the work behind the numbers.",
    cardDescription:
      "Automate data collection, reconciliation, reporting, document processing, and financial workflows.",
    overviewLine: "Reduce manual financial work and improve the speed and accuracy of your processes.",
    capabilities: [
      "Invoice processing",
      "Reconciliation",
      "Data extraction",
      "Reporting",
      "Financial workflows",
      "Document processing",
    ],
    heroLine: "Close faster, reconcile automatically, and stop paying skilled people to retype documents.",
    problemHeadline: "Finance teams spend their best hours moving numbers between documents.",
    problemCopy:
      "Invoices arrive as PDFs and get retyped. Reconciliation means matching lines across exports. Month-end reporting means chasing inputs from every department. The work is precise, repetitive, and exactly what software now does reliably — with an audit trail people can't match.",
    workflow: [
      "Document arrives",
      "System extracts and validates the data",
      "Matches it against existing records",
      "Flags discrepancies for review",
      "Posts clean entries automatically",
      "Feeds reporting in real time",
    ],
    impactMeasures: [
      { label: "Processing cost", description: "Cost per document or transaction, before and after." },
      { label: "Close speed", description: "Days to close the month or complete reconciliation." },
      { label: "Accuracy", description: "Discrepancies caught by the system vs. found downstream." },
    ],
    relatedCaseSlug: "saas-audit",
  },
  {
    slug: "e-commerce",
    name: "E-commerce",
    icon: ShoppingCart,
    cardHeadline: "Automate the complexity behind every order.",
    cardDescription:
      "Connect orders, inventory, suppliers, customer communications, and operational workflows.",
    overviewLine: "Automate the operational complexity behind your store.",
    capabilities: [
      "Order management",
      "Inventory",
      "Supplier workflows",
      "Customer communication",
      "Returns",
      "Reporting",
    ],
    heroLine: "Every order triggers a dozen tasks. Most of them shouldn't need a person.",
    problemHeadline: "Growth multiplies operational work faster than revenue.",
    problemCopy:
      "Each additional order means status updates, stock adjustments, supplier coordination, delivery questions, and the occasional return. Done manually, operations headcount scales with sales — and busy periods break the process exactly when it matters most.",
    workflow: [
      "Order comes in",
      "Inventory and supplier systems update automatically",
      "Customer gets proactive status communication",
      "Exceptions — delays, stock-outs, returns — are detected",
      "Eligible cases resolve automatically",
      "Edge cases route to your team with context",
    ],
    impactMeasures: [
      { label: "Orders per operator", description: "Order volume handled per operations headcount." },
      { label: "Contact rate", description: "Customer contacts per order — driven down by proactive communication." },
      { label: "Exception resolution", description: "Time to resolve delays, returns, and stock issues." },
    ],
    relatedCaseSlug: "capacity-planning",
  },
  {
    slug: "hr",
    name: "HR",
    icon: Users,
    cardHeadline: "Give your people team their time back.",
    cardDescription:
      "Automate recruitment workflows, onboarding, employee administration, reporting, and recurring HR processes.",
    overviewLine: "Automate repetitive people operations while keeping the human side human.",
    capabilities: [
      "Recruitment workflows",
      "Candidate screening",
      "Onboarding",
      "Employee administration",
      "Reporting",
      "Internal requests",
    ],
    heroLine: "HR should be about people. Most HR work is about paperwork.",
    problemHeadline: "The admin behind every hire, request, and process crowds out the human work.",
    problemCopy:
      "Screening hundreds of applications, scheduling interviews, preparing onboarding, answering the same policy questions, compiling headcount reports — people teams drown in coordination work. The result is slow hiring, inconsistent onboarding, and no time for the conversations that actually matter.",
    workflow: [
      "Application or request arrives",
      "System screens against defined criteria",
      "Qualified items move forward automatically",
      "Scheduling and paperwork happen without back-and-forth",
      "People decisions stay with people",
      "Every step is tracked for reporting",
    ],
    impactMeasures: [
      { label: "Time to hire", description: "Days from application to offer, per role." },
      { label: "Admin hours", description: "Coordination and paperwork time removed per hire and per month." },
      { label: "Onboarding consistency", description: "Steps completed on time for every new joiner." },
    ],
    relatedCaseSlug: "student-marketplace",
  },
];

export function getSolution(slug: string): Solution | undefined {
  return SOLUTIONS.find((s) => s.slug === slug);
}
