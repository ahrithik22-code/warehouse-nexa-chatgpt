from __future__ import annotations

from django.db.models import Sum
from rest_framework import permissions, response, status, views

from inventory.models import Batch, Product, SellerboardMetrics

from .services import PlannerInputs, build_planner_outputs, compute_low_fba_flag


def _planner_inputs(product: Product) -> PlannerInputs:
    metrics: SellerboardMetrics | None = getattr(product, "sellerboardmetrics", None)
    adu = metrics.adu if metrics else 0
    fba_available = metrics.fba_available if metrics else 0
    fba_reserved = metrics.fba_reserved if metrics else 0
    fba_stock = fba_available + fba_reserved
    manual_orders = getattr(product, "manualorders", None)
    blr_on_hand = (
        Batch.objects.filter(sku=product, warehouse__warehouse_id="blr")
        .aggregate(total=Sum("current_qty"))
        .get("total")
        or 0
    )
    recommended = metrics.recommended_quantity if metrics else 0
    return PlannerInputs(
        product=product,
        adu=adu,
        blr_on_hand=blr_on_hand,
        fba_stock=fba_stock,
        manual_orders=manual_orders,
        sellerboard_recommended=recommended,
    )


class PlannerBaseView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]


class ReorderView(PlannerBaseView):
    def get(self, request):
        payload = []
        products = Product.objects.all().select_related("sellerboardmetrics", "manualorders")
        for product in products:
            inputs = _planner_inputs(product)
            outputs = build_planner_outputs(inputs)
            payload.append(
                {
                    "sku": product.sku,
                    "reorder_qty": outputs.reorder_qty,
                    "total_stock": inputs.blr_on_hand + inputs.fba_stock + (inputs.manual_orders.total() if inputs.manual_orders else 0),
                    "less_than_sellerboard": outputs.less_than_sellerboard_flag,
                }
            )
        return response.Response(payload, status=status.HTTP_200_OK)


class FBAView(PlannerBaseView):
    def get(self, request):
        payload = []
        products = Product.objects.all().select_related("sellerboardmetrics", "manualorders")
        for product in products:
            inputs = _planner_inputs(product)
            outputs = build_planner_outputs(inputs)
            payload.append(
                {
                    "sku": product.sku,
                    "send_to_fba": outputs.send_to_fba,
                    "low_fba_flag": outputs.low_fba_flag,
                    "blr_on_hand": inputs.blr_on_hand,
                    "fba_stock": inputs.fba_stock,
                }
            )
        return response.Response(payload, status=status.HTTP_200_OK)


class ExcessView(PlannerBaseView):
    def get(self, request):
        payload = []
        products = Product.objects.all().select_related("sellerboardmetrics", "manualorders")
        for product in products:
            inputs = _planner_inputs(product)
            outputs = build_planner_outputs(inputs)
            payload.append(
                {
                    "sku": product.sku,
                    "excess_units": outputs.excess_units,
                    "excess_value": str(outputs.excess_value),
                }
            )
        return response.Response(payload, status=status.HTTP_200_OK)


class FlagsView(PlannerBaseView):
    def get(self, request):
        payload = []
        products = Product.objects.all().select_related("sellerboardmetrics", "manualorders")
        for product in products:
            inputs = _planner_inputs(product)
            outputs = build_planner_outputs(inputs)
            payload.append(
                {
                    "sku": product.sku,
                    "less_than_sellerboard": outputs.less_than_sellerboard_flag,
                    "low_fba": outputs.low_fba_flag,
                }
            )
        return response.Response(payload, status=status.HTTP_200_OK)
