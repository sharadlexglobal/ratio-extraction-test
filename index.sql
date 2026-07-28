-- Rebuilt search indexes for the people warehouse, on the new (Render) box.
--
-- Why these and not the old ones:
--   The old warehouse had 22 half-built indexes because the box killed every build
--   after ~30 minutes. Here statement_timeout is 0, so each build runs to completion.
--
-- The name indexes use text_pattern_ops so that a *parameterised* prefix range
--   lower(name) ~>=~ $1  AND  lower(name) ~<~ $2
-- can use them. Plain LIKE with a bind parameter cannot — that was the original trap.

\timing on

SET maintenance_work_mem = '8GB';
SET max_parallel_maintenance_workers = 4;
SET statement_timeout = 0;

-- ── Apollo (31M) ────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_ap_name_lc
  ON public.apollo_india_people ((lower(person_name)) text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_ap_linkedin
  ON public.apollo_india_people (linkedin_url)
  WHERE linkedin_url IS NOT NULL;

-- ── PeopleDataLabs (102M) — this is the one that never got built before ─────
CREATE INDEX IF NOT EXISTS idx_pdl_name_lc
  ON public.peopledatalabs_india ((lower(name)) text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_pdl_linkedin
  ON public.peopledatalabs_india (linkedin_url)
  WHERE linkedin_url IS NOT NULL;

ANALYZE public.apollo_india_people;
ANALYZE public.peopledatalabs_india;

-- ── proof ───────────────────────────────────────────────────────────────────
SELECT t.relname AS table_name,
       i.relname AS index_name,
       x.indisvalid AS valid,
       pg_size_pretty(pg_relation_size(i.oid)) AS size
FROM pg_class t
JOIN pg_index x ON x.indrelid = t.oid
JOIN pg_class i ON i.oid = x.indexrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'public'
ORDER BY t.relname, i.relname;

SELECT relname, n_live_tup AS rows,
       pg_size_pretty(pg_total_relation_size(relid)) AS total
FROM pg_stat_user_tables ORDER BY relname;
