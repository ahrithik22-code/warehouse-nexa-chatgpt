from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from io import StringIO
from typing import Iterable, List

from django.db import transaction

from inventory.models import Batch, ManualOrders, Product, SellerboardMetrics


@dataclass
class ReceivingRecord:
    date: datetime
    batch_id: str
    sku: str
    quantity_received: int
    warehouse_id: str
    metadata: dict


class ReceivingImportService:
    REQUIRED_FIELDS = {
        'date',
        'batch_id',
        'sku',
        'quantity_received',
        'warehouse_id',
    }

    def parse(self, raw: str) -> List[ReceivingRecord]:
        reader = csv.DictReader(StringIO(raw))
        records: List[ReceivingRecord] = []
        for row in reader:
            missing = self.REQUIRED_FIELDS - row.keys()
            if missing:
                raise ValueError(f"Missing columns: {missing}")
            metadata = {k: v for k, v in row.items() if k not in self.REQUIRED_FIELDS}
            records.append(
                ReceivingRecord(
                    date=datetime.fromisoformat(row['date']),
                    batch_id=row['batch_id'],
                    sku=row['sku'],
                    quantity_received=int(row['quantity_received']),
                    warehouse_id=row['warehouse_id'],
                    metadata=metadata,
                )
            )
        return records

    @transaction.atomic
    def apply(self, records: Iterable[ReceivingRecord]):
        for record in records:
            batch, created = Batch.objects.get_or_create(
                batch_id=record.batch_id,
                defaults={
                    'sku_id': record.sku,
                    'warehouse_id': record.warehouse_id,
                    'received_date': record.date,
                    'starting_qty': record.quantity_received,
                    'current_qty': record.quantity_received,
                },
            )
            if not created:
                continue
            for decimal_field in (
                'amazon_stn_price',
                'ewaybill_price',
                'gst_rate_pct',
                'base_cost_inr',
                'base_cost_rmb',
                'base_cost_usd',
            ):
                raw_value = record.metadata.get(decimal_field)
                if raw_value in (None, ''):
                    value = None
                else:
                    value = Decimal(str(raw_value))
                setattr(batch, decimal_field if decimal_field != 'gst_rate_pct' else 'gst_rate_pct_override', value)
            batch.ewaybill_product_name = record.metadata.get('product_name') or batch.ewaybill_product_name
            pieces_per_carton = record.metadata.get('pieces_per_carton')
            batch.pieces_per_carton = int(pieces_per_carton) if pieces_per_carton else batch.pieces_per_carton
            accession = record.metadata.get('accession')
            if accession:
                batch.accession = accession
            batch.save()


SEEN_SELLERBOARD_HASHES: set[str] = set()


class SellerboardImportService:
    REQUIRED_FIELDS = {
        'sku',
        'Estimated Sales Velocity',
        'FBA/FBM Stock',
        'Reserved',
    }

    def parse(self, raw: str, *, as_of: datetime | None = None) -> list[SellerboardMetrics]:
        content_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        if content_hash in SEEN_SELLERBOARD_HASHES:
            return []
        reader = csv.DictReader(StringIO(raw))
        metrics_list = []
        for row in reader:
            missing = self.REQUIRED_FIELDS - row.keys()
            if missing:
                raise ValueError(f"Missing columns: {missing}")
            sku = row['sku']
            product, _ = Product.objects.get_or_create(sku=sku, defaults={'title': sku})
            metrics, _ = SellerboardMetrics.objects.get_or_create(sku=product)
            metrics.adu = float(row['Estimated Sales Velocity'] or 0)
            metrics.fba_available = int(row['FBA/FBM Stock'] or 0)
            metrics.fba_reserved = int(row['Reserved'] or 0)
            metrics.as_of_ts = as_of or datetime.utcnow()
            metrics.recommended_quantity = int(row.get('Recommended quantity for reordering') or 0)
            metrics.save()
            metrics_list.append(metrics)
        SEEN_SELLERBOARD_HASHES.add(content_hash)
        return metrics_list


class ManualOrdersImportService:
    REQUIRED_FIELDS = {'sku', 'ordered_1', 'ordered_2', 'ordered_3'}

    def parse(self, raw: str):
        reader = csv.DictReader(StringIO(raw))
        for row in reader:
            missing = self.REQUIRED_FIELDS - row.keys()
            if missing:
                raise ValueError(f"Missing columns: {missing}")
            product, _ = Product.objects.get_or_create(sku=row['sku'], defaults={'title': row['sku']})
            manual, _ = ManualOrders.objects.get_or_create(sku=product)
            manual.ordered_1 = int(row['ordered_1'] or 0)
            manual.ordered_2 = int(row['ordered_2'] or 0)
            manual.ordered_3 = int(row['ordered_3'] or 0)
            manual.save()
