"""
KVKK 2026 Granular Consent Management

Implements hierarchical consent management for KVKK (Turkish GDPR) compliance.
Supports organization, scope, and document-level consent controls.

Components:
- manager.py: Consent CRUD and evaluation engine
- policy.py: Policy evaluation with inheritance
- audit.py: Consent change audit logging
"""

from services.consent.manager import (
    ConsentManager,
    ConsentType,
    ConsentLevel,
    ConsentDecision,
)

__all__ = [
    'ConsentManager',
    'ConsentType',
    'ConsentLevel',
    'ConsentDecision',
]
