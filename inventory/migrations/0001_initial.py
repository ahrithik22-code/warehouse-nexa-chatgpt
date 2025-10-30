from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import django.utils.timezone


def create_stockledger_partition(apps, schema_editor):
    schema_editor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_stockledger (
            ledger_id BIGSERIAL PRIMARY KEY,
            ts timestamptz NOT NULL DEFAULT NOW(),
            movement_type varchar(16) NOT NULL,
            movement_id bigint NOT NULL REFERENCES inventory_movement(movement_id) ON DELETE CASCADE,
            warehouse_id varchar(32) NOT NULL REFERENCES inventory_warehouse(warehouse_id) ON DELETE RESTRICT,
            sku_id varchar(64) NOT NULL REFERENCES inventory_product(sku) ON DELETE RESTRICT,
            batch_id varchar(64) NOT NULL REFERENCES inventory_batch(batch_id) ON DELETE RESTRICT,
            qty_in integer NOT NULL DEFAULT 0,
            qty_out integer NOT NULL DEFAULT 0,
            unit_cost numeric(10,2),
            user_id integer NOT NULL REFERENCES auth_user(id) ON DELETE RESTRICT,
            memo text
        ) PARTITION BY RANGE (ts);
        """
    )
    schema_editor.execute(
        """
        DO $$
        DECLARE
            start_month date := date_trunc('month', now())::date;
            stop_month date := start_month + interval '12 months';
            cur date := start_month;
            partition_name text;
        BEGIN
            WHILE cur < stop_month LOOP
                partition_name := format('inventory_stockledger_%s', to_char(cur, 'YYYYMM'));
                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %s PARTITION OF inventory_stockledger
                     FOR VALUES FROM (%L) TO (%L);',
                    partition_name,
                    cur,
                    cur + interval '1 month'
                );
                cur := cur + interval '1 month';
            END LOOP;
        END$$;
        """
    )


def drop_stockledger_partition(apps, schema_editor):
    schema_editor.execute("DROP TABLE IF EXISTS inventory_stockledger CASCADE;")


def create_rls_policies(apps, schema_editor):
    schema_editor.execute("ALTER TABLE inventory_batch ENABLE ROW LEVEL SECURITY;")
    schema_editor.execute("ALTER TABLE inventory_batch FORCE ROW LEVEL SECURITY;")
    schema_editor.execute(
        """
        CREATE POLICY IF NOT EXISTS batch_brand_scope ON inventory_batch
        USING (
            EXISTS (
                SELECT 1 FROM auth_user_groups aug
                JOIN auth_group_permissions agp ON agp.group_id = aug.group_id
                JOIN auth_permission ap ON ap.id = agp.permission_id
                WHERE aug.user_id = current_setting('app.current_user_id')::int
            )
        );
        """
    )


def drop_rls_policies(apps, schema_editor):
    schema_editor.execute("DROP POLICY IF EXISTS batch_brand_scope ON inventory_batch;")


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('supplier_id', models.CharField(max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('contact', models.CharField(blank=True, max_length=255)),
                ('default_lead_time_days', models.PositiveIntegerField(default=30)),
                ('default_moq', models.PositiveIntegerField(default=0)),
                ('default_round_multiple', models.PositiveIntegerField(default=1)),
            ],
            options={'ordering': ('name',)},
        ),
        migrations.CreateModel(
            name='Warehouse',
            fields=[
                ('warehouse_id', models.CharField(max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('address', models.TextField(blank=True)),
            ],
            options={'ordering': ('name',)},
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('sku', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('hsn_code', models.CharField(blank=True, max_length=64)),
                ('gst_rate_pct', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('brand', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(choices=[('active', 'Active'), ('discontinued', 'Discontinued')], default='active', max_length=16)),
                ('moq', models.PositiveIntegerField(default=0)),
                ('order_round_multiple', models.PositiveIntegerField(default=1)),
                ('lead_time_days', models.PositiveIntegerField(default=30)),
                ('safety_stock_days', models.PositiveIntegerField(default=0)),
                ('fba_target_days', models.PositiveIntegerField(default=30)),
                ('months_rule_override', models.PositiveIntegerField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('supplier', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='inventory.supplier')),
            ],
            options={'ordering': ('sku',)},
        ),
        migrations.CreateModel(
            name='ProductFlags',
            fields=[
                ('sku', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='inventory.product')),
                ('vero_flag', models.BooleanField(default=False)),
                ('can_send_to_fba', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='ManualOrders',
            fields=[
                ('sku', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='inventory.product')),
                ('ordered_1', models.PositiveIntegerField(default=0)),
                ('ordered_2', models.PositiveIntegerField(default=0)),
                ('ordered_3', models.PositiveIntegerField(default=0)),
                ('notes', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Batch',
            fields=[
                ('batch_id', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('received_date', models.DateField(default=django.utils.timezone.now)),
                ('supplier_batch_no', models.CharField(blank=True, max_length=128)),
                ('unit_cost', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('starting_qty', models.PositiveIntegerField()),
                ('current_qty', models.IntegerField()),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('gst_rate_pct_override', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('accession', models.CharField(blank=True, max_length=128)),
                ('amazon_stn_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('ewaybill_product_name', models.CharField(blank=True, max_length=255)),
                ('ewaybill_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('pieces_per_carton', models.PositiveIntegerField(blank=True, null=True)),
                ('base_cost_inr', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('base_cost_rmb', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('base_cost_usd', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('compliance_status', models.CharField(choices=[('pending', 'Pending'), ('complete', 'Complete')], default='pending', max_length=16)),
                ('sku', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.product')),
                ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.warehouse')),
            ],
            options={'ordering': ('sku', '-received_date')},
        ),
        migrations.CreateModel(
            name='Movement',
            fields=[
                ('movement_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('ts', models.DateTimeField(default=django.utils.timezone.now)),
                ('type', models.CharField(choices=[('receipt', 'Receipt'), ('transfer', 'Transfer'), ('fba', 'FBA'), ('adjustment', 'Adjustment'), ('scrap', 'Scrap'), ('return', 'Return')], max_length=16)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('committed', 'Committed'), ('cancelled', 'Cancelled')], default='draft', max_length=16)),
                ('channel', models.CharField(blank=True, max_length=32)),
                ('external_ref', models.CharField(blank=True, max_length=128)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movements_approved', to=settings.AUTH_USER_MODEL)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movements_created', to=settings.AUTH_USER_MODEL)),
                ('from_warehouse', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movement_from', to='inventory.warehouse')),
                ('to_warehouse', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movement_to', to='inventory.warehouse')),
            ],
            options={'ordering': ('-ts',)},
        ),
        migrations.CreateModel(
            name='MovementLine',
            fields=[
                ('movement_line_id', models.BigAutoField(primary_key=True, serialize=False)),
                ('quantity', models.PositiveIntegerField()),
                ('note', models.TextField(blank=True)),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.batch')),
                ('movement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='inventory.movement')),
                ('sku', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.product')),
            ],
        ),
        migrations.AddConstraint(
            model_name='movementline',
            constraint=models.UniqueConstraint(fields=('movement', 'sku', 'batch'), name='uniq_movement_sku_batch'),
        ),
        migrations.AddIndex(
            model_name='movementline',
            index=models.Index(fields=['movement'], name='inventory_movement_idx'),
        ),
        migrations.AddIndex(
            model_name='batch',
            index=models.Index(fields=['warehouse', 'sku'], name='inventory_batch_wh_sku'),
        ),
        migrations.AddIndex(
            model_name='batch',
            index=models.Index(fields=['sku', 'received_date'], name='inventory_batch_sku_received'),
        ),
        migrations.CreateModel(
            name='ChannelInventory',
            fields=[
                ('sku', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='inventory.product')),
                ('channel', models.CharField(default='amazon_fba', max_length=32)),
                ('available', models.PositiveIntegerField(default=0)),
                ('inbound_working', models.PositiveIntegerField(default=0)),
                ('inbound_shipped', models.PositiveIntegerField(default=0)),
                ('inbound_receiving', models.PositiveIntegerField(default=0)),
                ('reserved', models.PositiveIntegerField(default=0)),
                ('as_of_ts', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='SellerboardMetrics',
            fields=[
                ('sku', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='inventory.product')),
                ('adu', models.FloatField(default=0.0)),
                ('fba_available', models.IntegerField(default=0)),
                ('fba_reserved', models.IntegerField(default=0)),
                ('less_than_recommended', models.BooleanField(default=False)),
                ('recommended_quantity', models.IntegerField(default=0)),
                ('as_of_ts', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='PlannerSnapshot',
            fields=[
                ('sku', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='inventory.product')),
                ('blr_on_hand', models.IntegerField(default=0)),
                ('fba_stock', models.IntegerField(default=0)),
                ('ordered_1', models.IntegerField(default=0)),
                ('ordered_2', models.IntegerField(default=0)),
                ('ordered_3', models.IntegerField(default=0)),
                ('reorder_qty', models.IntegerField(default=0)),
                ('send_to_fba', models.IntegerField(default=0)),
                ('low_fba_flag', models.BooleanField(default=False)),
                ('less_than_sellerboard_flag', models.BooleanField(default=False)),
                ('excess_units', models.IntegerField(default=0)),
                ('excess_value', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('as_of_ts', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={'db_table': 'planner_snapshot'},
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='StockLedger',
                    fields=[
                        ('ledger_id', models.BigAutoField(primary_key=True, serialize=False)),
                        ('ts', models.DateTimeField(default=django.utils.timezone.now)),
                        ('movement_type', models.CharField(max_length=16)),
                        ('qty_in', models.IntegerField(default=0)),
                        ('qty_out', models.IntegerField(default=0)),
                        ('unit_cost', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                        ('memo', models.TextField(blank=True)),
                        ('movement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='inventory.movement')),
                        ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.warehouse')),
                        ('sku', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.product')),
                        ('batch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.batch')),
                        ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                    ],
                    options={
                        'db_table': 'inventory_stockledger',
                        'managed': False,
                    },
                ),
            ],
        ),
        migrations.RunPython(create_stockledger_partition, reverse_code=drop_stockledger_partition),
        migrations.RunPython(create_rls_policies, reverse_code=drop_rls_policies),
    ]
