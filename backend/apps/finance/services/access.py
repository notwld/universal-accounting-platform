from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import FinanceGrant
from apps.tenancy.models import Membership


def has_finance_permission(user_id: str, organization_id: str, action: str) -> bool:
    membership = Membership.objects.filter(
        user_id=user_id,
        organization_id=organization_id,
        status=Membership.Status.ACTIVE,
    ).first()
    if not membership:
        return False
    grant = (
        FinanceGrant.objects.select_related("role")
        .filter(user_id=user_id, organization_id=organization_id)
        .first()
    )
    if not grant:
        return False
    return action in (grant.role.permissions or [])


def require_permission(user_id: str, organization_id: str, action: str):
    if not has_finance_permission(user_id, organization_id, action):
        raise AuthAPIError("permission_denied", "Insufficient finance permission")
