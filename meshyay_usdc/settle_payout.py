"""The autonomous-settlement decision, extracted from Meshyay's payout flow.

In the full backend this lives inside ``_pay_supplier`` (app/routers/
supplier_offers.py), called when a supply deal is received. The relevant branch
is reproduced here so this repo shows the *decision*, not just the transfer:

    # USDC autonomous settlement (Circle Agent Wallet): the ops agent pays the
    # supplier in USDC on its own, but ONLY up to the human-set policy cap
    # (usdc_auto_cap_usd). Over the cap, or if this fails, we fall through to the
    # Stripe path / 'owed'. This is the "agent pays within policy" flow.
    if usdc_address and usdc_payout.within_auto_cap(amount) and not fx_stale:
        res = await usdc_payout.send_usdc(usdc_address, amount, offer_id)
        if res.get("ok"):
            doc["status"] = "paid"
            doc["rail"] = "usdc"
            doc["transfer_ref"] = res["tx_id"]
            ...
            return doc
    # else: existing Stripe transfer / 'owed' path (unchanged)

``settle_supplier_payout`` below is that logic as a standalone, testable unit.
"""
from __future__ import annotations

from . import usdc_payout


async def settle_supplier_payout(
    *,
    supplier_usdc_address: str,
    amount_usd: float,
    offer_id: str,
    fx_stale: bool = False,
) -> dict:
    """Decide how a supplier payout settles and (for USDC) execute it.

    Returns a payout record. ``rail`` is ``"usdc"`` when the ops agent settled
    autonomously in USDC, or ``"pending_human"`` when the amount is over the
    policy cap / the supplier has no wallet / a stale FX rate blocks auto-pay —
    in the full system those fall through to Stripe or are recorded as owed.
    """
    doc: dict = {
        "offer_id": offer_id,
        "amount_usd": amount_usd,
        "status": "pending",
        "rail": "",
        "transfer_ref": "",
    }

    # The agent pays on its own — but only within the human-set policy cap.
    if (
        supplier_usdc_address
        and usdc_payout.within_auto_cap(amount_usd)
        and not fx_stale
    ):
        res = await usdc_payout.send_usdc(
            supplier_usdc_address, amount_usd, offer_id
        )
        if res.get("ok"):
            doc["status"] = "paid"
            doc["rail"] = "usdc"
            doc["transfer_ref"] = res.get("tx_id", "")
            doc["usdc_state"] = res.get("state", "")
            return doc

    # Over the cap, no wallet, stale FX, or a failed transfer → a human settles
    # (Stripe transfer / recorded as owed in the full system).
    doc["status"] = "owed"
    doc["rail"] = "pending_human"
    return doc
