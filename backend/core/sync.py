"""
Incremental Sync Framework

Provides base classes and utilities for implementing incremental/delta sync
for connectors like Google Drive, Notion, etc.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
from core.db import get_supabase

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """Status of a sync operation."""
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncState:
    """Represents the current state of a sync operation."""
    user_id: str
    provider: str
    folder_id: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    next_page_token: Optional[str] = None
    last_cursor: Optional[str] = None
    items_synced: int = 0
    sync_status: SyncStatus = SyncStatus.IDLE
    error_message: Optional[str] = None


@dataclass
class SyncResult:
    """Result of a sync operation."""
    items_added: int = 0
    items_updated: int = 0
    items_deleted: int = 0
    has_more: bool = False
    next_page_token: Optional[str] = None
    next_cursor: Optional[str] = None
    error: Optional[str] = None


class SyncManager:
    """
    Manages sync state persistence and retrieval.
    
    Usage:
        manager = SyncManager(user_id, "google_drive")
        state = manager.get_state()
        
        # After sync
        manager.update_state(
            last_sync_at=datetime.now(),
            items_synced=100,
            sync_status=SyncStatus.COMPLETED
        )
    """
    
    def __init__(self, user_id: str, provider: str, folder_id: Optional[str] = None):
        self.user_id = user_id
        self.provider = provider
        self.folder_id = folder_id
        self.supabase = get_supabase()
    
    def get_state(self) -> Optional[SyncState]:
        """Get the current sync state from the database."""
        try:
            query = self.supabase.table("sync_state").select("*").eq(
                "user_id", self.user_id
            ).eq("provider", self.provider)
            
            if self.folder_id:
                query = query.eq("folder_id", self.folder_id)
            else:
                query = query.is_("folder_id", "null")
            
            result = query.execute()
            
            if result.data:
                row = result.data[0]
                return SyncState(
                    user_id=row["user_id"],
                    provider=row["provider"],
                    folder_id=row.get("folder_id"),
                    last_sync_at=datetime.fromisoformat(row["last_sync_at"]) if row.get("last_sync_at") else None,
                    next_page_token=row.get("next_page_token"),
                    last_cursor=row.get("last_cursor"),
                    items_synced=row.get("items_synced", 0),
                    sync_status=SyncStatus(row.get("sync_status", "idle")),
                    error_message=row.get("error_message")
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get sync state: {e}")
            return None
    
    def update_state(
        self,
        last_sync_at: Optional[datetime] = None,
        next_page_token: Optional[str] = None,
        last_cursor: Optional[str] = None,
        items_synced: Optional[int] = None,
        sync_status: Optional[SyncStatus] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update the sync state in the database."""
        try:
            data: Dict[str, Any] = {}
            
            if last_sync_at is not None:
                data["last_sync_at"] = last_sync_at.isoformat()
            if next_page_token is not None:
                data["next_page_token"] = next_page_token
            if last_cursor is not None:
                data["last_cursor"] = last_cursor
            if items_synced is not None:
                data["items_synced"] = items_synced
            if sync_status is not None:
                data["sync_status"] = sync_status.value
            if error_message is not None:
                data["error_message"] = error_message
            
            if not data:
                return True
            
            # Upsert the state
            data.update({
                "user_id": self.user_id,
                "provider": self.provider,
                "folder_id": self.folder_id
            })
            
            self.supabase.table("sync_state").upsert(
                data,
                on_conflict="user_id,provider,folder_id"
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Failed to update sync state: {e}")
            return False
    
    def start_sync(self) -> bool:
        """Mark sync as in progress."""
        return self.update_state(
            sync_status=SyncStatus.IN_PROGRESS,
            error_message=None
        )
    
    def complete_sync(self, items_synced: int) -> bool:
        """Mark sync as completed."""
        return self.update_state(
            last_sync_at=datetime.now(timezone.utc),
            items_synced=items_synced,
            sync_status=SyncStatus.COMPLETED,
            error_message=None
        )
    
    def fail_sync(self, error: str) -> bool:
        """Mark sync as failed."""
        return self.update_state(
            sync_status=SyncStatus.FAILED,
            error_message=error
        )


class IncrementalSyncMixin(ABC):
    """
    Mixin for connectors that support incremental sync.
    
    Usage:
        class DriveConnector(BaseConnector, IncrementalSyncMixin):
            async def get_changes(self, user_id, since=None, page_token=None):
                # Implementation
                pass
    """
    
    @abstractmethod
    async def get_changes(
        self,
        user_id: str,
        since: Optional[datetime] = None,
        page_token: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], Optional[str], bool]:
        """
        Get changes since last sync.
        
        Args:
            user_id: The user ID
            since: Optional datetime to get changes since
            page_token: Optional page token for pagination
            
        Returns:
            Tuple of (changes, next_page_token, has_more)
        """
        pass
    
    async def incremental_sync(
        self,
        user_id: str,
        provider: str,
        folder_id: Optional[str] = None
    ) -> SyncResult:
        """
        Perform an incremental sync using the sync manager.
        
        Returns a SyncResult with counts of added/updated/deleted items.
        """
        manager = SyncManager(user_id, provider, folder_id)
        result = SyncResult()
        
        # Get current state
        state = manager.get_state()
        since = state.last_sync_at if state else None
        page_token = state.next_page_token if state else None
        
        # Mark sync as started
        manager.start_sync()
        
        try:
            total_items = 0
            
            # Paginate through all changes
            while True:
                changes, next_token, has_more = await self.get_changes(
                    user_id, since=since, page_token=page_token
                )
                
                total_items += len(changes)
                
                # Process changes (subclass implements this)
                for change in changes:
                    change_type = change.get("changeType", "added")
                    if change_type == "added":
                        result.items_added += 1
                    elif change_type == "updated":
                        result.items_updated += 1
                    elif change_type == "deleted":
                        result.items_deleted += 1
                
                # Save progress
                manager.update_state(
                    next_page_token=next_token,
                    items_synced=total_items
                )
                
                if not has_more:
                    break
                    
                page_token = next_token
            
            # Mark complete
            manager.complete_sync(total_items)
            result.has_more = False
            
        except Exception as e:
            logger.error(f"Incremental sync failed: {e}")
            manager.fail_sync(str(e))
            result.error = str(e)
        
        return result
