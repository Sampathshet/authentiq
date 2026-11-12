import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings

GENESIS_HASH = "0" * 64


class LedgerError(RuntimeError):
    pass


class LedgerUnavailable(LedgerError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class LedgerAdapter:
    mode = "base"
    network = "AUTHENTIQ Ledger"

    def append(self, tx_type: str, actor_id: str | None, entity_type: str, entity_id: str, payload: dict) -> dict:
        raise NotImplementedError

    def verify_chain(self) -> dict:
        raise NotImplementedError

    def transactions(self) -> list[dict]:
        raise NotImplementedError

    def get_transaction(self, tx_id: str) -> dict | None:
        raise NotImplementedError

    def status(self) -> dict:
        raise NotImplementedError


class SimulationLedger(LedgerAdapter):
    mode = "simulation"

    def __init__(self, path: Path | None = None):
        self.path = path or settings.ledger_file
        self.network = settings.ledger_network
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def _read(self) -> list[dict]:
        records = []
        if not self.path.exists():
            return records
        with self.path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    records.append(json.loads(text))
                except json.JSONDecodeError as exc:
                    raise LedgerError(f"Ledger line {line_no} is not valid JSON") from exc
        return records

    def append(self, tx_type: str, actor_id: str | None, entity_type: str, entity_id: str, payload: dict) -> dict:
        with self._lock:
            records = self._read()
            last = records[-1] if records else None
            block_number = (last["block_number"] + 1) if last else 0
            prev_hash = last["record_hash"] if last else GENESIS_HASH
            timestamp = datetime.now(timezone.utc).isoformat()
            payload_digest = digest(payload)
            tx_id = f"aqtx_{block_number:08d}_{digest([timestamp, tx_type, entity_id, payload_digest])[:24]}"
            record = {
                "tx_id": tx_id,
                "block_number": block_number,
                "timestamp": timestamp,
                "tx_type": tx_type,
                "actor_id": actor_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "payload": payload,
                "payload_digest": payload_digest,
                "prev_hash": prev_hash,
                "mode": self.mode,
                "network": self.network,
                "status": "confirmed",
            }
            record["record_hash"] = digest(record)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(canonical_json(record) + "\n")
                handle.flush()
                import os

                os.fsync(handle.fileno())
            return record

    def verify_chain(self) -> dict:
        try:
            records = self._read()
        except LedgerError as exc:
            return {
                "valid": False,
                "records": 0,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "errors": [str(exc)],
                "mode": self.mode,
                "network": self.network,
            }
        errors = []
        previous_hash = GENESIS_HASH
        expected_block = 0
        for index, record in enumerate(records):
            if record.get("block_number") != expected_block:
                errors.append(f"Block sequence break at index {index}: expected {expected_block}, found {record.get('block_number')}")
            if record.get("prev_hash") != previous_hash:
                errors.append(f"Previous hash mismatch at block {record.get('block_number')}")
            stored_hash = record.get("record_hash")
            candidate = {key: value for key, value in record.items() if key != "record_hash"}
            if digest(candidate) != stored_hash:
                errors.append(f"Record hash mismatch at block {record.get('block_number')}")
            if digest(record.get("payload", {})) != record.get("payload_digest"):
                errors.append(f"Payload digest mismatch at block {record.get('block_number')}")
            previous_hash = stored_hash
            expected_block += 1
        return {
            "valid": len(errors) == 0,
            "records": len(records),
            "blocks": expected_block,
            "last_hash": previous_hash,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "errors": errors,
            "mode": self.mode,
            "network": self.network,
        }

    def transactions(self) -> list[dict]:
        return list(reversed(self._read()))

    def get_transaction(self, tx_id: str) -> dict | None:
        for record in self._read():
            if record["tx_id"] == tx_id:
                return record
        return None

    def status(self) -> dict:
        try:
            report = self.verify_chain()
            return {
                "mode": "simulation",
                "label": "Simulation Mode",
                "connected": True,
                "network": self.network,
                "chain_id": None,
                "contract_address": None,
                "block_number": report["blocks"],
                "last_hash": report.get("last_hash"),
                "tamper_detected": not report["valid"],
                "errors": report["errors"],
                "message": "Append-only local ledger. No public blockchain transaction is created in this mode.",
            }
        except Exception as exc:
            return {
                "mode": "simulation",
                "label": "Simulation Error",
                "connected": False,
                "network": self.network,
                "tamper_detected": None,
                "errors": [str(exc)],
                "message": "Ledger simulation is unavailable.",
            }
