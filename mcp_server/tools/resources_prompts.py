from app_instance import app


@app.resource("policy://credit-and-discount-authority")
def credit_and_discount_authority_policy() -> str:
    """Swiftrail's internal policy on credit hold severity and discount
    authority thresholds. Exposed as a resource (data to be read) rather than
    a tool, since it's a static reference document, not an action."""
    return (
        "SWIFTRAIL LOGISTICS -- CREDIT HOLD & DISCOUNT AUTHORITY POLICY\n"
        "(internal reference, v1.2)\n\n"
        "1. CREDIT HOLDS\n"
        "   - MINOR severity: invoice 30-89 days overdue. A sales_rep session\n"
        "     may release these directly.\n"
        "   - SEVERE severity: invoice 90+ days overdue, OR overdue balance\n"
        "     exceeds 25% of the customer's credit limit. Release always\n"
        "     pauses for explicit human confirmation, and can only be\n"
        "     finalized by a finance_manager session.\n\n"
        "2. RATE EXCEPTIONS (DISCOUNTS)\n"
        "   - Up to 15%: within a sales_rep's own authority, auto-approved.\n"
        "   - Above 15% (up to the 50% hard ceiling): always pauses for\n"
        "     explicit human confirmation, and can only be finalized by a\n"
        "     finance_manager session.\n"
    )


@app.prompt()
def draft_rate_exception_justification(
    shipment_id: str, discount_pct: str, reason_summary: str
) -> str:
    """Draft a justification for an above-authority rate exception request,
    ready to submit alongside approve_rate_exception."""
    return (
        f"Write a concise, specific justification (at least 20 characters, "
        f"no fluff) for requesting a {discount_pct}% discount on shipment "
        f"{shipment_id}. Context from the requester: {reason_summary}."
    )
