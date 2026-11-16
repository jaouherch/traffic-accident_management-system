# Security notes

This repository was prepared for an academic GitHub portfolio, not independently certified for production use.

## Before publishing

1. **Revoke the old Gmail app password** that was previously embedded in the original archive. Treat it as compromised even though it is absent from this version.
2. Replace any previously used JWT signing secret and administrator invitation code. Never reuse old values.
3. Copy `.env.example` to `.env` separately for each required component and use private values only in ignored local files.
4. Check screenshots and sample datasets for private names, faces, addresses, coordinates, and email addresses before uploading them.
5. Keep real uploads, SQLite databases, access tokens, API client exports, and dependency folders out of Git commits.
6. If secrets were ever pushed to GitHub, rotating them is necessary even after deleting the file; Git history can preserve previous versions.

## Known limitations

- Logout revocation is kept in a process-local in-memory blocklist; it does not persist across restarts. A production deployment should store token revocations in a shared persistent system.
- The browser uses local storage for JWT tokens. A production authentication design should assess XSS risk and consider a hardened cookie-based approach.
- Image uploads are limited in size and extension, but are not yet fully validated by decoding image content. Apply stricter validation and content-serving controls before opening uploads to the public Internet.
- SQLite and the simple admin bootstrap script target local demonstrations. Production use requires migrations, secure infrastructure, monitoring, backup, abuse/rate-limit controls, and security testing.

Report suspected vulnerabilities privately to the repository owner rather than opening public issues containing secrets.

