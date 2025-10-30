# ADR-001: Tech Stack

## Status

Proposed

## Context

The warehouse planning suite requires strong data integrity, planner-grade computation, and mobile-friendly operations for scanning and offline actions. The system must also integrate Sellerboard snapshots while enforcing compliance metadata on a per-batch basis.

## Decision

* **Backend:** Python Django 5 with Django REST Framework. Django provides batteries-included admin, ORM migrations, and mature Postgres support. DRF exposes a versionable API surface for the planner, imports, and movement engine.
* **Database:** PostgreSQL with row-level security (RLS) and native table partitioning. Partitioning on the stock ledger keeps historical movement data performant, while RLS enables brand or warehouse scoped access.
* **Frontend:** React (Vite) PWA with Tailwind and shadcn/ui (future milestone). This combination enables rapid UI iteration, offline caching, and scanner integrations.
* **Infrastructure:** Dockerized services deployable to Cloud Run with Cloud SQL for Postgres, paired with Sentry for observability.

## Consequences

* Django's ORM simplifies transactional enforcement of negative-stock checks.
* Postgres partitioning requires maintenance tasks to create future partitions, handled via migrations or scheduled jobs.
* The PWA approach allows Android-based scanning workflows without a dedicated native client.
