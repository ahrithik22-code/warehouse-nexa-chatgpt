from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from django.db import transaction

from .models import Batch, ComplianceError, MovementService, Product


@dataclass
class FBAPlanRow:
    sku: str
    quantity: int
    fc_code: str


@dataclass
class FBAExportRow:
    batch_id: str
    sku: str
    amazon_stn_price: str | None
    gst_rate_pct: str | None
    hsn_code: str | None
    product_name: str
    quantity_removed: int
    fc_code: str


class FBAAllocationService:
    def __init__(self, warehouse_id: str):
        self.warehouse_id = warehouse_id

    def import_plan(self, rows: Iterable[FBAPlanRow]) -> List[FBAExportRow]:
        export_rows: List[FBAExportRow] = []
        with transaction.atomic():
            for row in rows:
                product = Product.objects.get(sku=row.sku)
                warehouse_batches = (
                    Batch.objects.select_related('warehouse')
                    .filter(sku=product, warehouse__warehouse_id=self.warehouse_id)
                    .order_by('received_date')
                )
                first_batch = warehouse_batches.first()
                if not first_batch:
                    raise ValueError(f"No stock available for {row.sku}")
                allocated = MovementService.fifo_allocate(product, first_batch.warehouse, row.quantity)
                for allocation in allocated:
                    batch = allocation.batch
                    if batch.compliance_status != Batch.COMPLIANCE_COMPLETE:
                        raise ComplianceError(f"Batch {batch.batch_id} pending compliance")
                    export_rows.append(
                        FBAExportRow(
                            batch_id=batch.batch_id,
                            sku=batch.sku_id,
                            amazon_stn_price=str(batch.amazon_stn_price) if batch.amazon_stn_price is not None else None,
                            gst_rate_pct=str(batch.gst_rate_pct_override) if batch.gst_rate_pct_override is not None else None,
                            hsn_code=batch.sku.hsn_code,
                            product_name=batch.ewaybill_product_name or batch.sku.title,
                            quantity_removed=allocation.quantity,
                            fc_code=row.fc_code,
                        )
                    )
        return export_rows
