const cases = [
  {
    title: "Flight cancellation",
    organization: "ANA",
    amount: "¥120,000",
    status: "Action ready",
    time: "2m ago",
    priority: "high",
  },
  {
    title: "Insurance claim",
    organization: "Sompo",
    amount: "¥84,500",
    status: "Researching",
    time: "18m ago",
    priority: "medium",
  },
  {
    title: "Hotel refund",
    organization: "Booking",
    amount: "¥32,000",
    status: "Resolved",
    time: "Yesterday",
    priority: "low",
  },
];

function StatusDot({ priority }: { priority: string }) {
  return (
    <span
      className={`h-2 w-2 rounded-full ${
        priority === "high"
          ? "bg-amber-500"
          : priority === "medium"
            ? "bg-blue-500"
            : "bg-emerald-500"
      }`}
    />
  );
}

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f7f7f5] text-[#171717]">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-8 md:px-10">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#171717] text-sm font-semibold text-white">
              O
            </div>

            <span className="text-lg font-semibold tracking-tight">
              ONIT
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium">Tanishka</p>
              <p className="text-xs text-[#8a8a86]">
                Personal workspace
              </p>
            </div>

            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-black/10 bg-white text-sm font-medium">
              T
            </div>
          </div>
        </header>

        {/* Hero */}
        <section className="mt-20 max-w-2xl">
          <p className="mb-3 text-sm font-medium tracking-wide text-[#8a8a86]">
            SUNDAY, AUGUST 23
          </p>

          <h1 className="text-4xl font-semibold tracking-[-0.04em] md:text-5xl">
            Your cases,
            <br />
            moving forward.
          </h1>

          <p className="mt-5 max-w-xl text-base leading-7 text-[#73736e]">
            ONIT handles the work between a problem and its resolution.
            You step in when a decision matters.
          </p>
        </section>

        {/* Action required */}
        <section className="mt-12">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold tracking-[0.16em] text-[#8a8a86]">
                ACTION REQUIRED
              </p>

              <p className="mt-1 text-sm text-[#73736e]">
                ONIT prepared something for you.
              </p>
            </div>

            <span className="rounded-full bg-[#171717] px-3 py-1.5 text-xs font-medium text-white">
              1 case
            </span>
          </div>

          <button className="group w-full rounded-2xl border border-black/8 bg-white p-6 text-left shadow-[0_8px_30px_rgba(0,0,0,0.04)] transition hover:-translate-y-0.5 hover:shadow-[0_12px_40px_rgba(0,0,0,0.07)]">
            <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
              <div>
                <div className="flex items-center gap-2">
                  <StatusDot priority="high" />

                  <span className="text-xs font-medium uppercase tracking-[0.12em] text-[#8a8a86]">
                    Flight cancellation
                  </span>
                </div>

                <h2 className="mt-3 text-2xl font-semibold tracking-tight">
                  Refund ¥120,000 from ANA
                </h2>

                <p className="mt-2 max-w-xl text-sm leading-6 text-[#73736e]">
                  The cancellation evidence has been analyzed and the
                  refund request is ready for your approval.
                </p>
              </div>

              <div className="flex shrink-0 items-center gap-3">
                <span className="text-sm font-medium">Review</span>

                <span className="flex h-9 w-9 items-center justify-center rounded-full border border-black/10 transition group-hover:bg-[#171717] group-hover:text-white">
                  →
                </span>
              </div>
            </div>
          </button>
        </section>

        {/* Recent cases */}
        <section className="mt-14 flex-1">
          <div className="mb-4">
            <p className="text-xs font-semibold tracking-[0.16em] text-[#8a8a86]">
              RECENT CASES
            </p>
          </div>

          <div className="overflow-hidden rounded-2xl border border-black/8 bg-white">
            {cases.map((item, index) => (
              <button
                key={item.title}
                className={`group flex w-full items-center justify-between gap-4 px-5 py-5 text-left transition hover:bg-[#fafaf8] ${
                  index !== cases.length - 1
                    ? "border-b border-black/6"
                    : ""
                }`}
              >
                <div className="flex min-w-0 items-center gap-4">
                  <StatusDot priority={item.priority} />

                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {item.title}
                    </p>

                    <p className="mt-1 text-xs text-[#8a8a86]">
                      {item.organization} · {item.amount}
                    </p>
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-5">
                  <span className="hidden text-xs text-[#73736e] sm:block">
                    {item.status}
                  </span>

                  <span className="text-xs text-[#a0a09b]">
                    {item.time}
                  </span>

                  <span className="text-[#a0a09b] transition group-hover:translate-x-1 group-hover:text-[#171717]">
                    →
                  </span>
                </div>
              </button>
            ))}
          </div>
        </section>

        {/* New case */}
        <div className="mt-8 flex justify-end">
          <button className="flex items-center gap-2 rounded-full bg-[#171717] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#30302d]">
            <span className="text-lg leading-none">+</span>
            New case
          </button>
        </div>

        {/* Footer */}
        <footer className="mt-10 border-t border-black/6 py-6 text-xs text-[#a0a09b]">
          ONIT · Your problems, moving forward.
        </footer>
      </div>
    </main>
  );
}