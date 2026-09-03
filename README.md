# AURA — Autonomous Unified Razorpay Agent

AI-powered autonomous payment orchestration for exporters.

AURA is a multi-agent payment control layer that understands payment requests, analyzes vendor and export-compliance context, evaluates risk, and allows Razorpay payment execution only after explicit human authorization.

## Core Flow

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

## Key Features

- Natural-language payment intent understanding
- Multi-agent orchestration
- Vendor payment-timing analysis
- MSME / Section 43B(h) risk detection
- Export compliance checks
- Risk scoring and payment decisions
- Explicit human approval before payment execution
- Razorpay Test Mode integration
- Razorpay payment reconciliation
- Activity and audit trail
- Payment history
- Missing and invalid amount protection
- High-risk payment blocking

## Agent Architecture

### AURA Brain

The central orchestration layer that understands payment intent, extracts entities, selects the required agents, combines their results, and produces the final payment decision.

### Vendor Agent

Evaluates vendor payment risk, including MSME payment timelines, user-stated deadlines, overdue payments, and Section 43B(h)-related risk.

### Compliance Agent

Checks export-related compliance context including:

- GST LUT
- Shipping Bill
- Export Invoice
- EDPMS realization
- e-FIRC / realization proof

### Commerce Agent

Handles Razorpay payment preparation.

AURA follows:

**Analysis → Risk Decision → Human Authorization → Razorpay Execution**

AURA does not create a Razorpay order during analysis. Razorpay execution begins only after explicit approval.

### Risk Engine

| Risk | Score | Decision |
|---|---:|---|
| LOW | 25 | PAYMENT_READY |
| MEDIUM | 60 | REVIEW_REQUIRED |
| HIGH | 90 | BLOCK_PAYMENT |

## Tech Stack

- Python
- FastAPI
- Pydantic
- Razorpay API
- python-dotenv
- HTML / CSS / JavaScript
- Uvicorn

## Project Structure

```text
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