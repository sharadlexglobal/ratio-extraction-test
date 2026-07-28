#!/bin/sh
# Phase 5: copy the whole live `litigants` room (leadgen) to the new warehouse.
# This is a SNAPSHOT — the room is still being written to. The small mutable
# tables get re-copied fresh at cutover; court_rules_chunks is static.
if [ -f /tmp/lit_done ]; then echo "litigants already copied in this container — idling"; sleep infinity; fi

echo "=== LITIGANTS COPY START $(date -u +%H:%M:%S) ==="
psql "$DEST" -c "create extension if not exists vector;" 2>&1 | tail -1

echo "--- at source ---"
psql "$SRC" -c "select relname, n_live_tup from pg_stat_user_tables
                 where schemaname='litigants' order by relname" 2>&1

pg_dump "$SRC" --no-owner --no-acl --no-comments --clean --if-exists \
  --schema=litigants \
  | psql "$DEST" -v ON_ERROR_STOP=1 -q
RC=$?
if [ $RC -ne 0 ]; then echo "=== FAILED (exit $RC) $(date -u +%H:%M:%S) ==="; sleep 300; exit $RC; fi

echo "=== COPY DONE $(date -u +%H:%M:%S) ==="
psql "$DEST" -c "analyze;" 2>&1 | tail -1
psql "$DEST" -c "select relname, n_live_tup as rows, pg_size_pretty(pg_total_relation_size(relid)) as size
                   from pg_stat_user_tables where schemaname='litigants' order by relname"
psql "$DEST" -c "select i.relname as index_name, x.indisvalid as valid
                   from pg_class i join pg_index x on x.indexrelid=i.oid
                   join pg_namespace n on n.oid=i.relnamespace
                  where n.nspname='litigants' order by 1"
echo "=== ALL DONE $(date -u +%H:%M:%S) ==="
touch /tmp/lit_done
sleep infinity
