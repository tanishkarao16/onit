````markdown
# ONIT

### Your problems, moving forward.

ONIT is an evidence-backed case-resolution agent that helps move messy real-world problems from **problem → evidence → research → decision → action plan**, with human approval before consequential action.

Most AI assistants stop at an answer.

**ONIT is designed to move the case forward.**

---

## The Problem

Real-world problems rarely arrive as clean, structured tasks.

They arrive as emails, PDFs, receipts, screenshots, policy documents, free-form descriptions, incomplete information, and conflicting evidence.

A typical AI assistant can summarize the situation or suggest what to do.

But the user still has to:

1. Organize the case
2. Extract important facts
3. Research current information
4. Determine which sources are trustworthy
5. Connect external evidence to their situation
6. Decide what to do
7. Turn that decision into concrete next steps
8. Know when human approval is required

**ONIT brings these steps together into one persistent case workflow.**

---

## How It Works

```text
Problem
   ↓
Persistent Case
   ↓
Document Understanding
   ↓
Case Analysis
   ↓
Live Web Research
   ↓
Evidence Synthesis
   ↓
Decision
   ↓
Resolution Plan
   ↓
Human Approval
   ↓
Action
````

The user gives ONIT the information they already have.

ONIT builds the case, extracts evidence, researches what needs to be verified, produces an evidence-backed decision, and turns that decision into a resolution plan.

---

## Core Workflow

### 1. Case Intake

The user describes their problem in natural language.

For example:

> My Japan Airlines flight from Tokyo to Delhi was cancelled by the airline due to operational reasons. I paid ¥52,800 and have not received a refund. I did not request the cancellation. I contacted the airline about the refund and want to understand whether I am eligible for a refund and what I should do next.

The user does not need to understand ONIT's internal workflow.

---

### 2. Persistent Case

ONIT converts the problem into a persistent case.

The case maintains:

* Problem description
* Organization
* Structured case information
* Evidence
* Research
* Decisions
* Resolution plan
* Approval state
* Activity history

All stages operate on the same case.

---

### 3. Document Understanding with Nutrient

When supporting documents are provided, ONIT uses **Nutrient Document Web Services (DWS)** for document processing and fact extraction.

For example, a cancellation document can produce structured facts such as:

* Passenger
* Booking reference
* Organization
* Cancellation date
* Amount paid
* Currency
* Refund status
* Requested resolution
* Supporting facts

### Why Nutrient?

Nutrient handles the document-understanding work so ONIT can reason over structured evidence rather than treating the document as an opaque block of text.

The extracted facts become part of the persistent case and can be used by later analysis and decision stages.

---

### 4. Case Analysis

ONIT analyzes the case before making a recommendation.

The analysis identifies:

* What is known
* What is supported by the user's evidence
* What requires external verification
* What remains uncertain

This prevents the system from immediately turning a user description into a conclusion.

---

### 5. Live Web Research with SerpApi

Real-world information changes.

Policies, procedures, requirements, and eligibility conditions may not be reliably answered from model knowledge alone.

ONIT therefore uses **SerpApi** to perform live web research relevant to the specific case.

The research process can use the organization identified in the case to make searches more specific and prioritize authoritative sources.

For example:

```text
Japan Airlines
+
flight cancellation
+
refund
+
applicable policy
```

Research results are stored with the case.

ONIT can expose:

* Research sources
* Source URLs
* Relevance
* Supporting evidence

This makes the research traceable instead of invisible.

---

### 6. Evidence Synthesis

ONIT brings together two evidence streams.

#### Case Evidence

Information supplied by the user or extracted from their documents.

#### External Evidence

Information retrieved from current external sources through live research.

The system can therefore distinguish between:

```text
What happened?
      ↓
What does current external information say?
      ↓
How do those facts relate?
      ↓
What can reasonably be concluded?
```

---

### 7. Evidence-Backed Decision

ONIT synthesizes the available evidence into a decision.

A decision can include:

* Recommendation
* Reasoning
* Supporting evidence
* Evidence strength
* Confidence
* Uncertainty
* Relevant sources

The objective is not to hide uncertainty.

> **If the evidence is incomplete, the system should be able to show that it is incomplete.**

---

### 8. Resolution Plan

A recommendation alone still leaves work for the user.

ONIT converts the decision into a concrete resolution plan.

The plan can contain:

* Required next actions
* Information or documents needed
* Verification steps
* Sequencing
* Follow-up actions

The workflow moves from:

> "Here is what I think."

to:

> "Here is the evidence-backed plan for moving this case forward."

---

### 9. Human Approval

ONIT intentionally includes a human-control boundary.

The system does **not** claim that an external action happened when it did not.

When a consequential action requires human approval, the case enters:

```text
AWAITING_APPROVAL
```

The human remains in control before the system proceeds toward an external action.

> **The goal is not autonomous action at any cost. The goal is to move the problem forward while keeping the human in control.**

---

# Why ONIT Is Different

ONIT is not primarily a chatbot.

**It is a case-resolution system.**

| Traditional AI Assistant           | ONIT                                 |
| ---------------------------------- | ------------------------------------ |
| Answers a question                 | Builds a persistent case             |
| Primarily conversational           | Workflow-oriented                    |
| May rely on model knowledge        | Uses live research                   |
| Documents are input                | Documents become structured evidence |
| Gives a recommendation             | Produces an evidence-backed decision |
| Stops at the answer                | Generates a resolution plan          |
| May blur recommendation and action | Separates approval from action       |
| Limited traceability               | Maintains case evidence and activity |

---

# Example Use Case

The current demonstration uses a **synthetic flight-cancellation case**.

> **DEMO CASE — SYNTHETIC DOCUMENT**
>
> This demonstration does not represent a real customer incident.

The example involves a Japan Airlines flight cancellation and a missing refund.

ONIT processes the case through:

```text
Natural-language problem
        ↓
Persistent case
        ↓
Synthetic document
        ↓
Nutrient extraction
        ↓
Case analysis
        ↓
SerpApi live research
        ↓
Evidence synthesis
        ↓
Decision
        ↓
Resolution plan
        ↓
Human approval
```

The flight scenario is only a demonstration.

**The underlying case-resolution workflow is not flight-specific.**

The same architecture can support:

* Insurance claims
* Billing disputes
* Consumer disputes
* Warranty cases
* Travel disruptions
* Administrative procedures
* Service issues
* Document-heavy support workflows

---

# Architecture

```text
┌───────────────────────────────────────────────┐
│                    USER                       │
│                                               │
│        Problem + Documents + Context          │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│                 ONIT FRONTEND                 │
│                                               │
│             Next.js / React / TS              │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│                ONIT CASE ENGINE               │
│                                               │
│  Case Creation                                │
│       ↓                                       │
│  Analysis                                     │
│       ↓                                       │
│  Research                                     │
│       ↓                                       │
│  Evidence                                     │
│       ↓                                       │
│  Decision                                     │
│       ↓                                       │
│  Resolution Plan                              │
│       ↓                                       │
│  Human Approval                               │
└──────────────┬─────────────────┬──────────────┘
               │                 │
               ▼                 ▼
       ┌──────────────┐   ┌──────────────┐
       │   Nutrient   │   │   SerpApi    │
       │     DWS      │   │ Live Search  │
       └──────┬───────┘   └──────┬───────┘
              │                  │
              ▼                  ▼
       Structured Facts    External Sources
              │                  │
              └────────┬─────────┘
                       ▼
                Evidence Synthesis
                       │
                       ▼
                 Decision + Plan
                       │
                       ▼
                Human Approval
```

---

# Technology Stack

### Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS

### Backend

* Python
* FastAPI
* SQLAlchemy
* SQLite

### Document Processing

* Nutrient Document Web Services

### Web Research

* SerpApi

### Deployment

* Vercel
* Render

---

# Project Structure

```text
onit/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── db/
│   │   ├── integrations/
│   │   ├── models/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── app/
│   ├── components/
│   └── ...
│
└── README.md
```

---

# Running Locally

## Prerequisites

* Python 3.11+
* Node.js
* npm

## Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

## Frontend

In another terminal:

```bash
cd frontend

npm install
npm run dev
```

Frontend:

```text
http://localhost:3000
```

---

# Environment Variables

Configure the required integration credentials in the backend environment.

```env
SERPAPI_API_KEY=your_serpapi_api_key
NUTRIENT_API_KEY=your_nutrient_api_key
```

Never commit real API credentials to the repository.

---

# Testing

Run the backend test suite:

```bash
cd backend
pytest
```

---

# Live Demo

**ONIT:**
[https://onit-agent.vercel.app/](https://onit-agent.vercel.app/)

**Backend API:**
[https://onit-backend-p09z.onrender.com/](https://onit-backend-p09z.onrender.com/)

---

# Hackathon Integrations

## Nutrient

Nutrient Document Web Services is used for a core document-understanding operation.

**Heavy lifting:** document processing and extraction of structured case facts.

Those extracted facts become evidence inside the ONIT case-resolution workflow.

## SerpApi

SerpApi provides live web research for case-specific external evidence.

ONIT uses the results to ground decisions in current sources and make the research visible as part of the case.

---

# Design Principles

### Evidence before confidence

A confident answer without sufficient evidence is not necessarily a useful answer.

### Persistent cases

The problem, evidence, research, decision, and plan belong to the same case.

### Live information when needed

Current external information should be retrieved when it materially affects the decision.

### Explicit uncertainty

The system should distinguish between known facts, supported conclusions, and remaining uncertainty.

### Human control

Consequential external actions should not be represented as completed unless they actually occurred.

### Actionability

The output should help move the case forward, not simply explain the situation.

---

# Roadmap

Future versions of ONIT can extend the case engine toward:

* Richer document types
* Additional evidence sources
* Broader organization and domain detection
* More advanced source verification
* Additional case categories
* Deeper action integrations
* Case follow-up and monitoring
* Human-in-the-loop workflows for higher-stakes decisions

---

# License

MIT License.

---

# ONIT

### Your problems, moving forward.

**From messy information to evidence-backed action.**

```
```
