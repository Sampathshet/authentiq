from sqlalchemy.orm import Session

from app.core.config import settings
from app.ledger.blockchain import PolygonAdapter
from app.ledger.simulation import LedgerAdapter, LedgerError, LedgerUnavailable, SimulationLedger
from app.models import LedgerTransaction


class LedgerService:
    def __init__(self):
        self.adapter: LedgerAdapter
        self.fallback_reason: str | None = None
        if settings.ledger_mode.lower() == "polygon":
            try:
                self.adapter = PolygonAdapter()
            except LedgerUnavailable as exc:
                self.fallback_reason = str(exc)
                self.adapter = SimulationLedger()
        else:
            self.adapter = SimulationLedger()

    def _record(
        self,
        db: Session,
        tx_type: str,
        actor_id: str | None,
        entity_type: str,
        entity_id: str,
        payload: dict,
    ) -> LedgerTransaction:
        record = self.adapter.append(tx_type, actor_id, entity_type, entity_id, payload)
        transaction = LedgerTransaction(
            tx_id=record["tx_id"],
            block_number=int(record.get("block_number") or 0),
            tx_type=tx_type,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_digest=record.get("payload_digest") or "",
            prev_hash=record.get("prev_hash") or "",
            record_hash=record.get("record_hash") or record.get("chain_tx_hash", ""),
            payload=payload,
            mode=record.get("mode", self.adapter.mode),
            network=record.get("network", self.adapter.network),
            status=record.get("status", "confirmed"),
            chain_tx_hash=record.get("chain_tx_hash"),
        )
        db.add(transaction)
        db.flush()
        return transaction

    def register_creation(self, db, actor_id, registration) -> LedgerTransaction:
        return self._record(
            db,
            "creation_registered",
            actor_id,
            "registration",
            registration.registration_id,
            {
                "registration_id": registration.registration_id,
                "fingerprint": registration.sha256,
                "commitment": registration.commitment,
                "poseidon_commitment": registration.poseidon_commitment,
                "registered_at": registration.registered_at.isoformat(),
            },
        )

    def register_idea(self, db, actor_id, idea) -> LedgerTransaction:
        return self._record(
            db,
            "idea_protected",
            actor_id,
            "idea",
            idea.idea_ref,
            {
                "idea_ref": idea.idea_ref,
                "commitment": idea.commitment,
                "title_digest": __import__("hashlib").sha256(idea.title.encode()).hexdigest(),
            },
        )

    def record_version(self, db, actor_id, registration, version) -> LedgerTransaction:
        return self._record(
            db,
            "version_recorded",
            actor_id,
            "registration",
            registration.registration_id,
            {
                "registration_id": registration.registration_id,
                "version_no": version.version_no,
                "sha256": version.sha256,
                "parent_version_id": version.parent_version_id,
            },
        )

    def record_team_ownership(self, db, actor_id, project, allocations: list[dict]) -> LedgerTransaction:
        return self._record(
            db,
            "team_ownership_approved",
            actor_id,
            "team_project",
            project.id,
            {"project": project.name, "allocations": allocations},
        )

    def transfer_ownership(self, db, actor_id, registration, transfer) -> LedgerTransaction:
        return self._record(
            db,
            "ownership_transferred",
            actor_id,
            "registration",
            registration.registration_id,
            {
                "registration_id": registration.registration_id,
                "from_user_id": transfer.from_user_id,
                "to_user_id": transfer.to_user_id,
                "to_email": transfer.to_email,
                "transfer_id": transfer.id,
            },
        )

    def record_credential_rotation(self, db, actor_id, registration, transfer, previous_commitment, new_commitment) -> LedgerTransaction:
        return self._record(
            db,
            "ownership_credential_rotated",
            actor_id,
            "registration",
            registration.registration_id,
            {
                "registration_id": registration.registration_id,
                "transfer_id": transfer.id,
                "to_user_id": transfer.to_user_id,
                "previous_commitment": previous_commitment,
                "new_commitment": new_commitment,
                "fingerprint": registration.sha256,
            },
        )

    def record_dispute(self, db, actor_id, dispute) -> LedgerTransaction:
        return self._record(
            db,
            "dispute_opened",
            actor_id,
            "dispute",
            dispute.dispute_ref,
            {
                "dispute_ref": dispute.dispute_ref,
                "registration_id": dispute.registration_id,
                "reason_digest": __import__("hashlib").sha256(dispute.reason.encode()).hexdigest(),
            },
        )

    def record_proof_verification(self, db, actor_id, proof, registration) -> LedgerTransaction:
        return self._record(
            db,
            "proof_verified",
            actor_id,
            "registration",
            registration.registration_id,
            {
                "registration_id": registration.registration_id,
                "proof_scheme": proof.scheme,
                "commitment": registration.commitment,
            },
        )

    def record_provenance(self, db, actor_id, registration, provenance) -> LedgerTransaction:
        return self._record(
            db,
            "provenance_recorded",
            actor_id,
            "registration",
            registration.registration_id,
            {
                "registration_id": registration.registration_id,
                "declared_ai": provenance.declared_ai,
                "model_name": provenance.model_name,
            },
        )

    def record_idea_revision(self, db, actor_id, idea, revision) -> LedgerTransaction:
        return self._record(
            db,
            "idea_revision_recorded",
            actor_id,
            "idea",
            idea.idea_ref,
            {
                "idea_ref": idea.idea_ref,
                "revision_no": revision.revision_no,
                "commitment": revision.commitment,
            },
        )

    def verify_record(self, tx_id: str) -> dict | None:
        record = self.adapter.get_transaction(tx_id)
        if record is None:
            return None
        return record

    def get_transaction(self, tx_id: str) -> dict | None:
        return self.adapter.get_transaction(tx_id)

    def get_audit_history(self) -> list[dict]:
        return self.adapter.transactions()

    def audit(self) -> dict:
        return self.adapter.verify_chain()

    def status(self) -> dict:
        status = self.adapter.status()
        if self.fallback_reason:
            status["requested_mode"] = settings.ledger_mode
            status["message"] = (
                f"Requested Polygon mode is unavailable ({self.fallback_reason}). "
                "Running in clearly labelled simulation mode."
            )
            status["mode"] = "simulation"
            status["label"] = "Simulation Mode (Polygon unavailable)"
        return status


ledger_service = LedgerService()
