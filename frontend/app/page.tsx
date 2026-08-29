"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type CaseItem = {
  id: number;
  title: string;
  description: string;
  organization: string | null;
  amount: string | null;
  currency: string | null;
  status: string;
};

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

function StatusDot({ status }: { status: string }) {
  const priority =
    status === "ACTION_READY" || status === "AWAITING_APPROVAL"
      ? "high"
      : status === "RESOLVED" || status === "CLOSED"
        ? "low"
        : "medium";

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

function formatStatus(status: string) {
  return status
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function Home() {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const router = useRouter();

  // New case modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [organization, setOrganization] = useState<string | null>(null);
  const [amount, setAmount] = useState<string | null>(null);
  const [currency, setCurrency] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [apiErrorMsg, setApiErrorMsg] = useState<string | null>(null);

  // The API call is intentionally performed in an effect because it
  // synchronizes this client component with the ONIT case engine.
  // React 19's lint rule flags the resulting state updates.
  useEffect(() => {
    async function loadCases() {
      try {
        const response = await fetch(`${API_URL}/cases`);

        if (!response.ok) {
          throw new Error("Failed to load cases");
        }

        const data = await response.json();

        setCases(data.cases ?? []);
        setError(false);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }

    loadCases();
  }, []);

  async function refreshCases() {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/cases`);
      const d = await res.json();
      setCases(d.cases ?? []);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();

    setApiErrorMsg(null);

    if (!title.trim() || !description.trim()) {
      setApiErrorMsg("Title and description are required.");
      return;
    }

    const payload = {
      title: title.trim(),
      description: description.trim(),
      organization: organization?.trim() || null,
      amount: amount?.trim() || null,
      currency: amount && !currency ? "JPY" : currency || null,
    };

    setCreating(true);

    try {
      const res = await fetch(`${API_URL}/cases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Failed to create case");
      }

      // created successfully
      setIsModalOpen(false);
      setTitle("");
      setDescription("");
      setOrganization(null);
      setAmount(null);
      setCurrency(null);

      await refreshCases();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setApiErrorMsg(msg);
    } finally {
      setCreating(false);
    }
  }

  const actionCases = cases.filter(
    (item) =>
      item.status === "ACTION_READY" ||
      item.status === "AWAITING_APPROVAL",
  );

  const featuredCase = actionCases[0];

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
                {featuredCase
                  ? "ONIT prepared something for you."
                  : "Nothing needs your attention right now."}
              </p>
            </div>

            <span className="rounded-full bg-[#171717] px-3 py-1.5 text-xs font-medium text-white">
              {actionCases.length}{" "}
              {actionCases.length === 1 ? "case" : "cases"}
            </span>
          </div>

          {featuredCase ? (
            <button
              onClick={() => router.push(`/cases/${featuredCase.id}`)}
              className="group w-full rounded-2xl border border-black/8 bg-white p-6 text-left shadow-[0_8px_30px_rgba(0,0,0,0.04)] transition hover:-translate-y-0.5 hover:shadow-[0_12px_40px_rgba(0,0,0,0.07)]"
            >
              <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
                <div>
                  <div className="flex items-center gap-2">
                    <StatusDot status={featuredCase.status} />

                    <span className="text-xs font-medium uppercase tracking-[0.12em] text-[#8a8a86]">
                      {featuredCase.title}
                    </span>
                  </div>

                  <h2 className="mt-3 text-2xl font-semibold tracking-tight">
                    {featuredCase.amount
                      ? `${featuredCase.amount} from ${
                          featuredCase.organization ?? "the organization"
                        }`
                      : featuredCase.title}
                  </h2>

                  <p className="mt-2 max-w-xl text-sm leading-6 text-[#73736e]">
                    {featuredCase.description}
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
          ) : (
            <div className="rounded-2xl border border-black/8 bg-white p-8 text-center shadow-[0_8px_30px_rgba(0,0,0,0.03)]">
              <p className="text-sm font-medium">
                {loading
                  ? "Checking your cases..."
                  : error
                    ? "ONIT couldn't reach the case engine."
                    : "No cases need your attention yet."}
              </p>

              <p className="mt-2 text-sm text-[#8a8a86]">
                {loading
                  ? "ONIT is connecting to your workspace."
                  : error
                    ? "Make sure the ONIT backend is running."
                    : "Give ONIT a problem to work on."}
              </p>
            </div>
          )}
        </section>

        {/* Recent cases */}
        <section className="mt-14 flex-1">
          <div className="mb-4">
            <p className="text-xs font-semibold tracking-[0.16em] text-[#8a8a86]">
              RECENT CASES
            </p>
          </div>

          <div className="overflow-hidden rounded-2xl border border-black/8 bg-white">
            {loading ? (
              <div className="px-5 py-8 text-sm text-[#8a8a86]">
                Loading cases...
              </div>
            ) : cases.length === 0 ? (
              <div className="px-5 py-8 text-sm text-[#8a8a86]">
                No cases yet.
              </div>
            ) : (
              cases.map((item, index) => (
                <button
                  key={item.id}
                  onClick={() => router.push(`/cases/${item.id}`)}
                  className={`group flex w-full items-center justify-between gap-4 px-5 py-5 text-left transition hover:bg-[#fafaf8] ${
                    index !== cases.length - 1
                      ? "border-b border-black/6"
                      : ""
                  }`}
                >
                  <div className="flex min-w-0 items-center gap-4">
                    <StatusDot status={item.status} />

                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {item.title}
                      </p>

                      <p className="mt-1 text-xs text-[#8a8a86]">
                        {item.organization ?? "Unknown organization"}
                        {item.amount ? ` · ${item.amount}` : ""}
                      </p>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-5">
                    <span className="hidden text-xs text-[#73736e] sm:block">
                      {formatStatus(item.status)}
                    </span>

                    <span className="text-[#a0a09b] transition group-hover:translate-x-1 group-hover:text-[#171717]">
                      →
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </section>

        {/* New case */}
        <div className="mt-8 flex justify-end">
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 rounded-full bg-[#171717] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#30302d]"
          >
            <span className="text-lg leading-none">+</span>
            New case
          </button>
        </div>

        {/* Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
            <div className="mx-4 w-full max-w-xl rounded-xl bg-white p-6">
              <h3 className="text-lg font-semibold">Create new case</h3>

              <form onSubmit={handleCreate} className="mt-4 space-y-4">
                <div>
                  <label className="mb-1 block text-xs font-medium text-[#6b6b66]">Title</label>
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                    className="w-full rounded-md border px-3 py-2 text-sm"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-[#6b6b66]">Description</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    required
                    rows={4}
                    className="w-full rounded-md border px-3 py-2 text-sm"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-[#6b6b66]">Organization</label>
                    <input
                      value={organization ?? ""}
                      onChange={(e) => setOrganization(e.target.value || null)}
                      className="w-full rounded-md border px-3 py-2 text-sm"
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-[#6b6b66]">Amount</label>
                    <input
                      value={amount ?? ""}
                      onChange={(e) => setAmount(e.target.value || null)}
                      className="w-full rounded-md border px-3 py-2 text-sm"
                    />
                  </div>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-[#6b6b66]">Currency</label>
                  <input
                    value={currency ?? ""}
                    onChange={(e) => setCurrency(e.target.value || null)}
                    placeholder={amount ? "JPY" : undefined}
                    className="w-40 rounded-md border px-3 py-2 text-sm"
                  />
                </div>

                {apiErrorMsg && (
                  <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                    {apiErrorMsg}
                  </div>
                )}

                <div className="mt-2 flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="rounded-md px-4 py-2 text-sm"
                    disabled={creating}
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className="rounded-md bg-[#171717] px-4 py-2 text-sm font-medium text-white"
                    disabled={creating}
                  >
                    {creating ? "Creating…" : "Create case"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-10 border-t border-black/6 py-6 text-xs text-[#a0a09b]">
          ONIT · Your problems, moving forward.
        </footer>
      </div>
    </main>
  );
}