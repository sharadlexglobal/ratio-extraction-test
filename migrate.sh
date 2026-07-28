#!/bin/sh
# One-shot transfer of the two live people cupboards from the old warehouse to the new one.
# Runs inside Render Singapore, so the data never leaves the region.
# Indexes are deliberately NOT copied — they are rebuilt afterwards, properly.

TABLES="-t public.apollo_india_people -t public.peopledatalabs_india"
STAMP() { date -u +%H:%M:%S; }

if [ -f /tmp/done ]; then
  echo "already finished in this container — idling"
  sleep infinity
fi

echo "=== START $(STAMP) ==="
echo "source : $(psql "$SRC" -tAc 'select current_setting(''server_version'')' 2>&1 | head -1)"
echo "target : $(psql "$DEST" -tAc 'select current_setting(''server_version'')' 2>&1 | head -1)"

echo "--- rows waiting at source ---"
psql "$SRC" -c "select relname, n_live_tup from pg_stat_user_tables where relname in ('apollo_india_people','peopledatalabs_india') order by 1" 2>&1

echo "=== COPYING $(STAMP) (no indexes, data only) ==="
pg_dump "$SRC" \
  --no-owner --no-acl --no-comments \
  --clean --if-exists \
  --section=pre-data --section=data \
  $TABLES \
  | psql "$DEST" -v ON_ERROR_STOP=1 -q
RC=$?

if [ $RC -ne 0 ]; then
  echo "=== FAILED (exit $RC) $(STAMP) ==="
  sleep 300
  exit $RC
fi

echo "=== COPY DONE $(STAMP) ==="
psql "$DEST" -c "analyze public.apollo_india_people; analyze public.peopledatalabs_india;"
psql "$DEST" -c "select relname, n_live_tup as rows, pg_size_pretty(pg_total_relation_size(relid)) as size from pg_stat_user_tables order by 1"
echo "=== ALL DONE $(STAMP) ==="
touch /tmp/done
sleep infinity
