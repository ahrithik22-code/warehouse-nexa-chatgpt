from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Optional

from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.utils import timezone


class Supplier(models.Model):
    supplier_id = models.CharField(primary_key=True, max_length=32)
    name = models.CharField(max_length=255)
    contact = models.CharField(max_length=255, blank=True)
    default_lead_time_days = models.PositiveIntegerField(default=30)
    default_moq = models.PositiveIntegerField(default=0)
    default_round_multiple = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Warehouse(models.Model):
    warehouse_id = models.CharField(primary_key=True, max_length=32)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_DISCONTINUED = "discontinued"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_DISCONTINUED, "Discontinued"),
    ]

    sku = models.CharField(primary_key=True, max_length=64)
    title = models.CharField(max_length=255)
    hsn_code = models.CharField(max_length=64, blank=True)
    gst_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    brand = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    moq = models.PositiveIntegerField(default=0)
    order_round_multiple = models.PositiveIntegerField(default=1)
    lead_time_days = models.PositiveIntegerField(default=30)
    safety_stock_days = models.PositiveIntegerField(default=0)
    fba_target_days = models.PositiveIntegerField(default=30)
    months_rule_override = models.PositiveIntegerField(null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("sku",)

    def __str__(self) -> str:
        return f"{self.sku} - {self.title}"


class ProductFlags(models.Model):
    sku = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True)
    vero_flag = models.BooleanField(default=False)
    can_send_to_fba = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Flags<{self.sku_id}>"


class ManualOrders(models.Model):
    sku = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True)
    ordered_1 = models.PositiveIntegerField(default=0)
    ordered_2 = models.PositiveIntegerField(default=0)
    ordered_3 = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    def total(self) -> int:
        return self.ordered_1 + self.ordered_2 + self.ordered_3


class Batch(models.Model):
    COMPLIANCE_PENDING = "pending"
    COMPLIANCE_COMPLETE = "complete"
    COMPLIANCE_CHOICES = [
        (COMPLIANCE_PENDING, "Pending"),
        (COMPLIANCE_COMPLETE, "Complete"),
    ]

    batch_id = models.CharField(primary_key=True, max_length=64)
    sku = models.ForeignKey(Product, on_delete=models.PROTECT)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    received_date = models.DateField(default=timezone.now)
    supplier_batch_no = models.CharField(max_length=128, blank=True)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    starting_qty = models.PositiveIntegerField()
    current_qty = models.IntegerField()
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    gst_rate_pct_override = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    accession = models.CharField(max_length=128, blank=True)
    amazon_stn_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ewaybill_product_name = models.CharField(max_length=255, blank=True)
    ewaybill_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pieces_per_carton = models.PositiveIntegerField(null=True, blank=True)
    base_cost_inr = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    base_cost_rmb = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    base_cost_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    compliance_status = models.CharField(max_length=16, choices=COMPLIANCE_CHOICES, default=COMPLIANCE_PENDING)

    class Meta:
        indexes = [
            models.Index(fields=("warehouse", "sku")),
            models.Index(fields=("sku", "received_date")),
        ]
        ordering = ("sku", "-received_date")

    def __str__(self) -> str:
        return f"Batch<{self.batch_id}>"

    def is_compliant(self) -> bool:
        required_fields = [
            "gst_rate_pct_override",
            "accession",
            "amazon_stn_price",
            "ewaybill_product_name",
            "ewaybill_price",
            "pieces_per_carton",
            "base_cost_inr",
            "base_cost_rmb",
            "base_cost_usd",
        ]
        for field in required_fields:
            value = getattr(self, field)
            if value in (None, ""):
                return False
        return True


class Movement(models.Model):
    TYPE_RECEIPT = "receipt"
    TYPE_TRANSFER = "transfer"
    TYPE_FBA = "fba"
    TYPE_ADJUSTMENT = "adjustment"
    TYPE_SCRAP = "scrap"
    TYPE_RETURN = "return"

    TYPE_CHOICES = [
        (TYPE_RECEIPT, "Receipt"),
        (TYPE_TRANSFER, "Transfer"),
        (TYPE_FBA, "FBA"),
        (TYPE_ADJUSTMENT, "Adjustment"),
        (TYPE_SCRAP, "Scrap"),
        (TYPE_RETURN, "Return"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_COMMITTED = "committed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_COMMITTED, "Committed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    movement_id = models.BigAutoField(primary_key=True)
    ts = models.DateTimeField(default=timezone.now)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    from_warehouse = models.ForeignKey(Warehouse, null=True, blank=True, on_delete=models.PROTECT, related_name="movement_from")
    to_warehouse = models.ForeignKey(Warehouse, null=True, blank=True, on_delete=models.PROTECT, related_name="movement_to")
    channel = models.CharField(max_length=32, blank=True)
    external_ref = models.CharField(max_length=128, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movements_created")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movements_approved", null=True, blank=True)

    class Meta:
        ordering = ("-ts",)

    def __str__(self) -> str:
        return f"Movement<{self.movement_id}>"


class MovementLine(models.Model):
    movement_line_id = models.BigAutoField(primary_key=True)
    movement = models.ForeignKey(Movement, on_delete=models.CASCADE, related_name="lines")
    sku = models.ForeignKey(Product, on_delete=models.PROTECT)
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("movement", "sku", "batch"), name="uniq_movement_sku_batch"),
        ]
        indexes = [
            models.Index(fields=("movement",)),
        ]


class StockLedger(models.Model):
    ledger_id = models.BigAutoField(primary_key=True)
    ts = models.DateTimeField(default=timezone.now)
    movement_type = models.CharField(max_length=16)
    movement = models.ForeignKey(Movement, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    sku = models.ForeignKey(Product, on_delete=models.PROTECT)
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT)
    qty_in = models.IntegerField(default=0)
    qty_out = models.IntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    memo = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("warehouse", "sku")),
            models.Index(fields=("sku", "ts")),
        ]
        ordering = ("-ts",)
        db_table = "inventory_stockledger"


class ChannelInventory(models.Model):
    sku = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True)
    channel = models.CharField(max_length=32, default="amazon_fba")
    available = models.PositiveIntegerField(default=0)
    inbound_working = models.PositiveIntegerField(default=0)
    inbound_shipped = models.PositiveIntegerField(default=0)
    inbound_receiving = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    as_of_ts = models.DateTimeField(default=timezone.now)


class SellerboardMetrics(models.Model):
    sku = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True)
    adu = models.FloatField(default=0.0)
    fba_available = models.IntegerField(default=0)
    fba_reserved = models.IntegerField(default=0)
    less_than_recommended = models.BooleanField(default=False)
    recommended_quantity = models.IntegerField(default=0)
    as_of_ts = models.DateTimeField(default=timezone.now)


@dataclass
class AllocationLine:
    batch: Batch
    quantity: int
    reason: Optional[str] = None


class AllocationError(Exception):
    pass


class ComplianceError(AllocationError):
    pass


class NegativeStockError(AllocationError):
    pass


class MovementService:
    """Service layer for creating and committing movements."""

    @staticmethod
    def create_receipt(
        *,
        movement: Movement,
        receipt_lines: Iterable[dict],
    ) -> Movement:
        for line in receipt_lines:
            quantity = int(line["quantity"])
            received_date = line.get("received_date", timezone.now().date())
            if isinstance(received_date, str):
                received_date = timezone.datetime.fromisoformat(received_date).date()
            batch, created = Batch.objects.get_or_create(
                batch_id=line["batch_id"],
                defaults={
                    "sku_id": line["sku_id"],
                    "warehouse_id": line["warehouse_id"],
                    "received_date": received_date,
                    "starting_qty": quantity,
                    "current_qty": quantity,
                    "compliance_status": Batch.COMPLIANCE_PENDING,
                },
            )
            if not created:
                raise IntegrityError(f"Batch {batch.batch_id} already exists")
            MovementLine.objects.create(
                movement=movement,
                sku_id=line["sku_id"],
                batch=batch,
                quantity=quantity,
                note=line.get("note", ""),
            )
        return movement

    @staticmethod
    def _validate_compliance(lines: Iterable[AllocationLine]):
        for line in lines:
            if line.batch.compliance_status != Batch.COMPLIANCE_COMPLETE:
                raise ComplianceError(f"Batch {line.batch.batch_id} is pending compliance")

    @staticmethod
    def fifo_allocate(sku: Product, warehouse: Warehouse, quantity: int) -> list[AllocationLine]:
        if quantity <= 0:
            return []
        batches = (
            Batch.objects.select_for_update()
            .filter(sku=sku, warehouse=warehouse, current_qty__gt=0)
            .order_by("received_date", "batch_id")
        )
        allocated: list[AllocationLine] = []
        remaining = quantity
        for batch in batches:
            take = min(batch.current_qty, remaining)
            if take <= 0:
                continue
            allocated.append(AllocationLine(batch=batch, quantity=take))
            remaining -= take
            if remaining <= 0:
                break
        if remaining > 0:
            raise NegativeStockError("Not enough stock for allocation")
        MovementService._validate_compliance(allocated)
        return allocated

    @staticmethod
    def commit(movement: Movement):
        if movement.status != Movement.STATUS_DRAFT:
            raise AllocationError("Movement already processed")
        with transaction.atomic():
            now = timezone.now()
            ledger_entries = []
            for line in movement.lines.select_related("batch", "movement", "sku"):
                batch = line.batch
                if movement.type != Movement.TYPE_RECEIPT:
                    MovementService._validate_compliance([AllocationLine(batch=batch, quantity=line.quantity)])
                if movement.type == Movement.TYPE_RECEIPT:
                    batch.current_qty = models.F("current_qty") + line.quantity
                else:
                    batch.current_qty = models.F("current_qty") - line.quantity
                batch.save(update_fields=["current_qty"])
                batch.refresh_from_db(fields=["current_qty"])
                if batch.current_qty < 0:
                    raise NegativeStockError(f"Negative stock for batch {batch.batch_id}")
                qty_in = line.quantity if movement.type == Movement.TYPE_RECEIPT else 0
                qty_out = line.quantity if movement.type != Movement.TYPE_RECEIPT else 0
                ledger_entries.append(
                    StockLedger(
                        ts=now,
                        movement_type=movement.type,
                        movement=movement,
                        warehouse=batch.warehouse,
                        sku=batch.sku,
                        batch=batch,
                        qty_in=qty_in,
                        qty_out=qty_out,
                        unit_cost=batch.unit_cost,
                        user=movement.created_by,
                        memo=line.note,
                    )
                )
            StockLedger.objects.bulk_create(ledger_entries)
            movement.status = Movement.STATUS_COMMITTED
            movement.ts = now
            movement.save(update_fields=["status", "ts"])


class PlannerSnapshot(models.Model):
    sku = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True)
    blr_on_hand = models.IntegerField(default=0)
    fba_stock = models.IntegerField(default=0)
    ordered_1 = models.IntegerField(default=0)
    ordered_2 = models.IntegerField(default=0)
    ordered_3 = models.IntegerField(default=0)
    reorder_qty = models.IntegerField(default=0)
    send_to_fba = models.IntegerField(default=0)
    low_fba_flag = models.BooleanField(default=False)
    less_than_sellerboard_flag = models.BooleanField(default=False)
    excess_units = models.IntegerField(default=0)
    excess_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    as_of_ts = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "planner_snapshot"
