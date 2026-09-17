from contextlib import contextmanager

from django.db import transaction

from apps.authentication.exceptions import AuthAPIError
from apps.authentication.services.rls import set_rls_context


@contextmanager
def finance_tx(*, user_id: str, organization_id: str):
    if not user_id or not organization_id:
        raise AuthAPIError("missing_context", "Organization context required")
    with transaction.atomic():
        set_rls_context(user_id=user_id, organization_id=organization_id, location_id=None)
        yield
