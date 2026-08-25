"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

type CaseItem = {
  id: number;
  title: string;
  description: string;
  passenger: string | null;
  booking_reference: string | null;
  organization: string | null;
  airline: string | null;
  cancellation_date: string | null;
  amount: string | null;
  currency: string | null;
  refund_received: boolean | null;
  requested_resolution: string | null;
  supporting_facts: string | null;
  issue: string | null;
  recommended_action: string | null;
  priority: string | null;
  decision_reason: string | null;
  plan_summary: string | null;
  plan_steps: string | null;
  approval_required: boolean;
  status: string;
  created_at: string;
  updated_at: string;
};

type ActivityItem = {
  id: number;
  event_type: string;
  message: string;
  created_at: string;
};

type ResearchItem = {
  id: number;
  source: string;
  title: string;
  summary: string;
  relevance: string;
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
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function StatusPill({ status }: { status: string }) {
  const isReady =
    status === "ACTION_READY" ||
    status === "AWAITING_APPROVAL";

  const isResolved =
    status === "RESOLVED" ||
    status === "CLOSED";

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ${
        isReady
          ? "bg-amber-50 text-amber-700"
          : isResolved
            ? "bg-emerald-50 text-emerald-700"
            : "bg-zinc-100 text-zinc-600"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          isReady
            ? "bg-amber-500"
            : isResolved
              ? "bg-emerald-500"
              : "bg-zinc-400"
        }`}
      />

      {formatStatus(status)}
    </span>
  );
}

function SectionLabel({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <p className="text-xs font-semibold tracking-[0.16em] text-[#8a8a86]">
      {children}
    </p>
  );
}

export default function CasePage() {
  const params = useParams();
  const caseId = params.id;

  const [caseItem, setCaseItem] = useState<CaseItem | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [research, setResearch] = useState<ResearchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function fetchCase() {
      if (!caseId) {
        return;
      }

      try {
        const [
          caseResponse,
          activityResponse,
          researchResponse,
        ] = await Promise.all([
          fetch(`${API_URL}/cases/${caseId}`),
          fetch(`${API_URL}/cases/${caseId}/activity`),
          fetch(`${API_URL}/cases/${caseId}/research`),
        ]);

        if (!caseResponse.ok) {
          throw new Error("Case not found.");
        }

        const caseData = await caseResponse.json();
        const activityData = await activityResponse.json();
        const researchData = await researchResponse.json();

        if (cancelled) {
          return;
        }

        setCaseItem(caseData.case);
        setActivities(activityData.activities ?? []);
        setResearch(researchData.research ?? []);
        setError("");
        setLoading(false);
      } catch (err) {
        if (cancelled) {
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load this case.",
        );
        setLoading(false);
      }
    }

    fetchCase();

    return () => {
      cancelled = true;
    };
  }, [caseId]);

  async function refreshCase() {
    if (!caseId) {
      return;
    }

    try {
      const [
        caseResponse,
        activityResponse,
        researchResponse,
      ] = await Promise.all([
        fetch(`${API_URL}/cases/${caseId}`),
        fetch(`${API_URL}/cases/${caseId}/activity`),
        fetch(`${API_URL}/cases/${caseId}/research`),
      ]);

      if (!caseResponse.ok) {
        throw new Error("Case not found.");
      }

      const caseData = await caseResponse.json();
      const activityData = await activityResponse.json();
      const researchData = await researchResponse.json();

      setCaseItem(caseData.case);
      setActivities(activityData.activities ?? []);
      setResearch(researchData.research ?? []);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to refresh this case.",
      );
    }
  }

  async function requestApproval() {
    if (!caseItem) {
      return;
    }

    try {
      setActionLoading(true);
      setError("");

      const response = await fetch(
        `${API_URL}/cases/${caseItem.id}/request-approval`,
        {
          method: "POST",
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ?? "Unable to request approval.",
        );
      }

      await refreshCase();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to request approval.",
      );
    } finally {
      setActionLoading(false);
    }
  }

  async function runResearch() {
    if (!caseItem) {
      return;
    }

    try {
      setActionLoading(true);
      setError("");

      const response = await fetch(
        `${API_URL}/cases/${caseItem.id}/research`,
        {
          method: "POST",
        },
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ?? "Unable to research this case.",
        );
      }

      await refreshCase();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to research this case.",
      );
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
            className="text-sm text-[#73736e] transition hover:text-[#171717]"
          >
            ← Back to cases
          </Link>

          <div className="mt-20">
            <p className="text-sm text-[#8a8a86]">
              Loading case...
            </p>
          </div>
        </div>
      </main>
    );
  }

  if (error && !caseItem) {
    return (
      <main className="min-h-screen bg-[#f7f7f5] px-6 py-8 text-[#171717]">
        <div className="mx-auto max-w-5xl">
          <Link
            href="/"
            className="text-sm text-[#73736e] transition hover:text-[#171717]"
          >
            ← Back to cases
          </Link>

          <div className="mt-20 rounded-2xl border border-black/8 bg-white p-8">
            <p className="font-medium">
              We couldn&apos;t load this case.
            </p>

            <p className="mt-2 text-sm text-[#8a8a86]">
              {error}
            </p>
          </div>
        </div>
      </main>
    );
  }

  if (!caseItem) {
    return null;
  }

  const canResearch =
    caseItem.status === "EVIDENCE_READY";

  const canRequestApproval =
    caseItem.status === "ACTION_READY";

  return (
    <main className="min-h-screen bg-[#f7f7f5] text-[#171717]">
      <div className="mx-auto min-h-screen w-full max-w-5xl px-6 py-8 md:px-10">

        {/* Header */}
        <header className="flex items-center justify-between">
          <Link
            href="/"
            className="group flex items-center gap-2 text-sm text-[#73736e] transition hover:text-[#171717]"
          >
            <span className="transition group-hover:-translate-x-0.5">
              ←
            </span>

            <span>Back to cases</span>
          </Link>

          <div className="flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium">
                Tanishka
              </p>

              <p className="text-xs text-[#8a8a86]">
                Personal workspace
              </p>
            </div>

            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-black/10 bg-white text-sm font-medium">
              T
            </div>
          </div>
        </header>

        {/* Case heading */}
        <section className="mt-16">
          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-start">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-[#8a8a86]">
                Case #{caseItem.id}
              </p>

              <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] md:text-5xl">
                {caseItem.title}
              </h1>

              <p className="mt-4 max-w-2xl text-base leading-7 text-[#73736e]">
                {caseItem.description}
              </p>
            </div>

            <StatusPill status={caseItem.status} />
          </div>
        </section>

        {/* Error */}
        {error && (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Primary action */}
        {(canResearch || canRequestApproval) && (
          <section className="mt-10">
            <div className="rounded-2xl border border-black/8 bg-[#171717] p-6 text-white shadow-[0_12px_40px_rgba(0,0,0,0.08)]">
              <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
                <div>
                  <p className="text-xs font-semibold tracking-[0.16em] text-white/50">
                    {canResearch
                      ? "RESEARCH READY"
                      : "DECISION READY"}
                  </p>

                  <h2 className="mt-2 text-xl font-semibold">
                    {canResearch
                      ? "ONIT can investigate this case."
                      : "ONIT has prepared an action."}
                  </h2>

                  <p className="mt-2 max-w-xl text-sm leading-6 text-white/60">
                    {canResearch
                      ? "Run focused research to strengthen the case before a decision is made."
                      : "Review the recommendation before allowing ONIT to proceed."}
                  </p>
                </div>

                {canResearch && (
                  <button
                    onClick={runResearch}
                    disabled={actionLoading}
                    className="shrink-0 rounded-full bg-white px-5 py-3 text-sm font-medium text-[#171717] transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {actionLoading
                      ? "Researching..."
                      : "Run research →"}
                  </button>
                )}

                {canRequestApproval && (
                  <button
                    onClick={requestApproval}
                    disabled={actionLoading}
                    className="shrink-0 rounded-full bg-white px-5 py-3 text-sm font-medium text-[#171717] transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {actionLoading
                      ? "Preparing..."
                      : "Request approval →"}
                  </button>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Case information */}
        <section className="mt-12">
          <SectionLabel>CASE INFORMATION</SectionLabel>

          <div className="mt-4 grid overflow-hidden rounded-2xl border border-black/8 bg-white sm:grid-cols-2">
            <InfoItem
              label="Passenger"
              value={caseItem.passenger}
            />

            <InfoItem
              label="Organization"
              value={
                caseItem.organization ??
                caseItem.airline
              }
            />

            <InfoItem
              label="Booking reference"
              value={caseItem.booking_reference}
            />

            <InfoItem
              label="Amount"
              value={
                caseItem.amount
                  ? `${caseItem.currency ?? ""}${caseItem.amount}`
                  : null
              }
            />

            <InfoItem
              label="Cancellation date"
              value={caseItem.cancellation_date}
            />

            <InfoItem
              label="Refund received"
              value={
                caseItem.refund_received === null
                  ? null
                  : caseItem.refund_received
                    ? "Yes"
                    : "No"
              }
            />
          </div>
        </section>

        {/* Evidence */}
        {caseItem.supporting_facts && (
          <section className="mt-12">
            <SectionLabel>EVIDENCE</SectionLabel>

            <div className="mt-4 rounded-2xl border border-black/8 bg-white p-6">
              <p className="whitespace-pre-line text-sm leading-7 text-[#595955]">
                {caseItem.supporting_facts}
              </p>
            </div>
          </section>
        )}

        {/* Analysis */}
        {(caseItem.issue ||
          caseItem.recommended_action ||
          caseItem.decision_reason) && (
          <section className="mt-12">
            <SectionLabel>
              ONIT&apos;S ASSESSMENT
            </SectionLabel>

            <div className="mt-4 overflow-hidden rounded-2xl border border-black/8 bg-white">
              {caseItem.issue && (
                <AssessmentRow
                  label="Issue"
                  value={caseItem.issue}
                />
              )}

              {caseItem.recommended_action && (
                <AssessmentRow
                  label="Recommended action"
                  value={caseItem.recommended_action}
                />
              )}

              {caseItem.priority && (
                <AssessmentRow
                  label="Priority"
                  value={formatStatus(caseItem.priority)}
                />
              )}

              {caseItem.decision_reason && (
                <AssessmentRow
                  label="Why"
                  value={caseItem.decision_reason}
                  last
                />
              )}
            </div>
          </section>
        )}

        {/* Research */}
        <section className="mt-12">
          <SectionLabel>RESEARCH</SectionLabel>

          {research.length === 0 ? (
            <div className="mt-4 rounded-2xl border border-dashed border-black/10 bg-white/60 p-8">
              <p className="text-sm font-medium">
                No research recorded yet.
              </p>

              <p className="mt-2 text-sm leading-6 text-[#8a8a86]">
                ONIT will store the sources it uses as the case
                moves forward.
              </p>
            </div>
          ) : (
            <div className="mt-4 space-y-4">
              {research.map((item) => (
                <div
                  key={item.id}
                  className="rounded-2xl border border-black/8 bg-white p-6"
                >
                  <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8a8a86]">
                        {item.source}
                      </p>

                      <h3 className="mt-2 text-lg font-semibold">
                        {item.title}
                      </h3>
                    </div>

                    <span className="text-xs text-[#a0a09b]">
                      {formatDate(item.created_at)}
                    </span>
                  </div>

                  <p className="mt-4 text-sm leading-7 text-[#595955]">
                    {item.summary}
                  </p>

                  <div className="mt-5 rounded-xl bg-[#f7f7f5] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#8a8a86]">
                      Relevance
                    </p>

                    <p className="mt-2 text-sm leading-6 text-[#595955]">
                      {item.relevance}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Plan */}
        {(caseItem.plan_summary ||
          caseItem.plan_steps) && (
          <section className="mt-12">
            <SectionLabel>PLAN</SectionLabel>

            <div className="mt-4 rounded-2xl border border-black/8 bg-white p-6">
              {caseItem.plan_summary && (
                <p className="text-base font-medium leading-7">
                  {caseItem.plan_summary}
                </p>
              )}

              {caseItem.plan_steps && (
                <p className="mt-4 whitespace-pre-line text-sm leading-7 text-[#595955]">
                  {caseItem.plan_steps}
                </p>
              )}
            </div>
          </section>
        )}

        {/* Activity */}
        <section className="mt-12">
          <SectionLabel>ACTIVITY</SectionLabel>

          <div className="mt-4 rounded-2xl border border-black/8 bg-white p-6">
            {activities.length === 0 ? (
              <p className="text-sm text-[#8a8a86]">
                No activity recorded yet.
              </p>
            ) : (
              <div className="space-y-6">
                {activities.map((activity, index) => (
                  <div
                    key={activity.id}
                    className="flex gap-4"
                  >
                    <div className="flex flex-col items-center">
                      <span
                        className={`mt-1.5 h-2.5 w-2.5 rounded-full ${
                          index === activities.length - 1
                            ? "bg-amber-500"
                            : "bg-emerald-500"
                        }`}
                      />

                      {index !== activities.length - 1 && (
                        <span className="mt-2 h-full w-px bg-black/8" />
                      )}
                    </div>

                    <div className="min-w-0 flex-1 pb-1">
                      <div className="flex flex-col justify-between gap-1 sm:flex-row">
                        <p className="text-sm font-medium">
                          {formatStatus(activity.event_type)}
                        </p>

                        <span className="text-xs text-[#a0a09b]">
                          {formatDate(activity.created_at)}
                        </span>
                      </div>

                      <p className="mt-1 text-sm leading-6 text-[#73736e]">
                        {activity.message}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Approval notice */}
        {caseItem.status === "AWAITING_APPROVAL" && (
          <section className="mt-12">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
              <p className="text-xs font-semibold tracking-[0.14em] text-amber-700">
                YOUR DECISION
              </p>

              <h2 className="mt-2 text-xl font-semibold text-amber-950">
                ONIT is waiting for your approval.
              </h2>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-amber-900/70">
                No external action will be taken until you explicitly
                approve the prepared action.
              </p>

              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  disabled
                  className="rounded-full bg-[#171717] px-5 py-3 text-sm font-medium text-white opacity-50"
                >
                  Approve action
                </button>

                <button
                  disabled
                  className="rounded-full border border-amber-900/10 bg-white px-5 py-3 text-sm font-medium text-amber-900 opacity-50"
                >
                  Reject
                </button>
              </div>
            </div>
          </section>
        )}

        <footer className="mt-16 border-t border-black/6 py-8 text-xs text-[#a0a09b]">
          ONIT · Your problems, moving forward.
        </footer>
      </div>
    </main>
  );
}

function InfoItem({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <div className="border-b border-black/6 p-5 last:border-b-0 sm:nth-[even]:border-l">
      <p className="text-xs text-[#8a8a86]">
        {label}
      </p>

      <p className="mt-1 text-sm font-medium">
        {value ?? "Not available"}
      </p>
    </div>
  );
}

function AssessmentRow({
  label,
  value,
  last = false,
}: {
  label: string;
  value: string;
  last?: boolean;
}) {
  return (
    <div
      className={`grid gap-2 p-5 sm:grid-cols-[180px_1fr] ${
        last ? "" : "border-b border-black/6"
      }`}
    >
      <p className="text-xs font-medium uppercase tracking-[0.08em] text-[#8a8a86]">
        {label}
      </p>

      <p className="text-sm leading-6 text-[#454542]">
        {value}
      </p>
    </div>
  );
}