"""Service package — import submodules directly to avoid circular imports."""

__all__ = [
    "AuthCacheService",
    "BootstrapService",
    "ContextService",
    "IdentityService",
    "IdempotencyService",
    "SecurityService",
    "SessionService",
]


def __getattr__(name: str):
    if name == "AuthCacheService":
        from apps.authentication.services.cache_service import AuthCacheService

        return AuthCacheService
    if name == "BootstrapService":
        from apps.authentication.services.bootstrap_service import BootstrapService

        return BootstrapService
    if name == "IdempotencyService":
        from apps.authentication.services.bootstrap_service import IdempotencyService

        return IdempotencyService
    if name == "ContextService":
        from apps.authentication.services.context_service import ContextService

        return ContextService
    if name in ("IdentityService", "SecurityService"):
        from apps.authentication.services import security_service as ss

        return getattr(ss, name)
    if name == "SessionService":
        from apps.authentication.services.session_service import SessionService

        return SessionService
    raise AttributeError(name)
