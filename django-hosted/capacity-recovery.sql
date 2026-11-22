-- No paid plan or storage change. Preserve every existing workspace and ticket.
-- Raise only the shared synthetic demo's internal workspace guard: 100 -> 500.
-- Abort rather than replace an unexpected function or change owners/grants/data.
BEGIN;
DO $recovery$
DECLARE
  before_definition text;
  after_definition text;
  old_owner oid;
  old_acl text;
  before_sessions text;
  before_tickets text;
  old_guard text := '(SELECT count(*) FROM roleproof_private.sessions)>=100';
  new_guard text := '(SELECT count(*) FROM roleproof_private.sessions)>=500';
BEGIN
  PERFORM pg_advisory_xact_lock(7521331);
  LOCK TABLE roleproof_private.sessions, roleproof_private.tickets IN SHARE ROW EXCLUSIVE MODE;
  SELECT pg_get_functiondef(oid), proowner, proacl::text
    INTO before_definition, old_owner, old_acl
    FROM pg_proc WHERE oid='public.roleproof_rpc(text,text,jsonb)'::regprocedure;
  IF (length(before_definition)-length(replace(before_definition,old_guard,''))) / length(old_guard) <> 1 THEN
    RAISE EXCEPTION 'Expected exactly one 100-workspace guard; no change made';
  END IF;
  SELECT md5(coalesce(string_agg(row_to_json(s)::text,'' ORDER BY id),'')) INTO before_sessions FROM roleproof_private.sessions s;
  SELECT md5(coalesce(string_agg(row_to_json(t)::text,'' ORDER BY id),'')) INTO before_tickets FROM roleproof_private.tickets t;
  EXECUTE replace(before_definition,old_guard,new_guard);
  SELECT pg_get_functiondef(oid) INTO after_definition FROM pg_proc WHERE oid='public.roleproof_rpc(text,text,jsonb)'::regprocedure;
  IF after_definition <> replace(before_definition,old_guard,new_guard) OR
     (SELECT proowner <> old_owner OR proacl::text IS DISTINCT FROM old_acl FROM pg_proc WHERE oid='public.roleproof_rpc(text,text,jsonb)'::regprocedure) THEN
    RAISE EXCEPTION 'Unexpected function or permission change; transaction rolled back';
  END IF;
  IF before_sessions IS DISTINCT FROM (SELECT md5(coalesce(string_agg(row_to_json(s)::text,'' ORDER BY id),'')) FROM roleproof_private.sessions s) OR
     before_tickets IS DISTINCT FROM (SELECT md5(coalesce(string_agg(row_to_json(t)::text,'' ORDER BY id),'')) FROM roleproof_private.tickets t) THEN
    RAISE EXCEPTION 'Unexpected record change; transaction rolled back';
  END IF;
END $recovery$;
COMMIT;
SELECT (SELECT count(*) FROM roleproof_private.sessions) AS preserved_sessions,
       (SELECT count(*) FROM roleproof_private.tickets) AS preserved_tickets,
       position('(SELECT count(*) FROM roleproof_private.sessions)>=500' IN pg_get_functiondef('public.roleproof_rpc(text,text,jsonb)'::regprocedure)) > 0 AS cap_500,
       pg_get_userbyid(proowner) AS function_owner, proacl::text AS privileges
FROM pg_proc WHERE oid='public.roleproof_rpc(text,text,jsonb)'::regprocedure;
