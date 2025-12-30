"""
Team Service

Provides team management and plan inheritance logic.
The critical path is get_effective_plan() which is called on every request
to determine feature access - hence it's cached with async-lru.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    Team Hierarchy                           │
    ├─────────────────────────────────────────────────────────────┤
    │  Team Owner (Enterprise Plan)                               │
    │       └── Team Member A (inherits Enterprise)               │
    │       └── Team Member B (inherits Enterprise)               │
    │                                                             │
    │  Solo User (Free Plan)                                      │
    │       └── Personal Team (owns it, gets Free limits)         │
    └─────────────────────────────────────────────────────────────┘

Usage:
    from services.team_service import team_service
    
    # Get effective plan (cached, fast)
    plan = await team_service.get_effective_plan(user_id)
    
    # Invalidate cache when user upgrades
    team_service.invalidate_plan_cache(user_id)
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID

from async_lru import alru_cache

from core.db import get_supabase
from core.quotas import get_plan_limits

logger = logging.getLogger(__name__)


class TeamService:
    """
    Service for team management and plan inheritance.
    
    Key responsibilities:
    - Resolve user's effective plan (inherited from team owner)
    - Manage team CRUD operations
    - Handle team membership
    """
    
    @alru_cache(maxsize=1000, ttl=60)
    async def get_effective_plan(self, user_id: str) -> str:
        """
        Get the effective plan for a user (CACHED).
        
        This is the critical hot path - called on every request
        to determine feature access. Cached for 60 seconds.
        
        Logic:
        1. Find user's team membership
        2. Get team owner's plan
        3. Return that plan (inheritance)
        4. Fallback: user's own plan or 'free'
        
        Args:
            user_id: The user's UUID as string
            
        Returns:
            Plan name: 'free', 'starter', 'pro', or 'enterprise'
        """
        try:
            supabase = get_supabase()
            
            # Strategy: Use the database function for reliability
            # This is a single query that handles all the joins
            response = supabase.rpc(
                "get_effective_plan", 
                {"target_user_id": user_id}
            ).execute()
            
            if response.data:
                plan = response.data
                logger.debug(f"[TeamService] User {user_id[:8]}... effective plan: {plan}")
                return plan
            
            # Fallback: direct query
            return await self._get_effective_plan_direct(user_id)
            
        except Exception as e:
            logger.warning(f"[TeamService] RPC failed, trying direct query: {e}")
            return await self._get_effective_plan_direct(user_id)
    
    async def _get_effective_plan_direct(self, user_id: str) -> str:
        """
        Direct database query for effective plan (fallback).
        
        Includes subscription status checks and team lockout enforcement.
        
        Used when RPC is unavailable or fails.
        """
        try:
            supabase = get_supabase()
            
            # Step 1: Find user's team membership
            member_response = supabase.table("team_members").select(
                "team_id"
            ).eq("member_user_id", user_id).neq("status", "removed").limit(1).execute()
            
            if member_response.data and member_response.data[0].get("team_id"):
                team_id = member_response.data[0]["team_id"]
                
                # Step 2: Get team owner
                team_response = supabase.table("teams").select(
                    "owner_id"
                ).eq("id", team_id).single().execute()
                
                if team_response.data:
                    owner_id = team_response.data["owner_id"]
                    is_owner = (owner_id == user_id)
                    
                    # Step 3: Get owner's profile with plan AND subscription status
                    profile_response = supabase.table("user_profiles").select(
                        "plan, subscription_status"
                    ).eq("user_id", owner_id).single().execute()
                    
                    if profile_response.data:
                        owner_plan = profile_response.data.get("plan", "free")
                        subscription_status = profile_response.data.get("subscription_status", "active")
                        
                        # Check 1: Subscription Status
                        # Allow only active and trialing statuses
                        allowed_statuses = ["active", "trialing"]
                        if subscription_status not in allowed_statuses:
                            logger.info(
                                f"[TeamService] Owner {owner_id[:8]}... has status={subscription_status}, "
                                f"forcing 'none' (paywall) for user {user_id[:8]}..."
                            )
                            return "none"
                        
                        # Check 2: Team Lockout (MVP)
                        # If user is NOT the owner, check if owner's plan allows team members
                        if not is_owner:
                            plan_limits = get_plan_limits(owner_plan)
                            
                            if plan_limits.max_team_seats <= 1:
                                # Owner downgraded to a plan without team support
                                # Team members lose access (return 'free' plan)
                                logger.warning(
                                    f"[TeamService] Team lockout: Owner {owner_id[:8]}... "
                                    f"has {owner_plan} (max_seats=1), "
                                    f"member {user_id[:8]}... gets 'free'"
                                )
                                return "free"
                        
                        logger.debug(f"[TeamService] User {user_id[:8]}... inherits plan: {owner_plan}")
                        return owner_plan
            
            # Fallback: Get user's own plan
            own_profile = supabase.table("user_profiles").select(
                "plan, subscription_status"
            ).eq("user_id", user_id).single().execute()
            
            if own_profile.data:
                subscription_status = own_profile.data.get("subscription_status", "active")
                
                # Check subscription status for solo users too
                allowed_statuses = ["active", "trialing"]
                if subscription_status not in allowed_statuses:
                    logger.info(f"[TeamService] User {user_id[:8]}... has status={subscription_status}, forcing 'none'")
                    return "none"
                
                return own_profile.data.get("plan", "none")
            
            return "free"
            
        except Exception as e:
            logger.error(f"[TeamService] Direct query failed: {e}")
            return "none"
    
    def invalidate_plan_cache(self, user_id: str) -> None:
        """
        Invalidate the plan cache for a user.
        
        Call this when:
        - User upgrades/downgrades their plan
        - User joins/leaves a team
        - Team owner changes plans
        
        Args:
            user_id: The user's UUID as string
        """
        try:
            # Clear this specific user from cache
            self.get_effective_plan.cache_invalidate(user_id)
            logger.info(f"[TeamService] Cache invalidated for user {user_id[:8]}...")
        except Exception as e:
            logger.warning(f"[TeamService] Cache invalidation failed: {e}")
    
    def invalidate_all_cache(self) -> None:
        """
        Invalidate entire plan cache.
        
        Use sparingly - only for admin operations or deployments.
        """
        try:
            self.get_effective_plan.cache_clear()
            logger.info("[TeamService] Full cache cleared")
        except Exception as e:
            logger.warning(f"[TeamService] Full cache clear failed: {e}")
    
    async def verify_team_access(self, user_id: str) -> Dict[str, Any]:
        """
        Verify if a user has valid team access.
        
        This is a STRICT check that raises exceptions for blocked access.
        Use this for protecting critical endpoints.
        
        Checks:
        1. If user is team owner → ALLOW
        2. If user is team member:
           - Check owner's subscription status
           - Check if owner's plan allows team members
           - Block if either check fails
        
        Args:
            user_id: The user's UUID as string
            
        Returns:
            Dict with access info: {allowed: bool, reason: str, plan: str}
            
        Raises:
            TeamAccessDenied: If access is blocked due to team lockout
        """
        try:
            supabase = get_supabase()
            
            # Get user's team membership
            member_response = supabase.table("team_members").select(
                "team_id, role"
            ).eq("member_user_id", user_id).neq("status", "removed").limit(1).execute()
            
            if not member_response.data or not member_response.data[0].get("team_id"):
                # User has no team - solo user, always allowed
                return {"allowed": True, "reason": "solo_user", "plan": "free"}
            
            team_id = member_response.data[0]["team_id"]
            
            # Get team details
            team_response = supabase.table("teams").select(
                "owner_id"
            ).eq("id", team_id).single().execute()
            
            if not team_response.data:
                # Team not found - unusual, allow as fallback
                return {"allowed": True, "reason": "team_not_found", "plan": "free"}
            
            owner_id = team_response.data["owner_id"]
            is_owner = (owner_id == user_id)
            
            if is_owner:
                # Owners always have access to their own team
                return {"allowed": True, "reason": "team_owner", "plan": "unknown"}
            
            # User is a member - check owner's status and plan
            profile_response = supabase.table("user_profiles").select(
                "plan, subscription_status"
            ).eq("user_id", owner_id).single().execute()
            
            if not profile_response.data:
                return {"allowed": True, "reason": "owner_not_found", "plan": "free"}
            
            owner_plan = profile_response.data.get("plan", "free")
            subscription_status = profile_response.data.get("subscription_status", "active")
            
            # Check 1: Subscription Status
            restricted_statuses = ["unpaid", "past_due", "canceled", "expired"]
            if subscription_status in restricted_statuses:
                logger.warning(
                    f"[TeamService] Access denied for {user_id[:8]}...: "
                    f"Owner subscription status is '{subscription_status}'"
                )
                return {
                    "allowed": False,
                    "reason": "subscription_inactive",
                    "plan": "free",
                    "message": "Team access is suspended. Owner's subscription is inactive."
                }
            
            # Check 2: Team Lockout (owner downgraded)
            plan_limits = get_plan_limits(owner_plan)
            
            if plan_limits.max_team_seats <= 1:
                logger.warning(
                    f"[TeamService] Access denied for {user_id[:8]}...: "
                    f"Owner plan '{owner_plan}' doesn't allow team members"
                )
                return {
                    "allowed": False,
                    "reason": "team_not_available",
                    "plan": "free",
                    "message": f"Team access is suspended. Owner must upgrade to Enterprise."
                }
            
            # All checks passed
            return {
                "allowed": True,
                "reason": "team_member",
                "plan": owner_plan
            }
            
        except Exception as e:
            logger.error(f"[TeamService] verify_team_access failed: {e}")
            # On error, fail open but log
            return {"allowed": True, "reason": "error", "plan": "free", "error": str(e)}
    
    async def get_user_team_member(self, user_id: str) -> Optional[Any]:
        """
        Get team member object for billing logic.
        Returns a TeamMember-like object with team_id.
        """
        try:
            supabase = get_supabase()
            response = supabase.table("team_members").select(
                "team_id, member_user_id"
            ).eq("member_user_id", user_id).limit(1).execute()
            
            if response.data:
                from models import TeamMember
                data = response.data[0]
                return TeamMember(
                    team_id=data["team_id"],
                    member_user_id=data["member_user_id"]
                )
            return None
        except Exception as e:
            logger.error(f"[TeamService] get_user_team_member failed: {e}")
            return None

    async def get_user_team(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the team a user belongs to.
        
        Args:
            user_id: The user's UUID as string
            
        Returns:
            Team dict with id, name, slug, owner_id, or None
        """
        try:
            supabase = get_supabase()
            
            # Find user's team via membership
            member_response = supabase.table("team_members").select(
                "team_id, role, joined_at"
            ).eq("member_user_id", user_id).limit(1).execute()
            
            if not member_response.data:
                return None
            
            team_id = member_response.data[0].get("team_id")
            member_role = member_response.data[0].get("role")
            joined_at = member_response.data[0].get("joined_at")
            
            if not team_id:
                return None
            
            # Get team details
            team_response = supabase.table("teams").select(
                "id, name, slug, owner_id, created_at"
            ).eq("id", team_id).single().execute()
            
            if team_response.data:
                team = team_response.data
                team["user_role"] = member_role
                team["user_joined_at"] = joined_at
                team["is_owner"] = team["owner_id"] == user_id
                return team
            
            return None
            
        except Exception as e:
            logger.error(f"[TeamService] get_user_team failed: {e}")
            return None
    
    async def get_team_by_id(self, team_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a team by its ID.
        
        Args:
            team_id: The team's UUID as string
            
        Returns:
            Team dict or None
        """
        try:
            supabase = get_supabase()
            
            response = supabase.table("teams").select(
                "id, name, slug, owner_id, created_at, updated_at"
            ).eq("id", team_id).single().execute()
            
            return response.data if response.data else None
            
        except Exception as e:
            logger.error(f"[TeamService] get_team_by_id failed: {e}")
            return None
    
    async def create_team(
        self, 
        owner_id: str, 
        name: str, 
        slug: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new team.
        
        Note: For MVP, each user can only own one team.
        The auto-team trigger handles this for new users.
        
        Args:
            owner_id: The owner's user UUID
            name: Team name
            slug: Optional URL-friendly slug
            
        Returns:
            Created team dict or None
        """
        try:
            supabase = get_supabase()
            
            team_data = {
                "name": name,
                "owner_id": owner_id,
            }
            
            if slug:
                team_data["slug"] = slug
            
            response = supabase.table("teams").insert(team_data).execute()
            
            if response.data:
                team = response.data[0]
                
                # Add owner as admin member
                supabase.table("team_members").insert({
                    "team_id": team["id"],
                    "owner_user_id": owner_id,
                    "member_user_id": owner_id,
                    "role": "admin",
                    "status": "active",
                    "joined_at": team.get("created_at")
                }).execute()
                
                logger.info(f"[TeamService] Team created: {team['id']}")
                return team
            
            return None
            
        except Exception as e:
            logger.error(f"[TeamService] create_team failed: {e}")
            return None
    
    async def update_team(
        self, 
        team_id: str, 
        name: Optional[str] = None,
        slug: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update team settings.
        
        Args:
            team_id: The team's UUID
            name: New team name (optional)
            slug: New team slug (optional)
            
        Returns:
            Updated team dict or None
        """
        try:
            supabase = get_supabase()
            
            update_data = {"updated_at": "now()"}
            if name:
                update_data["name"] = name
            if slug:
                update_data["slug"] = slug
            
            response = supabase.table("teams").update(
                update_data
            ).eq("id", team_id).execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"[TeamService] update_team failed: {e}")
            return None
    
    async def get_team_members(self, team_id: str) -> list:
        """
        Get all members of a team.
        
        Args:
            team_id: The team's UUID
            
        Returns:
            List of team member dicts
        """
        try:
            supabase = get_supabase()
            
            response = supabase.table("team_members").select(
                "id, email, name, role, status, member_user_id, joined_at, created_at"
            ).eq("team_id", team_id).order("created_at", desc=True).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"[TeamService] get_team_members failed: {e}")
            return []
    
    # =========================================================================
    # TEAM MANAGEMENT (Enterprise-only features)
    # =========================================================================
    
    async def _check_team_feature_access(self, owner_id: str) -> tuple[bool, str, Dict[str, Any]]:
        """
        Check if the owner's plan allows team management.
        
        Returns:
            Tuple of (allowed, error_message, plan_limits)
        """
        try:
            supabase = get_supabase()
            
            # Get owner's plan
            profile_response = supabase.table("user_profiles").select(
                "plan"
            ).eq("user_id", owner_id).single().execute()
            
            plan = "free"
            if profile_response.data:
                plan = profile_response.data.get("plan", "free")
            
            limits = get_plan_limits(plan)
            
            # Check if plan allows team members (max_team_seats > 1)
            if limits.max_team_seats <= 1:
                return (
                    False, 
                    f"Team management requires Enterprise plan. Current plan: {plan}", 
                    limits.model_dump()
                )
            
            return (True, "", limits.model_dump())
            
        except Exception as e:
            logger.error(f"[TeamService] _check_team_feature_access failed: {e}")
            return (False, "Failed to verify plan", {})
    
    async def _get_current_member_count(self, team_id: str) -> int:
        """Get current number of team members."""
        try:
            supabase = get_supabase()
            
            response = supabase.table("team_members").select(
                "id", count="exact"
            ).eq("team_id", team_id).neq("status", "removed").execute()
            
            return response.count or 0
            
        except Exception as e:
            logger.error(f"[TeamService] _get_current_member_count failed: {e}")
            return 0
    
    async def invite_member(
        self, 
        owner_id: str, 
        email: str, 
        role: str = "viewer",
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invite a new member to the team.
        
        **Enterprise Only**: Only plans with max_team_seats > 1 can invite.
        
        Args:
            owner_id: The team owner's user UUID
            email: Email address to invite
            role: Role to assign (admin, editor, viewer)
            name: Display name for the invitee
            
        Returns:
            Dict with success status, member data, or error
            
        Raises:
            PermissionError: If plan doesn't allow team management
        """
        import uuid
        from datetime import datetime
        
        # Step 1: Check plan allows team feature
        allowed, error_msg, limits = await self._check_team_feature_access(owner_id)
        if not allowed:
            logger.warning(f"[TeamService] Invite blocked for {owner_id[:8]}...: {error_msg}")
            return {"success": False, "error": error_msg, "code": "UPGRADE_REQUIRED"}
        
        try:
            supabase = get_supabase()
            
            # Get owner's team
            team = await self.get_user_team(owner_id)
            if not team:
                return {"success": False, "error": "Team not found", "code": "NOT_FOUND"}
            
            team_id = team["id"]
            
            # Check seat limit
            current_count = await self._get_current_member_count(team_id)
            max_seats = limits.get("max_team_seats", 1)
            
            if current_count >= max_seats:
                return {
                    "success": False, 
                    "error": f"Team seat limit reached ({current_count}/{max_seats})",
                    "code": "SEAT_LIMIT"
                }
            
            # Check if already invited
            existing = supabase.table("team_members").select(
                "id, status"
            ).eq("team_id", team_id).eq("email", email).execute()
            
            if existing.data:
                existing_status = existing.data[0].get("status")
                if existing_status != "removed":
                    return {
                        "success": False, 
                        "error": f"Email already invited (status: {existing_status})",
                        "code": "ALREADY_EXISTS"
                    }
            
            # Generate invite token
            invite_token = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            # Validate role
            if role not in ["admin", "editor", "viewer"]:
                role = "viewer"
            
            # Create invite
            member_data = {
                "team_id": team_id,
                "owner_user_id": owner_id,
                "email": email,
                "name": name or email.split("@")[0],
                "role": role,
                "status": "invited",
                "created_at": now,
                "invited_at": now
            }
            
            response = supabase.table("team_members").insert(member_data).execute()
            
            if response.data:
                member = response.data[0]
                logger.info(f"[TeamService] Invited {email} to team {team_id[:8]}...")
                
                # Send invite email (through email service)
                await self._send_invite_email(email, name or email.split("@")[0], team["name"], invite_token)
                
                return {
                    "success": True,
                    "member": member,
                    "invite_token": invite_token
                }
            
            return {"success": False, "error": "Failed to create invite", "code": "INSERT_FAILED"}
            
        except Exception as e:
            logger.error(f"[TeamService] invite_member failed: {e}")
            return {"success": False, "error": str(e), "code": "INTERNAL_ERROR"}
    
    async def _send_invite_email(
        self, 
        to_email: str, 
        name: str, 
        team_name: str, 
        invite_token: str
    ) -> bool:
        """
        Send team invitation email.
        
        For MVP, this just logs the invite link.
        """
        try:
            # Construct invite link
            from core.config import settings
            invite_link = f"{settings.APP_URL}/invite/{invite_token}"
            
            logger.info(
                f"[TeamService] 📧 INVITE EMAIL (MVP Console Output)\n"
                f"  To: {to_email}\n"
                f"  Name: {name}\n"
                f"  Team: {team_name}\n"
                f"  Link: {invite_link}"
            )
            
            # Send actual email
            from services.email import email_service
            email_service.send_team_invite(to_email, name, team_name, invite_link)
            
            return True
            
        except Exception as e:
            logger.warning(f"[TeamService] _send_invite_email failed: {e}")
            return False

    async def bulk_invite_csv(
        self, 
        owner_id: str, 
        csv_content: str
    ) -> Dict[str, Any]:
        """
        Bulk invite members from CSV content.
        
        **Enterprise Only**: Requires plan with team feature.
        
        Expected CSV format:
        email,role,name
        alice@example.com,editor,Alice
        bob@example.com,viewer,Bob
        
        Args:
            owner_id: The team owner's user UUID
            csv_content: Raw CSV string
            
        Returns:
            Dict with success/failure counts and details
        """
        import csv
        import io
        
        # Step 1: Check plan allows team feature
        allowed, error_msg, limits = await self._check_team_feature_access(owner_id)
        if not allowed:
            return {"success": False, "error": error_msg, "code": "UPGRADE_REQUIRED"}
        
        try:
            # Parse CSV
            reader = csv.DictReader(io.StringIO(csv_content))
            
            results = {
                "success": True,
                "total": 0,
                "invited": 0,
                "failed": 0,
                "errors": [],
                "members": []
            }
            
            for row in reader:
                results["total"] += 1
                
                email = row.get("email", "").strip()
                role = row.get("role", "viewer").strip().lower()
                name = row.get("name", "").strip()
                
                if not email or "@" not in email:
                    results["failed"] += 1
                    results["errors"].append({"email": email, "error": "Invalid email"})
                    continue
                
                # Invite each member
                invite_result = await self.invite_member(
                    owner_id=owner_id,
                    email=email,
                    role=role,
                    name=name if name else None
                )
                
                if invite_result.get("success"):
                    results["invited"] += 1
                    results["members"].append(invite_result.get("member", {}))
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "email": email,
                        "error": invite_result.get("error", "Unknown error")
                    })
            
            logger.info(
                f"[TeamService] Bulk invite: {results['invited']}/{results['total']} succeeded"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"[TeamService] bulk_invite_csv failed: {e}")
            return {"success": False, "error": str(e), "code": "PARSE_ERROR"}
    
    async def remove_member(
        self, 
        owner_id: str, 
        member_id: str,
        hard_delete: bool = False
    ) -> Dict[str, Any]:
        """
        Remove a member from the team.
        
        By default does soft delete (status='removed').
        
        Args:
            owner_id: The team owner's user UUID  
            member_id: The team_members row ID to remove
            hard_delete: If True, actually delete the row
            
        Returns:
            Dict with success status
        """
        try:
            supabase = get_supabase()
            
            # Verify the member belongs to owner's team
            member_response = supabase.table("team_members").select(
                "id, team_id, member_user_id, owner_user_id"
            ).eq("id", member_id).single().execute()
            
            if not member_response.data:
                return {"success": False, "error": "Member not found", "code": "NOT_FOUND"}
            
            member = member_response.data
            
            # Verify ownership
            if member.get("owner_user_id") != owner_id:
                return {"success": False, "error": "Not authorized", "code": "FORBIDDEN"}
            
            # Don't allow removing yourself (the owner)
            if member.get("member_user_id") == owner_id:
                return {"success": False, "error": "Cannot remove team owner", "code": "OWNER_PROTECTED"}
            
            member_user_id = member.get("member_user_id")
            
            if hard_delete:
                supabase.table("team_members").delete().eq("id", member_id).execute()
                logger.info(f"[TeamService] Hard deleted member {member_id}")
            else:
                supabase.table("team_members").update({
                    "status": "removed"
                }).eq("id", member_id).execute()
                logger.info(f"[TeamService] Soft deleted member {member_id}")
            
            # CRITICAL: Invalidate removed user's plan cache
            if member_user_id:
                self.invalidate_plan_cache(member_user_id)
                logger.info(f"[TeamService] Invalidated cache for removed user {member_user_id[:8]}...")
            
            return {"success": True, "member_id": member_id}
            
        except Exception as e:
            logger.error(f"[TeamService] remove_member failed: {e}")
            return {"success": False, "error": str(e), "code": "INTERNAL_ERROR"}


# Singleton instance
team_service = TeamService()

