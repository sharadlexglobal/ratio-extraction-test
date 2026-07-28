#!/bin/sh
# Phase 2: build the search indexes on the new warehouse.
# Runs inside Render so a dropped laptop connection cannot cancel a 100M-row build.
if [ -f /tmp/idx_done ]; then echo "indexes already built in this container — idling"; sleep infinity; fi
echo "=== INDEX BUILD START $(date -u +%H:%M:%S) ==="
psql "$DEST" -v ON_ERROR_STOP=1 -f /index.sql
RC=$?
echo "=== INDEX BUILD EXIT $RC  $(date -u +%H:%M:%S) ==="
[ $RC -eq 0 ] && touch /tmp/idx_done
sleep infinity
