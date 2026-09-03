"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

type CaseItem = {
  id: number;
  title: string;
  description: string;
  organization: string | null;
  amount: string | null;
  currency: string | null;
  status: string;
  created_at?: string;
  updated_at?: string;
};

import { API_URL } from "./lib/api";

function StatusDot({ status }: { status: string }) {
  const priority =
    status === "ACTION_READY" || status === "AWAITING_APPROVAL"
      ? "high"
      : status === "RESOLVED" || status === "CLOSED"
        ? "low"
        : "medium";

  return (
    <span
      className={`h-2 w-2 shrink-0 rounded-full ${
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

function formatDate(value?: string) {
  if (!value) return "";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "";

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function getCaseTimestamp(item: CaseItem) {
  const value = item.created_at ?? item.updated_at;

  if (!value) return 0;

  const time = new Date(value).getTime();

  return Number.isNaN(time) ? 0 : time;
}

function deriveTitle(input: string) {
  const clean = input.trim();

  if (!clean) return "New case";

  const firstLine = clean
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean);

  if (!firstLine) return "New case";

  if (firstLine.length <= 80) {
    return firstLine;
  }

  return `${firstLine.slice(0, 77)}...`;
}

export default function Home() {
  const router = useRouter();

  const [cases, setCases] = useState<CaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [isModalOpen, setIsModalOpen] = useState(false);

  const [problem, setProblem] = useState("");
  const [showDetails, setShowDetails] = useState(false);

  const [title, setTitle] = useState("");
  const [organization, setOrganization] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("");

  const [creating, setCreating] = useState(false);
  const [apiErrorMsg, setApiErrorMsg] = useState<string | null>(null);

  const [search, setSearch] = useState("");

  async function loadCases() {
    try {
      const response = await fetch(`${API_URL}/cases`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Failed to load cases");
      }

      const data = await response.json();

      setCases(Array.isArray(data.cases) ? data.cases : []);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;

    async function initializeCases() {
      try {
        const response = await fetch(`${API_URL}/cases`, {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error("Failed to load cases");
        }

        const data = await response.json();

        if (!active) return;

        setCases(Array.isArray(data.cases) ? data.cases : []);
        setError(false);
      } catch {
        if (!active) return;
        setError(true);
      } finally {
        if (!active) return;
        setLoading(false);
      }
    }

    void initializeCases();

    return () => {
      active = false;
    };
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setApiErrorMsg(null);

    const cleanProblem = problem.trim();

    if (!cleanProblem) {
      setApiErrorMsg(
        "Tell ONIT what happened. You can write it naturally."
      );
      return;
    }

    const finalTitle = title.trim() || deriveTitle(cleanProblem);

      const payload = {
      title: finalTitle,
      description: cleanProblem,
      organization: organization.trim() || null,
      amount: amount.trim() || null,
      // Do NOT default currency to JPY; respect user's input or leave null
      currency: currency.trim() || null,
    };

    setCreating(true);

    try {
      const response = await fetch(`${API_URL}/cases`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));

        throw new Error(
          typeof body.detail === "string"
            ? body.detail
            : "ONIT could not create this case."
        );
      }

      const data = await response.json();

      setProblem("");
      setTitle("");
      setOrganization("");
      setAmount("");
      setCurrency("");
      setShowDetails(false);
      setApiErrorMsg(null);
      setIsModalOpen(false);

      await loadCases();

      const createdCase = data?.case;

      if (createdCase?.id) {
        router.push(`/cases/${createdCase.id}`);
      }
    } catch (err: unknown) {
      setApiErrorMsg(
        err instanceof Error
          ? err.message
          : "Something went wrong while creating the case."
      );
    } finally {
      setCreating(false);
    }
  }

  const sortedCases = useMemo(() => {
    return [...cases].sort(
      (a, b) => getCaseTimestamp(b) - getCaseTimestamp(a)
    );
  }, [cases]);

  const actionCases = useMemo(() => {
    return sortedCases.filter(
      (item) =>
        item.status === "ACTION_READY" ||
        item.status === "AWAITING_APPROVAL"
    );
  }, [sortedCases]);

  const filteredCases = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return sortedCases;
    }

    return sortedCases.filter((item) => {
      const haystack = [
        item.title,
        item.description,
        item.organization,
        item.amount,
        item.currency,
        item.status,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(query);
    });
  }, [search, sortedCases]);

  const featuredCase = actionCases[0];

  const todayLabel = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  })
    .format(new Date())
    .toUpperCase();

  function openNewCase() {
    setApiErrorMsg(null);
    setIsModalOpen(true);
  }

  function closeNewCase() {
    if (creating) return;

    setIsModalOpen(false);
    setApiErrorMsg(null);
  }

  return (
    <main className="min-h-screen bg-[#f7f7f5] text-[#171717]">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-5 py-7 md:px-10 md:py-8">
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
              <p className="text-sm font-medium">Onit Workspace</p>
              <p className="text-xs text-[#8a8a86]">
                Personal workspace
              </p>
            </div>

           
          </div>
        </header>

        <section className="mt-16 flex flex-col gap-8 md:mt-20 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <p className="mb-3 text-xs font-semibold tracking-[0.16em] text-[#8a8a86]">
              {todayLabel}
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
          </div>

          <button
            type="button"
            onClick={openNewCase}
            className="flex shrink-0 items-center justify-center gap-2 rounded-full bg-[#171717] px-6 py-3.5 text-sm font-medium text-white shadow-sm transition hover:bg-[#30302d] md:mb-1"
          >
            <span className="text-lg leading-none">+</span>
            New case
          </button>
        </section>

        <section className="mt-12">
          <div className="mb-4 flex items-end justify-between gap-4">
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
              type="button"
              onClick={() =>
                router.push(`/cases/${featuredCase.id}`)
              }
              className="group w-full rounded-2xl border border-black/8 bg-white p-6 text-left shadow-[0_8px_30px_rgba(0,0,0,0.04)] transition hover:-translate-y-0.5 hover:shadow-[0_12px_40px_rgba(0,0,0,0.07)]"
            >
              <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <StatusDot status={featuredCase.status} />

                    <span className="text-xs font-medium uppercase tracking-[0.12em] text-[#8a8a86]">
                      {formatStatus(featuredCase.status)}
                    </span>
                  </div>

                  <h2 className="mt-3 text-2xl font-semibold tracking-tight">
                    {featuredCase.title}
                  </h2>

                  <p className="mt-2 max-w-xl text-sm leading-6 text-[#73736e]">
                    {featuredCase.description}
                  </p>

                  {featuredCase.organization && (
                    <p className="mt-3 text-xs text-[#8a8a86]">
                      {featuredCase.organization}
                      {featuredCase.amount
                        ? ` · ${featuredCase.amount}`
                        : ""}
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-3">
                  <span className="text-sm font-medium">
                    Review
                  </span>

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
                    : cases.length === 0
                      ? "Your workspace is ready. Create your first case to get started."
                      : "Give ONIT a problem to work on."}
              </p>

              {!loading && !error && cases.length === 0 && (
                <button
                  type="button"
                  onClick={openNewCase}
                  className="mt-5 rounded-full bg-[#171717] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#30302d]"
                >
                  + Create your first case
                </button>
              )}
            </div>
          )}
        </section>

        <section className="mt-14 flex-1">
          <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold tracking-[0.16em] text-[#8a8a86]">
                CASES
              </p>

              <p className="mt-1 text-sm text-[#73736e]">
                {cases.length}{" "}
                {cases.length === 1 ? "case" : "cases"} in your workspace
              </p>
            </div>

            <div className="relative w-full sm:w-72">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#a0a09b]">
                ⌕
              </span>

              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search cases..."
                className="w-full rounded-full border border-black/10 bg-white py-2.5 pl-9 pr-4 text-sm outline-none transition placeholder:text-[#a0a09b] focus:border-black/20 focus:ring-2 focus:ring-black/5"
              />
            </div>
          </div>

          <div className="overflow-hidden rounded-2xl border border-black/8 bg-white">
            {loading ? (
              <div className="px-5 py-10 text-sm text-[#8a8a86]">
                Loading cases...
              </div>
            ) : error ? (
              <div className="px-5 py-10">
                <p className="text-sm font-medium">
                  ONIT could not load your cases.
                </p>

                <p className="mt-2 text-sm text-[#8a8a86]">
                  Make sure the backend is running and try again.
                </p>

                <button
                  type="button"
                  onClick={() => {
                    setLoading(true);
                    void loadCases();
                  }}
                  className="mt-5 rounded-full bg-[#171717] px-4 py-2 text-sm font-medium text-white"
                >
                  Try again
                </button>
              </div>
                   ) : filteredCases.length === 0 ? (
              <div className="px-5 py-12 text-center">
                <p className="text-sm font-medium">
                  {search ? "No matching cases." : "No cases yet."}
                </p>

                <p className="mt-2 text-sm text-[#8a8a86]">
                  {search
                    ? "Try a different search."
                    : "Your workspace is ready. Create your first case to get started."}
                </p>

                {!search && (
                  <button
                    type="button"
                    onClick={openNewCase}
                    className="mt-5 rounded-full bg-[#171717] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#30302d]"
                  >
                    + Create your first case
                  </button>
                )}
              </div>
            ) : (
              filteredCases.map((item, index) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() =>
                    router.push(`/cases/${item.id}`)
                  }
                  className={`group flex w-full items-center justify-between gap-4 px-5 py-5 text-left transition hover:bg-[#fafaf8] ${
                    index !== filteredCases.length - 1
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

                      <p className="mt-1 truncate text-xs text-[#8a8a86]">
                        {item.organization ??
                          "Information still being understood"}
                        {item.amount
                          ? ` · ${item.amount}`
                          : ""}
                      </p>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-4">
                    <div className="hidden text-right sm:block">
                      <p className="text-xs text-[#73736e]">
                        {formatStatus(item.status)}
                      </p>

                      {item.created_at && (
                        <p className="mt-1 text-[11px] text-[#b0b0aa]">
                          {formatDate(item.created_at)}
                        </p>
                      )}
                    </div>

                    <span className="text-[#a0a09b] transition group-hover:translate-x-1 group-hover:text-[#171717]">
                      →
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </section>

        <footer className="mt-10 border-t border-black/6 py-6 text-xs text-[#a0a09b]">
          ONIT · Your problems, moving forward.
        </footer>
      </div>

      {isModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-[2px]"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeNewCase();
            }
          }}
        >
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl md:p-8">
            <div className="flex items-start justify-between gap-6">
              <div>
                <p className="text-xs font-semibold tracking-[0.16em] text-[#8a8a86]">
                  NEW CASE
                </p>

                <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                  Tell ONIT what happened.
                </h2>

                <p className="mt-2 max-w-lg text-sm leading-6 text-[#73736e]">
                  You do not need to structure the problem perfectly.
                  Give ONIT whatever information you have.
                </p>
              </div>

              <button
                type="button"
                onClick={closeNewCase}
                disabled={creating}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-black/10 text-[#73736e] transition hover:bg-[#f7f7f5]"
                aria-label="Close"
              >
                ×
              </button>
            </div>

            <form onSubmit={handleCreate} className="mt-7">
              <label className="mb-2 block text-sm font-medium">
                What do you need help with?
              </label>

              <textarea
                autoFocus
                value={problem}
                onChange={(event) => setProblem(event.target.value)}
                placeholder={`Example:

My flight from Tokyo to Delhi was cancelled by Example Airways. I paid ¥120,000 for the booking and haven't received a refund. My booking reference is ABC123. I want the full amount back.`}
                rows={8}
                className="w-full resize-y rounded-2xl border border-black/10 bg-[#fafaf8] px-4 py-4 text-sm leading-6 outline-none transition placeholder:text-[#aaa9a3] focus:border-black/20 focus:bg-white focus:ring-4 focus:ring-black/5"
              />

              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs text-[#a0a09b]">
                  Paste a message, describe an incident, or write the
                  problem in your own words.
                </p>

                <button
                  type="button"
                  onClick={() => setShowDetails((value) => !value)}
                  className="text-xs font-medium text-[#555550] underline underline-offset-4"
                >
                  {showDetails
                    ? "Hide optional details"
                    : "Add optional details"}
                </button>
              </div>

              {showDetails && (
                <div className="mt-5 rounded-2xl border border-black/8 bg-[#fafaf8] p-4">
                  <p className="mb-4 text-xs font-semibold tracking-[0.12em] text-[#8a8a86]">
                    OPTIONAL
                  </p>

                  <div className="space-y-4">
                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-[#6b6b66]">
                        Title
                      </label>

                      <input
                        value={title}
                        onChange={(event) =>
                          setTitle(event.target.value)
                        }
                        placeholder="Leave empty and ONIT will derive one"
                        className="w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-black/20"
                      />
                    </div>

                    <div>
                      <label className="mb-1.5 block text-xs font-medium text-[#6b6b66]">
                        Organization
                      </label>

                      <input
                        value={organization}
                        onChange={(event) =>
                          setOrganization(event.target.value)
                        }
                        placeholder="Airline, company, school, municipality..."
                        className="w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-black/20"
                      />
                    </div>

                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                      <div>
                        <label className="mb-1.5 block text-xs font-medium text-[#6b6b66]">
                          Amount
                        </label>

                        <input
                          value={amount}
                          onChange={(event) =>
                            setAmount(event.target.value)
                          }
                          placeholder="120000"
                          className="w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-black/20"
                        />
                      </div>

                      <div>
                        <label className="mb-1.5 block text-xs font-medium text-[#6b6b66]">
                          Currency
                        </label>

                        <input
                          value={currency}
                          onChange={(event) =>
                            setCurrency(event.target.value)
                          }
                          placeholder="JPY"
                          className="w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm outline-none focus:border-black/20"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {apiErrorMsg && (
                <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {apiErrorMsg}
                </div>
              )}

              <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={closeNewCase}
                  disabled={creating}
                  className="rounded-full px-5 py-3 text-sm font-medium text-[#555550] transition hover:bg-[#f7f7f5] disabled:opacity-50"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={creating || !problem.trim()}
                  className="rounded-full bg-[#171717] px-6 py-3 text-sm font-medium text-white transition hover:bg-[#30302d] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {creating ? "Creating case…" : "Create case →"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
