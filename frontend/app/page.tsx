
import Link from "next/link";

const steps = [
  {
    number: "01",
    title: "Document",
    description:
      "Record what happened and securely submit the digital evidence you already have.",
  },
  {
    number: "02",
    title: "Preserve",
    description:
      "Create a fingerprint of each uploaded file so later changes can be checked.",
  },
  {
    number: "03",
    title: "Review",
    description:
      "Examine evidence, integrity records and AI-assisted leads with human oversight.",
  },
];

export default function Home() {
  return (
    <main className="mt-8">
      {/* Hero */}
      <section className="home-hero relative isolate flex min-h-[570px] flex-col items-center justify-center overflow-hidden px-5 py-20 text-center sm:min-h-[620px] sm:px-10">

        {/* Faded digital fingerprint background */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-24 top-1/2 z-[-1] w-[390px] -translate-y-1/2 opacity-[0.11] sm:-right-16 sm:w-[490px] md:right-[-35px] md:w-[540px]"
        >
          <svg
            viewBox="0 0 500 500"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="h-auto w-full"
          >
            <g
              stroke="#c79925"
              strokeWidth="2.2"
              strokeLinecap="round"
            >
              <path d="M250 45 C135 45 55 132 55 245 C55 300 75 350 105 390" />
              <path d="M250 75 C153 75 83 148 83 245 C83 292 98 330 125 367" />
              <path d="M250 105 C172 105 111 164 111 245 C111 285 124 319 148 348" />
              <path d="M250 135 C190 135 139 181 139 245 C139 279 151 307 171 330" />
              <path d="M250 165 C207 165 167 198 167 245 C167 272 178 296 195 315" />
              <path d="M250 195 C224 195 195 215 195 245 C195 265 204 283 219 298" />
              <path d="M250 225 C240 225 223 233 223 245 C223 260 233 272 250 282" />
              <path d="M250 45 C365 45 445 132 445 245 C445 300 425 350 395 390" />
              <path d="M250 75 C347 75 417 148 417 245 C417 292 402 330 375 367" />
              <path d="M250 105 C328 105 389 164 389 245 C389 285 376 319 352 348" />
              <path d="M250 135 C310 135 361 181 361 245 C361 279 349 307 329 330" />
              <path d="M250 165 C293 165 333 198 333 245 C333 272 322 296 305 315" />
              <path d="M250 195 C276 195 305 215 305 245 C305 265 296 283 281 298" />
              <path d="M250 255 C250 300 280 322 315 337" />
              <path d="M250 282 C250 335 287 365 337 383" />
              <path d="M250 310 C250 368 300 405 350 420" />
              <path d="M250 340 C250 397 300 433 365 450" />
              <path d="M250 255 C250 300 220 322 185 337" />
              <path d="M250 282 C250 335 213 365 163 383" />
              <path d="M250 310 C250 368 200 405 150 420" />
              <path d="M250 340 C250 397 200 433 135 450" />
            </g>

            {/* Connected digital nodes */}
            <g fill="#B28A22">
              <circle cx="55" cy="245" r="5" />
              <circle cx="445" cy="245" r="5" />
              <circle cx="105" cy="390" r="4" />
              <circle cx="395" cy="390" r="4" />
              <circle cx="250" cy="45" r="5" />
              <circle cx="250" cy="450" r="4" />
              <circle cx="83" cy="148" r="3" />
              <circle cx="417" cy="148" r="3" />
              <circle cx="139" cy="330" r="3" />
              <circle cx="361" cy="330" r="3" />
            </g>

            <g
              stroke="#B28A22"
              strokeWidth="1"
              opacity="0.65"
            >
              <path d="M55 245 L15 215 L35 165" />
              <path d="M445 245 L485 215 L465 165" />
              <path d="M105 390 L65 430 L95 465" />
              <path d="M395 390 L435 430 L405 465" />
            </g>
          </svg>
        </div>

        {/* Soft background wash */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_78%_45%,rgba(178,138,34,0.045),transparent_42%)]"
        />

        <p className="home-reveal home-delay-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-[#AD841E] sm:text-xs">
          Digital evidence preservation platform
        </p>

        <h1 className="home-reveal home-delay-2 mt-8 max-w-5xl text-4xl font-semibold leading-[1.12] tracking-[-0.045em] text-[#242424] sm:text-6xl md:text-7xl">
          Preserve Evidence.
          <br />
          <span className="text-[#B28A22]">
            Establish Integrity.
          </span>
          <br />
          Connect the Dots.
        </h1>

        <p className="home-reveal home-delay-3 mt-8 max-w-2xl text-sm leading-7 text-[#77736D] sm:text-base sm:leading-8">
          DigitalWitness provides a structured platform to preserve digital
          evidence, verify its integrity and discover potential connections
          across investigations.
        </p>

        <div className="home-reveal home-delay-4 mt-9 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/login"
            className="inline-flex items-center border border-[#B28A22] bg-[#B28A22] px-7 py-3 text-sm font-medium text-white transition duration-300 hover:bg-[#96721B]"
          >
            Get started <span className="ml-5">→</span>
          </Link>

          <Link
            href="/login"
            className="inline-flex items-center border border-[#D8D3C9] px-7 py-3 text-sm font-medium text-[#292929] transition duration-300 hover:border-[#292929]"
          >
            Sign in
          </Link>
        </div>

        <div className="home-reveal home-delay-4 mt-16 flex flex-col items-center gap-3">
          <div className="flex items-center gap-3 text-[10px] uppercase tracking-[0.18em] text-[#99938A]">
            <span className="h-px w-8 bg-[#C9B989]" />
            Preserve · Review · Prepare
            <span className="h-px w-8 bg-[#C9B989]" />
          </div>

          {/* New brand tagline */}
          <p className="max-w-xl text-xs font-medium tracking-wide text-[#8D877D] sm:text-sm">
            Preserving Digital Truth. Protecting Evidence Integrity.
          </p>
        </div>
      </section>

      {/* Purpose */}
      <section
        id="about"
        className="grid gap-8 border-t border-line py-14 md:grid-cols-[1fr_1.2fr] md:gap-16"
      >
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted">
            Why DigitalWitness
          </p>
          <h2 className="mt-4 max-w-md text-2xl font-semibold leading-tight tracking-tight text-ink sm:text-3xl">
            Evidence deserves more than a screenshot folder.
          </h2>
        </div>

        <div>
          <p className="text-sm leading-7 text-muted">
            Digital incidents can leave people with scattered screenshots,
            messages, recordings and documents. DigitalWitness helps organise
            that material, preserve file fingerprints and make the review
            process more structured.
          </p>
          <p className="mt-4 text-sm leading-7 text-muted">
            The platform supports documentation and review. It does not
            determine guilt, guarantee authenticity or replace official
            reporting channels.
          </p>
        </div>
      </section>

      {/* Process */}
      <section id="how-it-works" className="border-t border-line py-14">
        <div className="mb-8">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted">
            The process
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-ink">
            From documentation to review.
          </h2>
        </div>

        <div className="grid border-l border-t border-line sm:grid-cols-3">
          {steps.map((step) => (
            <article
              key={step.number}
              className="border-b border-r border-line p-6 sm:p-7"
            >
              <p className="text-xs font-semibold tracking-widest text-[#AD841E]">
                {step.number}
              </p>
              <h3 className="mt-8 text-lg font-semibold text-ink">
                {step.title}
              </h3>
              <p className="mt-3 text-sm leading-6 text-muted">
                {step.description}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* Trust */}
      <section className="border-t border-line py-14">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted">
          Important to understand
        </p>

        <div className="mt-6 grid gap-8 sm:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold text-ink">
              Integrity is not authenticity
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted">
              A successful integrity check means a file matches its recorded
              fingerprint. It does not prove that the original content was
              true or genuine.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-ink">
              AI supports human review
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted">
              Automated analysis can surface possible leads, but its output
              may be incomplete or incorrect. Reviewers must examine the
              original context.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="flex flex-col justify-between gap-6 border-t border-line py-10 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-semibold text-ink">
            Ready to document your evidence?
          </h2>
          <p className="mt-2 text-sm text-muted">
            Start with the material you already have.
          </p>
        </div>

        <Link
          href="/login"
          className="inline-flex w-fit items-center bg-ink px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
        >
          Continue to DigitalWitness
          <span className="ml-5">→</span>
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-line py-5 text-xs text-muted">
        DigitalWitness · Evidence documentation and review
      </footer>
    </main>
  );
}
