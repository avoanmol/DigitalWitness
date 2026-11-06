# Vercel services deployment

Set the Vercel project Root Directory to `.`. The root vercel.json defines:
- frontend: Next.js, all public traffic, including /api/*.
- backend: internal container built from the root Dockerfile; no public rewrite.
- frontend calls backend using the runtime BACKEND_URL binding. Never set that variable manually.

The root Dockerfile already runs FastAPI; a separate app service would duplicate it.
The Next.js /api/* handler removes /api and forwards authorization, multipart uploads,
query strings and download headers to the unchanged FastAPI routes.

Set NEXT_PUBLIC_API_URL=/api and NEXT_PUBLIC_USE_MOCK=false before building.
Never expose signing, encryption, database or JWT secrets as NEXT_PUBLIC variables.

This does not provision PostgreSQL, private S3-compatible object storage or continuous
AI/integrity workers. Configure a hosted DATABASE_URL, storage credentials/TLS and
existing encryption, receipt, JWT and Amoy secrets using .env.example. Docker hostnames
and laptop localhost are not reachable cloud services. Keep existing encryption keys
when migrating evidence. Run python -m alembic upgrade head once against the hosted DB.
Keep polling workers on continuous worker hosting or configure reviewed Vercel daemons
separately; do not start them inside the autoscaling API container.

From the repo root, use npx vercel dev -L with Docker available to test generated
bindings. A current Vercel CLI supporting services is required. Then test deployed
login, uploads, downloads, AI completion and Amoy anchoring. Platform upload and
function duration limits still apply: the local 100 MB setting is not a verified
Vercel upload capacity. This is deployment configuration, not a completed deployment.
