import pytest

from inventory.models import ManualOrders, Product
from planner.services import PlannerInputs, build_planner_outputs


@pytest.mark.django_db
def test_reorder_respects_moq_and_rounding():
    product = Product.objects.create(
        sku='SKU-PLAN',
        title='Planner Product',
        moq=100,
        order_round_multiple=50,
        safety_stock_days=0,
        fba_target_days=30,
    )
    manual = ManualOrders.objects.create(sku=product, ordered_1=10, ordered_2=0, ordered_3=0)
    inputs = PlannerInputs(
        product=product,
        adu=10,
        blr_on_hand=20,
        fba_stock=5,
        manual_orders=manual,
        sellerboard_recommended=0,
    )
    outputs = build_planner_outputs(inputs)
    assert outputs.reorder_qty >= product.moq
    assert outputs.reorder_qty % product.order_round_multiple == 0


@pytest.mark.django_db
def test_low_fba_flag_triggers():
    product = Product.objects.create(
        sku='SKU-FBA',
        title='Planner Product',
        fba_target_days=30,
    )
    inputs = PlannerInputs(
        product=product,
        adu=1,
        blr_on_hand=20,
        fba_stock=5,
        manual_orders=None,
        sellerboard_recommended=0,
    )
    outputs = build_planner_outputs(inputs)
    assert outputs.low_fba_flag is True
