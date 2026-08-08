"""The autonomous-settlement decision (agent pays under cap; human over cap)."""
import asyncio

import pytest

from meshyay_usdc import usdc_payout
from meshyay_usdc.settle_payout import settle_supplier_payout
from meshyay_usdc.config import settings


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def circle_up(monkeypatch):
    monkeypatch.setattr(settings, "circle_api_key", "K")
    monkeypatch.setattr(settings, "circle_entity_secret", "S")
    monkeypatch.setattr(settings, "circle_wallet_id", "w")
    monkeypatch.setattr(settings, "usdc_auto_cap_usd", 50.0)
    monkeypatch.setattr(usdc_payout, "_send_sync",
                        lambda d, a, r: {"id": "tx-abc", "state": "INITIATED"})


def test_under_cap_agent_settles_in_usdc(circle_up):
    doc = run(settle_supplier_payout(
        supplier_usdc_address="0xSupplier", amount_usd=40.0, offer_id="OF-1"))
    assert doc["rail"] == "usdc"
    assert doc["status"] == "paid"
    assert doc["transfer_ref"] == "tx-abc"


def test_over_cap_waits_for_human(circle_up):
    doc = run(settle_supplier_payout(
        supplier_usdc_address="0xSupplier", amount_usd=250.0, offer_id="OF-2"))
    assert doc["rail"] == "pending_human"
    assert doc["status"] == "owed"


def test_no_wallet_waits_for_human(circle_up):
    doc = run(settle_supplier_payout(
        supplier_usdc_address="", amount_usd=10.0, offer_id="OF-3"))
    assert doc["rail"] == "pending_human"


def test_stale_fx_blocks_auto_settlement(circle_up):
    doc = run(settle_supplier_payout(
        supplier_usdc_address="0xSupplier", amount_usd=10.0, offer_id="OF-4",
        fx_stale=True))
    assert doc["rail"] == "pending_human"
