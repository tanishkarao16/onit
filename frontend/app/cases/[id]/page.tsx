"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

type CaseItem = {
  id: number;
  title: string;
  description: string;

  passenger?: string | null;
  booking_reference?: string | null;

  organization?: string | null;
  airline?: string | null;

  cancellation_date?: string | null;

  amount?: string | number | null;
  currency?: string | null;

  refund_received?: boolean | string | null;

  requested_resolution?: string | null;
  supporting_facts?: string | null;

  issue?: string | null;
  recommended_action?: string | null;
  priority?: string | null;
  decision_reason?: string | null;

  plan_summary?: string | null;
  plan_steps?: string | null;

  approval_required?: boolean | null;

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
  source?: string | null;
  title?: string | null;
  summary?: string | null;
  relevance?: string | null;
  url?: string | null;
  created_at: string;
};

type EvidenceItem = {
  id: number;
  filename?: string | null;
  evidence_type?: string | null;
  mimetype?: string | null;
  extraction_status?: string | null;
  extracted_facts?: Record<string, unknown> | null;
  created_at: string;
};

type ResponseItem = {
  id: number;
  response_type: string;
  message: string;
  resolved: boolean;
  created_at: string;
};

type WorkflowStatus =
  | "CREATED"
  | "EVIDENCE_READY"
  | "RESEARCHING"
  | "ACTION_READY"
  | "AWAITING_APPROVAL"
  | "SUBMITTED"
  | "WAITING_FOR_RESPONSE"
  | "FOLLOW_UP_REQUIRED"
  | "ESCALATION_REQUIRED"
  | "RESOLVED"
  | "CLOSED";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

const WORKFLOW_STATUSES: WorkflowStatus[] = [
  "CREATED",
  "EVIDENCE_READY",
  "RESEARCHING",
  "ACTION_READY",
  "AWAITING_APPROVAL",
  "SUBMITTED",
  "WAITING_FOR_RESPONSE",
  "FOLLOW_UP_REQUIRED",
  "ESCALATION_REQUIRED",
  "RESOLVED",
  "CLOSED",
];

const WORKFLOW_LABELS: Record<string, string> = {
  CREATED: "Case",
  EVIDENCE_READY: "Evidence",
  RESEARCHING: "Research",
  ACTION_READY: "Decision",
  AWAITING_APPROVAL: "Approval",
  SUBMITTED: "Submitted",
  WAITING_FOR_RESPONSE: "Response",
  FOLLOW_UP_REQUIRED: "Follow-up",
  ESCALATION_REQUIRED: "Escalation",
  RESOLVED: "Resolution",
  CLOSED: "Closed",
};

function normalizeStatus(
  status?: string | null,
): string {
  return String(status ?? "")
    .trim()
    .toUpperCase();
}

function formatStatus(
  status?: string | null,
): string {
  if (!status) {
    return "Unknown";
  }

  return status
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDate(
  value?: string | null,
): string {
  if (!value) {
    return "";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatLabel(
  value: string,
): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatAmount(
  amount?: string | number | null,
  currency?: string | null,
): string | null {
  if (
    amount === null ||
    amount === undefined ||
    amount === ""
  ) {
    return null;
  }

  const rawAmount = String(amount).trim();

  if (!rawAmount) {
    return null;
  }

  const rawCurrency = String(currency ?? "").trim();

  if (!rawCurrency) {
    return rawAmount;
  }

  const alreadyContainsCurrency =
    rawAmount
      .toLowerCase()
      .startsWith(rawCurrency.toLowerCase());

  if (alreadyContainsCurrency) {
    return rawAmount;
  }

  const currencyAtEnd =
    rawAmount
      .toLowerCase()
      .endsWith(rawCurrency.toLowerCase());

  if (currencyAtEnd) {
    return rawAmount;
  }

  return `${rawCurrency}${rawAmount}`;
}

function formatUnknownValue(
  value: unknown,
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }

  if (typeof value === "string") {
    return value;
  }

  if (
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return "—";
    }

    return value
      .map((item) => formatUnknownValue(item))
      .join("; ");
  }

  if (
    typeof value === "object"
  ) {
    const entries = Object.entries(
      value as Record<string, unknown>,
    );

    if (entries.length === 0) {
      return "—";
    }

    return entries
      .map(
        ([key, nestedValue]) =>
          `${formatLabel(key)}: ${formatUnknownValue(
            nestedValue,
          )}`,
      )
      .join(" · ");
  }

  return String(value);
}

function getDomain(
  url?: string | null,
  fallback?: string | null,
): string {
  if (!url) {
    return fallback || "Source";
  }

  try {
    return new URL(url).hostname;
  } catch {
    return fallback || "Source";
  }
}

function getRelevanceLabel(
  relevance?: string | null,
): string {
  if (!relevance) {
    return "Not specified";
  }

  return formatStatus(relevance);
}

function StatusPill({
  status,
}: {
  status: string;
}) {
  const normalized = normalizeStatus(status);

  const ready =
    normalized === "ACTION_READY" ||
    normalized === "AWAITING_APPROVAL";

  const resolved =
    normalized === "RESOLVED" ||
    normalized === "CLOSED";

  const research =
    normalized === "RESEARCHING";

  const evidence =
    normalized === "EVIDENCE_READY";

  const postExecution =
    normalized === "SUBMITTED" ||
    normalized === "WAITING_FOR_RESPONSE" ||
    normalized === "FOLLOW_UP_REQUIRED" ||
    normalized === "ESCALATION_REQUIRED";

  return (
    <span
      className={[
        "inline-flex items-center gap-2 rounded-full px-3 py-1.5",
        "text-xs font-medium",
        ready
          ? "bg-amber-50 text-amber-700"
          : resolved
            ? "bg-emerald-50 text-emerald-700"
            : research
              ? "bg-blue-50 text-blue-700"
              : evidence
                ? "bg-violet-50 text-violet-700"
                : postExecution
                  ? "bg-zinc-100 text-zinc-600"
                  : "bg-zinc-100 text-zinc-600",
      ].join(" ")}
    >
      <span
        className={[
          "h-1.5 w-1.5 rounded-full",
          ready
            ? "bg-amber-500"
            : resolved
              ? "bg-emerald-500"
              : research
                ? "bg-blue-500"
                : evidence
                  ? "bg-violet-500"
                  : postExecution
                    ? "bg-zinc-400"
                    : "bg-zinc-400",
        ].join(" ")}
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

function InfoItem({
  label,
  value,
}: {
  label: string;
  value?: string | null;
}) {
  return (
    <div className="border-b border-black/[0.06] p-5 last:border-b-0">
      <p className="text-xs text-[#8a8a86]">
        {label}
      </p>

      <p className="mt-1 text-sm font-medium text-[#171717]">
        {value || "Not available"}
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
      className={[
        "grid gap-3 p-5 md:grid-cols-[180px_1fr]",
        !last
          ? "border-b border-black/[0.06]"
          : "",
      ].join(" ")}
    >
      <p className="text-xs font-medium uppercase tracking-[0.08em] text-[#8a8a86]">
        {label}
      </p>

      <p className="whitespace-pre-line text-sm leading-7 text-[#454542]">
        {value}
      </p>
    </div>
  );
}

function EvidenceStrength({
  evidenceCount,
  researchCount,
}: {
  evidenceCount: number;
  researchCount: number;
}) {
  if (
    evidenceCount > 0 &&
    researchCount > 0
  ) {
    return (
      <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700">
        Strong
      </span>
    );
  }

  if (
    evidenceCount > 0 ||
    researchCount > 0
  ) {
    return (
      <span className="rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700">
        Moderate
      </span>
    );
  }

  return (
    <span className="rounded-full bg-zinc-100 px-3 py-1.5 text-xs font-medium text-zinc-600">
      Insufficient
    </span>
  );
}

function Step({
  number,
  title,
  description,
  state,
}: {
  number: string;
  title: string;
  description: string;
  state:
    | "complete"
    | "current"
    | "upcoming";
}) {
  return (
    <div className="flex gap-3">
      <div
        className={[
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
          state === "complete"
            ? "bg-[#171717] text-white"
            : state === "current"
              ? "border border-amber-300 bg-amber-50 text-amber-700"
              : "border border-black/10 bg-white text-[#a0a09b]",
        ].join(" ")}
      >
        {state === "complete"
          ? "✓"
          : number}
      </div>

      <div className="pt-0.5">
        <p
          className={[
            "text-sm font-medium",
            state === "upcoming"
              ? "text-[#a0a09b]"
              : "text-[#171717]",
          ].join(" ")}
        >
          {title}
        </p>

        <p className="mt-1 text-xs leading-5 text-[#8a8a86]">
          {description}
        </p>
      </div>
    </div>
  );
}

function WorkflowStep({
  status,
  index,
  complete,
  current,
}: {
  status: string;
  index: number;
  complete: boolean;
  current: boolean;
}) {
  return (
    <div className="flex flex-1 items-start">
      <div className="flex flex-col items-center text-center">
        <div
          className={[
            "flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold",
            complete
              ? "bg-[#171717] text-white"
              : current
                ? "border border-amber-300 bg-amber-50 text-amber-700"
                : "border border-black/10 bg-[#fafaf8] text-[#a0a09b]",
          ].join(" ")}
        >
          {complete
            ? "✓"
            : index + 1}
        </div>

        <p
          className={[
            "mt-2 whitespace-nowrap text-[11px] font-medium",
            current
              ? "text-[#171717]"
              : "text-[#8a8a86]",
          ].join(" ")}
        >
          {WORKFLOW_LABELS[status] ??
            formatStatus(status)}
        </p>
      </div>

      {index <
        WORKFLOW_STATUSES.length - 1 && (
        <div
          className={[
            "mt-4 h-px flex-1",
            complete
              ? "bg-[#171717]"
              : "bg-black/10",
          ].join(" ")}
        />
      )}
    </div>
  );
}

export default function CasePage() {
  const params = useParams();

  const caseId = Array.isArray(params.id)
    ? params.id[0]
    : params.id;

  const [caseItem, setCaseItem] =
    useState<CaseItem | null>(null);

  const [activities, setActivities] =
    useState<ActivityItem[]>([]);

  const [research, setResearch] =
    useState<ResearchItem[]>([]);

  const [evidence, setEvidence] =
    useState<EvidenceItem[]>([]);

  const [responses, setResponses] =
    useState<ResponseItem[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [actionLoading, setActionLoading] =
    useState(false);

  const [uploadLoading, setUploadLoading] =
    useState(false);

  const [showReview, setShowReview] =
    useState(false);

   const [approving, setApproving] =
    useState(false);

  const [executing, setExecuting] =
    useState(false);

  const [followUpLoading, setFollowUpLoading] =
    useState(false);

  const [recordResponseLoading, setRecordResponseLoading] =
    useState(false);

  const loadCase = useCallback(
    async (
      signal?: AbortSignal,
    ) => {
      if (!caseId) {
        return;
      }

      try {
        setError("");

        const responses =
          await Promise.all([
            fetch(
              `${API_URL}/cases/${caseId}`,
              {
                cache: "no-store",
                signal,
              },
            ),

            fetch(
              `${API_URL}/cases/${caseId}/activity`,
              {
                cache: "no-store",
                signal,
              },
            ),

            fetch(
              `${API_URL}/cases/${caseId}/research`,
              {
                cache: "no-store",
                signal,
              },
            ),

            fetch(
              `${API_URL}/cases/${caseId}/evidence`,
              {
                cache: "no-store",
                signal,
              },
            ),

          ]);

        const [
          caseResponse,
          activityResponse,
          researchResponse,
          evidenceResponse
        ] = responses;

        if (!caseResponse.ok) {
          throw new Error(
            "Case not found.",
          );
        }

        const caseData =
          await caseResponse.json();

        const activityData =
          activityResponse.ok
            ? await activityResponse.json()
            : { activities: [] };

        const researchData =
          researchResponse.ok
            ? await researchResponse.json()
            : { research: [] };

        const evidenceData =
          evidenceResponse.ok
            ? await evidenceResponse.json()
            : { evidence: [] };

        if (signal?.aborted) {
          return;
        }

        setCaseItem(
          caseData?.case ?? null,
        );

        setResponses(
          Array.isArray(caseData?.responses)
            ? caseData.responses
            : [],
        );

        setActivities(
          Array.isArray(
            activityData?.activities,
          )
            ? activityData.activities
            : [],
        );

        setResearch(
          Array.isArray(
            researchData?.research,
          )
            ? researchData.research
            : [],
        );

        setEvidence(
          Array.isArray(
            evidenceData?.evidence,
          )
            ? evidenceData.evidence
            : [],
        );

      } catch (err) {
        if (
          err instanceof DOMException &&
          err.name === "AbortError"
        ) {
          return;
        }

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load this case.",
        );
      }
    },
    [caseId],
  );

  useEffect(() => {
    const controller =
      new AbortController();

    const load = async () => {
      setLoading(true);

      await loadCase(
        controller.signal,
      );

      if (!controller.signal.aborted) {
        setLoading(false);
      }
    };

    void load();

    return () => {
      controller.abort();
    };
  }, [loadCase]);

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

      const data =
        await response
          .json()
          .catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data?.detail ??
            "Unable to request approval.",
        );
      }

      await loadCase();
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
    if (!caseItem) {
      return;
    }

    try {
      setApproving(true);
      setError("");

      const response = await fetch(
        `${API_URL}/cases/${caseItem.id}/approve`,
        {
          method: "POST",
        },
      );

      const data =
        await response
          .json()
          .catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data?.detail ??
            "Unable to approve action.",
        );
      }

      await loadCase();

      setShowReview(false);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to approve action.",
      );
    } finally {
      setApproving(false);
    }
  }

   async function executeAction() {
     if (!caseItem) {
       return;
     }

     try {
       setExecuting(true);
       setError("");

       const response = await fetch(
         `${API_URL}/cases/${caseItem.id}/execute`,
         {
           method: "POST",
         },
       );

       const data =
         await response
           .json()
           .catch(() => ({}));

       if (!response.ok) {
         throw new Error(
           data?.detail ??
             "Unable to execute action.",
         );
       }

       await loadCase();
     } catch (err) {
       setError(
         err instanceof Error
           ? err.message
           : "Unable to execute action.",
       );
     } finally {
       setExecuting(false);
     }
   }

   async function sendFollowUp() {
     if (!caseItem) {
       return;
     }

     try {
       setFollowUpLoading(true);
       setError("");

       const response = await fetch(
         `${API_URL}/cases/${caseItem.id}/follow-up`,
         {
           method: "POST",
         },
       );

       const data =
         await response
           .json()
           .catch(() => ({}));

       if (!response.ok) {
         throw new Error(
           data?.detail ??
             "Unable to send follow-up.",
         );
       }

       await loadCase();
     } catch (err) {
       setError(
         err instanceof Error
           ? err.message
           : "Unable to send follow-up.",
       );
     } finally {
       setFollowUpLoading(false);
     }
   }

   async function recordResponse(
     responseType: string,
     message: string,
     resolved: boolean,
   ) {
     if (!caseItem) {
       return;
     }

     try {
       setRecordResponseLoading(true);
       setError("");

       const response = await fetch(
         `${API_URL}/cases/${caseItem.id}/response`,
         {
           method: "POST",
           headers: {
             "Content-Type":
               "application/json",
           },
           body: JSON.stringify({
             response_type: responseType,
             message,
             resolved,
           }),
         },
       );

       const data =
         await response
           .json()
           .catch(() => ({}));

       if (!response.ok) {
         throw new Error(
           data?.detail ??
             "Unable to record response.",
         );
       }

       await loadCase();
     } catch (err) {
       setError(
         err instanceof Error
           ? err.message
           : "Unable to record response.",
       );
     } finally {
       setRecordResponseLoading(false);
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

      const data =
        await response
          .json()
          .catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data?.detail ??
            "Unable to research this case.",
        );
      }

      await loadCase();
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

  async function uploadEvidence(
    file: File | null,
    text?: string,
  ) {
    if (!caseItem) {
      return;
    }

    try {
      setUploadLoading(true);
      setError("");

      const form = new FormData();

      if (file) {
        form.append(
          "file",
          file,
          file.name,
        );
      } else if (text?.trim()) {
        form.append(
          "text",
          text.trim(),
        );
      } else {
        throw new Error(
          "No file or text provided.",
        );
      }

      const response = await fetch(
        `${API_URL}/cases/${caseItem.id}/evidence`,
        {
          method: "POST",
          body: form,
        },
      );

      const data =
        await response
          .json()
          .catch(() => ({}));

      if (!response.ok) {
        throw new Error(
          data?.detail ??
            "Unable to upload evidence.",
        );
      }

      await loadCase();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to upload evidence.",
      );
    } finally {
      setUploadLoading(false);
    }
  }

    const normalizedStatus =
    normalizeStatus(
      caseItem?.status,
    );

  const canResearch =
    normalizedStatus ===
    "EVIDENCE_READY";

  const researchRunning =
    normalizedStatus === "RESEARCHING";

  const awaitingApproval =
    normalizedStatus ===
    "AWAITING_APPROVAL";

  const actionReady =
    normalizedStatus ===
    "ACTION_READY";

  const approvalGranted =
    activities.some(
      (activity) =>
        normalizeStatus(
          activity.event_type,
        ) === "APPROVAL_GRANTED",
    );

  const canRequestApproval =
    actionReady &&
    !approvalGranted;

  const canExecute =
    actionReady &&
    approvalGranted;

  const submitted =
    normalizedStatus ===
    "SUBMITTED";

  const waitingForResponse =
    normalizedStatus ===
    "WAITING_FOR_RESPONSE";

  const followUpRequired =
    normalizedStatus ===
    "FOLLOW_UP_REQUIRED";

  const escalationRequired =
    normalizedStatus ===
    "ESCALATION_REQUIRED";

  const resolved =
    normalizedStatus ===
      "RESOLVED" ||
    normalizedStatus ===
      "CLOSED";


  const workflow = useMemo(() => {
    const currentIndex =
      WORKFLOW_STATUSES.indexOf(
        normalizedStatus as WorkflowStatus,
      );

    return WORKFLOW_STATUSES.map(
      (status, index) => ({
        status,
        index,
        complete:
          currentIndex >= 0 &&
          index < currentIndex,
        current:
          status === normalizedStatus,
      }),
    );
  }, [normalizedStatus]);

  const displayAmount =
    formatAmount(
      caseItem?.amount,
      caseItem?.currency,
    );

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

          <div className="mt-20 space-y-4">
            <div className="h-3 w-24 animate-pulse rounded bg-black/5" />

            <div className="h-12 w-2/3 animate-pulse rounded bg-black/5" />

            <div className="h-5 w-1/2 animate-pulse rounded bg-black/5" />
          </div>
        </div>
      </main>
    );
  }

  if (!caseItem) {
    return (
      <main className="min-h-screen bg-[#f7f7f5] px-6 py-8 text-[#171717]">
        <div className="mx-auto max-w-5xl">
          <Link
            href="/"
            className="text-sm text-[#73736e] transition hover:text-[#171717]"
          >
            ← Back to cases
          </Link>

          <div className="mt-20 rounded-2xl border border-black/10 bg-white p-8">
            <p className="font-medium">
              We couldn&apos;t load this case.
            </p>

            <p className="mt-2 text-sm text-[#8a8a86]">
              {error ||
                "The case does not exist."}
            </p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f7f7f5] text-[#171717]">
      <div className="mx-auto w-full max-w-6xl px-6 py-8 md:px-10">

        {/* HEADER */}

        <header className="flex items-center justify-between">
          <Link
            href="/"
            className="group flex items-center gap-2 text-sm text-[#73736e] transition hover:text-[#171717]"
          >
            <span className="transition group-hover:-translate-x-0.5">
              ←
            </span>

            <span>
              Back to cases
            </span>
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

        {/* HERO */}

        <section className="mt-14">
          <div className="flex flex-col justify-between gap-6 md:flex-row md:items-start">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-[#8a8a86]">
                Case #{caseItem.id}
              </p>

              <h1 className="mt-3 max-w-4xl text-4xl font-semibold tracking-[-0.045em] md:text-5xl">
                {caseItem.title ||
                  "Untitled case"}
              </h1>

              <p className="mt-4 max-w-3xl text-base leading-7 text-[#73736e]">
                {caseItem.description ||
                  "No case description provided."}
              </p>
            </div>

            <div className="shrink-0">
              <StatusPill
                status={
                  caseItem.status
                }
              />
            </div>
          </div>
        </section>

        {/* ERROR */}

        {error && (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700">
            {error}
          </div>
        )}

        {/* WORKFLOW */}

        <section className="mt-10">
          <div className="overflow-x-auto rounded-2xl border border-black/[0.08] bg-white p-5">
            <div className="flex min-w-[720px] items-start">
              {workflow.map(
                (step) => (
                  <WorkflowStep
                    key={
                      step.status
                    }
                    status={
                      step.status
                    }
                    index={
                      step.index
                    }
                    complete={
                      step.complete
                    }
                    current={
                      step.current
                    }
                  />
                ),
              )}
            </div>
          </div>
        </section>

        {/* PRIMARY ACTION */}

        {(canResearch ||
          canRequestApproval ||
          canExecute ||
          submitted ||
          waitingForResponse ||
          followUpRequired ||
          escalationRequired) && (
          <section className="mt-8">
            <div className="rounded-2xl bg-[#171717] p-6 text-white shadow-[0_14px_50px_rgba(0,0,0,0.08)]">
              <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">

                <div>
                  <p className="text-xs font-semibold tracking-[0.16em] text-white/50">
                    {canResearch
                      ? "RESEARCH READY"
                      : canRequestApproval
                        ? "DECISION READY"
                        : canExecute
                          ? "ACTION READY"
                          : submitted
                            ? "ACTION SUBMITTED"
                            : waitingForResponse
                              ? "AWAITING RESPONSE"
                              : followUpRequired
                                ? "FOLLOW-UP REQUIRED"
                                : "ESCALATION REQUIRED"}
                  </p>

                  <h2 className="mt-2 text-xl font-semibold">
                    {canResearch
                      ? "ONIT can investigate this case."
                      : canRequestApproval
                        ? "ONIT has prepared an action."
                        : canExecute
                          ? "The approved action is ready to execute."
                          : submitted
                            ? "Action submitted."
                            : waitingForResponse
                              ? "Waiting for a response."
                              : followUpRequired
                                ? "Follow-up required."
                                : "This case requires escalation."}
                  </h2>

                  <p className="mt-2 max-w-xl text-sm leading-6 text-white/60">
                    {canResearch
                      ? "ONIT has enough case information to begin focused external research."
                      : canRequestApproval
                        ? "The recommendation and execution plan are ready for your review."
                        : canExecute
                          ? "Human approval has been recorded. ONIT can now submit the prepared action."
                          : submitted
                            ? "ONIT has submitted the approved action and is awaiting the external organization's response."
                            : waitingForResponse
                              ? "The action has been submitted and ONIT is now waiting for the external organization to respond."
                              : followUpRequired
                                ? "The external response requires further action. ONIT will send a follow-up to continue progressing this case."
                                : "This case has been flagged for escalation and will require additional attention."}
                  </p>
                </div>

                {canResearch && (
                  <button
                    type="button"
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
                    type="button"
                    onClick={requestApproval}
                    disabled={actionLoading}
                    className="shrink-0 rounded-full bg-white px-5 py-3 text-sm font-medium text-[#171717] transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {actionLoading
                      ? "Preparing..."
                      : "Request approval →"}
                  </button>
                )}

                {canExecute && (
                  <button
                    type="button"
                    onClick={executeAction}
                    disabled={executing}
                    className="shrink-0 rounded-full bg-white px-5 py-3 text-sm font-semibold text-[#171717] transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {executing
                      ? "Executing..."
                      : "Execute action →"}
                  </button>
                )}

                {followUpRequired && (
                  <button
                    type="button"
                    onClick={sendFollowUp}
                    disabled={followUpLoading}
                    className="shrink-0 rounded-full bg-white px-5 py-3 text-sm font-medium text-[#171717] transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {followUpLoading
                      ? "Sending..."
                      : "Send follow-up →"}
                  </button>
                )}

              </div>
            </div>
          </section>
        )}

        {/* RESEARCHING STATE */}

        {researchRunning && (
          <section className="mt-8">
            <div className="rounded-2xl border border-blue-200 bg-blue-50 p-6">
              <p className="text-xs font-semibold tracking-[0.16em] text-blue-700">
                RESEARCH IN PROGRESS
              </p>

              <h2 className="mt-2 text-xl font-semibold text-blue-950">
                ONIT is researching this case.
              </h2>

              <p className="mt-2 text-sm leading-6 text-blue-900/70">
                External sources are being evaluated against the case facts.
              </p>
            </div>
          </section>
        )}

        {/* SUBMITTED STATE */}

        {submitted && (
          <section className="mt-8">
            <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-6">
              <p className="text-xs font-semibold tracking-[0.16em] text-zinc-600">
                ACTION SUBMITTED
              </p>

              <h2 className="mt-2 text-xl font-semibold text-zinc-900">
                Action submitted.
              </h2>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-700">
                ONIT has submitted the approved action and is awaiting the external organization&apos;s response.
              </p>
            </div>
          </section>
        )}

        {/* WAITING FOR RESPONSE STATE */}

        {waitingForResponse && (
          <section className="mt-8">
            <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-6">
              <p className="text-xs font-semibold tracking-[0.16em] text-zinc-600">
                AWAITING RESPONSE
              </p>

              <h2 className="mt-2 text-xl font-semibold text-zinc-900">
                Waiting for a response.
              </h2>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-700">
                The action has been submitted and ONIT is now waiting for the external organization to respond.
              </p>
            </div>
          </section>
        )}

        {/* FOLLOW-UP REQUIRED STATE */}

        {followUpRequired && (
          <section className="mt-8">
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
              <p className="text-xs font-semibold tracking-[0.16em] text-amber-700">
                FOLLOW-UP REQUIRED
              </p>

              <h2 className="mt-2 text-xl font-semibold text-amber-950">
                Follow-up required.
              </h2>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-amber-900/70">
                The external response requires further action.
              </p>
            </div>
          </section>
        )}

        {/* ESCALATION REQUIRED STATE */}

        {escalationRequired && (
          <section className="mt-8">
            <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
              <p className="text-xs font-semibold tracking-[0.16em] text-red-700">
                ESCALATION REQUIRED
              </p>

              <h2 className="mt-2 text-xl font-semibold text-red-950">
                This case requires escalation.
              </h2>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-red-900/70">
                The case has been flagged for escalation and will require additional attention.
              </p>
            </div>
          </section>
        )}

        {/* CASE INFORMATION */}

        <section className="mt-12">
          <SectionLabel>
            CASE INFORMATION
          </SectionLabel>

          <div className="mt-4 grid overflow-hidden rounded-2xl border border-black/[0.08] bg-white sm:grid-cols-2">
            <InfoItem
              label="Passenger"
              value={
                caseItem.passenger
              }
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
              value={
                caseItem.booking_reference
              }
            />

            <InfoItem
              label="Amount"
              value={
                displayAmount
              }
            />

            <InfoItem
              label="Cancellation date"
              value={
                caseItem.cancellation_date
              }
            />

            <InfoItem
              label="Refund received"
              value={
                caseItem.refund_received ===
                  null ||
                caseItem.refund_received ===
                  undefined
                  ? null
                  : typeof caseItem.refund_received ===
                      "string"
                    ? caseItem.refund_received
                    : caseItem.refund_received
                      ? "Yes"
                      : "No"
              }
            />

            <InfoItem
              label="Requested resolution"
              value={
                caseItem.requested_resolution
              }
            />

            <InfoItem
              label="Created"
              value={
                formatDate(
                  caseItem.created_at,
                )
              }
            />
          </div>
        </section>

        {/* EVIDENCE */}

        <section className="mt-12">
          <div className="flex items-end justify-between gap-4">
            <div>
              <SectionLabel>
                EVIDENCE
              </SectionLabel>

              <p className="mt-1 text-sm text-[#73736e]">
                Documents and facts ONIT can use to understand the case.
              </p>
            </div>

            <label className="relative inline-flex shrink-0 cursor-pointer items-center">
              <input
                type="file"
                className="sr-only"
                disabled={
                  uploadLoading
                }
                onChange={(
                  event,
                ) => {
                  const file =
                    event
                      .target
                      .files?.[0] ??
                    null;

                  if (file) {
                    void uploadEvidence(
                      file,
                    );
                  }

                  event.currentTarget.value =
                    "";
                }}
              />

              <span className="rounded-full border border-black/10 bg-white px-4 py-2.5 text-sm font-medium transition hover:bg-[#fafaf8]">
                {uploadLoading
                  ? "Uploading..."
                  : "+ Add evidence"}
              </span>
            </label>
          </div>

          <div className="mt-4 space-y-4">
            {evidence.length ===
            0 ? (
              caseItem.supporting_facts ? (
                <div className="rounded-2xl border border-black/[0.08] bg-white p-6">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8a8a86]">
                    Supporting facts
                  </p>

                  <p className="mt-3 whitespace-pre-line text-sm leading-7 text-[#595955]">
                    {
                      caseItem.supporting_facts
                    }
                  </p>
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-black/10 bg-white/60 p-8">
                  <p className="text-sm font-medium">
                    No evidence has been uploaded yet.
                  </p>

                  <p className="mt-2 text-sm leading-6 text-[#8a8a86]">
                    Add a document and ONIT will extract the facts it can use.
                  </p>
                </div>
              )
            ) : (
              evidence.map(
                (item) => {
                  const facts =
                    item.extracted_facts;

                  const factEntries =
                    facts &&
                    typeof facts ===
                      "object"
                      ? Object.entries(
                          facts,
                        )
                      : [];

                  return (
                    <div
                      key={
                        item.id
                      }
                      className="rounded-2xl border border-black/[0.08] bg-white p-6"
                    >
                      <div className="flex flex-col justify-between gap-3 sm:flex-row">
                        <div>
                          <p className="text-sm font-semibold">
                            {item.filename ??
                              item.evidence_type ??
                              "Text evidence"}
                          </p>

                          <p className="mt-1 text-xs text-[#8a8a86]">
                            {(
                              item.evidence_type ??
                              "TEXT"
                            ).toUpperCase()}
                            {" · "}
                            {item.mimetype ??
                              "text"}
                          </p>
                        </div>

                        <span className="text-xs text-[#a0a09b]">
                          {formatDate(
                            item.created_at,
                          )}
                        </span>
                      </div>

                      <div className="mt-5">
                        {factEntries.length >
                        0 ? (
                          <div className="grid gap-3 sm:grid-cols-2">
                            {factEntries.map(
                              ([
                                key,
                                value,
                              ]) => (
                                <div
                                  key={
                                    key
                                  }
                                  className="rounded-xl bg-[#f7f7f5] p-4"
                                >
                                  <p className="text-xs text-[#8a8a86]">
                                    {formatLabel(
                                      key,
                                    )}
                                  </p>

                                  <p className="mt-1 whitespace-pre-line text-sm leading-6 text-[#454542]">
                                    {formatUnknownValue(
                                      value,
                                    )}
                                  </p>
                                </div>
                              ),
                            )}
                          </div>
                        ) : (
                          <p className="text-sm text-[#8a8a86]">
                            No extracted facts available.
                          </p>
                        )}
                      </div>

                      <div className="mt-5">
                        <span className="rounded-full bg-zinc-50 px-3 py-1.5 text-xs text-zinc-600">
                          {item.extraction_status ??
                            "Unknown status"}
                        </span>
                      </div>
                    </div>
                  );
                },
              )
            )}
          </div>
        </section>

        {/* ASSESSMENT */}

        {(caseItem.issue ||
          caseItem.recommended_action ||
          caseItem.priority ||
          caseItem.decision_reason) && (
          <section className="mt-12">
            <SectionLabel>
              ONIT&apos;S ASSESSMENT
            </SectionLabel>

            <div className="mt-4 overflow-hidden rounded-2xl border border-black/[0.08] bg-white">
              {caseItem.issue && (
                <AssessmentRow
                  label="Issue"
                  value={
                    caseItem.issue
                  }
                />
              )}

              {caseItem.recommended_action && (
                <AssessmentRow
                  label="Recommended action"
                  value={
                    caseItem.recommended_action
                  }
                />
              )}

              {caseItem.priority && (
                <AssessmentRow
                  label="Priority"
                  value={formatStatus(
                    caseItem.priority,
                  )}
                />
              )}

              {caseItem.decision_reason && (
                <AssessmentRow
                  label="Why"
                  value={
                    caseItem.decision_reason
                  }
                  last
                />
              )}
            </div>
          </section>
        )}

        {/* RESEARCH */}

        <section className="mt-12">
          <SectionLabel>
            EXTERNAL RESEARCH
          </SectionLabel>

          <p className="mt-1 text-sm text-[#73736e]">
            Sources ONIT used to validate the case and support its decision.
          </p>

          {research.length ===
          0 ? (
            <div className="mt-4 rounded-2xl border border-dashed border-black/10 bg-white/60 p-8">
              <p className="text-sm font-medium">
                No external research recorded yet.
              </p>

              <p className="mt-2 text-sm leading-6 text-[#8a8a86]">
                {canResearch
                  ? "Research is ready to run."
                  : "ONIT will record its sources here once research is performed."}
              </p>
            </div>
          ) : (
            <div className="mt-4 space-y-4">
              {research.map(
                (item) => {
                  const domain =
                    getDomain(
                      item.url,
                      item.source,
                    );

                  return (
                    <div
                      key={
                        item.id
                      }
                      className="rounded-2xl border border-black/[0.08] bg-white p-6"
                    >
                      <div className="flex flex-col justify-between gap-4 sm:flex-row">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded-full bg-[#f7f7f5] px-3 py-1 text-xs font-medium text-[#73736e]">
                              {item.source ??
                                "External source"}
                            </span>

                            <span className="text-xs text-[#a0a09b]">
                              {
                                domain
                              }
                            </span>
                          </div>

                          <h3 className="mt-3 text-lg font-semibold">
                            {item.title ??
                              "Untitled source"}
                          </h3>
                        </div>

                        {item.url && (
                          <a
                            href={
                              item.url
                            }
                            target="_blank"
                            rel="noreferrer"
                            className="shrink-0 text-sm font-medium text-[#171717] underline decoration-black/20 underline-offset-4 hover:decoration-black"
                          >
                            Open source ↗
                          </a>
                        )}
                      </div>

                      {item.summary && (
                        <p className="mt-4 text-sm leading-7 text-[#595955]">
                          {
                            item.summary
                          }
                        </p>
                      )}

                      <div className="mt-5 rounded-xl bg-[#f7f7f5] p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#8a8a86]">
                          Why it matters
                        </p>

                        <p className="mt-2 text-sm leading-6 text-[#595955]">
                          {item.relevance &&
                          ![
                            "low",
                            "medium",
                            "high",
                          ].includes(
                            item.relevance.toLowerCase(),
                          )
                            ? item.relevance
                            : "This source was identified as relevant to the case and used as supporting research."}
                        </p>

                        {item.relevance &&
                          [
                            "low",
                            "medium",
                            "high",
                          ].includes(
                            item.relevance.toLowerCase(),
                          ) && (
                            <p className="mt-3 text-xs text-[#8a8a86]">
                              Relevance:{" "}
                              <span className="font-medium text-[#595955]">
                                {getRelevanceLabel(
                                  item.relevance,
                                )}
                              </span>
                            </p>
                          )}
                      </div>
                    </div>
                  );
                },
              )}
            </div>
          )}
        </section>

        {/* EVIDENCE TRAIL */}

        <section className="mt-12">
          <SectionLabel>
            EVIDENCE TRAIL
          </SectionLabel>

          <div className="mt-4 rounded-2xl border border-black/[0.08] bg-white p-6">
            <div className="grid gap-8 lg:grid-cols-[1fr_300px]">
              <div>
                <p className="text-sm font-medium">
                  How ONIT moved from information to a decision.
                </p>

                <div className="mt-6 space-y-6">

                  <Step
                    number="1"
                    title="Case facts"
                    description="Information supplied directly through the case."
                    state="complete"
                  />

                  <Step
                    number="2"
                    title="Evidence"
                    description={
                      evidence.length >
                      0
                        ? `${evidence.length} evidence item${
                            evidence.length ===
                            1
                              ? ""
                              : "s"
                          } available.`
                        : "No uploaded evidence yet."
                    }
                    state={
                      evidence.length >
                      0
                        ? "complete"
                        : normalizedStatus ===
                            "EVIDENCE_READY"
                          ? "current"
                          : "upcoming"
                    }
                  />

                  <Step
                    number="3"
                    title="External research"
                    description={
                      research.length >
                      0
                        ? `${research.length} source${
                            research.length ===
                            1
                              ? ""
                              : "s"
                          } recorded.`
                        : researchRunning
                          ? "ONIT is currently researching this case."
                          : "No external research recorded yet."
                    }
                    state={
                      research.length >
                      0
                        ? "complete"
                        : researchRunning ||
                            canResearch
                          ? "current"
                          : "upcoming"
                    }
                  />

                  <Step
                    number="4"
                    title="Decision"
                    description={
                      caseItem.recommended_action ??
                      "ONIT has not produced a recommendation yet."
                    }
                    state={
                      caseItem.recommended_action
                        ? "complete"
                        : "upcoming"
                    }
                  />

                  <Step
                    number="5"
                    title="Human approval"
                    description={
                      awaitingApproval
                        ? "Your review is required before proceeding."
                        : actionReady ||
                            submitted ||
                            waitingForResponse ||
                            followUpRequired ||
                            escalationRequired ||
                            resolved
                          ? "Human approval has been recorded."
                          : "Approval will be requested when the action is ready."
                    }
                    state={
                      actionReady ||
                      submitted ||
                      waitingForResponse ||
                      followUpRequired ||
                      escalationRequired ||
                      resolved
                        ? "complete"
                        : awaitingApproval
                          ? "current"
                          : "upcoming"
                    }
                  />

                  <Step
                    number="6"
                    title="Action submitted"
                    description={
                      submitted ||
                      waitingForResponse ||
                      followUpRequired ||
                      escalationRequired ||
                        resolved
                        ? "ONIT submitted the prepared action."
                        : "The approved action will be submitted for execution."
                    }
                    state={
                      submitted ||
                      waitingForResponse ||
                      followUpRequired ||
                      escalationRequired ||
                      resolved
                        ? "complete"
                        : actionReady ||
                          awaitingApproval
                          ? "current"
                          : "upcoming"
                    }
                  />

                  <Step
                    number="7"
                    title="Response received"
                    description={
                      responses.length >
                      0
                        ? `${responses.length} response${
                            responses.length ===
                            1
                              ? ""
                              : "s"
                          } received.`
                        : waitingForResponse ||
                            followUpRequired ||
                            escalationRequired ||
                            resolved
                          ? "ONIT is tracking the external response."
                          : "Waiting for the external organization to respond."
                    }
                    state={
                      responses.length >
                      0
                        ? "complete"
                        : waitingForResponse ||
                            followUpRequired ||
                            escalationRequired ||
                            resolved
                          ? "current"
                          : "upcoming"
                    }
                  />

                  <Step
                    number="8"
                    title="Resolution"
                    description={
                      resolved
                        ? "This case has been resolved."
                        : "The case will be resolved once a satisfactory response is received."
                    }
                    state={
                      resolved
                        ? "complete"
                        : "upcoming"
                    }
                  />
                </div>
              </div>

              <aside>
                <div className="rounded-2xl bg-[#f7f7f5] p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8a8a86]">
                    Decision support
                  </p>

                  <p className="mt-3 text-sm font-medium leading-6">
                    {caseItem.recommended_action ??
                      "No recommendation yet."}
                  </p>

                  <div className="mt-5">
                    <p className="text-xs text-[#8a8a86]">
                      Evidence strength
                    </p>

                    <div className="mt-2">
                      <EvidenceStrength
                        evidenceCount={
                          evidence.length
                        }
                        researchCount={
                          research.length
                        }
                      />
                    </div>
                  </div>

                  <div className="mt-5 border-t border-black/[0.06] pt-5">
                    <p className="text-xs text-[#8a8a86]">
                      Supporting material
                    </p>

                    <div className="mt-3 space-y-2 text-sm text-[#454542]">
                      <p>
                        {
                          evidence.length
                        }{" "}
                        evidence{" "}
                        {evidence.length ===
                        1
                          ? "item"
                          : "items"}
                      </p>

                      <p>
                        {
                          research.length
                        }{" "}
                        research{" "}
                        {research.length ===
                        1
                          ? "source"
                          : "sources"}
                      </p>
                    </div>
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </section>

        {/* PLAN */}

        {(caseItem.plan_summary ||
          caseItem.plan_steps) && (
          <section className="mt-12">
            <SectionLabel>
              EXECUTION PLAN
            </SectionLabel>

            <div className="mt-4 rounded-2xl border border-black/[0.08] bg-white p-6">
              {caseItem.plan_summary && (
                <p className="text-lg font-medium leading-7">
                  {
                    caseItem.plan_summary
                  }
                </p>
              )}

              {caseItem.plan_steps && (
                <div className="mt-5 whitespace-pre-line rounded-xl bg-[#f7f7f5] p-5 text-sm leading-7 text-[#454542]">
                  {
                    caseItem.plan_steps
                  }
                </div>
              )}
            </div>
          </section>
        )}

        {/* HUMAN REVIEW */}

        {awaitingApproval &&
          caseItem.approval_required !==
            false && (
            <section className="mt-12">
              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
                <div className="flex flex-col justify-between gap-6 md:flex-row md:items-start">
                  <div>
                    <p className="text-xs font-semibold tracking-[0.16em] text-amber-700">
                      HUMAN REVIEW REQUIRED
                    </p>

                    <h2 className="mt-2 text-xl font-semibold text-amber-950">
                      ONIT is ready for your decision.
                    </h2>

                    <p className="mt-3 max-w-2xl text-sm leading-6 text-amber-900/70">
                      ONIT has completed the available analysis and prepared an execution plan. Nothing will proceed without your approval.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() =>
                      setShowReview(
                        (value) =>
                          !value,
                      )
                    }
                    className="shrink-0 rounded-full bg-[#171717] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#30302d]"
                  >
                    {showReview
                      ? "Close review"
                      : "Review & approve"}
                  </button>
                </div>

                {showReview && (
                  <div className="mt-6 rounded-2xl border border-amber-900/10 bg-white p-6">
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8a8a86]">
                      Final review
                    </p>

                    <div className="mt-5 space-y-5">

                      <div>
                        <p className="text-xs text-[#8a8a86]">
                          Decision
                        </p>

                        <p className="mt-1 text-sm font-medium leading-6">
                          {caseItem.recommended_action ??
                            "No recommendation provided."}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-[#8a8a86]">
                          Why
                        </p>

                        <p className="mt-1 whitespace-pre-line text-sm leading-6 text-[#454542]">
                          {caseItem.decision_reason ??
                            "No decision reason provided."}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-[#8a8a86]">
                          Execution plan
                        </p>

                        <p className="mt-1 whitespace-pre-line text-sm leading-6 text-[#454542]">
                          {caseItem.plan_steps ??
                            caseItem.plan_summary ??
                            "No execution plan provided."}
                        </p>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-3">

                        <div className="rounded-xl bg-[#f7f7f5] p-4">
                          <p className="text-xs text-[#8a8a86]">
                            Evidence
                          </p>

                          <p className="mt-1 text-sm font-medium">
                            {
                              evidence.length
                            }{" "}
                            {evidence.length ===
                            1
                              ? "item"
                              : "items"}
                          </p>
                        </div>

                        <div className="rounded-xl bg-[#f7f7f5] p-4">
                          <p className="text-xs text-[#8a8a86]">
                            Research
                          </p>

                          <p className="mt-1 text-sm font-medium">
                            {
                              research.length
                            }{" "}
                            {research.length ===
                            1
                              ? "source"
                              : "sources"}
                          </p>
                        </div>

                        <div className="rounded-xl bg-[#f7f7f5] p-4">
                          <p className="text-xs text-[#8a8a86]">
                            Strength
                          </p>

                          <div className="mt-2">
                            <EvidenceStrength
                              evidenceCount={
                                evidence.length
                              }
                              researchCount={
                                research.length
                              }
                            />
                          </div>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-3 border-t border-black/[0.06] pt-5">
                        <button
                          type="button"
                          onClick={
                            approveAction
                          }
                          disabled={
                            approving
                          }
                          className="rounded-full bg-[#171717] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#30302d] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {approving
                            ? "Approving..."
                            : "Approve & continue →"}
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            setShowReview(
                              false,
                            )
                          }
                          disabled={
                            approving
                          }
                          className="rounded-full border border-black/10 bg-white px-5 py-3 text-sm font-medium text-[#595955] disabled:opacity-50"
                        >
                          Keep reviewing
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

        {/* ACTION READY */}

        {actionReady && (
          <section className="mt-12">
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
              <div className="flex items-start gap-4">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-sm font-semibold text-white">
                  ✓
                </div>

                <div>
                  <p className="text-xs font-semibold tracking-[0.16em] text-emerald-700">
                    ACTION READY
                  </p>

                  <h2 className="mt-2 text-xl font-semibold text-emerald-950">
                    Action is ready for human approval.
                  </h2>

                  <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-900/70">
                    ONIT has prepared the action below. Human approval is required before execution.
                  </p>

                  <div className="mt-5 rounded-xl border border-emerald-900/10 bg-white p-5">
                    <p className="text-xs uppercase tracking-[0.1em] text-[#8a8a86]">
                      Proposed action
                    </p>

                    <p className="mt-2 text-sm font-semibold">
                      {caseItem.recommended_action ??
                        "No action provided."}
                    </p>

                    {(caseItem.plan_steps ||
                      caseItem.plan_summary) && (
                      <p className="mt-4 whitespace-pre-line text-sm leading-7 text-[#454542]">
                        {caseItem.plan_steps ??
                          caseItem.plan_summary}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* RESOLVED */}

        {resolved && (
          <section className="mt-12">
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
              <p className="text-xs font-semibold tracking-[0.16em] text-emerald-700">
                RESOLUTION
              </p>

              <h2 className="mt-2 text-xl font-semibold text-emerald-950">
                This case has been resolved.
              </h2>

              <p className="mt-2 text-sm leading-6 text-emerald-900/70">
                ONIT has recorded the case as complete.
              </p>

              {responses.length >
               0 && (
                <div className="mt-5 rounded-xl border border-emerald-900/10 bg-white p-5">
                  <p className="text-xs uppercase tracking-[0.1em] text-[#8a8a86]">
                    Latest response
                  </p>

                  <p className="mt-2 text-sm font-semibold">
                    {
                      responses[responses.length -
                        1].response_type
                    }
                  </p>

                  <p className="mt-2 whitespace-pre-line text-sm leading-7 text-[#454542]">
                    {
                      responses[responses.length -
                        1].message
                    }
                  </p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* RESPONSES */}

        <section className="mt-12">
          <SectionLabel>
            RESPONSES
          </SectionLabel>

          <p className="mt-1 text-sm text-[#73736e]">
            Responses received from the external organization.
          </p>

          {responses.length ===
          0 ? (
            <div className="mt-4 rounded-2xl border border-dashed border-black/10 bg-white/60 p-8">
              <p className="text-sm font-medium">
                No responses recorded yet.
              </p>

              <p className="mt-2 text-sm leading-6 text-[#8a8a86]">
                Responses will appear here once the external organization replies.
              </p>
            </div>
          ) : (
            <div className="mt-4 space-y-4">
              {responses.map(
                (item) => (
                  <div
                    key={
                      item.id
                    }
                    className="rounded-2xl border border-black/[0.08] bg-white p-6"
                  >
                    <div className="flex flex-col justify-between gap-3 sm:flex-row">
                      <div>
                        <p className="text-sm font-semibold">
                          {formatLabel(
                            item.response_type,
                          )}
                        </p>

                        <p className="mt-1 text-xs text-[#8a8a86]">
                          {item.resolved
                            ? "Resolved"
                            : "Follow-up required"}
                        </p>
                      </div>

                      <span className="text-xs text-[#a0a09b]">
                        {formatDate(
                          item.created_at,
                        )}
                      </span>
                    </div>

                    <p className="mt-4 whitespace-pre-line text-sm leading-7 text-[#595955]">
                      {item.message}
                    </p>
                  </div>
                ),
              )}
            </div>
          )}
        </section>

        {/* RESPONSE RECORDING */}

        {(waitingForResponse ||
          followUpRequired) && (
          <section className="mt-12">
            <SectionLabel>
              RECORD RESPONSE
            </SectionLabel>

            <div className="mt-4 rounded-2xl border border-black/[0.08] bg-white p-6">
              <p className="text-sm font-medium">
                Simulate an external response for development and testing.
              </p>

              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-medium uppercase tracking-[0.08em] text-[#8a8a86]">
                    Response type
                  </label>

                  <input
                    type="text"
                    id="response-type"
                    defaultValue="REFUND_APPROVED"
                    className="mt-2 w-full rounded-xl border border-black/10 bg-[#f7f7f5] px-4 py-2.5 text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium uppercase tracking-[0.08em] text-[#8a8a86]">
                    Message
                  </label>

                  <input
                    type="text"
                    id="response-message"
                    defaultValue="Airline confirmed the refund."
                    className="mt-2 w-full rounded-xl border border-black/10 bg-[#f7f7f5] px-4 py-2.5 text-sm"
                  />
                </div>
              </div>

              <div className="mt-4 flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm text-[#454542]">
                  <input
                    type="checkbox"
                    id="response-resolved"
                    defaultChecked
                    className="h-4 w-4 rounded border-black/20"
                  />

                  Resolves case
                </label>
              </div>

              <div className="mt-5">
                <button
                  type="button"
                  onClick={() => {
                    const type =
                      document.getElementById(
                        "response-type",
                      ) as
                        | HTMLInputElement
                        | null;

                    const message =
                      document.getElementById(
                        "response-message",
                      ) as
                        | HTMLInputElement
                        | null;

                    const resolved =
                      document.getElementById(
                        "response-resolved",
                      ) as
                        | HTMLInputElement
                        | null;

                    if (
                      !type ||
                      !message
                    ) {
                      return;
                    }

                    void recordResponse(
                      type.value ||
                        "UNKNOWN",
                      message.value,
                      resolved
                        ? resolved
                            .checked
                        : false,
                    );
                  }}
                  disabled={
                    recordResponseLoading
                  }
                  className="rounded-full bg-[#171717] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#30302d] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {recordResponseLoading
                    ? "Recording..."
                    : "Record response →"}
                </button>
              </div>
            </div>
          </section>
        )}

        {/* ACTIVITY */}

        <section className="mt-12">
          <SectionLabel>
            ACTIVITY
          </SectionLabel>

          <div className="mt-4 rounded-2xl border border-black/[0.08] bg-white p-6">
            {activities.length ===
            0 ? (
              <p className="text-sm text-[#8a8a86]">
                No activity recorded yet.
              </p>
            ) : (
              <div className="space-y-6">
                {activities.map(
                  (
                    activity,
                    index,
                  ) => (
                    <div
                      key={
                        activity.id
                      }
                      className="flex gap-4"
                    >
                      <div className="flex flex-col items-center">
                        <span
                          className={[
                            "mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full",
                            index ===
                            activities.length -
                              1
                              ? "bg-amber-500"
                              : "bg-emerald-500",
                          ].join(" ")}
                        />

                        {index !==
                          activities.length -
                            1 && (
                          <span className="mt-2 h-full w-px bg-black/[0.08]" />
                        )}
                      </div>

                      <div className="min-w-0 flex-1 pb-1">
                        <div className="flex flex-col justify-between gap-1 sm:flex-row">
                          <p className="text-sm font-medium">
                            {formatStatus(
                              activity.event_type,
                            )}
                          </p>

                          <span className="text-xs text-[#a0a09b]">
                            {formatDate(
                              activity.created_at,
                            )}
                          </span>
                        </div>

                        <p className="mt-1 text-sm leading-6 text-[#73736e]">
                          {
                            activity.message
                          }
                        </p>
                      </div>
                    </div>
                  ),
                )}
              </div>
            )}
          </div>
        </section>

        {/* FOOTER */}

        <footer className="mt-16 border-t border-black/[0.06] py-8 text-xs text-[#a0a09b]">
          ONIT · Your problems, moving forward.
        </footer>
      </div>
    </main>
  );
}
