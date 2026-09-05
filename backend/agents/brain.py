import json
import re
from datetime import date, timedelta

from agents.vendor import check_vendor_payment
from agents.compliance import check_export_compliance
from services.risk_engine import calculate_risk

try:
    from services.ai_intent import analyze_payment_intent
except Exception:
    analyze_payment_intent = None


# ============================================================
# AURA — Autonomous Unified Razorpay Agent
# ============================================================
#
# AI Intent Layer:
#   Qwen 2.5:3B understands the natural-language request.
#
# AURA Brain:
#   Uses deterministic validation + AI enrichment to route
#   the correct agents.
#
# Risk Engine:
#   Deterministically decides LOW / MEDIUM / HIGH.
#
# IMPORTANT:
#   AI NEVER approves or executes payments.
#   Razorpay execution remains behind explicit human approval.
# ============================================================


# ============================================================
# ACTIVITY
# ============================================================

def build_activity(
    agent: str,
    message: str,
    status: str = "completed"
):
    return {
        "agent": agent,
        "message": message,
        "status": status
    }


# ============================================================
# AMOUNT EXTRACTION
# ============================================================

def extract_amount(request: str):
    """
    Extract payment amount from natural-language requests.

    Supports:
        ₹50,000
        ₹50000
        Rs 50000
        INR 50000
        50k
        50 thousand
        1 lakh
        ten thousand
        twenty five thousand
        fifty thousand
        one hundred thousand
        one lakh
        two lakh
        one hundred and twenty five thousand

    IMPORTANT:
        Never invents a default amount.
    """

    if not request:
        return None

    text = request.lower().replace(",", "").strip()

    # ========================================================
    # 1. Numeric formats
    # ========================================================

    patterns = [
        r"₹\s*(\d+(?:\.\d+)?)",
        r"\brs\.?\s*(\d+(?:\.\d+)?)",
        r"\binr\s*(\d+(?:\.\d+)?)",
        r"\b(\d+(?:\.\d+)?)\s*(?:thousand|k)\b",
        r"\b(\d+(?:\.\d+)?)\s*lakh\b",
        r"\bamount\s*(?:is|of)?\s*(\d+(?:\.\d+)?)\b",
    ]

    for index, pattern in enumerate(patterns):

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:
            continue

        try:
            value = float(match.group(1))

            if index == 3:
                value *= 1000

            elif index == 4:
                value *= 100000

            if value <= 0:
                return None

            return value

        except (TypeError, ValueError):
            return None

    # ========================================================
    # 2. English number-word conversion
    # ========================================================

    number_words = {
        "zero": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
        "thirty": 30,
        "forty": 40,
        "fifty": 50,
        "sixty": 60,
        "seventy": 70,
        "eighty": 80,
        "ninety": 90,
    }

    def words_to_number(words):
        total = 0
        current = 0

        for word in words:

            if word in number_words:
                current += number_words[word]

            elif word == "hundred":
                if current == 0:
                    current = 1

                current *= 100

            elif word == "thousand":
                if current == 0:
                    current = 1

                total += current * 1000
                current = 0

            elif word == "lakh":
                if current == 0:
                    current = 1

                total += current * 100000
                current = 0

            elif word == "and":
                continue

            else:
                return None

        total += current

        if total <= 0:
            return None

        return total

    # ========================================================
    # 3. Find English number phrases
    # ========================================================

    word = (
        r"(?:zero|one|two|three|four|five|six|seven|eight|nine|"
        r"ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
        r"seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|"
        r"sixty|seventy|eighty|ninety|hundred|thousand|lakh|and)"
    )

    words_pattern = rf"\b({word}(?:\s+{word}){{0,10}})\b"

    for match in re.finditer(
        words_pattern,
        text,
        re.IGNORECASE
    ):
        phrase = match.group(1).strip()
        phrase_words = phrase.split()

        # A standalone number word such as "ten" should not
        # accidentally become a payment amount. Require an
        # amount multiplier for natural-language amounts.
        if not re.search(
            r"\b(thousand|lakh|hundred)\b",
            phrase,
            re.IGNORECASE
        ):
            continue

        value = words_to_number(phrase_words)

        if value is not None and value > 0:
            return float(value)

    return None


# ============================================================
# VENDOR EXTRACTION
# ============================================================

def extract_vendor_name(request: str):

    if not request:
        return None

    patterns = [
        r"\bpay\s+([A-Za-z][A-Za-z0-9&.\- ]+?)(?=\s+₹|\s+rs\.?|\s+inr|\s+for\b|\s+after\b|\.|$)",

        r"\bvendor\s+([A-Za-z][A-Za-z0-9&.\- ]+?)(?=\s+₹|\s+rs\.?|\s+inr|\s+for\b|\.|$)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            request,
            re.IGNORECASE
        )

        if match:

            name = match.group(1).strip()

            if name:
                return name

    return None


# ============================================================
# INVOICE EXTRACTION
# ============================================================

def extract_invoice_number(request: str):

    if not request:
        return None

    match = re.search(
        r"\binvoice\s+(?:number\s+|no\.?\s+|#\s*)?([A-Za-z0-9\-_\/]+)",
        request,
        re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    return None


# ============================================================
# DUE-DAY EXTRACTION
# ============================================================

def extract_explicit_due_days(request: str):
    """
    Detect explicit timing from the user's request.

    Examples:
        due within 5 days
        due in 3 days
        payment deadline in 2 days
        overdue
        payment is late
    """

    if not request:
        return None

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

        r"\bpayment deadline\s+(?:is\s+)?"
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


# ============================================================
# APPLY USER-STATED DEADLINE
# ============================================================

def apply_explicit_vendor_deadline(
    vendor_result: dict,
    request: str
):

    due_days = extract_explicit_due_days(request)

    if due_days is None:
        return vendor_result

    today = date.today()

    stated_due_date = (
        today + timedelta(days=due_days)
    )

    vendor_result = dict(vendor_result)

    vendor_result["stated_deadline"] = True
    vendor_result["deadline_source"] = "USER_STATED"
    vendor_result["stated_days_remaining"] = due_days
    vendor_result["due_date"] = str(stated_due_date)
    vendor_result["days_remaining"] = due_days

    # OVERDUE
    if due_days <= 0:

        vendor_result["status"] = "OVERDUE"
        vendor_result["risk"] = "HIGH"
        vendor_result["43B_h_risk"] = "HIGH"
        vendor_result["decision"] = "BLOCK_PAYMENT"

        vendor_result["message"] = (
            "The user-stated MSME payment deadline has already "
            "passed and may create Section 43B(h) tax risk."
        )

        vendor_result["recommended_action"] = (
            "Escalate the payment immediately and review the "
            "tax impact before proceeding."
        )

    # DUE SOON
    elif due_days <= 5:

        vendor_result["status"] = "DUE_SOON"
        vendor_result["risk"] = "MEDIUM"
        vendor_result["43B_h_risk"] = "MEDIUM"
        vendor_result["decision"] = "REVIEW_REQUIRED"

        vendor_result["message"] = (
            f"The user-stated MSME payment deadline is in "
            f"{due_days} day"
            f"{'s' if due_days != 1 else ''}."
        )

        vendor_result["recommended_action"] = (
            "Prioritize this payment and complete it before "
            "the stated deadline."
        )

    # WITHIN LIMIT
    else:

        vendor_result["status"] = "WITHIN_LIMIT"
        vendor_result["risk"] = "LOW"
        vendor_result["43B_h_risk"] = "LOW"
        vendor_result["decision"] = "PAYMENT_READY"

        vendor_result["message"] = (
            f"The user-stated MSME payment deadline is in "
            f"{due_days} days and is not currently due soon."
        )

        vendor_result["recommended_action"] = (
            "Payment can proceed while remaining within the "
            "current review threshold."
        )

    return vendor_result


# ============================================================
# AI INTENT LAYER
# ============================================================

def run_ai_intent_layer(request: str):

    if analyze_payment_intent is None:

        return {
            "success": False,
            "status": "unavailable",
            "message": "AI Intent Layer is unavailable.",
            "data": {
                "intent": None,
                "amount": None,
                "currency": None,
                "vendor_name": None,
                "invoice_number": None,
                "due_days": None,
                "is_overdue": False,
                "requires_compliance": False
            }
        }

    try:

        result = analyze_payment_intent(
            request
        )

        if not isinstance(result, dict):

            return {
                "success": False,
                "status": "error",
                "message": "AI returned an invalid response.",
                "data": {}
            }

        result = dict(result)

        result["status"] = "available"

        return result

    except Exception as exc:

        return {
            "success": False,
            "status": "error",
            "message": f"AI Intent Layer error: {str(exc)}",
            "data": {}
        }


# ============================================================
# DETERMINISTIC INTENT
# ============================================================

def detect_intent(request: str):

    text = request.lower().strip()

    has_payment = bool(
        re.search(
            r"\bpay\b|\bpayment\b|"
            r"\bprocess\b.*\bpayment\b|"
            r"\btransfer\b|\bsettle\b",
            text
        )
    )

    has_compliance = bool(
        re.search(
            r"\bcompliance\b|"
            r"\bgst\s+lut\b|"
            r"\bshipping\s+bill\b|"
            r"\bexport\s+invoice\b|"
            r"\bedpms\b|"
            r"\be-firc\b|"
            r"\bfirc\b|"
            r"\brealization\b",
            text
        )
    )

    has_vendor = bool(
        re.search(
            r"\bvendor\b|"
            r"\bmsme\b|"
            r"\bmicro enterprise\b|"
            r"\bsmall enterprise\b|"
            r"\bsection 43b\b|"
            r"\b43b\(h\)",
            text
        )
    )

    if has_payment and has_compliance:
        return "full_export_workflow"

    if has_payment and has_vendor:
        return "vendor_commerce"

    if has_payment:
        return "commerce"

    if has_compliance:
        return "compliance"

    return "unknown"


# ============================================================
# AI-ENRICHED AGENT ROUTING
# ============================================================

def determine_agent_requirements(
    request: str,
    deterministic_intent: str,
    ai_result: dict
):
    """
    Combines deterministic routing with AI enrichment.

    AI can help identify:
        - payment intent
        - due date
        - vendor
        - compliance requirement

    AI does NOT determine final risk.
    """

    ai_data = {}

    if isinstance(ai_result, dict):

        ai_data = ai_result.get(
            "data",
            {}
        )

        if not isinstance(ai_data, dict):
            ai_data = {}

    text = request.lower()

    ai_intent = str(
        ai_data.get("intent") or ""
    ).lower().strip()

    ai_due_days = ai_data.get(
        "due_days"
    )

    ai_overdue = bool(
        ai_data.get("is_overdue", False)
    )

    ai_requires_compliance = bool(
        ai_data.get(
            "requires_compliance",
            False
        )
    )

    # --------------------------------------------------------
    # Compliance detection
    # --------------------------------------------------------

    has_compliance_keywords = bool(
        re.search(
            r"\bcompliance\b|"
            r"\bgst\s+lut\b|"
            r"\bshipping\s+bill\b|"
            r"\bexport\s+invoice\b|"
            r"\bedpms\b|"
            r"\be-firc\b|"
            r"\bfirc\b|"
            r"\brealization\b",
            text
        )
    )

    requires_compliance = (
        ai_requires_compliance
        or has_compliance_keywords
    )

    # --------------------------------------------------------
    # Vendor/payment timing detection
    # --------------------------------------------------------

    explicit_due_days = extract_explicit_due_days(
        request
    )

    vendor_context = bool(
        explicit_due_days is not None
        or ai_due_days is not None
        or ai_overdue
        or re.search(
            r"\bvendor\b|"
            r"\bmsme\b|"
            r"\bmicro enterprise\b|"
            r"\bsmall enterprise\b|"
            r"\bsection 43b\b|"
            r"\b43b\(h\)",
            text
        )
    )

    # AI identified a payment and timing context.
    if ai_intent == "payment":
        vendor_context = (
            vendor_context
            or ai_due_days is not None
            or ai_overdue
        )

    # --------------------------------------------------------
    # Final routing
    # --------------------------------------------------------

    if deterministic_intent == "unknown":

        if ai_intent == "payment":
            deterministic_intent = "commerce"

        elif ai_intent == "compliance":
            deterministic_intent = "compliance"

    if deterministic_intent in [
        "commerce",
        "vendor_commerce",
        "full_export_workflow",
        "compliance_commerce"
    ]:

        if requires_compliance and vendor_context:
            final_intent = "full_export_workflow"

        elif requires_compliance:
            final_intent = "compliance_commerce"

        elif vendor_context:
            final_intent = "vendor_commerce"

        else:
            final_intent = "commerce"

    else:

        final_intent = deterministic_intent

    required_agents = ["brain"]

    if final_intent in [
        "vendor_commerce",
        "full_export_workflow"
    ]:
        required_agents.append("vendor")

    if final_intent in [
        "compliance",
        "compliance_commerce",
        "full_export_workflow"
    ]:
        required_agents.append("compliance")

    if final_intent in [
        "commerce",
        "vendor_commerce",
        "compliance_commerce",
        "full_export_workflow"
    ]:
        required_agents.append("commerce")

    return final_intent, required_agents


# ============================================================
# VENDOR AGENT
# ============================================================

def run_vendor_agent(request: str):

    amount = extract_amount(request)

    if amount is None:

        return {
            "agent": "vendor",
            "status": "INVALID_REQUEST",
            "risk": "HIGH",
            "43B_h_risk": "HIGH",
            "decision": "BLOCK_PAYMENT",
            "message": (
                "Payment amount is missing. AURA cannot evaluate "
                "or authorize a payment without an explicit amount."
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

def run_compliance_agent(request: str):

    try:

        result = check_export_compliance()

        if isinstance(result, dict):
            return result

    except TypeError:

        try:

            result = check_export_compliance(
                request
            )

            if isinstance(result, dict):
                return result

        except Exception:
            pass

    except Exception:
        pass

    return {
        "agent": "compliance",
        "status": "ERROR",
        "risk": "HIGH",
        "decision": "BLOCK_PAYMENT",
        "message": (
            "Unable to complete export compliance evaluation."
        ),
        "recommended_action": (
            "Review the required export documents before payment."
        )
    }


# ============================================================
# RISK DECISION
# ============================================================

def decide_payment_action(
    risk_level: str
):

    normalized = str(
        risk_level
    ).upper().strip()

    decision_map = {
        "HIGH": "BLOCK_PAYMENT",
        "MEDIUM": "REVIEW_REQUIRED",
        "LOW": "PAYMENT_READY"
    }

    return decision_map.get(
        normalized,
        "BLOCK_PAYMENT"
    )


# ============================================================
# AGENTIC COMMERCE CONTEXT
# ============================================================

def build_agentic_commerce_context(
    amount,
    currency="INR"
):

    return {
        "protocol_style": "AP2/ACP-inspired",
        "payment_action": "HUMAN_APPROVAL_REQUIRED",
        "execution_status": "AWAITING_HUMAN_APPROVAL",
        "amount": amount,
        "currency": currency,
        "razorpay_order_created": False,
        "message": (
            "AURA has prepared the payment context. "
            "Razorpay execution requires explicit human "
            "authorization."
        )
    }


# ============================================================
# EXECUTABLE REQUEST VALIDATION
# ============================================================

def validate_executable_request(
    request: str,
    intent: str,
    amount
):

    executable_intents = [
        "commerce",
        "vendor_commerce",
        "compliance_commerce",
        "full_export_workflow"
    ]

    if (
        amount is None
        and intent in executable_intents
    ):

        return {
            "valid": False,
            "response": {
                "agent": "aura",
                "name": "AURA",
                "expansion": (
                    "Autonomous Unified Razorpay Agent"
                ),
                "status": "invalid_request",
                "request": request,
                "intent": intent,
                "required_agents": [],
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
                    "AURA cannot continue an executable "
                    "payment workflow without an explicit amount."
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
        }

    return {
        "valid": True,
        "response": None
    }


# ============================================================
# MAIN AURA BRAIN
# ============================================================

def aura_brain(request: str):

    if not request or not request.strip():

        return {
            "agent": "aura",
            "name": "AURA",
            "expansion": (
                "Autonomous Unified Razorpay Agent"
            ),
            "status": "invalid_request",
            "request": request,
            "intent": "unknown",
            "message": "Request cannot be empty.",
            "action_required": (
                "Provide a payment or analysis request."
            ),
            "razorpay_order_id": None,
            "activity": [
                build_activity(
                    "brain",
                    "Empty request received",
                    "blocked"
                )
            ]
        }

    request = request.strip()

    # ========================================================
    # 1. AI INTENT
    # ========================================================

    ai_result = run_ai_intent_layer(
        request
    )

    # ========================================================
    # 2. DETERMINISTIC INTENT
    # ========================================================

    deterministic_intent = detect_intent(
        request
    )

    # ========================================================
    # 3. AI-ENRICHED ROUTING
    # ========================================================

    intent, required_agents = (
        determine_agent_requirements(
            request=request,
            deterministic_intent=deterministic_intent,
            ai_result=ai_result
        )
    )

    # ========================================================
    # 4. AMOUNT
    # ========================================================

    amount = extract_amount(
        request
    )

    # ========================================================
    # 5. SAFE VALIDATION
    # ========================================================

    validation = validate_executable_request(
        request=request,
        intent=intent,
        amount=amount
    )

    if not validation["valid"]:

        response = validation["response"]

        response["ai_intent"] = ai_result

        return response

    # ========================================================
    # 6. ENTITIES
    # ========================================================

    deterministic_vendor = extract_vendor_name(
        request
    )

    deterministic_invoice = extract_invoice_number(
        request
    )

    ai_data = {}

    if isinstance(ai_result, dict):

        ai_data = ai_result.get(
            "data",
            {}
        )

        if not isinstance(ai_data, dict):
            ai_data = {}

    vendor_name = (
        deterministic_vendor
        or ai_data.get("vendor_name")
    )

    invoice_number = (
        deterministic_invoice
        or ai_data.get("invoice_number")
    )

    # ========================================================
    # 7. ACTIVITY
    # ========================================================

    activity = [
        build_activity(
            "brain",
            "Received exporter request"
        ),

        build_activity(
            "ai_intent",
            "Qwen 2.5:3B analyzed the request"
        ),

        build_activity(
            "brain",
            f"Intent classified as {intent}"
        )
    ]

    # ========================================================
    # 8. AGENT RESULTS
    # ========================================================

    vendor_result = None
    compliance_result = None
    commerce_result = None

    # --------------------------------------------------------
    # VENDOR
    # --------------------------------------------------------

    if "vendor" in required_agents:

        vendor_result = run_vendor_agent(
            request
        )

        activity.append(
            build_activity(
                "vendor",
                "Vendor payment risk evaluated"
            )
        )

    # --------------------------------------------------------
    # COMPLIANCE
    # --------------------------------------------------------

    if "compliance" in required_agents:

        compliance_result = run_compliance_agent(
            request
        )

        activity.append(
            build_activity(
                "compliance",
                "Export compliance requirements evaluated"
            )
        )

    # ========================================================
    # 9. RISK SOURCES
    # ========================================================

    risks = []

    if vendor_result:

        vendor_risk = vendor_result.get(
            "risk"
        )

        if vendor_risk:
            risks.append(vendor_risk)

    if compliance_result:

        compliance_risk = compliance_result.get(
            "risk"
        )

        if compliance_risk:
            risks.append(compliance_risk)

    # ========================================================
    # 10. RISK ENGINE
    # ========================================================

    risk_result = calculate_risk(
        risks
    )

    risk_level = risk_result.get(
        "risk_level",
        "LOW"
    )

    decision = decide_payment_action(
        risk_level
    )

    activity.append(
        build_activity(
            "risk_engine",
            f"Risk assessed as {risk_level}"
        )
    )

    # ========================================================
    # 11. FINAL DETERMINISTIC SAFETY DECISION
    # ========================================================

    if risk_level == "HIGH":

        decision = "BLOCK_PAYMENT"

    elif risk_level == "MEDIUM":

        decision = "REVIEW_REQUIRED"

    elif risk_level == "LOW":

        decision = "PAYMENT_READY"

    else:

        decision = "BLOCK_PAYMENT"

    # ========================================================
    # 12. ACTIVITY FOR FINAL DECISION
    # ========================================================

    if decision == "BLOCK_PAYMENT":

        activity.append(
            build_activity(
                "brain",
                "Payment blocked due to high risk",
                "blocked"
            )
        )

    elif decision == "REVIEW_REQUIRED":

        activity.append(
            build_activity(
                "brain",
                "Human review required before payment",
                "review"
            )
        )

    elif decision == "PAYMENT_READY":

        activity.append(
            build_activity(
                "brain",
                "Payment is ready for human authorization"
            )
        )

    # ========================================================
    # 13. COMMERCE
    # ========================================================

    if "commerce" in required_agents:

        commerce_result = (
            build_agentic_commerce_context(
                amount=amount,
                currency="INR"
            )
        )

        activity.append(
            build_activity(
                "commerce",
                "Payment prepared and awaiting human approval"
            )
        )

    # ========================================================
    # 14. RECOMMENDATION
    # ========================================================

    recommendation = risk_result.get(
        "recommendation"
    )

    if vendor_result:

        vendor_action = vendor_result.get(
            "recommended_action"
        )

        if vendor_action:
            recommendation = vendor_action

    if compliance_result:

        compliance_action = (
            compliance_result.get(
                "recommended_action"
            )
            or compliance_result.get(
                "next_action"
            )
        )

        if (
            compliance_action
            and risk_level in [
                "MEDIUM",
                "HIGH"
            ]
        ):

            recommendation = compliance_action

    # ========================================================
    # 15. PAYMENT ACTION
    # ========================================================

    payment_action = None
    razorpay_order_id = None

    if commerce_result:

        payment_action = (
            "HUMAN_APPROVAL_REQUIRED"
        )

        # CRITICAL:
        #
        # No Razorpay order is created here.
        #
        # /payment/approve is responsible for creating
        # the Razorpay order after explicit human approval.

    # ========================================================
    # 16. FINAL RESPONSE
    # ========================================================

    response = {

        "agent": "aura",

        "name": "AURA",

        "expansion": (
            "Autonomous Unified Razorpay Agent"
        ),

        "status": "completed",

        "request": request,

        "intent": intent,

        "required_agents": required_agents,

        "entities": {
            "amount": amount,
            "currency": (
                "INR"
                if amount is not None
                else None
            ),
            "vendor_name": vendor_name,
            "invoice_number": invoice_number
        },

        "ai_intent": ai_result,

        "decision": decision,

        "risk": risk_result,

        "recommendation": recommendation,

        "vendor": vendor_result,

        "compliance": compliance_result,

        "commerce": commerce_result,

        "payment_action": payment_action,

        "razorpay_order_id": razorpay_order_id,

        "activity": activity,

        "audit": {
            "analysis_completed": True,

            "ai_intent_used_for_routing": True,

            "razorpay_order_created": False,

            "human_approval_required": (
                commerce_result is not None
            ),

            "payment_execution_allowed": False
        }
    }

    # ========================================================
    # 17. FINAL EXECUTION SAFETY
    # ========================================================

    # Initial brain analysis NEVER creates a Razorpay order.

    response["razorpay_order_id"] = None

    response["audit"][
        "razorpay_order_created"
    ] = False

    response["audit"][
        "payment_execution_allowed"
    ] = False

    return response


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    test_request = (
        "Pay ABC Exports ₹50,000 for invoice INV-102. "
        "The payment is due within 5 days."
    )

    result = aura_brain(
        test_request
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )