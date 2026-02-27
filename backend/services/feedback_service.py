"""
Feedback Service - Chat Response Quality Analytics

Business logic for collecting and analyzing user feedback on AI chat responses.
All database operations are organization-scoped for multi-tenant security.

Related Files:
- backend/api/v1/feedback.py (API endpoints)
- supabase/migrations/20260122000000_message_feedback.sql (schema)
- frontend-new/components/chat/FeedbackButtons.tsx (UI)

Usage:
    from services.feedback_service import feedback_service

    result = await feedback_service.submit_feedback(
        supabase=supabase,
        user_id="...",
        organization_id="...",
        message_id="...",
        rating="negative",
        feedback_text="Answer was outdated"
    )
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class FeedbackService:
    """
    Service for chat feedback operations.

    All methods are stateless and require a Supabase client.
    Organization scoping is enforced at this layer for security.
    """

    async def submit_feedback(
        self,
        supabase,
        user_id: str,
        organization_id: str,
        message_id: str,
        conversation_id: str,
        rating: str,
        query_text: str,
        answer_preview: str,
        sources_snapshot: list[dict],
        feedback_text: str | None = None
    ) -> dict[str, Any]:
        """
        Submit or update feedback for a message.

        Uses upsert to allow users to change their rating.

        Args:
            supabase: Supabase client
            user_id: UUID of the user submitting feedback
            organization_id: UUID of the user's organization
            message_id: UUID of the message being rated
            conversation_id: UUID of the conversation
            rating: 'positive' or 'negative'
            query_text: The user's original question
            answer_preview: First 500 chars of the AI response
            sources_snapshot: List of source metadata at feedback time
            feedback_text: Optional comment (max 100 chars)

        Returns:
            dict with id, message_id, rating, created_at, updated_at, is_update

        Raises:
            ValueError: Invalid rating or feedback_text too long
        """
        # Validate rating
        if rating not in ('positive', 'negative'):
            raise ValueError(f"Invalid rating: {rating}. Must be 'positive' or 'negative'")

        # Validate feedback_text length
        if feedback_text and len(feedback_text) > 100:
            raise ValueError(f"feedback_text exceeds 100 characters ({len(feedback_text)})")

        # Truncate answer_preview to 500 chars for GDPR data minimization
        answer_preview = answer_preview[:500] if answer_preview else ""

        # Prepare upsert data
        feedback_data = {
            "message_id": message_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "conversation_id": conversation_id,
            "rating": rating,
            "feedback_text": feedback_text,
            "query_text": query_text,
            "answer_preview": answer_preview,
            "sources_snapshot": sources_snapshot or [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Check if feedback already exists
        existing = supabase.table("message_feedback")\
            .select("id, created_at")\
            .eq("message_id", message_id)\
            .eq("user_id", user_id)\
            .maybe_single()\
            .execute()

        is_update = existing is not None and bool(existing.data)

        if is_update:
            # Update existing feedback
            result = supabase.table("message_feedback")\
                .update({
                    "rating": rating,
                    "feedback_text": feedback_text,
                    "updated_at": feedback_data["updated_at"],
                })\
                .eq("id", existing.data["id"])\
                .execute()

            logger.info(
                f"📝 [Feedback] Updated: user={user_id[:8]}... message={message_id[:8]}... "
                f"rating={rating}"
            )
        else:
            # Insert new feedback
            feedback_data["created_at"] = datetime.now(timezone.utc).isoformat()
            result = supabase.table("message_feedback")\
                .insert(feedback_data)\
                .execute()

            logger.info(
                f"📝 [Feedback] Created: user={user_id[:8]}... message={message_id[:8]}... "
                f"rating={rating}"
            )

        if not result.data:
            raise RuntimeError("Failed to save feedback")

        return {
            "id": result.data[0]["id"],
            "message_id": message_id,
            "rating": rating,
            "created_at": result.data[0].get("created_at"),
            "updated_at": result.data[0].get("updated_at"),
            "is_update": is_update,
        }

    async def get_user_feedback_for_conversation(
        self,
        supabase,
        user_id: str,
        conversation_id: str
    ) -> dict[str, str]:
        """
        Get all feedback a user has given in a conversation.

        Returns:
            Dict mapping message_id -> rating ('positive' or 'negative')
        """
        result = supabase.table("message_feedback")\
            .select("message_id, rating")\
            .eq("user_id", user_id)\
            .eq("conversation_id", conversation_id)\
            .execute()

        return {
            row["message_id"]: row["rating"]
            for row in (result.data or [])
        }

    async def get_team_feedback(
        self,
        supabase,
        organization_id: str,
        limit: int = 50,
        offset: int = 0,
        rating: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        source_label: str | None = None
    ) -> dict[str, Any]:
        """
        Get feedback analytics for a team/organization.

        Args:
            supabase: Supabase client
            organization_id: UUID of the organization
            limit: Max items to return (max 100)
            offset: Pagination offset
            rating: Filter by 'positive' or 'negative'
            from_date: ISO date string for start of range
            to_date: ISO date string for end of range
            source_label: Filter by source document label

        Returns:
            dict with items, total, has_more, summary
        """
        # Clamp limit
        limit = min(limit, 100)

        # Build query
        query = supabase.table("message_feedback")\
            .select("*", count="exact")\
            .eq("organization_id", organization_id)

        # Apply filters
        if rating:
            query = query.eq("rating", rating)
        if from_date:
            query = query.gte("created_at", from_date)
        if to_date:
            query = query.lte("created_at", to_date)
        if source_label:
            # Filter by source label in JSONB array
            query = query.contains("sources_snapshot", [{"label": source_label}])

        # Execute with pagination
        result = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        total = result.count if result.count is not None else 0

        # Batch-fetch user emails (single query instead of N)
        rows = result.data or []
        user_ids = [row["user_id"] for row in rows]
        email_map = await self._get_user_emails_batch(supabase, user_ids)

        items = []
        for row in rows:
            items.append({
                "id": row["id"],
                "rating": row["rating"],
                "feedback_text": row.get("feedback_text"),
                "query_text": row["query_text"],
                "answer_preview": row["answer_preview"],
                "sources": row.get("sources_snapshot", []),
                "user_email": email_map.get(row["user_id"], "unknown"),
                "created_at": row["created_at"],
            })

        # Get summary statistics
        summary = await self._get_feedback_summary(supabase, organization_id)

        return {
            "items": items,
            "total": total,
            "has_more": (offset + limit) < total,
            "summary": summary,
        }

    async def get_source_metrics(
        self,
        supabase,
        organization_id: str,
        min_feedback_count: int = 5,
        sort_by: str = "negative_rate_pct",
        sort_order: str = "desc",
        limit: int = 20,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Get aggregated source quality metrics.

        When from_date/to_date are provided, uses the RPC function for date-filtered
        results. Otherwise falls back to the fast materialized view.

        Args:
            supabase: Supabase client
            organization_id: UUID of the organization
            min_feedback_count: Exclude sources with fewer ratings
            sort_by: Column to sort by
            sort_order: 'asc' or 'desc'
            limit: Max items to return (max 50)
            from_date: ISO date string for start of range
            to_date: ISO date string for end of range

        Returns:
            dict with items and total
        """
        # Clamp limit
        limit = min(limit, 50)

        # Validate sort column
        valid_sort_columns = ["negative_rate_pct", "total_feedback", "negative_count", "positive_count"]
        if sort_by not in valid_sort_columns:
            sort_by = "negative_rate_pct"

        # Use RPC for date-filtered queries, materialized view otherwise
        if from_date or to_date:
            rpc_params: dict[str, Any] = {
                "p_organization_id": organization_id,
                "p_min_feedback_count": min_feedback_count,
                "p_sort_by": sort_by,
                "p_sort_order": sort_order,
                "p_limit": limit,
            }
            if from_date:
                rpc_params["p_from_date"] = from_date
            if to_date:
                rpc_params["p_to_date"] = to_date

            result = supabase.rpc("get_source_metrics_filtered", rpc_params).execute()
            rows = result.data or []
        else:
            # Fast path: materialized view (no date filtering)
            query = supabase.table("source_feedback_metrics")\
                .select("*", count="exact")\
                .eq("organization_id", organization_id)\
                .gte("total_feedback", min_feedback_count)

            if sort_order == "asc":
                query = query.order(sort_by, desc=False)
            else:
                query = query.order(sort_by, desc=True)

            result = query.limit(limit).execute()
            rows = result.data or []

        items = [
            {
                "source_label": row["source_label"],
                "source_type": row.get("source_type"),
                "source_url": row.get("source_url"),
                "positive_count": int(row["positive_count"]),
                "negative_count": int(row["negative_count"]),
                "total_feedback": int(row["total_feedback"]),
                "negative_rate_pct": float(row["negative_rate_pct"]) if row.get("negative_rate_pct") else 0.0,
                "last_feedback_at": row.get("last_feedback_at"),
            }
            for row in rows
        ]

        return {
            "items": items,
            "total": len(items),
        }

    async def get_feedback_trend(
        self,
        supabase,
        organization_id: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get daily feedback counts for the trend chart.

        Uses the get_feedback_trend RPC function to aggregate by day.

        Returns:
            List of { date, positive_count, negative_count } dicts
        """
        rpc_params: dict[str, Any] = {
            "p_organization_id": organization_id,
        }
        if from_date:
            rpc_params["p_from_date"] = from_date
        if to_date:
            rpc_params["p_to_date"] = to_date

        result = supabase.rpc("get_feedback_trend", rpc_params).execute()

        return [
            {
                "date": row["date"],
                "positive_count": int(row["positive_count"]),
                "negative_count": int(row["negative_count"]),
            }
            for row in (result.data or [])
        ]

    async def get_platform_feedback(
        self,
        supabase,
        limit: int = 50,
        offset: int = 0,
        rating: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        organization_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get feedback across all organizations (platform admin only).

        Similar to get_team_feedback but without org filter (or with optional org filter).

        Args:
            supabase: Supabase client (must use service role)
            limit: Max items to return
            offset: Pagination offset
            rating: Filter by rating
            from_date: Filter by start date
            to_date: Filter by end date
            organization_id: Optional filter by specific org

        Returns:
            dict with items, total, has_more, summary
        """
        # Clamp limit
        limit = min(limit, 100)

        # Build query (no org filter for platform-wide)
        query = supabase.table("message_feedback")\
            .select("*", count="exact")

        # Apply filters
        if organization_id:
            query = query.eq("organization_id", organization_id)
        if rating:
            query = query.eq("rating", rating)
        if from_date:
            query = query.gte("created_at", from_date)
        if to_date:
            query = query.lte("created_at", to_date)

        # Execute
        result = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()

        total = result.count if result.count is not None else 0

        # Batch-fetch user emails and org names (single query each instead of N)
        rows = result.data or []
        user_ids = [row["user_id"] for row in rows]
        org_ids = [row["organization_id"] for row in rows]
        email_map = await self._get_user_emails_batch(supabase, user_ids)
        org_name_map = await self._get_org_names_batch(supabase, org_ids)

        items = []
        for row in rows:
            org_id = row["organization_id"]
            items.append({
                "id": row["id"],
                "organization_id": org_id,
                "organization_name": org_name_map.get(org_id, f"org-{org_id[:8]}..."),
                "rating": row["rating"],
                "feedback_text": row.get("feedback_text"),
                "query_text": row["query_text"],
                "answer_preview": row["answer_preview"],
                "sources": row.get("sources_snapshot", []),
                "user_email": email_map.get(row["user_id"], "unknown"),
                "created_at": row["created_at"],
            })

        # Get platform-wide summary
        summary = await self._get_platform_summary(supabase)

        return {
            "items": items,
            "total": total,
            "has_more": (offset + limit) < total,
            "summary": summary,
        }

    async def refresh_metrics(self, supabase) -> None:
        """
        Refresh the source_feedback_metrics materialized view.

        Call after bulk feedback operations or on a schedule.
        """
        try:
            supabase.rpc("refresh_source_feedback_metrics").execute()
            logger.info("📊 [Feedback] Refreshed source_feedback_metrics view")
        except Exception as e:
            logger.error(f"❌ [Feedback] Failed to refresh metrics: {e}")
            raise

    async def _get_feedback_summary(
        self,
        supabase,
        organization_id: str
    ) -> dict[str, Any]:
        """Get summary statistics for an organization."""
        # Use count-only queries (no row data fetched) and derive positive = total - negative
        total_result = supabase.table("message_feedback")\
            .select("*", count="exact", head=True)\
            .eq("organization_id", organization_id)\
            .execute()

        negative = supabase.table("message_feedback")\
            .select("*", count="exact", head=True)\
            .eq("organization_id", organization_id)\
            .eq("rating", "negative")\
            .execute()

        total = total_result.count or 0
        negative_count = negative.count or 0
        positive_count = total - negative_count

        return {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "total_count": total,
            "negative_rate_pct": round(
                (negative_count / total * 100) if total > 0 else 0, 2
            ),
        }

    async def _get_platform_summary(self, supabase) -> dict[str, Any]:
        """Get platform-wide summary statistics."""
        total_result = supabase.table("message_feedback")\
            .select("*", count="exact", head=True)\
            .execute()

        negative = supabase.table("message_feedback")\
            .select("*", count="exact", head=True)\
            .eq("rating", "negative")\
            .execute()

        # Count unique organizations with feedback (capped for performance)
        orgs = supabase.table("message_feedback")\
            .select("organization_id")\
            .limit(1000)\
            .execute()

        unique_orgs = len(set(row["organization_id"] for row in (orgs.data or [])))

        total = total_result.count or 0
        negative_count = negative.count or 0
        positive_count = total - negative_count

        return {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "total_count": total,
            "negative_rate_pct": round(
                (negative_count / total * 100) if total > 0 else 0, 2
            ),
            "organizations_with_feedback": unique_orgs,
        }

    async def _get_user_emails_batch(self, supabase, user_ids: list[str]) -> dict[str, str]:
        """Get emails for multiple users in a single query via user_profiles table."""
        if not user_ids:
            return {}
        unique_ids = list(set(user_ids))
        result_map: dict[str, str] = {}
        try:
            profiles = supabase.table("user_profiles")\
                .select("user_id, email")\
                .in_("user_id", unique_ids)\
                .execute()
            for row in (profiles.data or []):
                email = row.get("email")
                if email:
                    result_map[row["user_id"]] = email
                else:
                    result_map[row["user_id"]] = f"user-{row['user_id'][:8]}..."
        except Exception as e:
            logger.debug(f"[Feedback] Batch email lookup failed: {e}")
        # Fill in any missing user_ids
        for uid in unique_ids:
            if uid not in result_map:
                result_map[uid] = "unknown"
        return result_map

    async def _get_org_names_batch(self, supabase, org_ids: list[str]) -> dict[str, str]:
        """Get organization names for multiple orgs in a single query."""
        if not org_ids:
            return {}
        unique_ids = list(set(org_ids))
        result_map: dict[str, str] = {}
        try:
            teams = supabase.table("teams")\
                .select("id, name")\
                .in_("id", unique_ids)\
                .execute()
            for row in (teams.data or []):
                result_map[row["id"]] = row["name"]
        except Exception as e:
            logger.debug(f"[Feedback] Batch org name lookup failed: {e}")
        # Fill in any missing org_ids
        for oid in unique_ids:
            if oid not in result_map:
                result_map[oid] = f"org-{oid[:8]}..."
        return result_map

    async def _get_user_email(self, supabase, user_id: str) -> str:
        """Get user email by ID (for display in analytics)."""
        try:
            # Try to get from auth.users via admin API
            user = supabase.auth.admin.get_user_by_id(user_id)
            if user and user.user:
                return user.user.email or "unknown"
        except Exception as e:
            logger.debug(f"[Feedback] Failed to fetch user email from auth: {e}")

        # Fallback: try user_profiles
        try:
            profile = supabase.table("user_profiles")\
                .select("user_id")\
                .eq("user_id", user_id)\
                .maybe_single()\
                .execute()
            if profile is not None and profile.data:
                return f"user-{user_id[:8]}..."
        except Exception as e:
            logger.debug(f"[Feedback] Failed to fetch user profile: {e}")

        return "unknown"

    async def _get_org_name(self, supabase, organization_id: str) -> str:
        """Get organization/team name by ID."""
        try:
            team = supabase.table("teams")\
                .select("name")\
                .eq("id", organization_id)\
                .maybe_single()\
                .execute()
            if team is not None and team.data:
                return team.data["name"]
        except Exception as e:
            logger.debug(f"[Feedback] Failed to fetch organization name: {e}")

        return f"org-{organization_id[:8]}..."


# Singleton instance
feedback_service = FeedbackService()
