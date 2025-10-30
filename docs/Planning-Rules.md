# Planning Rules

## China Reorder

* **China target (K)** = `adu * 30 * months + adu * safety_stock_days` where `months = months_rule_override or (4 if adu > 6 else 3)`.
* **Total stock (H)** = `blr_on_hand + fba_stock + ordered_1 + ordered_2 + ordered_3`.
* **Reorder quantity** = round up `max(0, K - H)` to `order_round_multiple` and enforce `moq` if the result is positive.
* Discontinued products never reorder.

## Send to Amazon

* Default send quantity = `max(0, adu * fba_target_days - fba_stock)` clipped to Bangalore on-hand stock.
* Discontinued items can use a **send all remaining** override.
* Raise a **Low-FBA safeguard** when `fba_stock < 10` and `blr_on_hand > 5`.

## Less-than-Sellerboard Flag

* Uses Sellerboard column **I** (`Recommended quantity for reordering`).
* Flag when `I - (blr_on_hand + fba_stock + ordered_1 + ordered_2 + ordered_3) > 0`.

## Excess Inventory

* Excess when `(blr_on_hand + fba_stock) > adu * 120`.
* Excess units = surplus over the 120-day buffer; value derived from FIFO batch costs.
