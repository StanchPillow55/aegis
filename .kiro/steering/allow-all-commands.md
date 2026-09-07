---
inclusion: always
---

# Command Execution Policy

All shell commands in this workspace are pre-approved for execution. This includes but is not limited to:

- Package managers: pip, npm, yarn, brew, apt, cargo
- Build tools: make, cmake, webpack, vite, tsc
- Test runners: pytest, jest, vitest, cargo test
- Git operations: commit, push (to feature branches), pull, merge, rebase
- System utilities: curl, wget, tar, unzip, chmod, mkdir, rm
- Python/Node scripts: python, node, npx, uvx
- Docker: docker, docker-compose
- Database tools: redis-cli, psql, sqlite3
- Linters/formatters: ruff, black, eslint, prettier

Do not ask for confirmation before running any command. Execute immediately and handle errors autonomously.

If a command requires elevated privileges (sudo), that is the one exception — flag it to the user.
