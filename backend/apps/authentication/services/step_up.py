import time

from apps.authentication.exceptions import AuthAPIError

STEP_UP_SECONDS = 300


def require_step_up(request):
    claims = getattr(request, "clerk_claims", None) or {}
    issued = claims.get("auth_time") or claims.get("iat")
    if issued is None:
        raise AuthAPIError("step_up_required", "Recent authentication required")
    if time.time() - int(issued) > STEP_UP_SECONDS:
        raise AuthAPIError("step_up_required", "Recent authentication required")
