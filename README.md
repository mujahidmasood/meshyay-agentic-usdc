# Meshyay × Circle — Autonomous USDC Supplier Payouts

Verification repo for the **Agentic Economy Prize** (Build with Gemini XPRIZE).

Meshyay is an AI-run commerce business. When a supply deal is accepted, an
**ops agent settles the supplier's payout in USDC on its own** — no human at the
money step — **but only within a policy cap a human sets** (`usdc_auto_cap_usd`,
default **$50**). Above the cap, the payout is held for a human. This is Circle's
Agentic Economy thesis exactly: *the agent can reason, plan, execute — and now it
can pay too, safely, within policy.*

This repo contains the integration code that runs in the Meshyay backend,
extracted as a standalone, testable package so it can be reviewed and run on its
own. The files are copied verbatim from production (`app/services/usdc_payout.py`
and the `_pay_supplier` branch in `app/routers/supplier_offers.py`), changing
only import paths.

## How it works

```
supply deal accepted
        │
        ▼
settle_supplier_payout(amount, supplier_wallet, …)
        │
        ├─ within_auto_cap(amount)?  (configured AND 0 < amount ≤ $50)
        │        └─ yes ─▶ agent calls Circle → USDC transfer → rail="usdc"  ✅ autonomous
        │
        └─ over cap / no wallet / stale FX ─▶ held for a human (Stripe / owed)
```

- **`meshyay_usdc/usdc_payout.py`** — Circle **developer-controlled wallets**
  (Agent Wallets) client. `send_usdc()` submits a USDC transfer via the official
  `circle-developer-controlled-wallets` SDK, which generates the per-request
  entity-secret ciphertext. Never raises; no-ops when unconfigured.
- **`meshyay_usdc/settle_payout.py`** — the autonomous-vs-human decision
  (`within_auto_cap` gate), i.e. the exact `_pay_supplier` branch.
- **`meshyay_usdc/config.py`** — the settings (Circle keys + the policy cap).

### The policy gate (the crux)

```python
def within_auto_cap(amount_usd: float) -> bool:
    # agent auto-settles only when Circle is configured AND the amount is
    # positive AND at/under the human-set cap
    return configured() and 0 < amount_usd <= auto_cap()
```

## Safety

- **Testnet by default** — the Sepolia USDC token UUID. Mainnet is
  a deliberate config change (mainnet token id + a mainnet-funded wallet).
- **Optional per supplier** — a supplier is only paid in USDC if they provide a
  wallet address; otherwise the existing (Stripe) rail is used. No supplier is
  forced onto crypto.
- **Bounded autonomy** — the human sets the cap; the agent only acts under it.

## Run the tests

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q          # policy gate + settlement decision, Circle SDK stubbed
```

## Configure against Circle sandbox (to run a real testnet transfer)

Set these in your environment (never commit them):

```bash
export CIRCLE_API_KEY=...             # Circle sandbox API key
export CIRCLE_ENTITY_SECRET=...       # registered entity secret
export CIRCLE_WALLET_ID=...           # a funded testnet wallet in your wallet set
export CIRCLE_USDC_TOKEN_ID=5797fbd6-3795-519d-84ca-ec4c5f80c3b1  # USDC ETH-SEPOLIA (default)
export USDC_AUTO_CAP_USD=50
```

Fund the wallet from the [Circle testnet faucet](https://faucet.circle.com), then
`send_usdc(destination, amount, ref)` moves testnet USDC to `destination`.

## Links

- Circle Agent Stack — https://www.circle.com/agent-stack
- Developer-controlled wallets — https://developers.circle.com/w3s
- Testnet faucet — https://faucet.circle.com

## License

MIT — see [LICENSE](LICENSE).
