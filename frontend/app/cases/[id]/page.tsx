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
  url?: string | null;
  created_at: string;
};

type EvidenceItem = {
  id: number;
  filename: string | null;
  evidence_type: string | null;
  mimetype: string | null;
  extraction_status: string | null;
  extracted_facts: Record<string, unknown> | null;
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
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploadLoading, setUploadLoading] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [approving, setApproving] = useState(false);

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
          evidenceResponse,
        ] = await Promise.all([
          fetch(`${API_URL}/cases/${caseId}`),
          fetch(`${API_URL}/cases/${caseId}/activity`),
          fetch(`${API_URL}/cases/${caseId}/research`),
          fetch(`${API_URL}/cases/${caseId}/evidence`),
        ]);

        if (!caseResponse.ok) {
          throw new Error("Case not found.");
        }

        const caseData = await caseResponse.json();
        const activityData = await activityResponse.json();
        const researchData = await researchResponse.json();
        const evidenceData = await evidenceResponse.json();

        if (cancelled) {
          return;
        }

        setCaseItem(caseData.case);
        setActivities(activityData.activities ?? []);
        setResearch(researchData.research ?? []);
        setEvidence(evidenceData.evidence ?? []);
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
        evidenceResponse,
      ] = await Promise.all([
        fetch(`${API_URL}/cases/${caseId}`),
        fetch(`${API_URL}/cases/${caseId}/activity`),
        fetch(`${API_URL}/cases/${caseId}/research`),
        fetch(`${API_URL}/cases/${caseId}/evidence`),
      ]);

      if (!caseResponse.ok) {
        throw new Error("Case not found.");
      }

      const caseData = await caseResponse.json();
      const activityData = await activityResponse.json();
      const researchData = await researchResponse.json();
      const evidenceData = await evidenceResponse.json();

      setCaseItem(caseData.case);
      setActivities(activityData.activities ?? []);
      setResearch(researchData.research ?? []);
      setEvidence(evidenceData.evidence ?? []);
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

  async function approveAction() {
    if (!caseItem) return;

    try {
      setApproving(true);
      setError("");

      const resp = await fetch(`${API_URL}/cases/${caseItem.id}/approve`, {
        method: "POST",
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail ?? "Unable to approve action.");
      }

      // refresh case and related lists
      await refreshCase();
      setShowReview(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to approve action.");
    } finally {
      setApproving(false);
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

  async function uploadEvidence(file: File | null, text?: string) {
    if (!caseItem) return;

    try {
      setUploadLoading(true);
      setError("");

      const form = new FormData();

      if (file) {
        form.append("file", file, file.name);
      } else if (text) {
        form.append("text", text);
      } else {
        throw new Error("No file or text provided");
      }

      const resp = await fetch(`${API_URL}/cases/${caseItem.id}/evidence`, {
        method: "POST",
        body: form,
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      await refreshCase();
      // fetch evidence list
      const ev = await (await fetch(`${API_URL}/cases/${caseItem.id}/evidence`)).json();
      setEvidence(ev.evidence ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploadLoading(false);
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
        <section className="mt-12">
          <SectionLabel>EVIDENCE</SectionLabel>

          <div className="mt-4 flex flex-col gap-4">
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm text-[#8a8a86]">
                Uploaded evidence and extracted facts.
              </p>

              <div className="flex items-center gap-3">
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="file"
                    className="sr-only"
                    onChange={(e) => {
                      const f = e.target.files?.[0] ?? null;
                      if (f) uploadEvidence(f);
                      e.currentTarget.value = "";
                    }}
                  />

                  <span className="rounded-full border border-black/8 bg-white px-4 py-2 text-sm font-medium">
                    {uploadLoading ? "Uploading..." : "Add evidence"}
                  </span>
                </label>
              </div>
            </div>

            {evidence.length === 0 ? (
              // fallback to any supporting_facts text if available
              (caseItem.supporting_facts && (
                <div className="rounded-2xl border border-black/8 bg-white p-6">
                  <p className="whitespace-pre-line text-sm leading-7 text-[#595955]">
                    {caseItem.supporting_facts}
                  </p>
                </div>
              )) || (
                <div className="rounded-2xl border border-dashed border-black/10 bg-white/60 p-8">
                  <p className="text-sm font-medium">
                    No supporting evidence has been added yet.
                  </p>

                    <p className="mt-2 text-sm leading-6 text-[#8a8a86]">
                    Use the Add evidence button to upload a document or paste text.
                  </p>
                </div>
              )
            ) : (
              <div className="mt-2 space-y-4">
                {evidence.map((ev) => (
                  <div
                    key={ev.id}
                    className="rounded-2xl border border-black/8 bg-white p-6"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold">
                          {ev.filename ?? (ev.evidence_type ?? "Text input")}
                        </p>

                        <p className="mt-2 text-xs text-[#8a8a86]">
                          {ev.evidence_type ? ev.evidence_type.toUpperCase() : "TEXT"} · {ev.mimetype ?? "-"}
                        </p>
                      </div>

                      <div className="text-right text-xs text-[#a0a09b]">
                        {formatDate(ev.created_at)}
                      </div>
                    </div>

                    <div className="mt-4 grid gap-2 sm:grid-cols-2">
                      {ev.extracted_facts ? (
                        Object.entries(ev.extracted_facts).map(([k, v]) => {
                          const display = Array.isArray(v)
                            ? (v as string[]).join("; ")
                            : v == null
                              ? "—"
                              : String(v);

                          return (
                            <div key={k} className="rounded-md bg-[#f7f7f5] p-3">
                              <p className="text-xs text-[#8a8a86]">{k.replaceAll("_", " ")}</p>
                              <p className="mt-1 text-sm text-[#454542]">{display}</p>
                            </div>
                          );
                        })
                      ) : (
                        <div className="rounded-md bg-[#f7f7f5] p-3">
                          <p className="text-sm text-[#595955]">No extracted facts.</p>
                        </div>
                      )}
                    </div>

                    <div className="mt-4 flex items-center gap-3">
                      <span className="rounded-full bg-zinc-50 px-3 py-1 text-xs text-zinc-600">
                        {ev.extraction_status ?? "UNKNOWN"}
                      </span>

                      {ev.extracted_facts && typeof ev.extracted_facts === "object" && ev.extracted_facts !== null && ("booking_reference" in ev.extracted_facts) && !!(ev.extracted_facts as Record<string, unknown>)["booking_reference"] && (
                        <a
                          href={`#`}
                          onClick={(e) => e.preventDefault()}
                          className="ml-auto text-sm font-medium text-[#171717]"
                        >
                          View source
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

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

        {/* Evidence Trail (provenance) */}
        <section className="mt-12">
          <SectionLabel>EVIDENCE TRAIL</SectionLabel>

          <div className="mt-4 rounded-2xl border border-black/8 bg-white p-6">
            <p className="text-sm text-[#595955]">Why ONIT reached this decision</p>

            <div className="mt-4 grid gap-6 md:grid-cols-[1fr_320px]">
              <div>
                <h4 className="text-sm font-semibold">CASE FACTS</h4>
                <ul className="mt-2 space-y-1 text-sm text-[#454542]">
                  {caseItem.refund_received !== null && (
                    <li>Refund received: {caseItem.refund_received ? "Yes" : "No"}</li>
                  )}

                  {caseItem.cancellation_date && (
                    <li>Cancellation date: {caseItem.cancellation_date}</li>
                  )}

                  {caseItem.requested_resolution && (
                    <li>Requested resolution: {caseItem.requested_resolution}</li>
                  )}
                </ul>

                <div className="my-4 flex items-center justify-center text-sm text-[#8a8a86]">↓</div>

                <h4 className="text-sm font-semibold">UPLOADED EVIDENCE</h4>

                {evidence.length === 0 ? (
                  <p className="mt-2 text-sm text-[#8a8a86]">No uploaded evidence yet.</p>
                ) : (
                  <div className="mt-2 space-y-3">
                    {evidence.map((ev) => (
                      <div key={ev.id} className="rounded-md border border-black/6 p-3">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium">{ev.filename ?? (ev.evidence_type ?? 'Text input')}</p>
                          <span className="text-xs text-[#8a8a86]">{formatDate(ev.created_at)}</span>
                        </div>

                        <div className="mt-2 text-sm text-[#595955]">
                          {ev.extracted_facts ? (
                            <ul className="space-y-1">
                              {Object.entries(ev.extracted_facts as Record<string, unknown>).map(([k, v]) => (
                                <li key={k}>
                                  <span className="font-medium">{k.replaceAll("_", " ")}: </span>
                                  <span>{Array.isArray(v) ? (v as string[]).join('; ') : String(v ?? '—')}</span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-[#8a8a86]">No extracted facts.</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="my-4 flex items-center justify-center text-sm text-[#8a8a86]">↓</div>

                <h4 className="text-sm font-semibold">EXTERNAL RESEARCH</h4>

                {research.length === 0 ? (
                  <p className="mt-2 text-sm text-[#8a8a86]">No external research recorded yet.</p>
                ) : (
                  <div className="mt-2 space-y-3">
                    {research.map((r) => {
                      const url = r.url ?? '';
                      const domain = (url.split('/')[2] || r.source || '').toLowerCase();
                      const isGov = domain.includes('.gov') || (r.source || '').toLowerCase().includes('gov');
                      const isAirline = caseItem.airline ? domain.includes((caseItem.airline || '').toLowerCase()) || (r.source || '').toLowerCase().includes((caseItem.airline || '').toLowerCase()) : false;
                      const classification = isGov ? 'OFFICIAL' : isAirline ? 'AIRLINE' : 'OTHER';

                      return (
                        <div key={r.id} className="rounded-md border border-black/6 p-3">
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <p className="text-sm font-medium">{r.title}</p>
                              <p className="mt-1 text-xs text-[#8a8a86]">{classification} · {r.relevance}</p>
                            </div>

                            <div className="text-right">
                              {r.url ? (
                                <a href={r.url} target="_blank" rel="noreferrer" className="text-sm font-medium text-[#171717]">Open</a>
                              ) : null}
                            </div>
                          </div>

                          <p className="mt-2 text-sm text-[#595955]">{r.summary}</p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <aside>
                <div className="rounded-md bg-[#f7f7f5] p-4">
                  <h5 className="text-sm font-semibold">ONIT DECISION</h5>
                  <p className="mt-2 text-sm text-[#454542]">{caseItem.recommended_action ?? 'No recommendation yet.'}</p>

                  <div className="mt-4">
                    <p className="text-xs text-[#8a8a86]">Evidence strength</p>
                    <p className="mt-1 text-sm font-medium">
                      {evidence.length > 0 && research.length > 0 ? 'Strong' : (evidence.length > 0 || research.length > 0 ? 'Moderate' : 'Insufficient')}
                    </p>
                  </div>

                  <div className="mt-4">
                    <p className="text-xs text-[#8a8a86]">Decision supported by</p>
                    <ul className="mt-2 space-y-2 text-sm text-[#454542]">
                      {caseItem.refund_received !== null && (
                        <li>✓ Refund received: {caseItem.refund_received ? 'Yes' : 'No'}{evidence.some(ev => (ev.extracted_facts && ((ev.extracted_facts as Record<string, unknown>)['refund_received'] !== undefined))) ? ' — uploaded evidence' : ''}</li>
                      )}

                      {caseItem.cancellation_date && (
                        <li>✓ Cancellation date: {caseItem.cancellation_date}{evidence.some(ev => ev.extracted_facts && (ev.extracted_facts as Record<string, unknown>)['cancellation_date']) ? ' — uploaded evidence' : ''}</li>
                      )}

                      {caseItem.requested_resolution && (
                        <li>✓ Requested resolution: {caseItem.requested_resolution}{evidence.some(ev => ev.extracted_facts && (ev.extracted_facts as Record<string, unknown>)['requested_resolution']) ? ' — uploaded evidence' : ''}</li>
                      )}

                      {research.slice(0, 3).map(r => (
                        <li key={`sup-${r.id}`}>✓ {r.title} — {((r.url && r.url.includes('.gov')) ? 'Official source' : 'External source')}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </aside>
            </div>
          </div>
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

        {/* Human review / approval */}
        {caseItem.status === "AWAITING_APPROVAL" && caseItem.approval_required && (
          <section className="mt-12">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
              <p className="text-xs font-semibold tracking-[0.14em] text-amber-700">
                HUMAN REVIEW REQUIRED
              </p>

              <h2 className="mt-2 text-xl font-semibold text-amber-950">
                ONIT has completed its analysis and prepared an execution plan.
              </h2>

              <p className="mt-4 max-w-2xl text-sm leading-6 text-amber-900/70">
                <strong>Decision</strong>
                <br />
                {caseItem.recommended_action ?? "(No decision)"}
              </p>

              <p className="mt-3 max-w-2xl text-sm leading-6 text-amber-900/70">
                <strong>Why</strong>
                <br />
                {caseItem.decision_reason ?? "No reason provided."}
              </p>

              <div className="mt-4 max-w-2xl">
                <p className="text-sm font-semibold">Execution plan</p>
                <div className="mt-2 whitespace-pre-line text-sm text-[#171717]">{caseItem.plan_steps ?? caseItem.plan_summary ?? "No plan provided."}</div>
              </div>

              <div className="mt-5 flex flex-wrap gap-3">
                {!showReview ? (
                  <button
                    onClick={() => setShowReview(true)}
                    disabled={actionLoading}
                    className="rounded-full bg-white px-5 py-3 text-sm font-medium text-[#171717]"
                  >
                    Review &amp; Approve
                  </button>
                ) : (
                  <div className="w-full rounded-2xl border border-black/8 bg-white p-4">
                    <p className="text-sm font-medium">Review this action before approving.</p>

                    <div className="mt-3 space-y-2 text-sm text-[#454542]">
                      <p><strong>Decision:</strong> {caseItem.recommended_action ?? '—'}</p>
                      <p><strong>Why:</strong> {caseItem.decision_reason ?? '—'}</p>
                      <p><strong>Evidence strength:</strong> {evidence.length > 0 && research.length > 0 ? 'Strong' : (evidence.length > 0 || research.length > 0 ? 'Moderate' : 'Insufficient')}</p>
                      <p><strong>Supporting evidence:</strong> {evidence.length > 0 ? `${evidence.length} items` : 'None'}</p>
                      <p><strong>Research sources:</strong> {research.length > 0 ? `${research.length} sources` : 'None'}</p>
                    </div>

                    <div className="mt-4 flex gap-3">
                      <button
                        onClick={approveAction}
                        disabled={approving}
                        className="rounded-full bg-[#171717] px-5 py-3 text-sm font-medium text-white disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {approving ? 'Approving...' : 'Approve & Continue'}
                      </button>

                      <button
                        onClick={() => setShowReview(false)}
                        disabled={approving}
                        className="rounded-full border border-amber-900/10 bg-white px-5 py-3 text-sm font-medium text-amber-900"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Show ACTION_READY after approval */}
        {caseItem.status === "ACTION_READY" && (
          <section className="mt-12">
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
              <p className="text-xs font-semibold tracking-[0.14em] text-emerald-700">ACTION READY</p>

              <h2 className="mt-2 text-xl font-semibold text-emerald-950">Ready for execution</h2>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-900/70">
                Human approval has been recorded. ONIT prepared the following action:
              </p>

              <div className="mt-4 max-w-2xl">
                <p className="text-sm font-semibold">{caseItem.recommended_action ?? 'No action provided.'}</p>

                <div className="mt-3 whitespace-pre-line text-sm text-[#171717]">{caseItem.plan_steps ?? caseItem.plan_summary ?? 'No plan provided.'}</div>
              </div>

              <p className="mt-4 text-sm text-emerald-900/80">Approved by human review.</p>
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