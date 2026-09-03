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
Natural-language payment understanding
Multi-agent orchestration
Vendor payment-timing analysis
MSME / Section 43B(h) risk detection
Export compliance checks
Risk scoring and payment decisions
Human approval before payment execution
Razorpay Test Mode integration
Razorpay payment reconciliation
Activity and audit trail
Payment history
Missing and invalid amount protection
High-risk payment blocking
Agent Architecture
1. AURA Brain

The central orchestration layer that:

Understands payment intent
Extracts payment entities
Selects the required agents
Combines agent results
Produces the final payment decision
2. Vendor Agent

Evaluates vendor payment risk, including:

MSME payment timelines
User-stated payment deadlines
Overdue payments
Section 43B(h)-related risk
3. Compliance Agent

Checks export-related compliance context:

GST LUT
Shipping Bill
Export Invoice
EDPMS realization
e-FIRC / realization proof
4. Commerce Agent

Handles Razorpay payment preparation and execution.

AURA follows:

Analysis → Risk Decision → Human Authorization → Razorpay Execution

Important: AURA does not create a Razorpay order during initial analysis. Razorpay execution begins only after explicit human approval.

5. Risk Engine
Risk Level	Score	Decision
LOW	25	PAYMENT_READY
MEDIUM	60	REVIEW_REQUIRED
HIGH	90	BLOCK_PAYMENT
Demo Scenarios
LOW Risk

Request:

Pay ABC Exports ₹50,000 for invoice INV-102

Expected:

LOW → 25 → PAYMENT_READY

MEDIUM Risk

Request:

Pay ABC Exports ₹50,000 for invoice INV-102. The payment is due within 5 days.

Expected:

MEDIUM → 60 → REVIEW_REQUIRED

HIGH Risk

Request:

Pay ABC Exports ₹50,000 for invoice INV-102. The payment is overdue.

Expected:

HIGH → 90 → BLOCK_PAYMENT

Export Compliance

Request:

Pay ABC Exports ₹50,000 for invoice INV-102 after checking the GST LUT, shipping bill, export invoice, EDPMS realization and e-FIRC.

AURA runs the relevant agents and identifies outstanding compliance items before authorization.

Missing Amount Protection

Request:

Pay ABC Exports for invoice INV-102

AURA does not invent or assume a payment amount.

The payment workflow is blocked until an explicit amount is provided.

No Order Before Approval

Request:

Pay ABC Exports ₹10,000 for invoice INV-103

Before clicking APPROVE PAYMENT:

Razorpay Order: Not Created

Only after human approval is the Razorpay order created.

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

Human authorization is required before Razorpay execution.

Audit & Payment Tracking

AURA provides visibility into the complete payment lifecycle:

Agent execution status
Risk assessment
Payment decision
Approval state
Razorpay order status
Captured payment status
Payment history
Activity and audit trail
Tech Stack
Technology	Purpose
Python	Core application
FastAPI	Backend API
Pydantic	Data validation
Razorpay API	Payment execution
python-dotenv	Environment configuration
HTML / CSS / JavaScript	Frontend
Uvicorn	Application server
Project Structure
AURA/
├── backend/
│   ├── agents/
│   │   ├── brain.py
│   │   ├── commerce.py
│   │   ├── compliance.py
│   │   └── vendor.py
│   │
│   ├── models/
│   ├── services/
│   ├── data/
│   ├── documents/
│   ├── frontend/
│   ├── tests/
│   │
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
│
├── .gitignore
└── README.md
Setup
1. Clone the Repository
git clone https://github.com/vigneshwar2005-a/AURA.git
cd AURA
2. Create Virtual Environment
cd backend
python -m venv venv
3. Install Dependencies
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

AURA is designed with payment safety as a core principle.

Real credentials are stored only in .env
.env is excluded from Git
.env.example contains placeholders only
Razorpay orders are not created during initial analysis
High-risk payments are blocked
Missing payment amounts are rejected
Human approval is required before Razorpay execution
Project Status

Buildathon-ready prototype using Razorpay Test Mode.

Current Capabilities
Multi-agent payment orchestration
Vendor risk analysis
Export compliance analysis
Risk-based payment decisions
Human-in-the-loop authorization
Razorpay Checkout integration
Payment capture
Payment reconciliation
Audit trail
Payment history
Safety and edge-case handling