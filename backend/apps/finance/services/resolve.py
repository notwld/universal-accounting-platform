from apps.authentication.exceptions import AuthAPIError


def org_get(model, org, pk, msg="Not found"):
    if not pk:
        raise AuthAPIError("cross_organization", msg)
    obj = model.objects.filter(pk=pk, organization=org).first()
    if not obj:
        raise AuthAPIError("cross_organization", msg)
    return obj


def org_get_optional(model, org, pk, msg="Not found"):
    if not pk:
        return None
    return org_get(model, org, pk, msg)


def currency_get(code):
    from apps.finance.models import Currency

    obj = Currency.objects.filter(pk=code).first()
    if not obj:
        raise AuthAPIError("validation_error", "Currency not found")
    return obj
