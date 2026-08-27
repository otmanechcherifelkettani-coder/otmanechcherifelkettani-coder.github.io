// Central site configuration. Everything a future CMS would own lives in
// src/data — copy, metrics, clients, testimonials — so claims can be
// updated without touching components.

export const CONTACT = {
  email: "otmankettani5@gmail.com",
  linkedin: "https://linkedin.com/in/otmaneekettani",
};

export const NAV = [
  { label: "What we do", to: "/solutions" },
  { label: "Results", to: "/case-studies" },
  { label: "How we work", to: "/approach" },
  { label: "Resources", to: "/resources" },
  { label: "About", to: "/about" },
];

// Track-record metrics. These are the founder's shipped, measured numbers
// (see the Work page of the original site) — replace or extend with
// Cadence-client metrics as engagements complete.
export const IMPACT_METRICS = [
  { value: "$35M+", label: "Annual impact shipped", note: "measured against baselines, across career engagements" },
  { value: "−34%", label: "Support contact volume", note: "at a global delivery platform, post automation" },
  { value: "+20%", label: "CSAT after LLM rebuild", note: "quality up while cost per contact went down" },
  { value: "20+", label: "Experiments at global scale", note: "cost- and engagement-focused, before scaling anything" },
];

// Client logos. Deliberately empty until real Cadence clients agree to be
// named — the Trust section renders only when this has entries.
export type Client = { name: string; logoUrl?: string };
export const CLIENTS: Client[] = [];

// Testimonials. Deliberately empty until real, specific quotes exist —
// the Testimonials section renders only when this has entries.
export type Testimonial = { quote: string; name: string; title: string; company: string };
export const TESTIMONIALS: Testimonial[] = [];
