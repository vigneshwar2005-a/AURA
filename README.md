AURA — Autonomous Unified Razorpay Agent

AI-powered autonomous payment orchestration for exporters.

AURA is a multi-agent payment control layer that understands payment requests, analyzes vendor and export-compliance context, evaluates risk, and allows Razorpay payment execution only after explicit human authorization.

Core Flow

Business User
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
Captured Payment
↓
Audit Trail & Payment History

Key Features
Natural-language payment intent understanding
Multi-agent orchestration
Vendor payment-timing analysis
MSME / Section 43B(h) risk detection
Export compliance checks
Risk scoring and payment decisions
Explicit human approval before payment execution
Razorpay Test Mode integration
Razorpay payment reconciliation
Activity and audit trail
Payment history
Missing and invalid amount protection
High-risk payment blocking
Agent Architecture
AURA Brain

The central orchestration layer that understands payment intent, extracts entities, selects the required agents, combines their results, and produces the final payment decision.

Vendor Agent

Evaluates vendor payment risk, including MSME payment timelines, user-stated deadlines, overdue payments, and Section 43B(h)-related risk.

Compliance Agent

Checks export-related compliance context including:

GST LUT
Shipping Bill
Export Invoice
EDPMS realization
e-FIRC / realization proof
Commerce Agent

Handles Razorpay payment preparation.

AURA follows:

Analysis → Risk Decision → Human Authorization → Razorpay Execution

AURA does not create a Razorpay order during analysis. Razorpay execution begins only after explicit approval.

Risk Engine
Risk	Score	Decision
LOW	25	PAYMENT_READY
MEDIUM	60	REVIEW_REQUIRED
HIGH	90	BLOCK_PAYMENT
Demo Scenarios
LOW Risk

Pay ABC Exports ₹50,000 for invoice INV-102

Expected: LOW → 25 → PAYMENT_READY

MEDIUM Risk

Pay ABC Exports ₹50,000 for invoice INV-102. The payment is due within 5 days.

Expected: MEDIUM → 60 → REVIEW_REQUIRED

HIGH Risk

Pay ABC Exports ₹50,000 for invoice INV-102. The payment is overdue.

Expected: HIGH → 90 → BLOCK_PAYMENT

Export Compliance

Pay ABC Exports ₹50,000 for invoice INV-102 after checking the GST LUT, shipping bill, export invoice, EDPMS realization and e-FIRC.

AURA runs the relevant agents and identifies outstanding compliance items before authorization.

Missing Amount

Pay ABC Exports for invoice INV-102

AURA does not invent an amount. The payment workflow is blocked until an explicit amount is provided.

No-Order-Before-Approval

Pay ABC Exports ₹10,000 for invoice INV-103

Before clicking APPROVE PAYMENT:

Razorpay Order: Not Created

Only after human approval should the Razorpay order be created.

Razorpay Payment Flow

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

Razorpay execution happens only after explicit human approval.

Tech Stack
Python
FastAPI
Pydantic
Razorpay API
python-dotenv
HTML / CSS / JavaScript
Uvicorn
Project Structure
AURA/
├── backend/
│   ├── agents/
│   │   ├── brain.py
│   │   ├── commerce.py
│   │   ├── compliance.py
│   │   └── vendor.py
│   ├── models/
│   ├── services/
│   ├── data/
│   ├── documents/
│   ├── frontend/
│   ├── tests/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── .gitignore
└── README.md
Setup
1. Clone the repository
git clone https://github.com/vigneshwar2005-a/AURA.git
cd AURA
2. Create virtual environment
cd backend
python -m venv venv
3. Install dependencies
.\venv\Scripts\python.exe -m pip install -r requirements.txt
4. Configure Razorpay

Copy .env.example to .env:

Copy-Item .env.example .env

Add your Razorpay Test Mode credentials:

RAZORPAY_KEY_ID=your_razorpay_test_key_id
RAZORPAY_KEY_SECRET=your_razorpay_test_key_secret
RAZORPAY_WEBHOOK_SECRET=your_razorpay_webhook_secret

Never commit the real .env file.

Run AURA
Backend

From C:\Aura\backend:

.\venv\Scripts\python.exe -m uvicorn main:app --reload

Backend:

http://127.0.0.1:8000

Frontend

Open another terminal.

From C:\Aura:

.\backend\venv\Scripts\python.exe -m http.server 5500 --directory backend\frontend

Open:

http://127.0.0.1:5500/index.html

Security
Real credentials are stored only in .env
.env is excluded from Git
.env.example contains placeholders only
Razorpay orders are not created during initial analysis
High-risk payments are blocked
Missing payment amounts are rejected
Human approval is required before Razorpay execution
Project Status

Buildathon-ready prototype using Razorpay Test Mode.