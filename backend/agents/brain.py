import re
from datetime import date, timedelta

from agents.vendor import check_vendor_payment
from agents.compliance import check_export_compliance
from services.risk_engine import calculate_risk


# ============================================================
# AURA BRAIN
# Autonomous multi-agent request orchestrator
#
# IMPORTANT:
# The Brain NEVER creates a Razorpay order.
# Razorpay order creation happens only after explicit
# human approval through /payment/approve.
# ============================================================


def extract_amount(request: str):
    """
    Extract an INR amount from a natural-language request.

    Supports:
      ₹50,000
      Rs 50000
      INR 50000
      50000 rupees
      ₹50k
      ₹1 lakh
    """

    request_lower = request.lower()

    patterns = [
        (
            r"₹\s*([\d,]+(?:\.\d+)?)\s*(k|thousand|lakh)?",
            True
        ),
        (
            r"rs\.?\s*([\d,]+(?:\.\d+)?)\s*(k|thousand|lakh)?",
            True
        ),
        (
            r"inr\s*([\d,]+(?:\.\d+)?)\s*(k|thousand|lakh)?",
            True
        ),
        (
            r"([\d,]+(?:\.\d+)?)\s*(k|thousand|lakh)\b",
            True
        ),
        (
            r"([\d,]+(?:\.\d+)?)\s*(?:rupees?)",
            False
        ),
    ]

    for pattern, has_multiplier in patterns:
        match = re.search(
            pattern,
            request_lower,
            re.IGNORECASE
        )

        if not match:
            continue

        try:
            amount = float(
                match.group(1).replace(",", "")
            )
        except (TypeError, ValueError):
            continue

        if has_multiplier:
            multiplier = match.group(2)

            if multiplier:
                multiplier = multiplier.lower()

                if multiplier in ["k", "thousand"]:
                    amount *= 1000

                elif multiplier == "lakh":
                    amount *= 100000

        return amount

    return None


def extract_invoice_number(request: str):
    """
    Extract invoice numbers such as:

      INV-102
      INV102
      Invoice 102
    """

    patterns = [
        r"\bINV[-\s]?([A-Za-z0-9-]+)\b",
        r"\binvoice[-\s#:]?([A-Za-z0-9-]+)\b",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            request,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

    return None


def extract_vendor_name(request: str):
    """
    Try to identify a vendor/supplier name.

    Examples:

      Pay ABC Exports ₹50,000
      Pay supplier ABC Exports
      Vendor XYZ Traders
    """

    patterns = [
        r"(?:pay|payment to|pay to|supplier|vendor)\s+"
        r"([A-Za-z][A-Za-z0-9 &.-]{2,60}?)"
        r"(?=\s+₹|\s+rs\.?|\s+inr|\s+for|\s+invoice|$)"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            request,
            re.IGNORECASE
        )

        if match:
            name = match.group(1).strip()

            ignored = {
                "my",
                "the",
                "a",
                "an",
                "supplier",
                "vendor"
            }

            if name.lower() not in ignored:
                return name

    return None


def extract_service(request: str):
    """
    Identify the commerce service from the request.
    """

    request_lower = request.lower()

    service_keywords = {
        "customs": "Customs Service",
        "shipping": "Shipping Service",
        "logistics": "Logistics Service",
        "freight": "Freight Service",
        "documentation": "Export Documentation Service",
        "consulting": "Export Consulting Service",
        "software": "Software Service",
        "development": "Software Development Service",
        "inspection": "Export Inspection Service",
        "warehousing": "Warehousing Service",
        "warehouse": "Warehousing Service",
        "insurance": "Export Insurance Service",
    }

    for keyword, service_name in service_keywords.items():
        if keyword in request_lower:
            return service_name

    return "AURA Exporter Service"


def detect_intent(request: str):
    """
    Determine which AURA agents are required.

    Returns:

      vendor
      compliance
      commerce
      vendor_commerce
      compliance_commerce
      vendor_compliance
      full_export_workflow
      analysis
      unknown
    """

    text = request.lower()

    vendor_keywords = [
        "vendor",
        "supplier",
        "msme",
        "43b",
        "43b(h)",
        "invoice",
        "payment due",
        "payment deadline"
    ]

    compliance_keywords = [
        "compliance",
        "edpms",
        "firc",
        "e-firc",
        "fira",
        "gst",
        "lut",
        "shipping bill",
        "export invoice",
        "realization",
        "softex",
        "purpose code"
    ]

    commerce_keywords = [
        "payment",
        "pay",
        "order",
        "buy",
        "purchase",
        "checkout",
        "razorpay"
    ]

    needs_vendor = any(
        keyword in text
        for keyword in vendor_keywords
    )

    needs_compliance = any(
        keyword in text
        for keyword in compliance_keywords
    )

    needs_commerce = any(
        keyword in text
        for keyword in commerce_keywords
    )

    # IMPORTANT:
    # Check full workflow FIRST.
    if (
        needs_vendor
        and needs_compliance
        and needs_commerce
    ):
        return "full_export_workflow"

    if needs_vendor and needs_commerce:
        return "vendor_commerce"

    if needs_compliance and needs_commerce:
        return "compliance_commerce"

    if needs_vendor and needs_compliance:
        return "vendor_compliance"

    if needs_vendor:
        return "vendor"

    if needs_compliance:
        return "compliance"

    if needs_commerce:
        return "commerce"

    if any(
        word in text
        for word in [
            "analyze",
            "analyse",
            "check",
            "audit",
            "risk",
            "exporter",
            "business"
        ]
    ):
        return "analysis"

    return "unknown"


def get_required_agents(intent: str):
    """
    Return the agents required for the detected intent.
    """

    mapping = {
        "vendor": [
            "VENDOR"
        ],
        "compliance": [
            "COMPLIANCE"
        ],
        "commerce": [
            "COMMERCE"
        ],
        "vendor_commerce": [
            "VENDOR",
            "COMMERCE"
        ],
        "compliance_commerce": [
            "COMPLIANCE",
            "COMMERCE"
        ],
        "vendor_compliance": [
            "VENDOR",
            "COMPLIANCE"
        ],
        "full_export_workflow": [
            "VENDOR",
            "COMPLIANCE",
            "COMMERCE"
        ],
        "analysis": [
            "BRAIN"
        ],
        "unknown": [
            "BRAIN"
        ]
    }

    return mapping.get(
        intent,
        ["BRAIN"]
    )


def build_activity(
    agent,
    action,
    status="completed"
):
    """
    Create a standardized explainable
    agent activity event.
    """

    return {
        "agent": agent,
        "action": action,
        "status": status
    }


def build_agentic_commerce_context(
    request: str,
    intent: str,
    required_agents: list[str],
    amount,
    vendor_name,
    invoice_number,
    service: str,
    decision: dict,
):
    """
    Build a structured agentic-commerce context for the demo.

    This is AP2/ACP-INSPIRED positioning, not a claim of native
    AP2 or ACP protocol compliance.
    """

    decision_name = decision.get(
        "decision",
        "NO_ACTION"
    )

    if decision_name == "PAYMENT_READY":
        authorization_state = "AWAITING_HUMAN_APPROVAL"
        execution_state = "DEFERRED_UNTIL_AUTHORIZED"

    elif decision_name == "REVIEW_REQUIRED":
        authorization_state = "HUMAN_REVIEW_REQUIRED"
        execution_state = "BLOCKED_PENDING_REVIEW"

    elif decision_name == "BLOCK_PAYMENT":
        authorization_state = "BLOCKED"
        execution_state = "BLOCKED"

    else:
        authorization_state = "NOT_REQUIRED"
        execution_state = "NOT_EXECUTABLE"

    return {
        "positioning": "AP2_ACP_INSPIRED_AGENTIC_COMMERCE",

        "protocol_note": (
            "Demo uses AP2/ACP-style concepts for agentic commerce. "
            "It is not claiming native AP2 or ACP protocol compliance."
        ),

        "user_intent": {
            "natural_language_request": request,
            "intent": intent,

            "entities": {
                "amount": amount,
                "currency": "INR",
                "vendor_name": vendor_name,
                "invoice_number": invoice_number,
                "service": service,
            },
        },

        "agent_plan": {
            "required_agents": required_agents,
            "execution_model": "MULTI_AGENT_ORCHESTRATION",
            "decision": decision_name,
        },

        "payment_intent": {
            "type": "BUSINESS_PAYMENT",
            "amount": amount,
            "currency": "INR",
            "payee": vendor_name,
            "invoice": invoice_number,
            "service": service,

            "status": (
                "READY_FOR_AUTHORIZATION"
                if decision_name == "PAYMENT_READY"
                else execution_state
            ),
        },

        "authorization": {
            "mode": "HUMAN_IN_THE_LOOP",

            "required": decision_name in [
                "PAYMENT_READY",
                "REVIEW_REQUIRED",
            ],

            "state": authorization_state,
            "approval_endpoint": "/payment/approve",
        },

        "payment_execution": {
            "provider": "Razorpay",

            "order_creation": (
                "AFTER_HUMAN_APPROVAL"
            ),

            "state": execution_state,
            "razorpay_order_id": None,
        },
    }


# ============================================================
# VENDOR AGENT
# ============================================================

def extract_explicit_due_days(request: str):
    """
    Extract an explicit payment deadline stated by the user.

    Examples:
      payment is due within 5 days
      due in 3 days
      deadline in 2 days
      payment due in 7 days
      overdue
    """

    text = request.lower().strip()

    if re.search(
        r"\boverdue\b|\bpast due\b|\bpayment is late\b",
        text
    ):
        return 0

    patterns = [
        r"\bdue\s+(?:within|in)\s+(\d+)\s+days?\b",

        r"\bpayment\s+(?:is\s+)?due\s+"
        r"(?:within|in)\s+(\d+)\s+days?\b",

        r"\bdeadline\s+(?:is\s+)?"
        r"(?:within|in)\s+(\d+)\s+days?\b",

        r"\bpayment\s+deadline\s+(?:is\s+)?"
        r"(?:within|in)\s+(\d+)\s+days?\b",

        r"\bwithin\s+(\d+)\s+days?\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:
                return int(match.group(1))

            except (TypeError, ValueError):
                return None

    return None


def apply_explicit_vendor_deadline(
    vendor_result: dict,
    request: str,
):
    """
    Apply a payment deadline explicitly stated in the
    natural-language request.
    """

    due_days = extract_explicit_due_days(
        request
    )

    if due_days is None:
        return vendor_result

    today = date.today()

    stated_due_date = (
        today + timedelta(days=due_days)
    )

    vendor_result = dict(
        vendor_result
    )

    vendor_result["stated_deadline"] = True

    vendor_result["deadline_source"] = (
        "USER_STATED"
    )

    vendor_result["stated_days_remaining"] = (
        due_days
    )

    vendor_result["due_date"] = (
        str(stated_due_date)
    )

    vendor_result["days_remaining"] = (
        due_days
    )

    # ========================================================
    # OVERDUE
    # ========================================================

    if due_days <= 0:

        vendor_result["status"] = "OVERDUE"

        vendor_result["risk"] = "HIGH"

        vendor_result["43B_h_risk"] = "HIGH"

        vendor_result["decision"] = (
            "BLOCK_PAYMENT"
        )

        vendor_result["message"] = (
            "The user-stated MSME payment deadline has already "
            "passed and may create Section 43B(h) tax risk."
        )

        vendor_result["recommended_action"] = (
            "Escalate the payment immediately and review the "
            "tax impact before proceeding."
        )

    # ========================================================
    # DUE SOON
    # ========================================================

    elif due_days <= 5:

        vendor_result["status"] = "DUE_SOON"

        vendor_result["risk"] = "MEDIUM"

        vendor_result["43B_h_risk"] = "MEDIUM"

        vendor_result["decision"] = (
            "REVIEW_REQUIRED"
        )

        vendor_result["message"] = (
            f"The user-stated MSME payment deadline is in "
            f"{due_days} "
            f"day{'s' if due_days != 1 else ''}."
        )

        vendor_result["recommended_action"] = (
            "Prioritize this payment and complete it before "
            "the stated deadline."
        )

    # ========================================================
    # WITHIN LIMIT
    # ========================================================

    else:

        vendor_result["status"] = "WITHIN_LIMIT"

        vendor_result["risk"] = "LOW"

        vendor_result["43B_h_risk"] = "LOW"

        vendor_result["decision"] = (
            "PAYMENT_READY"
        )

        vendor_result["message"] = (
            f"The user-stated MSME payment deadline is in "
            f"{due_days} days and is not currently due soon."
        )

        vendor_result["recommended_action"] = (
            "Payment can proceed while remaining within the "
            "current review threshold."
        )

    return vendor_result


def run_vendor_agent(request: str):
    """
    Execute Vendor Agent using information extracted
    from the natural-language request.
    """

    amount = extract_amount(
        request
    )

    # IMPORTANT:
    # Never invent a payment amount.
    if amount is None:

        return {
            "agent": "vendor",
            "status": "INVALID_REQUEST",
            "risk": "HIGH",
            "43B_h_risk": "HIGH",
            "decision": "BLOCK_PAYMENT",

            "message": (
                "Payment amount is missing. "
                "AURA cannot evaluate or authorize a payment "
                "without an explicit amount."
            ),

            "recommended_action": (
                "Provide the payment amount before continuing."
            )
        }

    result = check_vendor_payment(
        invoice_amount=amount,
        invoice_date=str(date.today()),
        is_msme=True,
        has_written_agreement=False
    )

    result = apply_explicit_vendor_deadline(
        vendor_result=result,
        request=request
    )

    return result


# ============================================================
# COMPLIANCE AGENT
# ============================================================

def run_compliance_agent():
    """
    Execute Compliance Agent.

    Demo-safe defaults can later be replaced by
    uploaded exporter documents or real integrations.
    """

    return check_export_compliance(
        shipping_bill=True,
        invoice=True,
        gst_lut=True,
        edpms_realized=False,
        e_firc=False
    )


# ============================================================
# PAYMENT DECISION
# ============================================================

def decide_payment_action(
    vendor_result=None,
    compliance_result=None
):
    """
    Decide whether payment is eligible.

    IMPORTANT:
    This function DOES NOT create a Razorpay order.

    It only determines whether payment may proceed
    to the human approval gate.
    """

    risks = []

    if vendor_result:

        vendor_risk = vendor_result.get(
            "43B_h_risk"
        )

        if vendor_risk:
            risks.append(
                vendor_risk
            )

    if compliance_result:

        compliance_risk = compliance_result.get(
            "risk"
        )

        if compliance_risk:
            risks.append(
                compliance_risk
            )

    overall_risk = calculate_risk(
        risks
    )

    if overall_risk["risk_level"] == "HIGH":

        return {
            "decision": "BLOCK_PAYMENT",
            "approval_required": True,

            "reason": (
                "High risk detected. "
                "Resolve outstanding issues before payment."
            ),

            "risk": overall_risk
        }

    if overall_risk["risk_level"] == "MEDIUM":

        return {
            "decision": "REVIEW_REQUIRED",
            "approval_required": True,

            "reason": (
                "Medium risk detected. "
                "Human review is required before payment."
            ),

            "risk": overall_risk
        }

    return {
        "decision": "PAYMENT_READY",
        "approval_required": True,

        "reason": (
            "No high-risk blocker detected. "
            "Payment can proceed through the approval gate."
        ),

        "risk": overall_risk
    }


# ============================================================
# AURA BRAIN
# ============================================================

def aura_brain(request: str):
    """
    Main AURA Brain entry point.

    Flow:

        Natural language request
                ↓
              Intent
                ↓
        Required agents
                ↓
        Vendor / Compliance
                ↓
              Risk
                ↓
        PAYMENT_READY / REVIEW_REQUIRED / BLOCK_PAYMENT
                ↓
        HUMAN APPROVAL GATE
                ↓
        /payment/approve
                ↓
        Razorpay order creation

    The Brain NEVER creates the Razorpay order.
    """

    if not request or not request.strip():

        return {
            "agent": "brain",
            "status": "invalid_request",

            "message": (
                "AURA requires an exporter request."
            )
        }

    request = request.strip()

    intent = detect_intent(
        request
    )

    required_agents = get_required_agents(
        intent
    )

    amount = extract_amount(
        request
    )

    # ========================================================
    # MISSING PAYMENT AMOUNT
    # ========================================================
    #
    # Never allow an executable payment request to continue
    # without an explicit amount.
    #

    if (
        amount is None
        and intent in [
            "commerce",
            "vendor_commerce",
            "compliance_commerce",
            "full_export_workflow"
        ]
    ):

        return {
            "agent": "aura",
            "name": "AURA",

            "expansion": (
                "Autonomous Unified Razorpay Agent"
            ),

            "status": "invalid_request",

            "request": request,

            "intent": intent,

            "required_agents": required_agents,

            "entities": {
                "amount": None,
                "vendor_name": extract_vendor_name(
                    request
                ),
                "invoice_number": extract_invoice_number(
                    request
                )
            },

            "message": (
                "Payment amount is missing. "
                "AURA cannot continue an executable payment "
                "workflow without an explicit amount."
            ),

            "action_required": (
                "Provide the payment amount before continuing."
            ),

            "razorpay_order_id": None,

            "activity": [
                build_activity(
                    "brain",
                    "Received exporter request"
                ),

                build_activity(
                    "brain",
                    f"Intent classified as {intent}"
                ),

                build_activity(
                    "brain",
                    "Payment blocked because amount is missing",
                    "blocked"
                )
            ]
        }

    vendor_name = extract_vendor_name(
        request
    )

    invoice_number = extract_invoice_number(
        request
    )

    activity = []

    # ========================================================
    # BRAIN START
    # ========================================================

    activity.append(
        build_activity(
            "brain",
            "Received exporter request"
        )
    )

    activity.append(
        build_activity(
            "brain",
            f"Intent classified as {intent}"
        )
    )

    activity.append(
        build_activity(
            "brain",
            "Required agents selected"
        )
    )

    results = {}

    vendor_result = None
    compliance_result = None

    # ========================================================
    # VENDOR AGENT
    # ========================================================

    if intent in [
        "vendor",
        "vendor_commerce",
        "vendor_compliance",
        "full_export_workflow"
    ]:

        activity.append(
            build_activity(
                "vendor",
                (
                    "Checking MSME payment deadline "
                    "and Section 43B(h) risk"
                ),
                "running"
            )
        )

        try:

            vendor_result = run_vendor_agent(
                request
            )

            results["vendor"] = vendor_result

            activity.append(
                build_activity(
                    "vendor",
                    "Vendor risk analysis completed"
                )
            )

        except Exception as error:

            activity.append(
                build_activity(
                    "vendor",
                    f"Vendor agent failed: {error}",
                    "failed"
                )
            )

            results["vendor"] = {
                "agent": "vendor",
                "status": "ERROR",
                "risk": "HIGH",
                "message": str(error)
            }

            vendor_result = results["vendor"]

    # ========================================================
    # COMPLIANCE AGENT
    # ========================================================

    if intent in [
        "compliance",
        "compliance_commerce",
        "vendor_compliance",
        "full_export_workflow"
    ]:

        activity.append(
            build_activity(
                "compliance",
                "Auditing export compliance documents",
                "running"
            )
        )

        try:

            compliance_result = run_compliance_agent()

            results["compliance"] = (
                compliance_result
            )

            activity.append(
                build_activity(
                    "compliance",
                    "Export compliance audit completed"
                )
            )

        except Exception as error:

            activity.append(
                build_activity(
                    "compliance",
                    f"Compliance agent failed: {error}",
                    "failed"
                )
            )

            results["compliance"] = {
                "agent": "compliance",
                "status": "ERROR",
                "risk": "HIGH",
                "message": str(error)
            }

            compliance_result = results["compliance"]

    # ========================================================
    # RISK ENGINE
    # ========================================================

    risks = []

    if vendor_result:

        vendor_risk = vendor_result.get(
            "43B_h_risk"
        )

        if vendor_risk:
            risks.append(
                vendor_risk
            )

    if compliance_result:

        compliance_risk = compliance_result.get(
            "risk"
        )

        if compliance_risk:
            risks.append(
                compliance_risk
            )

    aura_risk = calculate_risk(
        risks
    )

    results["aura_risk"] = aura_risk

    activity.append(
        build_activity(
            "risk",
            (
                f"Overall risk calculated as "
                f"{aura_risk['risk_level']}"
            )
        )
    )

    # ========================================================
    # PAYMENT DECISION
    # ========================================================

    if (
        vendor_result
        or compliance_result
    ):

        decision = decide_payment_action(
            vendor_result=vendor_result,
            compliance_result=compliance_result
        )

    elif intent == "commerce":

        decision = {
            "decision": "PAYMENT_READY",
            "approval_required": True,

            "reason": (
                "Payment request is eligible to proceed "
                "through the human approval gate."
            ),

            "risk": aura_risk
        }

    else:

        decision = {
            "decision": "NO_ACTION",
            "approval_required": False,

            "reason": (
                "No executable exporter action "
                "was identified."
            ),

            "risk": aura_risk
        }

    results["decision"] = decision

    # ========================================================
    # AGENTIC COMMERCE CONTEXT
    # ========================================================

    service = extract_service(
        request
    )

    results["agentic_commerce"] = (
        build_agentic_commerce_context(
            request=request,
            intent=intent,
            required_agents=required_agents,
            amount=amount,
            vendor_name=vendor_name,
            invoice_number=invoice_number,
            service=service,
            decision=decision,
        )
    )

    activity.append(
        build_activity(
            "aura",
            (
                "Created structured payment intent and "
                "authorization boundary"
            )
        )
    )

    # ========================================================
    # HUMAN APPROVAL GATE
    # ========================================================

    if decision["decision"] == "BLOCK_PAYMENT":

        activity.append(
            build_activity(
                "approval",
                (
                    "Payment blocked. "
                    "Human approval is unavailable until "
                    "HIGH risk is resolved."
                ),
                "blocked"
            )
        )

    elif decision["decision"] == "REVIEW_REQUIRED":

        activity.append(
            build_activity(
                "approval",
                (
                    "Human review required before "
                    "payment can proceed."
                ),
                "waiting"
            )
        )

    elif decision["decision"] == "PAYMENT_READY":

        activity.append(
            build_activity(
                "approval",
                (
                    "Waiting for explicit human approval. "
                    "Razorpay order will be created only "
                    "after approval."
                ),
                "waiting"
            )
        )

    # ========================================================
    # COMMERCE AGENT
    #
    # IMPORTANT:
    # NO create_order() HERE.
    #
    # The actual Razorpay order is created by:
    #
    #     POST /payment/approve
    #
    # after the human clicks:
    #
    #     APPROVE & OPEN RAZORPAY CHECKOUT
    # ========================================================

    if intent in [
        "commerce",
        "vendor_commerce",
        "compliance_commerce",
        "full_export_workflow"
    ]:

        activity.append(
            build_activity(
                "commerce",
                (
                    "Payment transaction prepared "
                    "but Razorpay order creation is "
                    "deferred until human approval."
                ),
                "waiting"
            )
        )

        results["commerce"] = {
            "status": "awaiting_approval",
            "service": extract_service(request),
            "amount": amount,
            "currency": "INR",

            "payment_action": (
                "HUMAN_APPROVAL_REQUIRED"
            ),

            "payment_intent_status": (
                "READY_FOR_AUTHORIZATION"
                if decision["decision"] == "PAYMENT_READY"
                else decision["decision"]
            ),

            "authorization_mode": (
                "HUMAN_IN_THE_LOOP"
            ),

            "razorpay_order_id": None,
            "razorpay_status": None,

            "message": (
                "No Razorpay order was created. "
                "AURA is waiting for explicit human approval."
            )
        }

    # ========================================================
    # UNKNOWN REQUEST
    # ========================================================

    if intent == "unknown":

        activity.append(
            build_activity(
                "brain",
                "Could not determine a suitable agent",
                "failed"
            )
        )

        return {
            "agent": "brain",
            "status": "unknown",
            "intent": intent,
            "required_agents": required_agents,
            "request": request,

            "message": (
                "AURA could not determine the required "
                "exporter workflow."
            ),

            "activity": activity
        }

    # ========================================================
    # FINAL BRAIN ACTIVITY
    # ========================================================

    activity.append(
        build_activity(
            "brain",
            "Multi-agent analysis completed"
        )
    )

    activity.append(
        build_activity(
            "aura",
            (
                "Payment intent is bounded by explicit human "
                "authorization before Razorpay execution"
            ),

            (
                "waiting"
                if decision["decision"] == "PAYMENT_READY"

                else "blocked"
                if decision["decision"] in [
                    "BLOCK_PAYMENT",
                    "REVIEW_REQUIRED",
                ]

                else "completed"
            )
        )
    )

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {
        "agent": "aura",
        "name": "AURA",

        "expansion": (
            "Autonomous Unified Razorpay Agent"
        ),

        "status": "analysis_complete",

        "request": request,

        "intent": intent,

        "required_agents": required_agents,

        "entities": {
            "amount": amount,
            "vendor_name": vendor_name,
            "invoice_number": invoice_number
        },

        "results": results,

        "activity": activity
    }