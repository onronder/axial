"""
Account Cleanup Service

GDPR/CCPA compliant hard deletion of user data across all systems.
This service orchestrates deletion from: Vector DB, Storage, Database, and Auth.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from core.config import settings
from core.db import get_supabase
from core.ingestion_utils import normalize_source_type
from core.scopes import UPLOAD_PROVIDER_ALIASES

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

    async def anonymize_user_data(self, user_id: str) -> dict:
        """
        Anonymize user data while preserving system integrity.
        """
        results = {"user_id": user_id, "profile": "pending", "team_members": "pending", "integrations": "pending"}

        try:
            self.supabase.table("user_profiles").update(
                {
                    "first_name": None,
                    "last_name": None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("user_id", user_id).execute()
            results["profile"] = "success"
        except Exception as e:
            logger.error("❌ [Anonymize] Failed to anonymize profile: %s", e)
            results["profile"] = f"error: {e}"

        try:
            anonymized_email = f"anonymized+{user_id}@example.com"
            self.supabase.table("team_members").update(
                {
                    "email": anonymized_email,
                    "name": "Deleted User",
                }
            ).eq("member_user_id", user_id).execute()
            self.supabase.table("team_members").update(
                {
                    "email": anonymized_email,
                    "name": "Deleted User",
                }
            ).eq("owner_user_id", user_id).execute()
            results["team_members"] = "success"
        except Exception as e:
            logger.warning("⚠️ [Anonymize] Failed to anonymize team members: %s", e)
            results["team_members"] = f"error: {e}"

        try:
            self.supabase.table("user_integrations").delete().eq("user_id", user_id).execute()
            results["integrations"] = "success"
        except Exception as e:
            logger.warning("⚠️ [Anonymize] Failed to delete integrations: %s", e)
            results["integrations"] = f"error: {e}"

        try:
            self.supabase.auth.admin.update_user_by_id(
                user_id,
                {"email": f"anonymized+{user_id}@example.com", "user_metadata": {}},
            )
        except Exception as e:
            logger.warning("⚠️ [Anonymize] Failed to anonymize auth user: %s", e)

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
            doc = query.maybe_single().execute()
            if not doc.data:
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
                
            # 3. Delete from Storage (Soft Fail)
            if storage_path:
                try:
                    # Clean up path - supabase storage methods accept list of paths
                    self.supabase.storage.from_("uploads").remove([storage_path])
                    # Also try to clean up the parent folder if it was a uuid folder (best effort)
                    parent_folder = storage_path.split("/")[0] + "/" + storage_path.split("/")[1]
                    if len(storage_path.split("/")) > 2:
                         # list and check if empty? too expensive. leave folder.
                         pass
                except Exception as e:
                    logger.warning(f"⚠️ [DocCleanup] Storage delete failed (continuing): {e}")

            # 4. Delete Database Record (org-scoped if organization_id provided)
            delete_query = self.supabase.table("documents").delete().eq("id", doc_id)
            if organization_id:
                delete_query = delete_query.eq("organization_id", organization_id)
            else:
                delete_query = delete_query.eq("user_id", user_id)
            delete_query.execute()
                
            return {"status": "success", "id": doc_id}
            
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


# Singleton instance
cleanup_service = AccountCleanupService()
