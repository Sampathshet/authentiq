from datetime import datetime, timezone


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def user_out(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "account_type": user.account_type,
        "role": user.role,
        "organization_id": user.organization_id,
        "avatar_color": user.avatar_color,
        "is_demo": user.is_demo,
        "created_at": iso(user.created_at),
        "last_login_at": iso(user.last_login_at),
    }


def registration_out(registration, owner_name: str | None = None, metadata=None, include_private=False, team_name: str | None = None) -> dict:
    payload = {
        "id": registration.id,
        "registration_id": registration.registration_id,
        "title": registration.title,
        "description": registration.description,
        "asset_type": registration.asset_type,
        "file_name": registration.file_name,
        "file_size": registration.file_size,
        "mime_type": registration.mime_type,
        "sha256": registration.sha256,
        "commitment": registration.commitment,
        "poseidon_commitment": registration.poseidon_commitment,
        "privacy": registration.privacy,
        "status": registration.status,
        "version": registration.version,
        "ledger_tx_id": registration.ledger_tx_id,
        "ledger_mode": registration.ledger_mode,
        "registered_at": iso(registration.registered_at),
        "creation_timestamp": iso(registration.creation_timestamp),
        "verified_at": iso(registration.verified_at),
        "owner_id": registration.user_id,
        "owner_name": owner_name,
        "organization_id": registration.organization_id,
        "team_id": registration.team_project_id,
        "team_name": team_name,
        "is_demo": registration.is_demo,
        "tags": registration.tags or [],
    }
    if metadata is not None:
        payload["metadata"] = {
            "original_name": metadata.original_name,
            "mime_type": metadata.mime_type,
            "extension": metadata.extension,
            "size_bytes": metadata.size_bytes,
            "chunk_count": metadata.chunk_count,
            "perceptual_hash": metadata.perceptual_hash,
        }
    if include_private:
        payload["storage_path"] = registration.storage_path
    return payload


def idea_out(idea, description: str | None = None, include_private=False) -> dict:
    return {
        "id": idea.id,
        "idea_ref": idea.idea_ref,
        "title": idea.title,
        "description": description,
        "commitment": idea.commitment,
        "privacy": idea.privacy,
        "status": idea.status,
        "ledger_tx_id": idea.ledger_tx_id,
        "ledger_mode": idea.ledger_mode,
        "created_at": iso(idea.created_at),
        "revealed_at": iso(idea.revealed_at),
        "owner_id": idea.user_id,
        "is_demo": idea.is_demo,
        "can_reveal": include_private,
    }


def version_out(version, contributor_name: str | None = None) -> dict:
    return {
        "id": version.id,
        "registration_id": version.registration_id,
        "version_no": version.version_no,
        "file_name": version.file_name,
        "file_size": version.file_size,
        "mime_type": version.mime_type,
        "sha256": version.sha256,
        "change_description": version.change_description,
        "contributor_id": version.contributor_id,
        "contributor_name": contributor_name,
        "parent_version_id": version.parent_version_id,
        "ledger_tx_id": version.ledger_tx_id,
        "created_at": iso(version.created_at),
    }


def provenance_out(record) -> dict:
    return {
        "id": record.id,
        "registration_id": record.registration_id,
        "declared_ai": record.declared_ai,
        "model_name": record.model_name,
        "tool_name": record.tool_name,
        "prompt_commitment": record.prompt_commitment,
        "human_contribution": record.human_contribution,
        "editing_details": record.editing_details,
        "creation_date": iso(record.creation_date),
        "analysis_available": record.analysis_available,
        "analysis": record.analysis,
        "ledger_tx_id": record.ledger_tx_id,
        "created_at": iso(record.created_at),
    }


def alert_out(alert, registration=None, matched=None) -> dict:
    return {
        "id": alert.id,
        "registration_id": alert.registration_id,
        "matched_registration_id": alert.matched_registration_id,
        "registration_label": registration.registration_id if registration else None,
        "matched_label": matched.registration_id if matched else None,
        "alert_type": alert.alert_type,
        "similarity_score": alert.similarity_score,
        "status": alert.status,
        "investigation_notes": alert.investigation_notes,
        "reviewed_at": iso(alert.reviewed_at),
        "created_at": iso(alert.created_at),
    }


def transfer_out(transfer, registration=None, from_name=None, to_name=None) -> dict:
    return {
        "id": transfer.id,
        "registration_id": transfer.registration_id,
        "registration_label": registration.registration_id if registration else None,
        "registration_title": registration.title if registration else None,
        "from_user_id": transfer.from_user_id,
        "from_name": from_name,
        "to_user_id": transfer.to_user_id,
        "to_name": to_name,
        "to_email": transfer.to_email,
        "status": transfer.status,
        "reason": transfer.reason,
        "rejection_reason": transfer.rejection_reason,
        "ledger_tx_id": transfer.ledger_tx_id,
        "created_at": iso(transfer.created_at),
        "recipient_responded_at": iso(transfer.recipient_responded_at),
        "owner_confirmed_at": iso(transfer.owner_confirmed_at),
        "completed_at": iso(transfer.completed_at),
    }


def dispute_out(dispute, registration=None, claimant_name=None) -> dict:
    return {
        "id": dispute.id,
        "dispute_ref": dispute.dispute_ref,
        "registration_id": dispute.registration_id,
        "registration_label": registration.registration_id if registration else None,
        "registration_title": registration.title if registration else None,
        "claimant_id": dispute.claimant_id,
        "claimant_name": claimant_name,
        "respondent_id": dispute.respondent_id,
        "reason": dispute.reason,
        "description": dispute.description,
        "status": dispute.status,
        "resolution": dispute.resolution,
        "earliest_registration_id": dispute.earliest_registration_id,
        "created_at": iso(dispute.created_at),
        "updated_at": iso(dispute.updated_at),
        "resolved_at": iso(dispute.resolved_at),
    }


def notification_out(item) -> dict:
    return {
        "id": item.id,
        "type": item.type,
        "title": item.title,
        "message": item.message,
        "entity_type": item.entity_type,
        "entity_id": item.entity_id,
        "is_read": item.is_read,
        "created_at": iso(item.created_at),
    }


def audit_out(item) -> dict:
    return {
        "id": item.id,
        "event_id": item.event_id,
        "actor_id": item.actor_id,
        "actor_ref": item.actor_ref,
        "action": item.action,
        "entity_type": item.entity_type,
        "entity_id": item.entity_id,
        "metadata": item.event_metadata,
        "ip_address": item.ip_address,
        "created_at": iso(item.created_at),
        "record_hash": item.record_hash,
    }


def ledger_out(item) -> dict:
    return {
        "id": item.id,
        "tx_id": item.tx_id,
        "block_number": item.block_number,
        "tx_type": item.tx_type,
        "actor_id": item.actor_id,
        "entity_type": item.entity_type,
        "entity_id": item.entity_id,
        "payload_digest": item.payload_digest,
        "prev_hash": item.prev_hash,
        "record_hash": item.record_hash,
        "mode": item.mode,
        "network": item.network,
        "status": item.status,
        "chain_tx_hash": item.chain_tx_hash,
        "timestamp": iso(item.timestamp),
    }


def team_member_out(member) -> dict:
    return {
        "id": member.id,
        "project_id": member.project_id,
        "user_id": member.user_id,
        "email": member.email,
        "display_name": member.display_name,
        "role": member.role,
        "status": member.status,
        "contribution_description": member.contribution_description,
        "ownership_percent": member.ownership_percent,
        "joined_at": iso(member.joined_at),
        "created_at": iso(member.created_at),
    }


def team_out(project, members=None, owner_name=None, role=None, membership_status=None) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "owner_id": project.owner_id,
        "owner_name": owner_name,
        "organization_id": project.organization_id,
        "status": project.status,
        "ledger_tx_id": project.ledger_tx_id,
        "created_at": iso(project.created_at),
        "member_count": len(members) if members is not None else 0,
        "members": [team_member_out(m) for m in members] if members is not None else [],
        "my_role": role,
        "my_status": membership_status,
        "is_demo": project.is_demo,
    }


def allocation_out(allocation, member=None) -> dict:
    return {
        "id": allocation.id,
        "project_id": allocation.project_id,
        "member_id": allocation.member_id,
        "member_email": member.email if member else None,
        "member_name": member.display_name if member else None,
        "percent": allocation.percent,
        "status": allocation.status,
        "proposed_by": allocation.proposed_by,
        "approvals": allocation.approvals or [],
        "created_at": iso(allocation.created_at),
        "approved_at": iso(allocation.approved_at),
    }
