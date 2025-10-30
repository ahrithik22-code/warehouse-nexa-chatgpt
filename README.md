# Warehouse & Replenishment Platform

This repository bootstraps a modular Django + React stack for managing warehouse stock, planning China reorders, and orchestrating Amazon FBA replenishment.

## Backend

* Django 5 project with apps for core services, inventory, planner, imports, and authz.
* Postgres schema modelling products, batches, movements, and planner snapshots.
* REST API via Django REST Framework with token-based authentication.

## Key Features

* Movement commit service prevents negative batch balances and enforces compliance status before outbound flows.
* Planner services compute China reorder targets, FBA send quantities, and risk flags such as low FBA stock or excess inventory.
* Import services for warehouse receipts, Sellerboard metrics, and manual China order buckets.

## Getting Started

1. Create a Python virtual environment and install project dependencies.
2. Configure the `POSTGRES_*` environment variables or update `warehouse/settings.py`.
3. Run migrations: `python manage.py migrate`.
4. Start the server: `python manage.py runserver`.

## Testing

Run `pytest` to execute the service layer test-suite.

## Frontend

The React PWA scaffold will be added in subsequent iterations.
