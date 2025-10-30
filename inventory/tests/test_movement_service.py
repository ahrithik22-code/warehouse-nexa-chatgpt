import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from inventory.models import (
    Batch,
    ComplianceError,
    Movement,
    MovementLine,
    MovementService,
    NegativeStockError,
    Product,
    Supplier,
    Warehouse,
)


@pytest.mark.django_db
def test_commit_blocks_negative_stock():
    supplier = Supplier.objects.create(supplier_id='sup1', name='Supplier')
    product = Product.objects.create(sku='SKU1', title='Sample', supplier=supplier)
    warehouse = Warehouse.objects.create(warehouse_id='blr', name='Bangalore')
    batch = Batch.objects.create(
        batch_id='B1',
        sku=product,
        warehouse=warehouse,
        received_date=timezone.now().date(),
        starting_qty=10,
        current_qty=10,
        compliance_status=Batch.COMPLIANCE_COMPLETE,
    )
    user = get_user_model().objects.create_user(username='tester', password='pass')
    movement = Movement.objects.create(
        type=Movement.TYPE_FBA,
        status=Movement.STATUS_DRAFT,
        created_by=user,
    )
    MovementLine.objects.create(movement=movement, sku=product, batch=batch, quantity=15)

    with pytest.raises(NegativeStockError):
        MovementService.commit(movement)


@pytest.mark.django_db
def test_commit_blocks_pending_compliance():
    supplier = Supplier.objects.create(supplier_id='sup2', name='Supplier')
    product = Product.objects.create(sku='SKU2', title='Sample', supplier=supplier)
    warehouse = Warehouse.objects.create(warehouse_id='blr', name='Bangalore')
    batch = Batch.objects.create(
        batch_id='B2',
        sku=product,
        warehouse=warehouse,
        received_date=timezone.now().date(),
        starting_qty=10,
        current_qty=10,
        compliance_status=Batch.COMPLIANCE_PENDING,
    )
    user = get_user_model().objects.create_user(username='tester2', password='pass')
    movement = Movement.objects.create(
        type=Movement.TYPE_FBA,
        status=Movement.STATUS_DRAFT,
        created_by=user,
    )
    MovementLine.objects.create(movement=movement, sku=product, batch=batch, quantity=1)

    with pytest.raises(ComplianceError):
        MovementService.commit(movement)
