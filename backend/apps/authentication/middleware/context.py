from django.utils.deprecation import MiddlewareMixin

from apps.authentication.exceptions import AuthAPIError
from apps.authentication.models import AuthUser
from apps.authentication.services.context_service import ContextService
from apps.authentication.services.rls import clear_rls_context, set_rls_context


class TenantContextMiddleware(MiddlewareMixin):
    """
    Attach org/location headers; validate membership BEFORE RLS (MD §38/#42/#89).
    Unvalidated headers never become trusted context / RLS tenant vars.
    """

    def process_request(self, request):
        request.organization_id = request.headers.get("X-Organization-ID") or None
        request.location_id = request.headers.get("X-Location-ID") or None
        request.organization = None
        request.location = None
        request.authorization = None
        request.trusted_context = False
        request.context_error = None

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = getattr(request, "user", None)
        if not isinstance(user, AuthUser) or not user.id:
            clear_rls_context()
            return None

        org_id = getattr(request, "organization_id", None)
        loc_id = getattr(request, "location_id", None)
        if org_id or loc_id:
            try:
                org, loc, roles = ContextService().validate_access(user, org_id, loc_id)
                request.organization = org
                request.location = loc
                request.authorization = {
                    "version": user.authorization_version,
                    "roles": roles,
                }
                request.trusted_context = True
                set_rls_context(
                    user_id=user.id,
                    organization_id=org.id if org else None,
                    location_id=loc.id if loc else None,
                )
            except AuthAPIError as exc:
                # Do not set tenant RLS from untrusted headers
                request.context_error = exc
                clear_rls_context()
                set_rls_context(user_id=user.id, organization_id=None, location_id=None)
        else:
            set_rls_context(user_id=user.id, organization_id=None, location_id=None)
        return None
