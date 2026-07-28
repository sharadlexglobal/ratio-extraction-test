#!/bin/sh
# Phase 4: the last three small cupboards, so nothing at all is lost when the old warehouse goes.
if [ -f /tmp/rest_done ]; then echo "already copied in this container — idling"; sleep infinity; fi
echo "=== LAST CUPBOARDS START $(date -u +%H:%M:%S) ==="
psql "$DEST" -c "create extension if not exists vector; create extension if not exists pg_trgm;" 2>&1 | tail -2
pg_dump "$SRC" --no-owner --no-acl --no-comments --clean --if-exists \
  -t public.crunchbase_india -t public.apollo_india_orgs -t public.court_rules_chunks \
  | psql "$DEST" -v ON_ERROR_STOP=1 -q
RC=$?
if [ $RC -ne 0 ]; then echo "=== FAILED (exit $RC) $(date -u +%H:%M:%S) ==="; sleep 300; exit $RC; fi
echo "=== COPY DONE $(date -u +%H:%M:%S) ==="
psql "$DEST" -c "select relname, n_live_tup as rows, pg_size_pretty(pg_total_relation_size(relid)) as size from pg_stat_user_tables order by n_live_tup desc"
psql "$DEST" -c "select pg_size_pretty(pg_database_size(current_database())) as total_used"
echo "=== ALL DONE $(date -u +%H:%M:%S) ==="
touch /tmp/rest_done
sleep infinity
