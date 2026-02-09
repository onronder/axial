"""
Scope Guard Action Approval System

Human-in-the-loop approval workflow for destructive actions.
Implements cryptographic mandates for secure action authorization.

Components:
- state_machine.py: Approval state machine (pending → approved → executed)
- mandate.py: Cryptographic mandate generation and verification
- actions.py: Action type definitions and handlers
- executor.py: Approved action execution
"""

from services.scope_guard.mandate import (
    Mandate,
    MandateGenerator,
)
from services.scope_guard.state_machine import (
    ActionType,
    ApprovalState,
    ScopeGuardStateMachine,
)

__all__ = [
    'ScopeGuardStateMachine',
    'ApprovalState',
    'ActionType',
    'Mandate',
    'MandateGenerator',
]
