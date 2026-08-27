import type { ComponentProps, ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

// Shared design-system primitives for the Cadence glassmorphism look:
// zinc-950 canvas, white/5 glass panels, white/10 borders, #ffcd75 accent.

export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("text-xs font-semibold uppercase tracking-wider text-zinc-500", className)}>
      {children}
    </div>
  );
}

export function GradientText({ children }: { children: ReactNode }) {
  return (
    <span className="bg-gradient-to-br from-white via-white to-[#ffcd75] bg-clip-text text-transparent">
      {children}
    </span>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  intro,
  center,
}: {
  eyebrow?: string;
  title: ReactNode;
  intro?: ReactNode;
  center?: boolean;
}) {
  return (
    <div className={cn("mb-12 max-w-3xl space-y-4", center && "mx-auto text-center")}>
      {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
      <h2 className="text-3xl sm:text-4xl lg:text-5xl font-medium tracking-tighter text-white">{title}</h2>
      {intro && <p className={cn("text-lg text-zinc-400 leading-relaxed", center && "mx-auto")}>{intro}</p>}
    </div>
  );
}

export function Section({ children, className, id }: { children: ReactNode; className?: string; id?: string }) {
  return (
    <section id={id} className={cn("mx-auto max-w-7xl px-4 py-16 sm:px-6 md:py-24 lg:px-8", className)}>
      {children}
    </section>
  );
}

export function GlassCard({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-8 backdrop-blur-xl transition-colors hover:bg-white/[0.07]",
        className
      )}
    >
      {children}
    </div>
  );
}

const primaryBtn =
  "group inline-flex items-center justify-center gap-2 rounded-full bg-white px-8 py-4 text-sm font-semibold text-zinc-950 transition-all hover:scale-[1.02] hover:bg-zinc-200 active:scale-[0.98]";
const ghostBtn =
  "group inline-flex items-center justify-center gap-2 rounded-full border border-white/10 bg-white/5 px-8 py-4 text-sm font-semibold text-white backdrop-blur-sm transition-colors hover:bg-white/10 hover:border-white/20";

type ButtonLinkProps = { to: string; variant?: "primary" | "ghost"; className?: string; children: ReactNode };

export function ButtonLink({ to, variant = "primary", className, children }: ButtonLinkProps) {
  const cls = cn(variant === "primary" ? primaryBtn : ghostBtn, className);
  const external = to.startsWith("http") || to.startsWith("mailto:");
  const arrow = <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />;
  if (external) {
    return (
      <a href={to} className={cls} {...(to.startsWith("http") ? { target: "_blank", rel: "noopener" } : {})}>
        {children}
        {arrow}
      </a>
    );
  }
  return (
    <Link to={to} className={cls}>
      {children}
      {arrow}
    </Link>
  );
}

export function TextLink({ to, children, className }: { to: string; children: ReactNode; className?: string }) {
  return (
    <Link
      to={to}
      className={cn(
        "group inline-flex items-center gap-1.5 text-sm font-semibold text-white transition-colors hover:text-[#ffcd75]",
        className
      )}
    >
      {children}
      <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
    </Link>
  );
}

export function Pill({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[10px] font-medium tracking-wide text-zinc-300",
        className
      )}
    >
      {children}
    </div>
  );
}

export function IconBadge({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/20", className)}>
      {children}
    </div>
  );
}

export function Field(props: ComponentProps<"input">) {
  return (
    <input
      {...props}
      className={cn(
        "w-full rounded-2xl border border-white/10 bg-white/5 px-5 py-3.5 text-sm text-white placeholder:text-zinc-500 outline-none backdrop-blur-sm transition-colors focus:border-white/30 focus:bg-white/[0.08]",
        props.className
      )}
    />
  );
}

export function TextArea(props: ComponentProps<"textarea">) {
  return (
    <textarea
      {...props}
      className={cn(
        "w-full rounded-2xl border border-white/10 bg-white/5 px-5 py-3.5 text-sm text-white placeholder:text-zinc-500 outline-none backdrop-blur-sm transition-colors focus:border-white/30 focus:bg-white/[0.08]",
        props.className
      )}
    />
  );
}

export function Select({ className, children, ...props }: ComponentProps<"select">) {
  return (
    <select
      {...props}
      className={cn(
        "w-full appearance-none rounded-2xl border border-white/10 bg-white/5 px-5 py-3.5 text-sm text-white outline-none backdrop-blur-sm transition-colors focus:border-white/30 focus:bg-white/[0.08] [&>option]:bg-zinc-900",
        className
      )}
    >
      {children}
    </select>
  );
}
