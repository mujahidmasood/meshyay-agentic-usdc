"""Policy-gate + send-wrapper tests (Circle SDK stubbed — no keys/network).

    pip install -r requirements.txt && pytest -q
"""
import asyncio

import pytest

from meshyay_usdc import usdc_payout
from meshyay_usdc.config import settings


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "circle_api_key", "TEST_KEY")
    monkeypatch.setattr(settings, "circle_entity_secret", "TEST_SECRET")
    monkeypatch.setattr(settings, "circle_wallet_id", "wallet-123")
    monkeypatch.setattr(settings, "circle_usdc_token_id", "USDC-ETH-SEPOLIA")
    monkeypatch.setattr(settings, "usdc_auto_cap_usd", 50.0)


def test_unconfigured_is_disabled(monkeypatch):
    monkeypatch.setattr(settings, "circle_api_key", "")
    assert usdc_payout.configured() is False
    assert usdc_payout.within_auto_cap(10) is False


def test_within_auto_cap_boundary(configured):
    assert usdc_payout.within_auto_cap(49.99) is True
    assert usdc_payout.within_auto_cap(50.0) is True      # at the cap = auto
    assert usdc_payout.within_auto_cap(50.01) is False    # over = human
    assert usdc_payout.within_auto_cap(0) is False
    assert usdc_payout.within_auto_cap(-5) is False


def test_auto_cap_falls_back_on_bad_value(monkeypatch):
    monkeypatch.setattr(settings, "usdc_auto_cap_usd", "not-a-number")
    assert usdc_payout.auto_cap() == 50.0


def test_send_unconfigured_returns_error(monkeypatch):
    monkeypatch.setattr(settings, "circle_api_key", "")
    out = run(usdc_payout.send_usdc("0xabc", 10, "OFFER-1"))
    assert out["ok"] is False and "not configured" in out["error"]


def test_send_success(configured, monkeypatch):
    monkeypatch.setattr(usdc_payout, "_send_sync",
                        lambda dest, amt, ref: {"id": "tx-9", "state": "INITIATED"})
    out = run(usdc_payout.send_usdc("0xabc", 25.0, "OFFER-1"))
    assert out == {"ok": True, "tx_id": "tx-9", "state": "INITIATED"}


def test_send_rejects_missing_destination(configured):
    assert run(usdc_payout.send_usdc("", 25.0, "OFFER-1"))["ok"] is False


def test_send_swallows_sdk_error(configured, monkeypatch):
    def boom(dest, amt, ref):
        raise RuntimeError("circle 401")
    monkeypatch.setattr(usdc_payout, "_send_sync", boom)
    out = run(usdc_payout.send_usdc("0xabc", 25.0, "OFFER-1"))
    assert out["ok"] is False and "circle 401" in out["error"]
