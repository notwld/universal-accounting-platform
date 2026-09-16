# Keep empty to avoid eager clerk import during DRF settings bootstrap.
__all__ = ["ClerkJWTAuthentication", "ClerkPrincipal"]


def __getattr__(name: str):
    if name in ("ClerkJWTAuthentication", "ClerkPrincipal"):
        from apps.authentication.authenticators.clerk import (
            ClerkJWTAuthentication,
            ClerkPrincipal,
        )

        return ClerkJWTAuthentication if name == "ClerkJWTAuthentication" else ClerkPrincipal
    raise AttributeError(name)
