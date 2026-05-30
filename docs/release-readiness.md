# Release Readiness

This checklist describes what should be true before Gainz is shared outside a trusted private beta.

## Required Before Public Source Release

- Private tax artifacts are not tracked.
- Generated folders are ignored: `saves/`, `exports/`, `uploads/`, `logs/`, `reconciliation/`, `quarantine/`, `audit_packet_*/`, and `audit_packets/`.
- First-run credentials are generated locally or provided through environment variables.
- Flask secret key is generated locally or provided through `GAINZ_SECRET_KEY`.
- README uses current positioning and no broken encoding.
- Demo CSVs contain synthetic data only.
- Tests cover core lot linking and parser behavior.

## Required Before Packaged Desktop Release

- One-click build process is documented.
- App data paths are outside the source tree or clearly ignored.
- First-run credential file is easy to find.
- Export and audit-packet actions show the output path.
- No private or developer-only scripts are included in release artifacts.

## Required Before Hosted Release

Do not host Gainz without a separate security and compliance design. A hosted service would require account isolation, encrypted storage, secrets management, logging controls, privacy policy, data retention policy, abuse controls, and professional review.
