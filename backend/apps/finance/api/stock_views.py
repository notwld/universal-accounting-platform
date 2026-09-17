from datetime import date

from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.authentication.exceptions import envelope_success
from apps.authentication.permissions.authenticated import IsApplicationUser
from apps.finance.api.views import ORG_HEADER, _org_action
from apps.finance.models import StockBalance, Warehouse
from apps.finance.services.stock import adjust_stock, default_warehouse, transfer_stock, valuation


class WarehouseListCreateView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.item.maintain")
        default_warehouse(org)
        items = [{"id": w.id, "name": w.name} for w in Warehouse.objects.filter(organization=org)]
        return envelope_success(request, {"items": items})

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        _, org = _org_action(request, "finance.item.maintain")
        name = (request.data.get("name") or "").strip() or "Main"
        wh, _ = Warehouse.objects.get_or_create(organization=org, name=name[:100])
        return envelope_success(request, {"id": wh.id, "name": wh.name}, http_status=201)


class StockBalanceListView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.item.maintain")
        items = [
            {
                "item_id": b.item_id,
                "warehouse_id": b.warehouse_id,
                "qty": str(b.qty),
                "value": str(b.value),
            }
            for b in StockBalance.objects.filter(organization=org)
        ]
        return envelope_success(request, {"items": items})


class StockAdjustView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.item.maintain")
        journal, item, wh = adjust_stock(
            user_id=user.id,
            org=org,
            warehouse_id=request.data.get("warehouse_id"),
            item_id=request.data.get("item_id"),
            quantity=request.data.get("quantity"),
            unit_cost=request.data.get("unit_cost"),
            entry_date=request.data.get("entry_date") or date.today().isoformat(),
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        return envelope_success(
            request, {"journal_id": journal.id, "item_id": item.id, "warehouse_id": wh.id}
        )


class StockTransferView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def post(self, request):
        user, org = _org_action(request, "finance.item.maintain")
        src, dst, item = transfer_stock(
            user_id=user.id,
            org=org,
            from_warehouse_id=request.data.get("from_warehouse_id"),
            to_warehouse_id=request.data.get("to_warehouse_id"),
            item_id=request.data.get("item_id"),
            quantity=request.data.get("quantity"),
            entry_date=request.data.get("entry_date") or date.today().isoformat(),
        )
        return envelope_success(
            request,
            {
                "from_warehouse_id": src.id,
                "to_warehouse_id": dst.id,
                "item_id": item.id,
            },
        )


class InventoryValuationView(APIView):
    permission_classes = [IsApplicationUser]

    @extend_schema(tags=["Finance"], parameters=[ORG_HEADER])
    def get(self, request):
        _, org = _org_action(request, "finance.report.view")
        return envelope_success(request, valuation(org=org))
