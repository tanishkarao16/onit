"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type CaseData = {
  id: number;
  title: string;
  description: string;
  organization: string | null;
  amount: string | null;
  currency: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  issue?: string | null;
  recommended_action?: string | null;
  priority?: string | null;
  decision_reason?: string | null;
};

type Activity = {
  id: number;
  event_type: string;
  message: string;
  created_at: string;
};

const API_URL = "http://127.0.0.1:8000";

function formatStatus(status: string) {
  return status
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDate(value: string) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function StatusPill({ status }: { status: string }) {
  const tone =
    status === "ACTION_READY" || status === "AWAITING_APPROVAL"
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : status === "RESOLVED" || status === "CLOSED"
        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
        : "bg-blue-50 text-blue-700 border-blue-200";

  return (
    <span
      className={`rounded-full border px-3 py-1.5 text-xs font-medium ${tone}`}
    >
      {formatStatus(status)}
    </span>
  );
}

export default function CasePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [caseData, setCaseData] = useState<CaseData | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadCase() {
      try {
        const { id } = await params;

        const [caseResponse, activityResponse] = await Promise.all([
          fetch(`${API_URL}/cases/${id}`),
          fetch(`${API_URL}/cases/${id}/activity`),
        ]);

        if (!caseResponse.ok) {
          throw new Error("Case not found");
        }

        const caseJson = await caseResponse.json();
        const activityJson = activityResponse.ok
          ? await activityResponse.json()
          : { activities: [] };

        if (!cancelled) {
          setCaseData(caseJson.case ?? null);
          setActivities(activityJson.activities ?? []);
        }
      } catch {
        if (!cancelled) {
          setError(true);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadCase();

    return () => {
      cancelled = true;
    };
  }, [params]);

  async function runAnalysis() {
    if (!caseData) return;

    setActionLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/cases/${caseData.id}/analyze`,
        {
          method: "POST",
        },
      );

      if (!response.ok) {
        throw new Error("Analysis failed");
      }

      const data = await response.json();

      setCaseData((current) =>
        current
          ? {
              ...current,
              status: data.case.status,
              issue: data.case.issue,
              recommended_action: data.case.recommended_action,
              priority: data.case.priority,
              decision_reason: data.case.decision_reason,
            }
          : current,
      );

      const activityResponse = await fetch(
        `${API_URL}/cases/${caseData.id}/activity`,
      );

      if (activityResponse.ok) {
        const activityData = await activityResponse.json();
        setActivities(activityData.activities ?? []);
      }
    } catch {
      window.alert("ONIT could not analyze this case.");
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-[#f7f7f5] px-6 py-8 text-[#171717]">
        <div className="mx-auto max-w-5xl">
          <Link
            href="/"
            className="text-sm text-[#73736e] hover:text-[#171717]"
          >
            ← Back to cases
          </Link>

          <div className="mt-16 rounded-2xl border border-black/8 bg-white p-8">
            <p className="text-sm text-[#73736e]">Loading case...</p>
          </div>
        </div>
      </main>
    );
  }

  if (error || !caseData) {
    return (
      <main className="min-h-screen bg-[#f7f7f5] px-6 py-8 text-[#171717]">
        <div className="mx-auto max-w-5xl">
          <Link
            href="/"
            className="text-sm text-[#73736e] hover:text-[#171717]"
          >
            ← Back to cases
          </Link>

          <div className="mt-16 rounded-2xl border border-black/8 bg-white p-8">
            <h1 className="text-xl font-semibold">
              Case could not be loaded.
            </h1>

            <p className="mt-2 text-sm text-[#73736e]">
              Make sure the ONIT backend is running and the case still exists.
            </p>
          </div>
        </div>
      </main>
    );
  }

  const canAnalyze =
    caseData.status === "CREATED" ||
    caseData.status === "EVIDENCE_READY";

  return (
    <main className="min-h-screen bg-[#f7f7f5] text-[#171717]">
      <div className="mx-auto min-h-screen w-full max-w-5xl px-6 py-8 md:px-10">
        <header className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#171717] text-sm font-semibold text-white">
              O
            </div>

            <span className="text-lg font-semibold tracking-tight">
              ONIT
            </span>
          </Link>

          <div className="flex h-9 w-9 items-center justify-center rounded-full border border-black/10 bg-white text-sm font-medium">
            T
          </div>
        </header>

        <div className="mt-12">
          <Link
            href="/"
            className="text-sm text-[#73736e] transition hover:text-[#171717]"
          >
            ← All cases
          </Link>
        </div>

        <section className="mt-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#8a8a86]">
                Case #{caseData.id}
              </p>

              <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] md:text-5xl">
                {caseData.title}
              </h1>

              <p className="mt-4 max-w-2xl text-base leading-7 text-[#73736e]">
                {caseData.description}
              </p>
            </div>

            <StatusPill status={caseData.status} />
          </div>
        </section>

        <section className="mt-10 grid gap-5 md:grid-cols-3">
          <div className="rounded-2xl border border-black/8 bg-white p-5">
            <p className="text-xs uppercase tracking-[0.14em] text-[#a0a09b]">
              Organization
            </p>

            <p className="mt-2 text-sm font-medium">
              {caseData.organization ?? "Not specified"}
            </p>
          </div>

          <div className="rounded-2xl border border-black/8 bg-white p-5">
            <p className="text-xs uppercase tracking-[0.14em] text-[#a0a09b]">
              Amount
            </p>

            <p className="mt-2 text-sm font-medium">
              {caseData.amount
                ? `${caseData.currency ?? ""}${caseData.amount}`
                : "Not specified"}
            </p>
          </div>

          <div className="rounded-2xl border border-black/8 bg-white p-5">
            <p className="text-xs uppercase tracking-[0.14em] text-[#a0a09b]">
              Created
            </p>

            <p className="mt-2 text-sm font-medium">
              {formatDate(caseData.created_at)}
            </p>
          </div>
        </section>

        <section className="mt-10 rounded-2xl border border-black/8 bg-white p-6 shadow-[0_8px_30px_rgba(0,0,0,0.03)] md:p-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#8a8a86]">
                ONIT decision engine
              </p>

              <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                Move this case forward.
              </h2>

              <p className="mt-2 max-w-xl text-sm leading-6 text-[#73736e]">
                ONIT analyzes the available case information and turns it
                into a concrete next action.
              </p>
            </div>

            {canAnalyze && (
              <button
                type="button"
                onClick={runAnalysis}
                disabled={actionLoading}
                className="rounded-full bg-[#171717] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#30302d] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {actionLoading ? "Analyzing..." : "Analyze case →"}
              </button>
            )}
          </div>

          {caseData.issue || caseData.recommended_action ? (
            <div className="mt-8 grid gap-5 border-t border-black/6 pt-7 md:grid-cols-2">
              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-[#a0a09b]">
                  Identified issue
                </p>

                <p className="mt-2 text-sm leading-6">
                  {caseData.issue ?? "No issue identified yet."}
                </p>
              </div>

              <div>
                <p className="text-xs uppercase tracking-[0.14em] text-[#a0a09b]">
                  Recommended action
                </p>

                <p className="mt-2 text-sm font-medium leading-6">
                  {caseData.recommended_action ??
                    "No recommendation available yet."}
                </p>
              </div>

              {caseData.decision_reason && (
                <div className="md:col-span-2">
                  <p className="text-xs uppercase tracking-[0.14em] text-[#a0a09b]">
                    Why ONIT recommends this
                  </p>

                  <p className="mt-2 text-sm leading-6 text-[#73736e]">
                    {caseData.decision_reason}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="mt-8 border-t border-black/6 pt-7">
              <p className="text-sm text-[#8a8a86]">
                No decision has been generated yet.
              </p>
            </div>
          )}
        </section>

        <section className="mt-10">
          <div className="mb-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#8a8a86]">
              CASE TIMELINE
            </p>
          </div>

          <div className="rounded-2xl border border-black/8 bg-white">
            {activities.length === 0 ? (
              <div className="p-6 text-sm text-[#8a8a86]">
                No activity recorded yet.
              </div>
            ) : (
              activities.map((activity, index) => (
                <div
                  key={activity.id}
                  className={`flex gap-4 p-6 ${
                    index !== activities.length - 1
                      ? "border-b border-black/6"
                      : ""
                  }`}
                >
                  <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-[#171717]" />

                  <div className="min-w-0">
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
                      <p className="text-sm font-medium">
                        {formatStatus(activity.event_type)}
                      </p>

                      <p className="text-xs text-[#a0a09b]">
                        {formatDate(activity.created_at)}
                      </p>
                    </div>

                    <p className="mt-1 text-sm leading-6 text-[#73736e]">
                      {activity.message}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <footer className="mt-12 border-t border-black/6 py-6 text-xs text-[#a0a09b]">
          ONIT · Your problems, moving forward.
        </footer>
      </div>
    </main>
  );
}
