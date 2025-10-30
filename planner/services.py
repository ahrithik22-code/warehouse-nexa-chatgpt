from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Avg

from inventory.models import Batch, ManualOrders, Product


@dataclass
class PlannerInputs:
    product: Product
    adu: float
    blr_on_hand: int
    fba_stock: int
    manual_orders: ManualOrders | None
    sellerboard_recommended: int


@dataclass
class PlannerOutputs:
    reorder_qty: int
    send_to_fba: int
    low_fba_flag: bool
    less_than_sellerboard_flag: bool
    excess_units: int
    excess_value: Decimal


def compute_china_target(product: Product, adu: float) -> int:
    months = product.months_rule_override or (4 if adu > 6 else 3)
    return int(adu * 30 * months + adu * product.safety_stock_days)


def compute_total_stock(blr_on_hand: int, fba_stock: int, manual_orders: ManualOrders | None) -> int:
    ordered = manual_orders.total() if manual_orders else 0
    return blr_on_hand + fba_stock + ordered


def round_to_multiple(value: int, multiple: int) -> int:
    if multiple <= 1:
        return value
    remainder = value % multiple
    return value if remainder == 0 else value + (multiple - remainder)


def compute_reorder_qty(inputs: PlannerInputs) -> int:
    product = inputs.product
    if product.status == Product.STATUS_DISCONTINUED:
        return 0
    target = compute_china_target(product, inputs.adu)
    total_stock = compute_total_stock(inputs.blr_on_hand, inputs.fba_stock, inputs.manual_orders)
    reorder = max(0, target - total_stock)
    reorder = round_to_multiple(reorder, product.order_round_multiple)
    if reorder > 0 and product.moq:
        reorder = max(reorder, product.moq)
    return reorder


def compute_send_to_fba(product: Product, adu: float, fba_stock: int, blr_on_hand: int, *, send_all: bool = False) -> int:
    if send_all and product.status == Product.STATUS_DISCONTINUED:
        return blr_on_hand
    if blr_on_hand <= 0:
        return 0
    target_days = product.fba_target_days
    n = adu * target_days
    send = max(0, int(n - fba_stock))
    if send > blr_on_hand:
        send = blr_on_hand
    return send


def compute_low_fba_flag(fba_stock: int, blr_on_hand: int) -> bool:
    return fba_stock < 10 and blr_on_hand > 5


def compute_less_than_sellerboard(inputs: PlannerInputs) -> bool:
    if inputs.product.status == Product.STATUS_DISCONTINUED:
        return False
    total_stock = compute_total_stock(inputs.blr_on_hand, inputs.fba_stock, inputs.manual_orders)
    diff = inputs.sellerboard_recommended - total_stock
    return diff > 0


def compute_excess(product: Product, adu: float, blr_on_hand: int, fba_stock: int) -> tuple[int, Decimal]:
    threshold = int(adu * 120)
    combined = blr_on_hand + fba_stock
    if combined <= threshold:
        return 0, Decimal("0")
    excess_units = combined - threshold
    avg_cost = Batch.objects.filter(sku=product).aggregate(avg=Avg("unit_cost")).get("avg")
    avg_cost_decimal = Decimal(avg_cost or 0)
    return excess_units, avg_cost_decimal * excess_units


def build_planner_outputs(inputs: PlannerInputs) -> PlannerOutputs:
    reorder_qty = compute_reorder_qty(inputs)
    send_to_fba = compute_send_to_fba(inputs.product, inputs.adu, inputs.fba_stock, inputs.blr_on_hand)
    low_fba_flag = compute_low_fba_flag(inputs.fba_stock, inputs.blr_on_hand)
    less_than_sellerboard_flag = compute_less_than_sellerboard(inputs)
    excess_units, excess_value = compute_excess(inputs.product, inputs.adu, inputs.blr_on_hand, inputs.fba_stock)
    return PlannerOutputs(
        reorder_qty=reorder_qty,
        send_to_fba=send_to_fba,
        low_fba_flag=low_fba_flag,
        less_than_sellerboard_flag=less_than_sellerboard_flag,
        excess_units=excess_units,
        excess_value=excess_value,
    )
