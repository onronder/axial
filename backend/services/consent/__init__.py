"""
GDPR/CCPA/KVKK 2026 Granular Consent Management

Implements hierarchical consent management for multi-jurisdictional compliance:
- GDPR Article 6/7: EU consent requirements
- CCPA 2026 ADMT: California Automated Decision-Making Technology opt-out
- KVKK Article 5: Turkish GDPR equivalent

Supports organization, scope, and document-level consent controls.

Components:
- manager.py: Consent CRUD and evaluation engine
- policy.py: Policy evaluation with inheritance
- audit.py: Consent change audit logging
"""

from services.consent.manager import (
    ConsentDecision,
    ConsentLevel,
    ConsentManager,
    ConsentType,
)

__all__ = [
    'ConsentManager',
    'ConsentType',
    'ConsentLevel',
    'ConsentDecision',
]
