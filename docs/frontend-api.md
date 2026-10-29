# Frontend and API integration

The Next.js client lives in `frontend/`; typed requests and response normalization are in `frontend/src/lib/api.ts`. Set `NEXT_PUBLIC_USE_MOCK=false` in the root `.env` and rebuild the web service to use FastAPI. Mock mode is labeled and uses synthetic browser-only fixtures.

## Connected user flows

- Registration, login, and profile: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`.
- Cases: `GET /cases`, `POST /cases`, `GET /cases/{id}`, `GET /cases/{id}/activity`.
- Upload and receipt: `POST /evidence/upload`, `GET /evidence/{id}`, `GET /evidence/{id}/file`, `GET /evidence/{id}/receipt`.
- Integrity: `POST /evidence/{id}/verify`, `GET /evidence/{id}/proof`, `GET /batches/{id}`.
- AI review: analysis, retry, case summary, links, flags, and aggregate reviewer feedback routes described in [ai-spec.md](ai-spec.md).
- Reports and audit: `GET /cases/{id}/report`, `GET /audit`, `GET /audit/verify`.
- Admin: `GET /admin/users`, `PATCH /admin/users/{id}`.

The API verifies permissions per request. Only reporters can create cases or submit evidence, and reporters are limited to cases they own. In this prototype, investigator, legal, and admin accounts can read every case; case-level assignment and organization membership are not implemented, so use synthetic records only. Investigators and admins can review AI flags and related-case links; both decisions require a saved reason. Legal accounts are read-only, and only admin can manage accounts. File/receipt/proof/metadata access and review decisions are appended to the audit log. Receipt signatures use canonical JSON and HMAC; the receipt endpoint returns `signature_valid`.

API errors use `{"error":{"code":"...","message":"...","details":{}}}`. Validation details omit submitted values so passwords and file metadata are not echoed back. The frontend also accepts legacy FastAPI `detail` responses for compatibility.

## Limits and notes

- Upload maximum is 100 MB by default. The browser checks the extension/size for convenience; the server validates the file and remains authoritative.
- Audio upload is preservation-only unless a transcription service is explicitly added. Video analysis samples at most four frames from a 60-second clip.
- AI flags and cross-case links are review leads. Reviewer feedback counts are not model accuracy; the system does not train from those labels.
- The evidence viewer previews original files retrieved through the authenticated API and does not create public object-storage URLs.
- API tokens are held in browser memory and cleared on reload/sign-out.
