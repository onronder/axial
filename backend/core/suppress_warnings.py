"""
Suppress known deprecation warnings from third-party packages.

This module MUST be imported FIRST in main.py and celery_app.py
before any other imports to catch warnings from package initialization.

Known Suppressions:
- clamd: Uses deprecated pkg_resources API (not updated by maintainers)
"""
import warnings

# =============================================================================
# clamd pkg_resources Deprecation Warning
# =============================================================================
# The clamd package (ClamAV Python client) uses pkg_resources to get its version:
#   __version__ = __import__('pkg_resources').get_distribution('clamd').version
#
# pkg_resources was deprecated in setuptools 67.0 and is scheduled for removal.
# The maintainers haven't updated clamd to use importlib.metadata yet.
#
# This warning is safe to ignore - it's just a future compatibility notice.
# The functionality works correctly; only the version lookup method is deprecated.
#
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="clamd"
)

# Also catch the broader setuptools warning that may appear
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="pkg_resources"
)
