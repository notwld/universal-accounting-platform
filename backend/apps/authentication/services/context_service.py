from apps.authentication.exceptions import AuthAPIError
from apps.authentication.services.cache_service import AuthCacheService
from apps.tenancy.models import Location, Membership, Organization


class ContextService:
    def __init__(self):
        self.cache = AuthCacheService()

    def resolve_defaults(self, user):
        membership = (
            Membership.objects.filter(user_id=user.id, status=Membership.Status.ACTIVE)
            .select_related("organization", "location")
            .order_by("created_at")
            .first()
        )
        if not membership:
            return None, None, []
        roles = membership.roles or ["member"]
        return membership.organization, membership.location, roles

    def validate_access(self, user, organization_id: str | None, location_id: str | None):
        if not organization_id:
            org, loc, roles = self.resolve_defaults(user)
            return org, loc, roles

        neg_key = f"ctxdeny:{user.id}:{organization_id}:{location_id or ''}"
        if self.cache.has_negative(neg_key):
            raise AuthAPIError(
                "organization_access_denied",
                "No active membership for organization",
            )

        cached = self.cache.get_context(
            user.id, organization_id, location_id or "", user.authorization_version
        )
        if cached:
            org = Organization.objects.filter(id=cached["organization_id"]).first()
            loc = (
                Location.objects.filter(id=cached["location_id"]).first()
                if cached.get("location_id")
                else None
            )
            return org, loc, cached.get("roles", [])

        lock_key = f"ctxfill:{user.id}:{organization_id}:{location_id or ''}:v{user.authorization_version}"

        def _fill():
            membership = (
                Membership.objects.filter(
                    user_id=user.id,
                    organization_id=organization_id,
                    status=Membership.Status.ACTIVE,
                )
                .select_related("organization", "location")
                .first()
            )
            if not membership:
                self.cache.set_negative(neg_key)
                raise AuthAPIError(
                    "organization_access_denied",
                    "No active membership for organization",
                )
            org = membership.organization
            loc = None
            if location_id:
                loc = Location.objects.filter(id=location_id, organization=org).first()
                if not loc:
                    raise AuthAPIError(
                        "location_access_denied",
                        "Location does not belong to organization",
                    )
                if membership.location_id and membership.location_id != location_id:
                    raise AuthAPIError(
                        "location_access_denied",
                        "No access to location",
                    )
            else:
                loc = membership.location
            roles = membership.roles or ["member"]
            self.cache.set_context(
                user.id,
                org.id,
                loc.id if loc else "",
                user.authorization_version,
                {
                    "organization_id": org.id,
                    "location_id": loc.id if loc else "",
                    "roles": roles,
                },
            )
            return org, loc, roles

        result = self.cache.with_stampede(lock_key, _fill)
        if result is None:
            # retry after wait
            cached = self.cache.get_context(
                user.id, organization_id, location_id or "", user.authorization_version
            )
            if cached:
                org = Organization.objects.filter(id=cached["organization_id"]).first()
                loc = (
                    Location.objects.filter(id=cached["location_id"]).first()
                    if cached.get("location_id")
                    else None
                )
                return org, loc, cached.get("roles", [])
            return _fill()
        return result

    def switch(self, user, organization_id: str, location_id: str | None):
        org, loc, roles = self.validate_access(user, organization_id, location_id)
        # MD: bump on authz-relevant change — switch validates new context membership
        user.authorization_version += 1
        user.save(update_fields=["authorization_version", "updated_at"])
        self.cache.invalidate_user(user.clerk_user_id)
        return org, loc, roles, user.authorization_version
