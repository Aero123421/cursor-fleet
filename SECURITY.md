# Security policy

`cursor-fleet` launches local AI coding agents that can read files, write files, and run commands through Cursor CLI. Use it only in repositories and environments where that risk is acceptable.

## Reporting vulnerabilities

Open a GitHub security advisory or send a private report to the repository maintainer once the project has an owner account.

## Secret handling

`cursor-fleet` denies common secret path patterns by default and tells workers not to read or transmit secrets. These are guardrails, not a sandbox guarantee.

Before using this tool in production repositories:

- Configure `safety.deny_paths` for your repo.
- Avoid running with Cursor `--force` unless you understand the risk.
- Prefer local verification commands that do not require production credentials.
- Review the final patch before committing or pushing.
