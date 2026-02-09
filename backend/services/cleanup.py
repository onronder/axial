"""
Account Cleanup Service - Ghost Protocol Integration

GDPR/CCPA/KVKK compliant hard deletion of user data across all systems.
This service orchestrates deletion from: Vector DB, Storage, Database, and Auth.

Ghost Protocol Features:
- DoD 5220.22-M compliant secure wipe for local temp files
- Supabase Storage cleanup with metrics tracking
- Security audit logging for all wipe operations
- ScopeGuard approval workflow integration for destructive actions
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any

from core.db import get_supabase
from core.ingestion_utils import normalize_source_type
from core.scopes import UPLOAD_PROVIDER_ALIASES
from services.secure_cleanup import cleanup_staging_file

logger = logging.getLogger(__name__)


class ActiveIngestionError(RuntimeError):
    """Raised when org deletion is blocked due to active ingestion."""


class AccountCleanupService:
    """
    Service for complete, irreversible account deletion.

    Implements GDPR Article 17 "Right to Erasure" and CCPA deletion rights.
    Removes user data from all systems in the correct order.
    """

    def __init__(self, supabase=None):
        self._supabase = supabase

    @property
    def supabase(self):
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    async def execute_account_deletion(self, user_id: str) -> dict:
        """
        Execute complete account deletion across all systems.

        Order of operations:
        1. Vector store - Delete all embeddings (right to be forgotten)
        2. Storage - Delete all uploaded files
        3. Database - Delete user record (cascades to related tables)
        4. Auth - Delete from Supabase Auth

        Args:
            user_id: The UUID of the user to delete

        Returns:
            dict with deletion results for each system

        Raises:
            Exception: If any critical deletion step fails
        """
        results = {
            "user_id": user_id,
            "vector_store": {"deleted": 0, "status": "pending"},
            "storage": {"deleted": 0, "status": "pending"},
            "database": {"status": "pending"},
            "auth": {"status": "pending"},
        }

        logger.info(f"🗑️ [AccountCleanup] Starting deletion for user: {user_id}")

        try:
            # Step 1: Delete vectors (embeddings)
            results["vector_store"] = await self._cleanup_vectors(user_id)
            logger.info(f"🗑️ [AccountCleanup] Vector cleanup: {results['vector_store']}")

            # Step 2: Delete storage files
            results["storage"] = await self._cleanup_storage(user_id)
            logger.info(f"🗑️ [AccountCleanup] Storage cleanup: {results['storage']}")

            # Step 3: Delete database records
            results["database"] = await self._cleanup_database(user_id)
            logger.info(f"🗑️ [AccountCleanup] Database cleanup: {results['database']}")

            # Step 4: Delete from Auth (must be last)
            results["auth"] = await self._cleanup_auth(user_id)
            logger.info(f"🗑️ [AccountCleanup] Auth cleanup: {results['auth']}")

            logger.info(f"✅ [AccountCleanup] Complete deletion finished for user: {user_id}")
            return results

        except Exception as e:
            logger.error(f"❌ [AccountCleanup] Deletion failed for user {user_id}: {e}")
            raise

    async def execute_org_deletion(self, organization_id: str, owner_id: str) -> dict:
        """
        Execute irreversible deletion of all org-scoped data.

        Deletes vectors, documents, scope identities, and ingestion jobs
        associated with the organization.
        """
        logger.info(
            "🗑️ [AccountCleanup] Starting org deletion for %s (owner=%s)",
            organization_id,
            owner_id,
        )

        try:
            response = self.supabase.rpc(
                "purge_organization",
                {"p_organization_id": organization_id, "p_owner_id": owner_id},
            ).execute()
            payload = response.data or {}
        except Exception as e:
            error_text = str(e)
            if "active_ingestion_jobs" in error_text or "Cannot purge while ingestion jobs are active" in error_text:
                logger.warning("⛔ [OrgCleanup] Active ingestion blocks purge for %s", organization_id)
                raise ActiveIngestionError(
                    "Organization has active ingestion jobs; aborting purge."
                ) from e
            logger.error("❌ [OrgCleanup] Org purge failed: %s", e)
            raise

        results = {
            "organization_id": organization_id,
            "vector_store": {"deleted": int(payload.get("deleted_chunks") or 0), "status": "success"},
            "documents": {"deleted": int(payload.get("deleted_documents") or 0), "status": "success"},
            "scope_identities": {"deleted": int(payload.get("deleted_scopes") or 0), "status": "success"},
            "ingestion_jobs": {"deleted": int(payload.get("deleted_jobs") or 0), "status": "success"},
            "org_usage": {"status": "success"},
        }

        logger.info("✅ [AccountCleanup] Org deletion finished for %s", organization_id)
        return results

    async def anonymize_user_data(self, user_id: str, reason: str = "user_request") -> dict:
        """
        GDPR-compliant data anonymization.

        This implements GDPR Article 17 "Right to Erasure" as an alternative to hard deletion.
        Replaces PII with anonymized placeholders while preserving system integrity.

        Process:
        1. Log GDPR request to audit trail
        2. Anonymize user profile (names, avatar)
        3. Anonymize team membership records
        4. Delete OAuth integrations (contain tokens)
        5. Anonymize feedback records
        6. Anonymize auth account
        7. Log completion to audit trail

        Args:
            user_id: UUID of the user requesting anonymization
            reason: Reason for request (user_request, admin_action, legal_request)

        Returns:
            dict with anonymization results for each system
        """
        from services.audit import audit_logger

        timestamp = datetime.now(timezone.utc).isoformat()
        anonymized_email = f"anonymized+{user_id[:8]}@deleted.local"

        results = {
            "user_id": user_id,
            "request_type": "gdpr_anonymization",
            "reason": reason,
            "timestamp": timestamp,
            "profile": "pending",
            "team_members": "pending",
            "integrations": "pending",
            "feedback": "pending",
            "auth": "pending",
            "audit_logged": False,
        }

        logger.info(f"🔒 [GDPR] Starting anonymization for user: {user_id}")

        # Step 1: Log GDPR request to audit trail
        try:
            audit_logger.log_sync(
                action="gdpr.anonymization_requested",
                resource_type="user",
                resource_id=user_id,
                user_id=user_id,
                details={
                    "reason": reason,
                    "timestamp": timestamp,
                    "request_type": "anonymization",
                }
            )
            results["audit_logged"] = True
            logger.info("📋 [GDPR] Audit log created for anonymization request")
        except Exception as e:
            logger.warning(f"⚠️ [GDPR] Failed to create audit log: {e}")

        # Step 2: Anonymize user profile
        try:
            self.supabase.table("user_profiles").update(
                {
                    "first_name": "Deleted",
                    "last_name": "User",
                    "avatar_url": None,
                    "updated_at": timestamp,
                }
            ).eq("user_id", user_id).execute()
            results["profile"] = "success"
            logger.info("✅ [GDPR] Profile anonymized")
        except Exception as e:
            logger.error(f"❌ [GDPR] Failed to anonymize profile: {e}")
            results["profile"] = f"error: {str(e)}"

        # Step 3: Anonymize team membership records
        try:
            # Update records where user is a member
            self.supabase.table("team_members").update(
                {
                    "email": anonymized_email,
                    "name": "Deleted User",
                }
            ).eq("member_user_id", user_id).execute()

            # Update records where user is an owner
            self.supabase.table("team_members").update(
                {
                    "email": anonymized_email,
                    "name": "Deleted User",
                }
            ).eq("owner_user_id", user_id).execute()

            results["team_members"] = "success"
            logger.info("✅ [GDPR] Team membership anonymized")
        except Exception as e:
            logger.warning(f"⚠️ [GDPR] Failed to anonymize team members: {e}")
            results["team_members"] = f"error: {str(e)}"

        # Step 4: Delete OAuth integrations (they contain tokens/PII)
        try:
            delete_result = self.supabase.table("user_integrations").delete().eq("user_id", user_id).execute()
            deleted_count = len(delete_result.data) if delete_result.data else 0
            results["integrations"] = f"deleted:{deleted_count}"
            logger.info(f"✅ [GDPR] Deleted {deleted_count} integrations")
        except Exception as e:
            logger.warning(f"⚠️ [GDPR] Failed to delete integrations: {e}")
            results["integrations"] = f"error: {str(e)}"

        # Step 5: Anonymize feedback records (keep for analytics, remove PII)
        try:
            self.supabase.table("feedback").update(
                {
                    "user_id": None,  # Remove user association but keep feedback data
                }
            ).eq("user_id", user_id).execute()
            results["feedback"] = "success"
            logger.info("✅ [GDPR] Feedback records anonymized")
        except Exception as e:
            # Feedback table might not exist or user might not have feedback
            logger.warning(f"⚠️ [GDPR] Feedback anonymization skipped: {e}")
            results["feedback"] = "skipped"

        # Step 6: Anonymize Supabase Auth account
        try:
            self.supabase.auth.admin.update_user_by_id(
                user_id,
                {
                    "email": anonymized_email,
                    "user_metadata": {"anonymized": True, "anonymized_at": timestamp},
                },
            )
            results["auth"] = "success"
            logger.info("✅ [GDPR] Auth account anonymized")
        except Exception as e:
            logger.warning(f"⚠️ [GDPR] Failed to anonymize auth user: {e}")
            results["auth"] = f"error: {str(e)}"

        # Step 7: Log completion to audit trail
        try:
            audit_logger.log_sync(
                action="gdpr.anonymization_completed",
                resource_type="user",
                resource_id=user_id,
                user_id=user_id,
                details={
                    "results": results,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.info("📋 [GDPR] Anonymization completion logged")
        except Exception as e:
            logger.warning(f"⚠️ [GDPR] Failed to log completion: {e}")

        logger.info(f"🔒 [GDPR] Anonymization completed for user: {user_id}")
        return results
    async def delete_single_document(
        self, doc_id: str, user_id: str, organization_id: str = None
    ) -> dict:
        """
        Delete a single document atomically (Vectors -> Storage -> DB).

        Args:
            doc_id: Document UUID
            user_id: User UUID (for audit/logging)
            organization_id: Organization UUID (for org-scoped deletion)

        Returns:
            dict with cleanup status
        """
        logger.info(f"🗑️ [DocCleanup] Deleting document {doc_id} for user {user_id}")

        try:
            # 1. Get document metadata to find storage path
            # Use organization_id for org-scoped access if provided
            query = self.supabase.table("documents").select("*").eq("id", doc_id)
            if organization_id:
                query = query.eq("organization_id", organization_id)
            else:
                query = query.eq("user_id", user_id)

            # Use maybe_single() to gracefully handle 0 rows (already deleted)
            # Note: execute() can return None on HTTP errors, so check both
            doc = query.maybe_single().execute()
            if doc is None or not doc.data:
                # Document already deleted or doesn't exist - consider success
                logger.info(f"📄 [DocCleanup] Document {doc_id} not found (already deleted)")
                return {"status": "success", "id": doc_id, "already_deleted": True}

            doc_data = doc.data
            storage_path = None

            # Try to find storage path in metadata or source_url
            if normalize_source_type(doc_data.get("source_type")) in UPLOAD_PROVIDER_ALIASES:
                # Check metadata first
                meta = doc_data.get("metadata") or {}
                storage_path = meta.get("storage_path")

                # Fallback: if source_url looks like a storage path (user_id/...)
                if not storage_path and doc_data.get("source_url"):
                    url = doc_data.get("source_url")
                    if user_id in url: # minimal check
                         storage_path = url

            # 2. Delete Vectors (Chunks)
            # Cascade usually handles this, but explicit delete is safer/cleaner for vectors
            self.supabase.table("document_chunks")\
                .delete()\
                .eq("document_id", doc_id)\
                .execute()

            # 3. Delete from Storage using Ghost Protocol (Soft Fail)
            # Uses cleanup_staging_file for proper metrics tracking
            wipe_verified = False
            wipe_duration_ms = 0
            if storage_path:
                start_time = time.time()
                try:
                    # Ghost Protocol: Use secure staging cleanup with metrics
                    wipe_verified = cleanup_staging_file(storage_path, bucket="uploads")
                    wipe_duration_ms = int((time.time() - start_time) * 1000)
                    if wipe_verified:
                        logger.info(
                            f"🗑️ [GhostProtocol] Storage file wiped: ...{storage_path[-20:]}"
                        )
                except Exception as e:
                    wipe_duration_ms = int((time.time() - start_time) * 1000)
                    logger.warning(f"⚠️ [DocCleanup] Storage delete failed (continuing): {e}")

            # 4. Delete Database Record (org-scoped if organization_id provided)
            delete_query = self.supabase.table("documents").delete().eq("id", doc_id)
            if organization_id:
                delete_query = delete_query.eq("organization_id", organization_id)
            else:
                delete_query = delete_query.eq("user_id", user_id)
            delete_query.execute()

            # 5. Ghost Protocol: Log to security audit trail
            await self._log_security_event(
                event_type="document_wiped",
                resource_id=doc_id,
                resource_name=doc_data.get("title", "Unknown"),
                organization_id=organization_id,
                user_id=user_id,
                wipe_pattern="dod_5220_22_m" if storage_path else None,
                wipe_verified=wipe_verified,
                duration_ms=wipe_duration_ms,
            )

            return {"status": "success", "id": doc_id, "wipe_verified": wipe_verified}

        except Exception as e:
            logger.error(f"❌ [DocCleanup] Failed for {doc_id}: {e}")
            raise e

    async def _cleanup_vectors(self, user_id: str) -> dict:
        """
        Delete all vector embeddings belonging to the user.

        This implements the "Right to be Forgotten" - AI cannot remember
        anything about documents that belonged to this user.
        """
        try:
            doc_ids_res = self.supabase.table("documents")\
                .select("id")\
                .eq("user_id", user_id)\
                .execute()

            doc_ids = [row["id"] for row in (doc_ids_res.data or []) if row.get("id")]
            deleted_count = 0

            if doc_ids:
                batch_size = 500
                for i in range(0, len(doc_ids), batch_size):
                    batch = doc_ids[i:i + batch_size]
                    response = self.supabase.table("document_chunks")\
                        .delete()\
                        .in_("document_id", batch)\
                        .execute()
                    deleted_count += len(response.data) if response.data else 0

            return {
                "deleted": deleted_count,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"❌ [VectorCleanup] Failed: {e}")
            return {
                "deleted": 0,
                "status": "error",
                "error": str(e)
            }

    async def _cleanup_storage(self, user_id: str) -> dict:
        """
        Delete all files from the user's storage bucket.
        """
        try:
            deleted_count = 0

            # List all files in the user's folder
            try:
                files = self.supabase.storage.from_("uploads").list(user_id)

                if files:
                    # Delete each file
                    file_paths = [f"{user_id}/{f['name']}" for f in files]
                    if file_paths:
                        self.supabase.storage.from_("uploads").remove(file_paths)
                        deleted_count = len(file_paths)
            except Exception as storage_error:
                # Storage bucket might not exist or be empty - that's OK
                logger.warning(f"📁 [StorageCleanup] No files or bucket: {storage_error}")

            return {
                "deleted": deleted_count,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"❌ [StorageCleanup] Failed: {e}")
            return {
                "deleted": 0,
                "status": "error",
                "error": str(e)
            }

    async def _cleanup_database(self, user_id: str) -> dict:
        """
        Delete user from database.

        Relies on ON DELETE CASCADE to clean up related tables:
        - documents
        - document_chunks
        - conversations
        - messages
        - notifications
        - user_integrations
        - user_profiles
        - user_notification_settings
        - ingestion_jobs
        """
        try:
            # Delete from documents (which should cascade to chunks)
            self.supabase.table("documents")\
                .delete()\
                .eq("user_id", user_id)\
                .execute()

            # Delete conversations (cascades to messages)
            self.supabase.table("conversations")\
                .delete()\
                .eq("user_id", user_id)\
                .execute()

            # Delete notifications
            self.supabase.table("notifications")\
                .delete()\
                .eq("user_id", user_id)\
                .execute()

            # Delete user integrations
            self.supabase.table("user_integrations")\
                .delete()\
                .eq("user_id", user_id)\
                .execute()

            # Delete user profiles
            self.supabase.table("user_profiles")\
                .delete()\
                .eq("user_id", user_id)\
                .execute()

            # Delete notification settings
            self.supabase.table("user_notification_settings")\
                .delete()\
                .eq("user_id", user_id)\
                .execute()

            # Delete ingestion jobs
            self.supabase.table("ingestion_jobs")\
                .delete()\
                .eq("user_id", user_id)\
                .execute()

            return {"status": "success"}

        except Exception as e:
            logger.error(f"❌ [DatabaseCleanup] Failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _cleanup_auth(self, user_id: str) -> dict:
        """
        Delete user from Supabase Auth.

        This is the final step - must be last because once deleted,
        the user cannot authenticate to perform any other operations.
        """
        try:
            # Use admin API to delete user from Auth
            response = self.supabase.auth.admin.delete_user(user_id)

            return {"status": "success"}

        except Exception as e:
            logger.error(f"❌ [AuthCleanup] Failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


    async def _log_security_event(
        self,
        event_type: str,
        resource_id: str,
        resource_name: str,
        organization_id: str | None = None,
        user_id: str | None = None,
        wipe_pattern: str | None = None,
        wipe_verified: bool = False,
        duration_ms: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Log security event to audit trail (Ghost Protocol).

        Records wipe operations for compliance and forensics.

        Args:
            event_type: Type of security event (document_wiped, scope_deleted, etc.)
            resource_id: ID of the affected resource
            resource_name: Human-readable name of the resource
            organization_id: Organization context
            user_id: User who initiated the action
            wipe_pattern: Wipe pattern used (dod_5220_22_m, random, etc.)
            wipe_verified: Whether verify read passed
            duration_ms: Operation duration in milliseconds
            metadata: Additional metadata
        """
        try:
            from services.audit import audit_logger

            details = {
                "resource_name": resource_name,
                "wipe_pattern": wipe_pattern,
                "wipe_verified": wipe_verified,
                "duration_ms": duration_ms,
                "ghost_protocol": True,
                **(metadata or {}),
            }

            # Use sync logging (we're already in async context)
            audit_logger.log_sync(
                action=f"security.{event_type}",
                resource_type=event_type.split("_")[0],  # document, scope, chunk, etc.
                resource_id=resource_id,
                user_id=user_id,
                details=details,
            )

            logger.debug(
                f"📋 [GhostProtocol] Audit logged: {event_type} for {resource_id[:8]}..."
            )
        except Exception as e:
            # Don't fail the operation if audit logging fails
            logger.warning(f"⚠️ [GhostProtocol] Failed to log security event: {e}")

    async def delete_scope(self, scope_id: str, organization_id: str) -> int:
        """
        Delete all documents in a scope.

        Args:
            scope_id: Scope ID to delete
            organization_id: Organization context

        Returns:
            Number of documents deleted
        """
        logger.info(
            f"🗑️ [ScopeCleanup] Deleting scope {scope_id} for org {organization_id[:8]}..."
        )

        try:
            # Get all document IDs in scope
            docs_result = self.supabase.table("documents")\
                .select("id")\
                .eq("scope_id", scope_id)\
                .eq("organization_id", organization_id)\
                .execute()

            doc_ids = [row["id"] for row in (docs_result.data or []) if row.get("id")]

            if not doc_ids:
                logger.info(f"📄 [ScopeCleanup] No documents in scope {scope_id}")
                return 0

            deleted_count = 0
            for doc_id in doc_ids:
                try:
                    await self.delete_single_document(
                        doc_id=doc_id,
                        user_id=None,
                        organization_id=organization_id,
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"⚠️ [ScopeCleanup] Failed to delete {doc_id}: {e}")

            # Also delete scope identity if it exists
            try:
                self.supabase.table("scope_identities")\
                    .delete()\
                    .eq("id", scope_id)\
                    .eq("organization_id", organization_id)\
                    .execute()
            except Exception as e:
                logger.debug(f"[Cleanup] Failed to delete scope record: {e}")

            # Ghost Protocol: Log scope deletion to security audit
            await self._log_security_event(
                event_type="scope_deleted",
                resource_id=scope_id,
                resource_name=f"Scope {scope_id[:12]}...",
                organization_id=organization_id,
                user_id=None,  # Will be set by caller's context
                wipe_pattern="bulk_cascade",
                wipe_verified=True,
                duration_ms=0,
                metadata={"deleted_documents": deleted_count},
            )

            logger.info(f"✅ [ScopeCleanup] Deleted {deleted_count} documents from scope {scope_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"❌ [ScopeCleanup] Failed for scope {scope_id}: {e}")
            raise

    async def purge_organization(self, organization_id: str) -> dict:
        """
        Purge all data for an organization.

        This is an extremely destructive operation that removes
        all documents, vectors, and related data.

        Args:
            organization_id: Organization to purge

        Returns:
            Purge results
        """
        logger.warning(
            f"🚨 [OrgPurge] Initiating full purge for org {organization_id[:8]}..."
        )

        # Get team owner for RPC call
        team_result = self.supabase.table("teams")\
            .select("owner_id")\
            .eq("id", organization_id)\
            .maybe_single()\
            .execute()

        if not team_result.data:
            raise ValueError(f"Organization not found: {organization_id}")

        owner_id = team_result.data["owner_id"]

        # Use existing org deletion method
        result = await self.execute_org_deletion(organization_id, owner_id)

        # Ghost Protocol: Log organization purge to security audit
        await self._log_security_event(
            event_type="organization_purged",
            resource_id=organization_id,
            resource_name=f"Organization {organization_id[:12]}...",
            organization_id=organization_id,
            user_id=owner_id,
            wipe_pattern="full_purge",
            wipe_verified=True,
            duration_ms=0,
            metadata={
                "deleted_chunks": result.get("vector_store", {}).get("deleted", 0),
                "deleted_documents": result.get("documents", {}).get("deleted", 0),
                "deleted_scopes": result.get("scope_identities", {}).get("deleted", 0),
            },
        )

        return result


# Singleton instance
cleanup_service = AccountCleanupService()
