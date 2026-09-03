def check_export_compliance(
    shipping_bill: bool,
    invoice: bool,
    gst_lut: bool,
    edpms_realized: bool,
    e_firc: bool
):
    """
    AURA Compliance Agent

    Checks important export-compliance items and returns:
    - compliance status
    - risk level
    - missing items
    - explanation for each missing item
    - recommended action
    """

    checks = [
        {
            "name": "Shipping Bill",
            "available": shipping_bill,
            "why": "Confirms that the export shipment has been declared.",
            "action": "Upload or verify the Shipping Bill."
        },
        {
            "name": "Export Invoice",
            "available": invoice,
            "why": "Supports the commercial value and details of the export transaction.",
            "action": "Upload or verify the final export invoice."
        },
        {
            "name": "GST LUT",
            "available": gst_lut,
            "why": "Supports export under LUT where applicable.",
            "action": "Verify that the applicable GST LUT is available and valid."
        },
        {
            "name": "EDPMS realization",
            "available": edpms_realized,
            "why": "Helps confirm realization of export proceeds through the banking system.",
            "action": "Check the bank/EDPMS status and resolve any outstanding realization."
        },
        {
            "name": "e-FIRC / realization proof",
            "available": e_firc,
            "why": "Provides supporting evidence of foreign inward remittance where applicable.",
            "action": "Obtain or verify the applicable realization proof."
        }
    ]

    missing_items = []
    explanations = []
    recommended_actions = []

    for check in checks:
        if not check["available"]:
            missing_items.append(check["name"])

            explanations.append({
                "item": check["name"],
                "why": check["why"]
            })

            recommended_actions.append({
                "item": check["name"],
                "action": check["action"]
            })

    missing_count = len(missing_items)

    # Determine overall compliance risk.
    if missing_count == 0:
        status = "COMPLIANT"
        risk = "LOW"

        message = (
            "All configured export compliance checks are satisfied."
        )

        next_action = (
            "No immediate compliance action required."
        )

    elif missing_count >= 3:
        status = "ACTION_REQUIRED"
        risk = "HIGH"

        message = (
            f"{missing_count} export compliance items are missing. "
            "Immediate review is recommended before proceeding."
        )

        next_action = (
            "Resolve the outstanding compliance items before "
            "payment or export closure."
        )

    else:
        status = "ACTION_REQUIRED"
        risk = "MEDIUM"

        message = (
            f"{missing_count} export compliance item(s) are missing. "
            "Review and resolve the outstanding items."
        )

        next_action = (
            "Resolve the outstanding compliance items before "
            "finalizing the workflow."
        )

    return {
        "agent": "compliance",
        "status": status,
        "risk": risk,
        "missing_count": missing_count,
        "missing_items": missing_items,
        "explanations": explanations,
        "recommended_actions": recommended_actions,
        "next_action": next_action,
        "message": message
    }