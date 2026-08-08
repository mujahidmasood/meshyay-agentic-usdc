"""Minimal settings for the standalone USDC-payout demonstration.

In the full Meshyay backend these live on the app-wide ``Settings`` object and
are supplied by a DB-backed managed-secret store. Here they load from the
environment so this repo is runnable on its own. NO secret is committed — set
them in your shell / a local ``.env`` you do not commit.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    # Circle developer-controlled-wallets credentials (sandbox for the demo).
    circle_api_key: str = os.getenv("CIRCLE_API_KEY", "")
    circle_entity_secret: str = os.getenv("CIRCLE_ENTITY_SECRET", "")
    circle_wallet_id: str = os.getenv("CIRCLE_WALLET_ID", "")
    # Testnet USDC token by default — mainnet is a deliberate change.
    circle_usdc_token_id: str = os.getenv("CIRCLE_USDC_TOKEN_ID", "USDC-ETH-SEPOLIA")
    # Policy cap: the agent auto-settles payouts at/under this many USD in USDC;
    # anything larger is held for a human.
    usdc_auto_cap_usd: float = float(os.getenv("USDC_AUTO_CAP_USD", "50"))
    usdc_fee_level: str = os.getenv("USDC_FEE_LEVEL", "LOW")


settings = Settings()
