from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP
import os

from .clients import create_blockchain_client
from .config import get_config
from .schemas import BalanceRequest
from .tools_blockchain import (
    get_latest_block,
    get_total_supply,
    get_issued_supply,
    get_block_by_number,
    get_entry_by_hash,
    get_transaction_by_hash,
    fetch_transactions,
)
from .tools_wallet import get_balance as wallet_balance, fetch_balance as wallet_fetch_balance
from .tools_health import health as health_impl, version as version_impl
from .tools_wallet import generate_seed_phrase as gen_seed_impl, generate_keypair as gen_keypair_impl
from . import prompts as prompt_catalog


# Create the MCP server using the SDK's standard pattern
mcp = FastMCP("AIBlock MCP Server", stateless_http=True)


@mcp.tool()
def health() -> dict:
    return health_impl()


@mcp.tool()
def version() -> dict:
    return version_impl()


@mcp.tool(name="get-latest-block")
def blockchain_get_latest_block() -> dict:
    cfg = get_config()
    client = create_blockchain_client(cfg)
    resp = get_latest_block(client)
    return resp.model_dump()


@mcp.tool(name="get-balance")
def wallet_get_balance() -> dict:
    print("[tool] wallet.get_balance invoked", flush=True)
    resp = wallet_balance()
    return resp.model_dump()


@mcp.tool(name="fetch-balance")
def wallet_fetch_balance_tool(addresses: list[str]) -> dict:
    print(f"[tool] wallet.fetch_balance invoked with addresses={addresses}", flush=True)
    resp = wallet_fetch_balance(addresses)
    return resp.model_dump()


@mcp.tool(name="get-total-supply")
def blockchain_get_total_supply() -> dict:
    cfg = get_config()
    client = create_blockchain_client(cfg)
    resp = get_total_supply(client)
    return resp.model_dump()


@mcp.tool(name="get-issued-supply")
def blockchain_get_issued_supply() -> dict:
    cfg = get_config()
    client = create_blockchain_client(cfg)
    resp = get_issued_supply(client)
    return resp.model_dump()


@mcp.tool(name="get-block-by-number")
def blockchain_get_block_by_number(height: int) -> dict:
    cfg = get_config()
    client = create_blockchain_client(cfg)
    resp = get_block_by_number(client, height)
    return resp.model_dump()


@mcp.tool(name="get-entry-by-hash")
def blockchain_get_entry_by_hash(hash: str) -> dict:  # noqa: A002
    cfg = get_config()
    client = create_blockchain_client(cfg)
    resp = get_entry_by_hash(client, hash)
    return resp.model_dump()


@mcp.tool(name="get-transaction-by-hash")
def blockchain_get_transaction_by_hash(tx_hash: str) -> dict:
    cfg = get_config()
    client = create_blockchain_client(cfg)
    resp = get_transaction_by_hash(client, tx_hash)
    return resp.model_dump()


@mcp.tool(name="fetch-transactions")
def blockchain_fetch_transactions(tx_hashes: list[str]) -> dict:
    cfg = get_config()
    client = create_blockchain_client(cfg)
    resp = fetch_transactions(client, tx_hashes)
    return resp.model_dump()


@mcp.tool(name="generate-seed-phrase")
def wallet_generate_seed_phrase() -> dict:
    return gen_seed_impl()


@mcp.tool(name="generate-keypair")
def wallet_generate_keypair(seedPhrase: Optional[str] = None) -> dict:  # noqa: N803 (external name)
    return gen_keypair_impl(seed_phrase=seedPhrase)


def _cors_wrapper(inner_app):
    allow_origins_env = os.environ.get("MCP_ALLOW_ORIGINS", "*")
    allow_origins = [o.strip() for o in allow_origins_env.split(",")] if allow_origins_env else ["*"]

    async def app(scope, receive, send):  # ASGI 3.0
        if scope.get("type") != "http":
            return await inner_app(scope, receive, send)

        async def send_with_cors(event):
            if event.get("type") == "http.response.start":
                headers = event.setdefault("headers", [])
                # Add CORS headers
                origin = None
                for name, value in scope.get("headers", []):
                    if name.lower() == b"origin":
                        origin = value.decode()
                        break
                allow_origin = "*" if "*" in allow_origins else (origin if origin in allow_origins else None)
                if allow_origin:
                    headers.append((b"access-control-allow-origin", allow_origin.encode()))
                headers.append((b"access-control-allow-headers", b"*"))
                headers.append((b"access-control-allow-methods", b"POST, OPTIONS"))
                headers.append((b"access-control-expose-headers", b"Mcp-Session-Id, X-Request-Id"))
            await send(event)

        # Handle preflight
        if scope.get("method") == "OPTIONS":
            start = {"type": "http.response.start", "status": 204, "headers": []}
            await send_with_cors(start)
            await send({"type": "http.response.body", "body": b""})
            return

        return await inner_app(scope, receive, send_with_cors)

    return app


# Expose Streamable HTTP ASGI app for the transport at root with minimal CORS
app = _cors_wrapper(mcp.streamable_http_app())


# Prompts registered via FastMCP.prompt() decorator (SDK standard)
@mcp.prompt(name="prompt.block.explain_header", title="Explain Block Header")
def prompt_block_explain_header(header_json: str) -> list[dict]:
    text = prompt_catalog.render_prompt("prompt.block.explain_header", header_json=header_json)
    return [{"role": "user", "content": text}]


@mcp.prompt(name="prompt.block.summarize", title="Summarize Block")
def prompt_block_summarize(block_json: str) -> list[dict]:
    text = prompt_catalog.render_prompt("prompt.block.summarize", block_json=block_json)
    return [{"role": "user", "content": text}]


@mcp.prompt(name="prompt.tx.explain", title="Explain Transaction")
def prompt_tx_explain(transaction_json: str) -> list[dict]:
    text = prompt_catalog.render_prompt("prompt.tx.explain", transaction_json=transaction_json)
    return [{"role": "user", "content": text}]


@mcp.prompt(name="prompt.tx.summarize_list", title="Summarize Transactions")
def prompt_tx_summarize_list(transactions_json: str) -> list[dict]:
    text = prompt_catalog.render_prompt("prompt.tx.summarize_list", transactions_json=transactions_json)
    return [{"role": "user", "content": text}]


@mcp.prompt(name="prompt.wallet.balance_summary", title="Wallet Balance Summary")
def prompt_wallet_balance_summary(balance_json: str) -> list[dict]:
    text = prompt_catalog.render_prompt("prompt.wallet.balance_summary", balance_json=balance_json)
    return [{"role": "user", "content": text}]


@mcp.prompt(name="prompt.error.help", title="Error Help")
def prompt_error_help(error_message: str, context: str) -> list[dict]:
    text = prompt_catalog.render_prompt("prompt.error.help", error_message=error_message, context=context)
    return [{"role": "user", "content": text}]


@mcp.prompt(name="prompt.security.seed_guidance", title="Seed Phrase Guidance")
def prompt_security_seed_guidance() -> list[dict]:
    text = prompt_catalog.render_prompt("prompt.security.seed_guidance")
    return [{"role": "user", "content": text}]

