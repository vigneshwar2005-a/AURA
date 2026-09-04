import json
import re
import urllib.request
import urllib.error


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:3b"


SYSTEM_PROMPT = """
You are the AI Intent Layer for AURA
(Autonomous Unified Razorpay Agent).

Your job is ONLY to understand the user's payment request
and extract structured information.

Return ONLY valid JSON.
Do not use markdown.
Do not explain anything.

JSON format:

{
  "intent": "payment | compliance | analysis | unknown",
  "amount": number or null,
  "currency": "INR" or null,
  "vendor_name": string or null,
  "invoice_number": string or null,
  "due_days": number or null,
  "is_overdue": true or false,
  "requires_compliance": true or false
}

Rules:

- Extract the payment amount if explicitly provided.
- Never invent an amount.
- Extract vendor/supplier name.
- Extract invoice number.
- Convert phrases such as "within 5 days" into due_days: 5.
- If the request says overdue, set is_overdue to true.
- Detect export compliance requests.
- If the request is unrelated to payment/export analysis,
  use intent "unknown".
- This layer must NEVER approve or execute a payment.
"""


def _extract_json(text: str):
    """
    Extract the first JSON object returned by the model.
    """

    text = text.strip()

    # Remove accidental markdown fences.
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object inside the response.
    match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )

    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _normalize_result(data: dict):
    """
    Normalize the model response into the structure
    expected by AURA.
    """

    amount = data.get("amount")

    if isinstance(amount, str):
        cleaned = (
            amount
            .replace("₹", "")
            .replace(",", "")
            .replace("INR", "")
            .strip()
        )

        try:
            amount = float(cleaned)
        except ValueError:
            amount = None

    if isinstance(amount, (int, float)):
        amount = float(amount)

    due_days = data.get("due_days")

    if isinstance(due_days, str):
        match = re.search(r"\d+", due_days)

        if match:
            due_days = int(match.group())
        else:
            due_days = None

    if isinstance(due_days, float):
        due_days = int(due_days)

    return {
        "intent": data.get(
            "intent",
            "unknown"
        ),
        "amount": amount,
        "currency": data.get(
            "currency",
            "INR" if amount is not None else None
        ),
        "vendor_name": data.get(
            "vendor_name"
        ),
        "invoice_number": data.get(
            "invoice_number"
        ),
        "due_days": due_days,
        "is_overdue": bool(
            data.get(
                "is_overdue",
                False
            )
        ),
        "requires_compliance": bool(
            data.get(
                "requires_compliance",
                False
            )
        ),
        "ai_provider": "Ollama",
        "ai_model": MODEL
    }


def analyze_payment_intent(request: str):
    """
    Send the user's natural-language request to the
    local Qwen model and return structured intent data.

    This function NEVER performs payment execution.
    """

    if not request or not request.strip():
        return {
            "success": False,
            "error": "Empty request."
        }

    prompt = (
        SYSTEM_PROMPT
        + "\n\nUSER REQUEST:\n"
        + request.strip()
    )

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    try:
        body = json.dumps(
            payload
        ).encode("utf-8")

        req = urllib.request.Request(
            OLLAMA_URL,
            data=body,
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(
            req,
            timeout=60
        ) as response:

            response_body = response.read().decode(
                "utf-8"
            )

        response_data = json.loads(
            response_body
        )

        model_text = response_data.get(
            "response",
            ""
        )

        parsed = _extract_json(
            model_text
        )

        if not isinstance(parsed, dict):
            return {
                "success": False,
                "error": (
                    "AI returned an invalid JSON response."
                )
            }

        normalized = _normalize_result(
            parsed
        )

        return {
            "success": True,
            "data": normalized
        }

    except urllib.error.URLError as error:
        return {
            "success": False,
            "error": (
                "Ollama is not reachable. "
                "Make sure Ollama is running."
            ),
            "details": str(error)
        }

    except TimeoutError:
        return {
            "success": False,
            "error": "Ollama request timed out."
        }

    except Exception as error:
        return {
            "success": False,
            "error": "AI intent analysis failed.",
            "details": str(error)
        }


if __name__ == "__main__":

    test_request = (
        "Pay ABC Exports ₹50,000 for invoice INV-102. "
        "The payment is due within 5 days."
    )

    result = analyze_payment_intent(
        test_request
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )