# Local backup & restore

Offline durability for the local-first SQLite store. No cloud backup.

## Export

```bash
curl -OJ http://127.0.0.1:8000/api/backup/export
# or Settings → Download backup
```

Creates `aegis-backup.zip` with `*.sqlite3` files under `DATA_DIR` plus `geo.json` when present.

## Restore

```bash
curl -F file=@aegis-backup.zip http://127.0.0.1:8000/api/backup/restore
```

Or Settings → Restore from ZIP. Overwrites matching files in `DATA_DIR`.

**Restart** `make os-dev` after restore so in-memory stores reopen the files.

## Notes

- Backup is host-local only; do not commit zips with personal health data.
- Restore refuses path traversal and non-sqlite/json members.
