# Research

- Existing compose is infra-only; CI installs `psycopg[binary]` ad hoc — bake it into the backend image (and requirements) so Postgres works.
- Next `NEXT_PUBLIC_*` must be build args; runtime `env` alone is not enough for client bundles.
- Inside the network: `postgres`, `redis`, `mailpit` service names; host ports stay 8000 / 5173 for CORS/Clerk.
