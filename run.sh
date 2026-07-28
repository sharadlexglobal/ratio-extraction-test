#!/bin/sh
# Phase 3: rescue the two LinkedIn cupboards before the old warehouse is torn down.
# Nothing in the app reads them, so no indexes are built — just the raw pages, kept safe.
if [ -f /tmp/li_done ]; then echo "linkedin already copied in this container — idling"; sleep infinity; fi

echo "=== LINKEDIN RESCUE START $(date -u +%H:%M:%S) ==="
echo "--- waiting at source ---"
psql "$SRC" -c "select relname, reltuples::bigint as approx_rows, pg_size_pretty(pg_total_relation_size(oid)) as size
                  from pg_class where relname in ('linkedin_india','linkedin_normalized')"

pg_dump "$SRC" --no-owner --no-acl --no-comments --clean --if-exists \
  --section=pre-data --section=data \
  -t public.linkedin_india -t public.linkedin_normalized \
  | psql "$DEST" -v ON_ERROR_STOP=1 -q
RC=$?

if [ $RC -ne 0 ]; then echo "=== FAILED (exit $RC) $(date -u +%H:%M:%S) ==="; sleep 300; exit $RC; fi

echo "=== COPY DONE $(date -u +%H:%M:%S) ==="
psql "$DEST" -c "analyze public.linkedin_india; analyze public.linkedin_normalized;"
psql "$DEST" -c "select relname, n_live_tup as rows, pg_size_pretty(pg_total_relation_size(relid)) as size
                   from pg_stat_user_tables order by n_live_tup desc"
psql "$DEST" -c "select pg_size_pretty(pg_database_size(current_database())) as total_used"
echo "=== ALL DONE $(date -u +%H:%M:%S) ==="
touch /tmp/li_done
sleep infinity
