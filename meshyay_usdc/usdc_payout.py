"""USDC supplier payouts via Circle developer-controlled wallets (Agent Wallets).

Circle's Agentic Economy thesis: an agent should be able to PAY on its own, not
stop and wait for a human at the money step. So Meshyay's ops agent settles a
supplier's payout in USDC autonomously — but only within a human-set policy cap
(``usdc_auto_cap_usd``). At/under the cap the agent pays; over it, the payout is
held for an admin. Human sets the policy, agent executes within it.

SAFETY: this is wired for a Circle **testnet** token by default
(``circle_usdc_token_id = USDC-ETH-SEPOLIA``). Moving real mainnet USDC is a
deliberate config change (a mainnet token id + a mainnet-funded wallet), never
the default. No-ops safely (logs, returns unconfigured) when Circle isn't set.

This file is copied verbatim from the Meshyay backend
(``app/services/usdc_payout.py``) except for the import path and the metering
call, so this public repo verifies exactly what runs in production.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from .config import settings

log = logging.getLogger("meshyay.usdc")


def configured() -> bool:
    """True when Circle credentials + a paying wallet are all set."""
    return bool(
        settings.circle_api_key
        and settings.circle_entity_secret
        and settings.circle_wallet_id
    )


def auto_cap() -> float:
    """The policy cap: payouts at/under this settle autonomously in USDC."""
    try:
        return float(settings.usdc_auto_cap_usd)
    except (TypeError, ValueError):
        return 50.0


def within_auto_cap(amount_usd: float) -> bool:
    return configured() and 0 < amount_usd <= auto_cap()


def _send_sync(destination: str, amount_usd: float, ref: str) -> dict:
    """Blocking Circle SDK call — run via asyncio.to_thread. Returns
    ``{id, state}`` or raises."""
    from circle.web3 import utils
    from circle.web3.developer_controlled_wallets import (
        TransactionsApi,
        CreateTransferTransactionForDeveloperRequest,
    )

    client = utils.init_developer_controlled_wallets_client(
        api_key=settings.circle_api_key,
        entity_secret=settings.circle_entity_secret,
    )
    req = CreateTransferTransactionForDeveloperRequest(
        wallet_id=settings.circle_wallet_id,
        token_id=settings.circle_usdc_token_id,
        destination_address=destination,
        amounts=[f"{amount_usd:.2f}"],
        fee_level=(settings.usdc_fee_level or "LOW"),
        idempotency_key=str(uuid.uuid4()),
        ref_id=ref[:50],
    )
    resp = TransactionsApi(client).create_developer_transaction_transfer(req)
    data = getattr(resp, "data", None)
    return {
        "id": getattr(data, "id", "") or "",
        "state": getattr(data, "state", "") or "INITIATED",
    }


async def send_usdc(destination: str, amount_usd: float, ref: str) -> dict:
    """Send ``amount_usd`` of USDC to ``destination``. Returns
    ``{ok, tx_id, state}`` or ``{ok: False, error}``. Never raises — a failed
    USDC settlement falls back to the caller's existing 'owed' handling."""
    if not configured():
        return {"ok": False, "error": "USDC payouts not configured"}
    if not destination or amount_usd <= 0:
        return {"ok": False, "error": "missing destination or amount"}
    try:
        out = await asyncio.to_thread(_send_sync, destination, amount_usd, ref)
        log.info("[usdc] sent %.2f USDC to %s tx=%s state=%s",
                 amount_usd, destination, out["id"], out["state"])
        return {"ok": True, "tx_id": out["id"], "state": out["state"]}
    except Exception as exc:  # noqa: BLE001 — degrade, never break a payout
        log.warning("[usdc] transfer failed: %s", exc)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
