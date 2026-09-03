import os
import json
import hmac
import hashlib
import uuid

from datetime import datetime, timezone

import razorpay
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from agents.brain import aura_brain
from agents.commerce import create_order

from models.schemas import (
    ExporterRequest,
    PaymentRequest,
    VendorRequest,
    ComplianceRequest,
)

from services.exporter_engine import run_exporter_analysis


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AURA",
    description="Autonomous Unified Razorpay Agent",
    version="2.3.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# RAZORPAY CONFIGURATION
# ============================================================

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(
        auth=(
            RAZORPAY_KEY_ID,
            RAZORPAY_KEY_SECRET,
        )
    )
else:
    razorpay_client = None


# ============================================================
# DATA STORAGE
# ============================================================

DATA_DIR = "data"

PAYMENTS_FILE = os.path.join(
    DATA_DIR,
    "payments.json",
)

APPROVALS_FILE = os.path.join(
    DATA_DIR,
    "approvals.json",
)

os.makedirs(
    DATA_DIR,
    exist_ok=True,
)


# ============================================================
# PAYMENT STORAGE HELPERS
# ============================================================

def load_payments():
    if not os.path.exists(PAYMENTS_FILE):
        return []

    try:
        with open(
            PAYMENTS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except Exception:
        return []


def save_payments(payments):
    with open(
        PAYMENTS_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payments,
            file,
            indent=4,
        )


# ============================================================
# APPROVAL STORAGE HELPERS
# ============================================================

def load_approvals():
    if not os.path.exists(APPROVALS_FILE):
        return []

    try:
        with open(
            APPROVALS_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        return []

    except Exception:
        return []


def save_approvals(approvals):
    with open(
        APPROVALS_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            approvals,
            file,
            indent=4,
        )


# ============================================================
# ROOT
# ============================================================

@app.get("/")
async def root():
    return {
        "product": "AURA",
        "name": "AURA",
        "expansion": "Autonomous Unified Razorpay Agent",
        "status": "online",
        "version": "2.3.0",
        "description": "Autonomous Exporter Agent Platform",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "razorpay": (
            "configured"
            if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET
            else "missing"
        ),
        "webhook": (
            "configured"
            if RAZORPAY_WEBHOOK_SECRET
            else "not_configured"
        ),
        "human_approval_gate": "enabled",
    }


# ============================================================
# AURA STATUS
# ============================================================

@app.get("/aura/status")
async def aura_status():
    return {
        "product": "AURA",
        "name": "AURA",
        "expansion": "Autonomous Unified Razorpay Agent",
        "status": "operational",
        "agents": {
            "brain": "online",
            "commerce": "online",
            "compliance": "online",
            "vendor": "online",
        },
        "systems": {
            "razorpay": (
                "connected"
                if RAZORPAY_KEY_ID
                else "not_configured"
            ),
            "risk_engine": "online",
            "exporter_engine": "online",
            "human_approval_gate": "enabled",
        },
    }


# ============================================================
# COMMERCE ORDER
# ============================================================

@app.post("/commerce/order")
async def commerce_order(
    service: str,
    hours: int,
    rate: float,
):
    if hours <= 0:
        raise HTTPException(
            status_code=400,
            detail="Hours must be greater than zero",
        )

    if rate <= 0:
        raise HTTPException(
            status_code=400,
            detail="Rate must be greater than zero",
        )

    try:
        return create_order(
            service=service,
            hours=hours,
            rate=rate,
            currency="INR",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Order creation failed: {str(e)}",
        )


# ============================================================
# EXPORTER ANALYSIS
# ============================================================

@app.post("/exporter/analyze")
async def exporter_analyze(
    data: ExporterRequest,
):
    try:
        vendor_data = None
        compliance_data = None

        if data.vendor:
            vendor_data = data.vendor.model_dump()

        if data.compliance:
            compliance_data = data.compliance.model_dump()

        return run_exporter_analysis(
            vendor_data=vendor_data,
            compliance_data=compliance_data,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Exporter analysis failed: {str(e)}",
        )


# ============================================================
# VENDOR CHECK
# ============================================================

@app.post("/vendor/check")
async def vendor_check(
    data: VendorRequest,
):
    try:
        from agents.vendor import check_vendor_payment

        return check_vendor_payment(
            invoice_amount=data.invoice_amount,
            invoice_date=data.invoice_date,
            is_msme=data.is_msme,
            has_written_agreement=data.has_written_agreement,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Vendor check failed: {str(e)}",
        )


# ============================================================
# COMPLIANCE CHECK
# ============================================================

@app.post("/compliance/check")
async def compliance_check(
    data: ComplianceRequest,
):
    try:
        from agents.compliance import check_export_compliance

        return check_export_compliance(
            shipping_bill=data.shipping_bill,
            invoice=data.invoice,
            gst_lut=data.gst_lut,
            edpms_realized=data.edpms_realized,
            e_firc=data.e_firc,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Compliance check failed: {str(e)}",
        )


# ============================================================
# PAYMENT CREATE
# ============================================================

@app.post("/payment/create")
async def payment_create(
    data: PaymentRequest,
):
    try:
        return create_order(
            service=data.service,
            hours=1,
            rate=data.amount,
            currency=data.currency,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Payment order creation failed: {str(e)}",
        )


# ============================================================
# AURA BRAIN
# ============================================================

@app.post("/brain")
async def brain(
    data: ExporterRequest,
):
    try:
        result = aura_brain(
            data.request
        )

        result["request_data"] = {
            "payment": (
                data.payment.model_dump()
                if data.payment
                else None
            ),
            "vendor": (
                data.vendor.model_dump()
                if data.vendor
                else None
            ),
            "compliance": (
                data.compliance.model_dump()
                if data.compliance
                else None
            ),
        }

        return result

    except Exception as e:
        print(
            "AURA Brain error:",
            str(e),
        )

        raise HTTPException(
            status_code=500,
            detail=f"AURA Brain failed: {str(e)}",
        )


# ============================================================
# HUMAN APPROVAL GATE
# ============================================================

@app.post("/payment/approve")
async def approve_payment(
    request: Request,
):
    try:
        data = await request.json()

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON request",
        )

    request_id = str(
        data.get("request_id")
        or uuid.uuid4()
    )

    decision = str(
        data.get("decision", "")
    ).upper().strip()

    amount = data.get("amount")

    service = data.get(
        "service",
        "AURA Exporter Service",
    )

    currency = str(
        data.get(
            "currency",
            "INR",
        )
    ).upper().strip()

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    if decision not in [
        "PAYMENT_READY",
        "APPROVED",
    ]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Payment cannot be approved. "
                "AURA decision must be "
                "PAYMENT_READY or APPROVED."
            ),
        )

    # --------------------------------------------------------
    # AMOUNT
    # --------------------------------------------------------

    if amount is None:
        raise HTTPException(
            status_code=400,
            detail="Payment amount is required.",
        )

    try:
        amount = float(amount)

    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Payment amount must be numeric.",
        )

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Payment amount must be greater than zero.",
        )

    # --------------------------------------------------------
    # CURRENCY
    # --------------------------------------------------------

    if len(currency) != 3:
        raise HTTPException(
            status_code=400,
            detail="Currency must be a 3-letter code.",
        )

    # --------------------------------------------------------
    # LOAD APPROVALS
    # --------------------------------------------------------

    approvals = load_approvals()

    # --------------------------------------------------------
    # DUPLICATE APPROVAL
    # --------------------------------------------------------

    for approval in approvals:

        if approval.get("request_id") == request_id:

            return {
                "status": "already_approved",
                "request_id": request_id,
                "approval_id": approval.get(
                    "approval_id"
                ),
                "razorpay_order_id": approval.get(
                    "razorpay_order_id"
                ),
                "amount": approval.get(
                    "amount",
                    amount,
                ),
                "currency": approval.get(
                    "currency",
                    currency,
                ),
                "payment_action": (
                    "OPEN_RAZORPAY_CHECKOUT"
                ),
                "message": (
                    "This payment request has "
                    "already been approved."
                ),
            }

    # --------------------------------------------------------
    # CREATE RAZORPAY ORDER
    # --------------------------------------------------------

    try:
        order = create_order(
            service=service,
            hours=1,
            rate=amount,
            currency=currency,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "Approved payment order creation failed: "
                f"{str(e)}"
            ),
        )

    razorpay_order_id = order.get(
        "razorpay_order_id"
    )

    if not razorpay_order_id:
        raise HTTPException(
            status_code=500,
            detail="Razorpay order ID was not returned.",
        )

    # --------------------------------------------------------
    # SAVE APPROVAL
    # --------------------------------------------------------

    approval_id = str(
        uuid.uuid4()
    )

    approval_record = {
        "approval_id": approval_id,
        "request_id": request_id,
        "service": service,
        "amount": amount,
        "currency": currency,
        "decision": "APPROVED",
        "approval_status": "APPROVED",
        "razorpay_order_id": razorpay_order_id,
        "approved_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "payment_action": (
            "HUMAN_APPROVED_CHECKOUT_REQUIRED"
        ),
    }

    approvals.append(
        approval_record
    )

    save_approvals(
        approvals
    )

    return {
        "status": "approved",
        "approval_id": approval_id,
        "request_id": request_id,
        "service": service,
        "amount": amount,
        "currency": currency,
        "razorpay_order_id": razorpay_order_id,
        "approval_required": False,
        "payment_action": "OPEN_RAZORPAY_CHECKOUT",
        "message": (
            "Human approval recorded successfully. "
            "Razorpay checkout may now be opened."
        ),
    }


# ============================================================
# APPROVAL HISTORY
# ============================================================

@app.get("/payment/approvals")
async def payment_approvals():

    approvals = load_approvals()

    return {
        "status": "success",
        "count": len(approvals),
        "approvals": approvals,
    }


# ============================================================
# RAZORPAY WEBHOOK
# ============================================================

@app.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
):
    body = await request.body()

    signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    # --------------------------------------------------------
    # SIGNATURE VERIFICATION
    # --------------------------------------------------------

    if (
        signature
        and RAZORPAY_WEBHOOK_SECRET
    ):

        expected_signature = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode(
                "utf-8"
            ),
            body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(
            signature,
            expected_signature,
        ):

            print(
                "Invalid Razorpay webhook signature"
            )

            raise HTTPException(
                status_code=400,
                detail="Invalid webhook signature",
            )

        print(
            "Razorpay webhook signature verified"
        )

    else:

        print(
            "Webhook received without signature"
        )

        print(
            "Development/Test request"
        )

    # --------------------------------------------------------
    # PARSE JSON
    # --------------------------------------------------------

    try:
        payload = json.loads(
            body.decode("utf-8")
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON",
        )

    event = payload.get(
        "event",
        "unknown",
    )

    print(
        "\n================================"
    )

    print(
        "AURA WEBHOOK RECEIVED"
    )

    print(
        "================================"
    )

    print(
        "Event:",
        event,
    )

    # ========================================================
    # PAYMENT CAPTURED
    # ========================================================

    if event == "payment.captured":

        try:

            payment_entity = (
                payload
                .get("payload", {})
                .get("payment", {})
                .get("entity", {})
            )

            payment_id = payment_entity.get(
                "id"
            )

            order_id = payment_entity.get(
                "order_id"
            )

            amount_paise = payment_entity.get(
                "amount",
                0,
            ) or 0

            amount_inr = (
                amount_paise / 100
            )

            currency = payment_entity.get(
                "currency",
                "INR",
            )

            status = payment_entity.get(
                "status",
                "captured",
            )

            method = payment_entity.get(
                "method"
            )

            email = payment_entity.get(
                "email"
            )

            contact = payment_entity.get(
                "contact"
            )

            transaction = {
                "transaction_id": payment_id,
                "razorpay_order_id": order_id,
                "amount": amount_inr,
                "currency": currency,
                "status": status,
                "payment_method": method,
                "customer_email": email,
                "customer_contact": contact,
                "event": event,
                "received_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "agent_status": "payment_verified",
                "next_action": "commerce_fulfillment",
            }

            payments = load_payments()

            existing_ids = {
                payment.get(
                    "transaction_id"
                )
                for payment in payments
            }

            if payment_id not in existing_ids:

                payments.append(
                    transaction
                )

                save_payments(
                    payments
                )

                print(
                    "Payment stored in AURA"
                )

            else:

                print(
                    "Duplicate webhook ignored"
                )

            print(
                "--------------------------------"
            )

            print(
                "Payment ID :",
                payment_id,
            )

            print(
                "Order ID   :",
                order_id,
            )

            print(
                "Amount     :",
                amount_inr,
                currency,
            )

            print(
                "Status     :",
                status,
            )

            print(
                "Method     :",
                method,
            )

            print(
                "--------------------------------"
            )

        except Exception as e:

            print(
                "Payment processing error:",
                str(e),
            )

            raise HTTPException(
                status_code=500,
                detail="Payment processing failed",
            )

    # ========================================================
    # PAYMENT FAILED
    # ========================================================

    elif event == "payment.failed":

        print(
            "Payment failed"
        )

    # ========================================================
    # PAYMENT AUTHORIZED
    # ========================================================

    elif event == "payment.authorized":

        print(
            "Payment authorized"
        )

    # ========================================================
    # OTHER EVENTS
    # ========================================================

    else:

        print(
            "Event received:",
            event,
        )

    print(
        "================================\n"
    )

    return {
        "status": "received",
        "event": event,
    }


# ============================================================
# CHECKOUT
# ============================================================

@app.get(
    "/checkout",
    response_class=HTMLResponse,
)
async def checkout(
    amount: float = 5000,
    service: str = "AURA Exporter Service",
):

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be greater than zero",
        )

    try:

        order = create_order(
            service=service,
            hours=1,
            rate=amount,
            currency="INR",
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Checkout order creation failed: "
                f"{str(e)}"
            ),
        )

    razorpay_order_id = order[
        "razorpay_order_id"
    ]

    amount_paise = int(
        round(
            amount * 100
        )
    )

    return f"""
<!DOCTYPE html>

<html>

<head>

    <title>AURA Checkout</title>

    <script
        src="https://checkout.razorpay.com/v1/checkout.js">
    </script>

    <style>

        body {{
            font-family: Arial, sans-serif;
            text-align: center;
            padding-top: 100px;
            background: #f5f5f5;
            color: #111;
        }}

        button {{
            padding: 15px 30px;
            font-size: 18px;
            cursor: pointer;
            background: #000;
            color: #fff;
            border: none;
            border-radius: 6px;
        }}

    </style>

</head>

<body>

    <h1>AURA Payment</h1>

    <h2>{service}</h2>

    <p>
        Amount: ₹{amount:,.2f}
    </p>

    <button onclick="payNow()">
        Pay ₹{amount:,.2f}
    </button>

    <script>

        function payNow() {{

            var options = {{

                "key": "{RAZORPAY_KEY_ID}",

                "amount": {amount_paise},

                "currency": "INR",

                "name": "AURA",

                "description": "{service}",

                "order_id": "{razorpay_order_id}",

                "handler": function(response) {{

                    console.log(
                        "Payment successful!"
                    );

                    console.log(
                        response
                    );

                    alert(
                        "Payment successful!\\n\\n"
                        +
                        "Payment ID: "
                        +
                        response.razorpay_payment_id
                    );

                }},

                "theme": {{
                    "color": "#000000"
                }}

            }};

            var rzp =
                new Razorpay(options);

            rzp.open();

        }}

    </script>

</body>

</html>
"""


# ============================================================
# PAYMENT HISTORY
# ============================================================

@app.get("/payments")
async def payments():

    """
    PAYMENT REFRESH / RECONCILIATION

    This endpoint does two things:

    1. Loads payments already stored by webhook.
    2. Directly asks Razorpay for captured payments.

    Therefore even if the webhook was missed,
    pressing REFRESH will recover the payment.
    """

    stored_payments = load_payments()

    # --------------------------------------------------------
    # RAZORPAY NOT CONFIGURED
    # --------------------------------------------------------

    if razorpay_client is None:

        return {
            "status": "success",
            "count": len(stored_payments),
            "payments": stored_payments,
            "sync": "razorpay_not_configured",
        }

    # --------------------------------------------------------
    # DIRECT RAZORPAY SYNC
    # --------------------------------------------------------

    try:

        print(
            "--------------------------------"
        )

        print(
            "AURA PAYMENT REFRESH"
        )

        print(
            "Fetching payments from Razorpay..."
        )

        # Razorpay returns payment records.
        result = razorpay_client.payment.all(
            {
                "count": 100,
            }
        )

        razorpay_items = result.get(
            "items",
            [],
        )

        print(
            "Razorpay payments received:",
            len(razorpay_items),
        )

        # ----------------------------------------------------
        # EXISTING PAYMENT IDS
        # ----------------------------------------------------

        existing_ids = {
            payment.get(
                "transaction_id"
            )
            for payment in stored_payments
            if payment.get(
                "transaction_id"
            )
        }

        added = 0

        # ----------------------------------------------------
        # PROCESS RAZORPAY PAYMENTS
        # ----------------------------------------------------

        for payment in razorpay_items:

            payment_id = payment.get(
                "id"
            )

            if not payment_id:
                continue

            status = str(
                payment.get(
                    "status",
                    "",
                )
            ).lower()

            # We only want successful payments.
            if status != "captured":
                continue

            # Already stored by webhook?
            if payment_id in existing_ids:
                continue

            amount_paise = (
                payment.get(
                    "amount",
                    0,
                )
                or 0
            )

            created_at = payment.get(
                "created_at"
            )

            if created_at:

                received_at = (
                    datetime.fromtimestamp(
                        created_at,
                        tz=timezone.utc,
                    ).isoformat()
                )

            else:

                received_at = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

            transaction = {
                "transaction_id": payment_id,

                "razorpay_order_id": payment.get(
                    "order_id"
                ),

                "amount": (
                    amount_paise / 100
                ),

                "currency": payment.get(
                    "currency",
                    "INR",
                ),

                "status": "captured",

                "payment_method": payment.get(
                    "method"
                ),

                "customer_email": payment.get(
                    "email"
                ),

                "customer_contact": payment.get(
                    "contact"
                ),

                "event": "razorpay_sync",

                "received_at": received_at,

                "agent_status": "payment_verified",

                "next_action": "commerce_fulfillment",
            }

            stored_payments.append(
                transaction
            )

            existing_ids.add(
                payment_id
            )

            added += 1

            print(
                "Synced payment:",
                payment_id,
                "₹",
                amount_paise / 100,
            )

        # ----------------------------------------------------
        # SAVE NEW PAYMENTS
        # ----------------------------------------------------

        if added > 0:

            save_payments(
                stored_payments
            )

            print(
                f"Razorpay sync completed: "
                f"{added} new captured payment(s)"
            )

        else:

            print(
                "Razorpay sync: no new captured payments"
            )

        # ----------------------------------------------------
        # SORT NEWEST FIRST
        # ----------------------------------------------------

        stored_payments.sort(
            key=lambda payment: payment.get(
                "received_at",
                "",
            ),
            reverse=True,
        )

        print(
            "Total AURA payments:",
            len(stored_payments),
        )

        print(
            "--------------------------------"
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {
            "status": "success",
            "count": len(stored_payments),
            "payments": stored_payments,
            "sync": "razorpay_ok",
            "synced_from_razorpay": added,
        }

    except Exception as e:

        print(
            "Razorpay payment history sync failed:",
            str(e),
        )

        # ----------------------------------------------------
        # FALLBACK
        # ----------------------------------------------------

        return {
            "status": "success",
            "count": len(stored_payments),
            "payments": stored_payments,
            "sync": "razorpay_sync_failed",
            "sync_error": str(e),
        }


# ============================================================
# SYSTEM INFORMATION
# ============================================================

@app.get("/system/info")
async def system_info():

    return {
        "application": "AURA",

        "full_name": (
            "Autonomous Unified Razorpay Agent"
        ),

        "version": "2.3.0",

        "architecture": (
            "Multi-Agent Exporter Platform"
        ),

        "agents": [
            "AURA Brain",
            "Commerce Agent",
            "Compliance Agent",
            "Vendor Agent",
        ],

        "risk_engine": "enabled",

        "human_approval_gate": "enabled",

        "razorpay": (
            "configured"
            if RAZORPAY_KEY_ID
            and RAZORPAY_KEY_SECRET
            else "not_configured"
        ),

        "webhook": (
            "configured"
            if RAZORPAY_WEBHOOK_SECRET
            else "not_configured"
        ),
    }