from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.ledger.simulation import LedgerAdapter, LedgerUnavailable


class PolygonAdapter(LedgerAdapter):
    mode = "polygon"
    network = "Polygon Amoy"

    def __init__(self):
        missing = [
            name
            for name, value in {
                "CHAIN_RPC_URL": settings.chain_rpc_url,
                "CHAIN_PRIVATE_KEY": settings.chain_private_key,
                "CHAIN_CONTRACT_ADDRESS": settings.chain_contract_address,
            }.items()
            if not value
        ]
        if missing:
            raise LedgerUnavailable(
                "Polygon adapter is not configured. Missing: " + ", ".join(missing)
            )

    def _rpc(self, method: str, params: list) -> dict:
        response = httpx.post(
            settings.chain_rpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise LedgerUnavailable(payload["error"].get("message", "RPC error"))
        return payload.get("result")

    def append(self, tx_type: str, actor_id: str | None, entity_type: str, entity_id: str, payload: dict) -> dict:
        try:
            from eth_account import Account
            from web3 import Web3
        except ImportError as exc:
            raise LedgerUnavailable(
                "Polygon mode requires the optional packages web3 and eth-account. Install them to enable it."
            ) from exc

        web3 = Web3(Web3.HTTPProvider(settings.chain_rpc_url))
        if not web3.is_connected():
            raise LedgerUnavailable("Could not connect to the configured Polygon RPC endpoint")
        account = Account.from_key(settings.chain_private_key)
        contract = web3.eth.contract(
            address=Web3.to_checksum_address(settings.chain_contract_address),
            abi=[
                {
                    "inputs": [
                        {"internalType": "string", "name": "recordId", "type": "string"},
                        {"internalType": "string", "name": "recordType", "type": "string"},
                        {"internalType": "string", "name": "payloadDigest", "type": "string"},
                        {"internalType": "string", "name": "entityId", "type": "string"},
                    ],
                    "name": "recordEvent",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function",
                }
            ],
        )
        from app.ledger.simulation import digest

        tx = contract.functions.recordEvent(
            entity_id, tx_type, digest(payload), entity_id
        ).build_transaction(
            {
                "from": account.address,
                "nonce": web3.eth.get_transaction_count(account.address),
                "chainId": settings.chain_id,
                "gas": 300000,
                "maxFeePerGas": web3.to_wei("35", "gwei"),
                "maxPriorityFeePerGas": web3.to_wei("30", "gwei"),
            }
        )
        signed = account.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        tx_hash = web3.eth.send_raw_transaction(raw)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status != 1:
            raise LedgerUnavailable("Polygon transaction reverted")
        return {
            "tx_id": web3.to_hex(tx_hash),
            "block_number": receipt.blockNumber,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tx_type": tx_type,
            "actor_id": actor_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "payload": payload,
            "mode": "polygon",
            "network": self.network,
            "status": "confirmed",
            "chain_tx_hash": web3.to_hex(tx_hash),
        }

    def verify_chain(self) -> dict:
        try:
            block = int(self._rpc("eth_blockNumber", []), 16)
            chain_id = int(self._rpc("eth_chainId", []), 16)
            return {
                "valid": chain_id == settings.chain_id,
                "records": None,
                "blocks": block,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "errors": [] if chain_id == settings.chain_id else [f"Connected chain id {chain_id} does not match configured chain id {settings.chain_id}"],
                "mode": self.mode,
                "network": self.network,
            }
        except Exception as exc:
            return {
                "valid": False,
                "records": None,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "errors": [str(exc)],
                "mode": self.mode,
                "network": self.network,
            }

    def transactions(self) -> list[dict]:
        return []

    def get_transaction(self, tx_id: str) -> dict | None:
        try:
            receipt = self._rpc("eth_getTransactionReceipt", [tx_id])
        except Exception:
            return None
        if not receipt:
            return None
        return {
            "tx_id": tx_id,
            "status": "confirmed" if int(receipt.get("status", "0x0"), 16) == 1 else "failed",
            "block_number": int(receipt.get("blockNumber", "0x0"), 16),
            "mode": self.mode,
            "network": self.network,
            "chain_tx_hash": tx_id,
        }

    def status(self) -> dict:
        try:
            chain_id = int(self._rpc("eth_chainId", []), 16)
            block = int(self._rpc("eth_blockNumber", []), 16)
            return {
                "mode": "polygon",
                "label": "Polygon Amoy Connected",
                "connected": True,
                "network": self.network,
                "chain_id": chain_id,
                "contract_address": settings.chain_contract_address,
                "block_number": block,
                "tamper_detected": False,
                "errors": [] if chain_id == settings.chain_id else ["Chain id mismatch"],
                "message": "Connected to Polygon Amoy. Records are submitted as real testnet transactions.",
            }
        except Exception as exc:
            return {
                "mode": "polygon",
                "label": "Disconnected",
                "connected": False,
                "network": self.network,
                "chain_id": settings.chain_id,
                "contract_address": settings.chain_contract_address or None,
                "tamper_detected": None,
                "errors": [str(exc)],
                "message": "Polygon Amoy is configured but unreachable.",
            }
