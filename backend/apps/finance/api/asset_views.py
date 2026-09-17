from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.authentication.exceptions import envelope_success
from apps.authentication.permissions.authenticated import IsApplicationUser
from apps.finance.api.views import ORG_HEADER, _org_action
from apps.finance.models import FixedAsset
from apps.finance.services.assets import capitalize, depreciate, dispose, register, write_down


def _asset(a: FixedAsset):
    return {
        "id": a.id,
        "number": a.number,
        "name": a.name,
        "cost": str(a.cost),
        "residual": str(a.residual),
        "accum": str(a.accum),
        "nbv": str(a.cost - a.accum),
        "life_months": a.life_months,
        "in_service_date": str(a.in_service_date),
        "status": a.status,
    }


class AssetListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        return envelope_success(request, {"items": [_asset(a) for a in FixedAsset.objects.filter(organization=org)]})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.document.post")
        asset, _journal = capitalize(
            user_id=user.id,
            org=org,
            payload=request.data,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, _asset(asset), http_status=201)


class AssetDepreciateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.document.post")
        charged = depreciate(
            user_id=user.id,
            org=org,
            through_date=request.data.get("through_date") or date.today().isoformat(),
            idempotency_key=request.headers.get("Idempotency-Key"),
            asset_id=request.data.get("asset_id"),
        )
        return envelope_success(request, {"charged": charged})


class AssetWriteDownView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, asset_id: str):
        user, org = _org_action(request, "finance.document.post")
        asset = write_down(
            user_id=user.id,
            org=org,
            asset_id=asset_id,
            amount=request.data.get("amount"),
            entry_date=request.data.get("entry_date") or date.today().isoformat(),
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, _asset(asset))


class AssetDisposeView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request, asset_id: str):
        user, org = _org_action(request, "finance.document.post")
        asset, _journal = dispose(
            user_id=user.id,
            org=org,
            asset_id=asset_id,
            entry_date=request.data.get("entry_date") or date.today().isoformat(),
            proceeds=request.data.get("proceeds") or 0,
            proceeds_account_id=request.data.get("proceeds_account_id"),
            gain_loss_account_id=request.data.get("gain_loss_account_id"),
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(request, _asset(asset))


class AssetRegisterView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        return envelope_success(request, register(org=org))
