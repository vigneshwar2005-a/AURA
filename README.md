#** AURA — Autonomous Unified Razorpay Agent

AI-powered autonomous payment orchestration for exporters.

AURA is a multi-agent payment control layer that understands natural-language payment requests, analyzes vendor and export-compliance context, evaluates risk, and allows Razorpay payment execution only after explicit human authorization.

Core Flow

User Request
     ↓
AI Intent Layer
(Qwen 2.5:3B via Ollama)
     ↓
AURA Brain
     ↓
Vendor / Compliance / Commerce Agents
     ↓
Risk Engine
     ↓
PAYMENT_READY / REVIEW_REQUIRED / BLOCK_PAYMENT
     ↓
Human Approval
     ↓
Razorpay Checkout
     ↓
Payment Captured
     ↓
Audit Trail & Payment History

---

## Why AURA?

Payment execution is only one part of an exporter payment workflow.

Before money is moved, a business may need to understand:

-  Who is being paid? 
-  Is the vendor payment overdue? 
-  Are there MSME-related payment risks? 
-  Are export compliance requirements satisfied? 
-  Are important export documents available? 
-  Should the payment proceed, require review, or be blocked? 
-  Can an AI system be trusted to directly execute a financial transaction? 

AURA addresses this gap by acting as an intelligent control layer between the user's payment intent and payment execution.

---

## Key Features

-  Natural-language payment requests 
-  AI-powered intent extraction 
-  Local Qwen 2.5:3B inference through Ollama 
-  Multi-agent orchestration 
-  Vendor payment-risk analysis 
-  MSME / Section 43B(h)-related risk detection 
-  Export compliance checks 
-  Risk scoring 
-  Deterministic payment decisions 
-  Human approval before Razorpay execution 
-  Razorpay Test Mode integration 
-  Payment capture 
-  Payment reconciliation 
-  Audit trail 
-  Payment history 
-  Missing amount protection 
-  High-risk payment blocking 
-  Explainable payment decisions 

---

#** AI Intent Layer

AURA includes a dedicated AI Intent Layer powered by:

- **Qwen 2.5:3B** 
- **Ollama** 
-  Local inference during the prototype 

The AI layer allows users to describe payment requests naturally instead of filling out multiple structured fields.

### Example

Pay ABC Exports ₹50,000 for invoice INV-102.
The payment is due within 5 days.

Qwen can extract structured information such as:

{
  "intent": "payment",
  "amount": 50000,
  "currency": "INR",
  "vendor_name": "ABC Exports",
  "invoice_number": "INV-102",
  "due_days": 5,
  "is_overdue": false,
  "requires_compliance": false
}

The structured information is then used by the AURA Brain for agent routing and workflow enrichment.

### AI Safety Boundary

Qwen does **not** approve or execute payments.

The architecture intentionally separates AI understanding from financial authorization:

AI
 ↓
Understands the request

Agents
 ↓
Analyze business context

Risk Engine
 ↓
Makes deterministic risk decision

Human
 ↓
Explicitly authorizes payment

Razorpay
 ↓
Executes payment

> **AI understands. Agents analyze. Risk Engine decides. Human authorizes. Razorpay executes.**

---

#** AURA Brain

The AURA Brain is the main orchestration layer.

It:

1.  Receives the natural-language request 
2.  Runs the AI Intent Layer 
3.  Performs deterministic intent detection 
4.  Extracts payment entities 
5.  Determines which agents are required 
6.  Executes the relevant agents 
7.  Collects risk signals 
8.  Passes those signals to the Risk Engine 
9.  Produces the final payment decision 
10.  Prepares the payment context for human approval 

The Brain never creates a Razorpay order during initial analysis.

---

#** Agents

## Vendor Agent

The Vendor Agent evaluates vendor payment risk.

It checks:

-  MSME vendor status 
-  Payment deadlines 
-  Overdue payments 
-  Payment timing 
-  Section 43B(h)-related risk 

### Example

Payment due within 5 days
        ↓
MEDIUM RISK
        ↓
REVIEW_REQUIRED

An overdue payment can result in:

HIGH RISK
    ↓
BLOCK_PAYMENT

---

## Compliance Agent

The Compliance Agent evaluates exporter-related requirements such as:

-  GST LUT 
-  Shipping Bill 
-  Export Invoice 
-  EDPMS realization 
-  e-FIRC / realization proof 

For example, if two configured compliance items are outstanding:

2 Missing Items
      ↓
MEDIUM
      ↓
REVIEW_REQUIRED

If three or more configured compliance items are missing:

3+ Missing Items
      ↓
HIGH
      ↓
BLOCK_PAYMENT

---

## Commerce Agent

The Commerce Agent prepares the payment context for Razorpay.

During initial AURA analysis:

Razorpay Order = NOT CREATED

The Razorpay order is created only after explicit human approval.

This ensures that analysis and execution remain separate.

---

#** Risk Engine

The Risk Engine combines risk signals from the specialized agents and produces a deterministic final risk level.

| RiskScoreDecision |    |                  |
| ----------------- | -- | ---------------- |
| LOW               | 25 | PAYMENT\_READY   |
| MEDIUM            | 60 | REVIEW\_REQUIRED |
| HIGH              | 90 | BLOCK\_PAYMENT   |

### Decision Flow

LOW
 ↓
PAYMENT_READY

MEDIUM
 ↓
REVIEW_REQUIRED

HIGH
 ↓
BLOCK_PAYMENT

The final financial decision does not depend on an AI-generated approval.

---

#** Human Approval

AURA introduces an explicit human authorization boundary.

The initial analysis can produce:

PAYMENT_READY

or:

REVIEW_REQUIRED

But the Razorpay payment is not executed automatically.

The user must explicitly approve the payment.

AURA Analysis
      ↓
Decision
      ↓
Human Approval
      ↓
Razorpay Order
      ↓
Razorpay Checkout
      ↓
Payment Captured

For:

BLOCK_PAYMENT

the payment cannot proceed through the normal approval flow.

---

#** Razorpay Payment Flow

AURA Analysis
     ↓
PAYMENT_READY
     ↓
APPROVE PAYMENT
     ↓
Razorpay Order
     ↓
Razorpay Checkout
     ↓
Payment Captured
     ↓
Payment History

AURA has been integrated with Razorpay Test Mode for the prototype.

---

#** Demo Scenarios

## 1. LOW Risk

### Request

Pay ABC Exports ₹10,000 for invoice INV-103

### Expected

Risk: LOW
Score: 25
Decision: PAYMENT_READY

No Razorpay order is created before approval.

---

## 2. MEDIUM Risk

### Request

Pay ABC Exports ₹50,000 for invoice INV-102.
The payment is due within 5 days.

### Expected

Risk: MEDIUM
Score: 60
Decision: REVIEW_REQUIRED

AURA requires human review before continuing.

---

## 3. HIGH Risk

### Request

Pay ABC Exports ₹50,000 for invoice INV-102.
The payment is overdue.

### Expected

Risk: HIGH
Score: 90
Decision: BLOCK_PAYMENT

No normal payment approval path is provided.

---

## 4. Export Compliance

### Request

Pay ABC Exports ₹50,000 for invoice INV-102
after checking the GST LUT, shipping bill,
export invoice, EDPMS realization and e-FIRC.

### Expected

AURA routes the request through the Compliance Agent.

The configured demo scenario identifies:

Missing:
- EDPMS realization
- e-FIRC / realization proof

Result:

Risk: MEDIUM
Score: 60
Decision: REVIEW_REQUIRED

---

## 5. Missing Amount

### Request

Pay ABC Exports for invoice INV-102

AURA does not invent an amount.

The workflow is blocked until an explicit payment amount is provided.

Payment amount missing
        ↓
INVALID_REQUEST
        ↓
NO RAZORPAY EXECUTION

---

## 6. No Order Before Approval

### Request

Pay ABC Exports ₹10,000 for invoice INV-103

Before clicking `APPROVE PAYMENT`:

Razorpay Order: Not Created

Only after explicit human approval:

Razorpay Order
     ↓
Checkout
     ↓
Payment

---

#** Audit Trail

AURA records important workflow events including:

-  Request received 
-  AI intent analysis 
-  Intent classification 
-  Agent execution 
-  Compliance evaluation 
-  Risk evaluation 
-  Human review requirement 
-  Payment blocking 
-  Payment readiness 
-  Payment execution status 

This provides visibility into **why a payment was allowed, reviewed, or blocked**.

---

#** Technology Stack

### Backend

-  Python 
-  FastAPI 
-  Pydantic 
-  Uvicorn 

### AI

-  Qwen 2.5:3B 
-  Ollama 
-  Local AI Intent Layer 

### Payments

-  Razorpay API 
-  Razorpay Test Mode 
-  Razorpay Checkout 

### Frontend

-  HTML 
-  CSS 
-  JavaScript 

### Configuration

-  python-dotenv 

---

#** Project Structure

AURA/
│
├── backend/
│   │
│   ├── agents/
│   │   ├── brain.py
│   │   ├── compliance.py
│   │   ├── commerce.py
│   │   └── vendor.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   │
│   ├── services/
│   │   ├── ai_intent.py
│   │   ├── exporter_engine.py
│   │   └── risk_engine.py
│   │
│   ├── data/
│   │
│   ├── documents/
│   │
│   ├── frontend/
│   │
│   ├── tests/
│   │
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
│
├── .gitignore
└── README.md

---

#** Setup

## 1. Clone the Repository

git clone https://github.com/vigneshwar2005-a/AURA.git
cd AURA

## 2. Create Virtual Environment

cd backend
python -m venv venv

## 3. Install Dependencies

.\venv\Scripts\python.exe -m pip install -r requirements.txt

## 4. Configure Razorpay

Copy `.env.example` to `.env`.

### Windows PowerShell

Copy-Item .env.example .env

Add your Razorpay Test Mode credentials:

RAZORPAY_KEY_ID=your_razorpay_test_key_id
RAZORPAY_KEY_SECRET=your_razorpay_test_key_secret
RAZORPAY_WEBHOOK_SECRET=your_razorpay_webhook_secret

**Never commit the real** **`.env`** **file.**

---

#** Run AURA

## Backend

From:

C:\Aura\backend

Run:

.\venv\Scripts\python.exe -m uvicorn main:app --reload

Backend:

http://127.0.0.1:8000

---

## Frontend

Open another terminal.

From:

C:\Aura

Run:

.\backend\venv\Scripts\python.exe -m http.server 5500 --directory backend\frontend

Open:

http://127.0.0.1:5500/index.html

---

#** Run the AI Intent Layer

Make sure Ollama is running with the Qwen model:

qwen2.5:3b

The AURA AI Intent Layer communicates with the local Ollama endpoint:

http://127.0.0.1:11434/api/generate

The AI layer is used for intent understanding and structured extraction only.

It does not execute payments.

---

#** Security & Safety

AURA is designed with multiple financial safety boundaries.

-  Real Razorpay credentials are stored only in `.env` 
- `.env` is excluded from Git 
- `.env.example` contains placeholders only 
-  AI does not directly approve payments 
-  AI does not directly execute payments 
-  Razorpay orders are not created during initial analysis 
-  Human approval is required before Razorpay execution 
-  High-risk payments are blocked 
-  Missing payment amounts are rejected 
-  Risk decisions are deterministic 
-  Payment activity is recorded in an audit trail 

---

#** Project Status

**Buildathon-ready prototype using Razorpay Test Mode.**

The prototype demonstrates:

Natural Language Request
        ↓
Qwen AI Intent Layer
        ↓
AURA Brain
        ↓
Multi-Agent Analysis
        ↓
Deterministic Risk Engine
        ↓
Human Authorization
        ↓
Razorpay Checkout
        ↓
Captured Payment
        ↓
Audit & Payment History