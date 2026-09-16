# Task 6 — AI Email Triage & RAG Assistant

**DevSynt AI Internship Program — Practical Evaluation Project**

An automated email management system that monitors a Gmail inbox, classifies incoming emails by intent and priority using Gemini AI, and routes each one to the correct action — RAG-grounded reply, HR forward, manager escalation, meeting notification, urgent alert, spam archive, or human review — with full logging and duplicate protection via Supabase.

**Core principle followed:** AI does not always answer. When a question falls outside the knowledge base, or an email doesn't fit a clear automated action, it is routed to a human instead of guessed at.

---

## 1. Overview

This project extends the Task 5 RAG chatbot (real-estate knowledge base: Company Overview, Property Listings, Services & Fees, FAQs, Policies) by plugging it behind a live email inbox instead of a chat widget. New emails are automatically read, classified, and routed through one of seven decision paths.

## 2. Architecture

```
Email (Gmail) → Parser (Gmail Trigger) → Dedup Check (Supabase)
              → AI Classification (Gemini) → Decision Engine (Switch)
              → ┬─ General/Sales Query → RAG Lookup (FastAPI) → grounded? 
              │                                    ├─ yes → Email Reply
              │                                    └─ no  → Human Review (Discord)
              ├─ Job Application     → Forward to HR (Email) + Discord Alert
              ├─ Project/Internal    → Forward to Manager (Email) + Discord Alert
              ├─ Meeting Request     → Notify Responsible Person (Email) + Discord Alert
              ├─ Urgent/Critical     → Immediate Discord Alert
              ├─ Promotional/Spam    → Archive (No-Op)
              └─ Uncategorized       → Human Review (Discord)
              → Log outcome to Supabase (email_logs table)
```

## 3. Tech Stack

- **Orchestration:** n8n (self-hosted, desktop)
- **AI Classification:** Google Gemini (via n8n's native Gemini node)
- **RAG Backend:** FastAPI + FAISS + Gemini (reused from Task 5, unchanged knowledge base)
- **Email:** Gmail API (via n8n's Gmail Trigger and Send nodes)
- **Notifications:** Discord (via incoming webhooks)
- **Logging & Dedup:** Supabase (PostgreSQL)

No paid services are required beyond free tiers of the above.

## 4. Setup

### 4.1 RAG Backend (reused from Task 5)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
Runs on `http://127.0.0.1:8000`. The `/chat` endpoint returns `{ answer, sources, grounded }` — the `grounded` boolean is the signal the automation uses to decide between an AI reply and human escalation.

### 4.2 Environment Variables
`.env` in `backend/` (same as Task 5): Gemini API key for the RAG pipeline.

### 4.3 n8n Workflow
1. Import the workflow JSON (see `/workflow` in this repo).
2. Configure credentials:
   - **Gmail OAuth2** — a dedicated test inbox (not a personal account), scoped for read/send/modify.
   - **Google Gemini** — same API key as the RAG backend, or a separate one.
   - **Supabase** — Project URL + legacy `service_role` key (Settings → API → "Legacy anon, service_role API keys" tab).
3. Create four Discord channels with incoming webhooks: `#hr-notifications`, `#manager-notifications`, `#meeting-notifications`, `#urgent-notifications`, `#human-review` (five, actually — see note in Limitations on channel naming).
4. Run the SQL below in Supabase to create the logging table.

### 4.4 Supabase Table
```sql
create table email_logs (
  id bigint generated always as identity primary key,
  message_id text unique not null,
  sender text,
  subject text,
  category text,
  priority text,
  requires_human boolean,
  ai_decision text,
  action_taken text,
  rag_used boolean default false,
  grounded boolean,
  response_sent boolean default false,
  forwarded_to text,
  discord_status text,
  error_status text,
  created_at timestamptz default now()
);
```
The `message_id text unique` constraint is what powers duplicate protection.

## 5. Email Intake & Parsing

n8n's Gmail Trigger node polls the inbox and returns pre-parsed fields (`subject`, `text` — clean plain-text body with HTML/quoted-reply noise stripped, `from`, `to`, `messageId`, `date`), so no separate custom parsing step was needed for the base case.

## 6. Duplicate Protection

Before any AI call is made, a Supabase "Get Many Rows" query checks `email_logs` for an existing row matching the incoming `messageId`. If found, the email is dropped (No-Op) without reprocessing. If not found, it proceeds to classification. This runs *before* the Gemini call specifically to avoid wasting API calls on emails already handled.

## 7. AI Classification & Routing Logic

A single Gemini prompt classifies each email into one of eleven categories (`general_query`, `sales_inquiry`, `job_application`, `project_related`, `internal_communication`, `meeting_request`, `urgent_request`, `complaint`, `promotional`, `spam`, `other`), and assigns a `priority` and `requires_human` flag. A small mapping step groups these into seven routing buckets (`rag`, `hr`, `manager`, `meeting`, `urgent`, `archive`, `human_review`) which a Switch node uses to branch the workflow.

Unrecognized or ambiguous emails fall through to `human_review` by default — the workflow never guesses at an action for a category it doesn't have a defined path for.

## 8. RAG Implementation & Grounding Guardrail

For `general_query` / `sales_inquiry` emails, the subject + body are sent to the existing Task 5 RAG endpoint. The endpoint returns a `grounded` boolean based on whether relevant chunks were found in the knowledge base above a similarity threshold.

- `grounded: true` → the AI's answer is emailed back to the sender.
- `grounded: false` → **no reply is sent**; the email is instead routed to the `#human-review` Discord channel with the original question, so a person can respond. This directly implements the task's "AI must not invent information" requirement — a not-found answer is never auto-sent.

## 9. Human Escalation Logic

An email reaches a human in three situations:
1. Its category doesn't map to a known bucket (`other` → `human_review`).
2. It's flagged `urgent_request` (immediate Discord alert, human handles directly).
3. A `general_query`/`sales_inquiry` gets a `grounded: false` response from the RAG endpoint.

## 10. Discord Integration

Each branch (HR, Manager, Meeting, Urgent, Human Review) posts a formatted alert to its own Discord channel via incoming webhook, containing sender, subject, category/priority, and relevant context — enough detail to act on without opening the email client.

## 11. Logging & Reliability

Every processed email is logged to the `email_logs` Supabase table with its classification, routing decision, action taken, RAG usage, grounding result, and whether a reply/forward was sent. The Gemini classification node has automatic retry enabled (via n8n node settings) to handle transient "service unavailable" errors from the AI provider. A malformed/unparseable AI response falls back to a safe default (`category: other`, `requires_human: true`) rather than crashing the workflow.

## 12. Limitations

- **Conversation/thread awareness (Test Scenario #10):** Gmail's `threadId` is available in the trigger data and is used when replying via RAG so responses land in the same email thread. However, the AI classification step does not currently re-read prior messages in a thread when classifying or answering a follow-up — each email is evaluated independently of conversation history. This is a scoped limitation for this cohort's submission rather than a full conversational-memory implementation.
- **Attachments** (e.g. resumes on job applications) are not automatically re-attached when forwarding to HR — the forwarded email includes the original sender, subject, and body text, but attachment handling would need an additional Gmail API step to download and re-attach binary files.
- **Archive branch** is a true no-op (nothing is sent anywhere, per the task's "never forward promotional/spam" rule) rather than actively moving the original email to a Gmail label/folder — this satisfies the requirement without adding Gmail-side state changes.
- Classification quality depends on Gemini's judgment on ambiguous emails (e.g. a job application was once scored `low` priority) — this is a model behavior, not a pipeline defect, and could be tightened with more explicit priority rules in the prompt.

## 13. Test Report

See `TEST_REPORT.md` for the 10 required test scenarios, expected vs. actual results, and issues found during testing.

## 14. Demo Video

[Demo video link — TODO: add after recording]

## 15. LinkedIn Post

[LinkedIn post link — TODO: add after publishing, per program requirement]
