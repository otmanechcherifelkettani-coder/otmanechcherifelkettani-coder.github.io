import HeroSection from '@/components/ui/glassmorphism-trust-hero';

function Header() {
  return (
    <header className="absolute top-0 left-0 right-0 z-20">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5 sm:px-6 lg:px-8">
        <a href="/cadence/" className="text-lg font-semibold tracking-tight text-white">
          Cadence
        </a>
        <nav className="flex items-center gap-2 sm:gap-6 text-sm text-zinc-400" aria-label="Primary">
          <a className="hidden sm:inline transition-colors hover:text-white" href="/cadence/work.html">Work</a>
          <a className="hidden sm:inline transition-colors hover:text-white" href="/cadence/about.html">About</a>
          <a
            href="mailto:otmankettani5@gmail.com"
            className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold text-white backdrop-blur-md transition-colors hover:bg-white/10 hover:border-white/20"
          >
            Email me
          </a>
        </nav>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <div className="relative w-full h-screen overflow-y-auto bg-zinc-950">
      <Header />
      <HeroSection />
    </div>
  );
}
