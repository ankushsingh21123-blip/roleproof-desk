-- Isolated synthetic portfolio database. Never run against an existing product DB.
BEGIN;
CREATE SCHEMA IF NOT EXISTS roleproof_private;
REVOKE ALL ON SCHEMA roleproof_private FROM PUBLIC, anon, authenticated;
CREATE TABLE IF NOT EXISTS roleproof_private.sessions (
 id text PRIMARY KEY CHECK(id ~ '^[a-f0-9]{64}$'),
 expires_at bigint NOT NULL, write_window bigint NOT NULL DEFAULT 0,
 write_count integer NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS roleproof_private.tickets (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 session_id text NOT NULL REFERENCES roleproof_private.sessions(id) ON DELETE CASCADE,
 title text NOT NULL CHECK(length(title) BETWEEN 3 AND 120),
 description text NOT NULL CHECK(length(description) BETWEEN 5 AND 2000),
 category text NOT NULL CHECK(category IN ('Account','Billing','Product','Other')),
 priority text NOT NULL CHECK(priority IN ('High','Medium','Low')),
 status text NOT NULL CHECK(status IN ('Open','In progress','Resolved')),
 version integer NOT NULL DEFAULT 1 CHECK(version > 0),
 created_at text NOT NULL, updated_at text NOT NULL
);
CREATE INDEX IF NOT EXISTS tickets_session ON roleproof_private.tickets(session_id);
ALTER TABLE roleproof_private.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE roleproof_private.tickets ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA roleproof_private FROM PUBLIC, anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA roleproof_private FROM PUBLIC, anon, authenticated;
CREATE OR REPLACE FUNCTION public.roleproof_rpc(action text, token_hash text, payload jsonb DEFAULT '{}'::jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, roleproof_private AS $$
DECLARE
 stamp bigint := floor(extract(epoch FROM clock_timestamp()));
 win bigint; s roleproof_private.sessions%ROWTYPE; t roleproof_private.tickets%ROWTYPE;
 rows_json jsonb; now_text text := to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
 ticket_id bigint;
BEGIN
 IF action='health' THEN
  PERFORM 1 FROM roleproof_private.sessions LIMIT 1;
  RETURN jsonb_build_object('status',200,'body',jsonb_build_object('status','ok','mode','hosted-isolated-demo','database','Supabase PostgreSQL','retention_days',7));
 END IF;
 IF token_hash IS NULL OR token_hash !~ '^[a-f0-9]{64}$' THEN
  RETURN jsonb_build_object('status',401,'body',jsonb_build_object('error','Invalid workspace token.'));
 END IF;
 -- One lock serializes anonymous session creation and enforces the global cap.
 IF action='session' THEN
  PERFORM pg_advisory_xact_lock(7521331);
  DELETE FROM roleproof_private.sessions WHERE expires_at<=stamp;
  SELECT * INTO s FROM roleproof_private.sessions WHERE id=token_hash AND expires_at>stamp;
  IF FOUND THEN RETURN jsonb_build_object('status',200,'body',jsonb_build_object('mode','hosted-isolated-demo','storage','Supabase PostgreSQL','expires_at',s.expires_at)); END IF;
  IF (SELECT count(*) FROM roleproof_private.sessions)>=100 THEN
   RETURN jsonb_build_object('status',503,'body',jsonb_build_object('error','The free demo is at capacity. Try after sessions expire.'));
  END IF;
  INSERT INTO roleproof_private.sessions(id,expires_at) VALUES(token_hash,stamp+604800);
  INSERT INTO roleproof_private.tickets(session_id,title,description,category,priority,status,created_at,updated_at) VALUES
  (token_hash,'Unable to update workspace name','Fictional example: saving a new workspace name leaves the previous value visible.','Account','High','Open',now_text,now_text),
  (token_hash,'Invoice download returns an empty file','Fictional example: the sample billing export downloads without any content.','Billing','High','In progress',now_text,now_text),
  (token_hash,'Keyboard focus skips the save button','Fictional example: keyboard navigation jumps from the input to the footer.','Product','Medium','Open',now_text,now_text),
  (token_hash,'Add CSV export for the activity list','Fictional example: export a filtered set of activity rows for offline review.','Product','Low','Open',now_text,now_text),
  (token_hash,'Clarify the demo data notice','Fictional example: the notice clearly labels all records as synthetic.','Other','Low','Resolved',now_text,now_text);
  RETURN jsonb_build_object('status',201,'body',jsonb_build_object('mode','hosted-isolated-demo','storage','Supabase PostgreSQL','expires_at',stamp+604800));
 END IF;
 SELECT * INTO s FROM roleproof_private.sessions WHERE id=token_hash AND expires_at>stamp FOR UPDATE;
 IF NOT FOUND THEN RETURN jsonb_build_object('status',401,'body',jsonb_build_object('error','Demo session expired. Reload to start a fresh synthetic workspace.')); END IF;
 IF action='list' THEN
  SELECT coalesce(jsonb_agg(to_jsonb(q)-'session_id'),'[]'::jsonb) INTO rows_json FROM
  (SELECT * FROM roleproof_private.tickets WHERE session_id=token_hash ORDER BY CASE WHEN status='Resolved' THEN 1 ELSE 0 END,CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,id DESC LIMIT 40) q;
  RETURN jsonb_build_object('status',200,'body',jsonb_build_object('tickets',rows_json));
 END IF;
 IF action NOT IN ('create','update') THEN RETURN jsonb_build_object('status',404,'body',jsonb_build_object('error','Route not found.')); END IF;
 win := stamp/60;
 IF s.write_window=win AND s.write_count>=20 THEN RETURN jsonb_build_object('status',429,'body',jsonb_build_object('error','Demo write limit reached. Try again in one minute.')); END IF;
 UPDATE roleproof_private.sessions SET write_count=CASE WHEN write_window=win THEN write_count+1 ELSE 1 END,write_window=win WHERE id=token_hash;
 IF action='create' THEN
  IF jsonb_typeof(payload)!='object' OR (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(payload) key) IS DISTINCT FROM ARRAY['category','description','priority','title'] OR EXISTS(SELECT 1 FROM jsonb_each(payload) e WHERE jsonb_typeof(e.value)!='string') OR
   length(btrim(payload->>'title')) NOT BETWEEN 3 AND 120 OR length(btrim(payload->>'description')) NOT BETWEEN 5 AND 2000 OR
   payload->>'category' NOT IN ('Account','Billing','Product','Other') OR payload->>'priority' NOT IN ('High','Medium','Low') THEN
   RETURN jsonb_build_object('status',400,'body',jsonb_build_object('error','Invalid ticket fields.'));
  END IF;
  IF (SELECT count(*) FROM roleproof_private.tickets WHERE session_id=token_hash)>=40 THEN RETURN jsonb_build_object('status',429,'body',jsonb_build_object('error','This workspace is limited to40tickets.')); END IF;
  INSERT INTO roleproof_private.tickets(session_id,title,description,category,priority,status,created_at,updated_at) VALUES(token_hash,btrim(payload->>'title'),btrim(payload->>'description'),payload->>'category',payload->>'priority','Open',now_text,now_text) RETURNING * INTO t;
  RETURN jsonb_build_object('status',201,'body',jsonb_build_object('ticket',to_jsonb(t)-'session_id'));
 END IF;
 IF jsonb_typeof(payload)!='object' OR (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(payload) key) IS DISTINCT FROM ARRAY['id','status','version'] OR
  jsonb_typeof(payload->'status')!='string' OR payload->>'status' NOT IN ('Open','In progress','Resolved') OR
  jsonb_typeof(payload->'version')!='number' OR coalesce(payload->>'version','') !~ '^[1-9][0-9]{0,8}$' OR coalesce(payload->>'id','') !~ '^[1-9][0-9]{0,14}$' THEN
  RETURN jsonb_build_object('status',400,'body',jsonb_build_object('error','Valid status and version required.'));
 END IF;
 ticket_id := (payload->>'id')::bigint;
 UPDATE roleproof_private.tickets SET status=payload->>'status',version=version+1,updated_at=now_text WHERE id=ticket_id AND session_id=token_hash AND version=(payload->>'version')::int RETURNING * INTO t;
 IF FOUND THEN RETURN jsonb_build_object('status',200,'body',jsonb_build_object('ticket',to_jsonb(t)-'session_id')); END IF;
 IF EXISTS(SELECT 1 FROM roleproof_private.tickets WHERE id=ticket_id AND session_id=token_hash) THEN RETURN jsonb_build_object('status',409,'body',jsonb_build_object('error','This ticket changed. Refresh before updating.')); END IF;
 RETURN jsonb_build_object('status',404,'body',jsonb_build_object('error','Ticket not found.'));
END $$;
REVOKE ALL ON FUNCTION public.roleproof_rpc(text,text,jsonb) FROM PUBLIC, authenticated;
GRANT EXECUTE ON FUNCTION public.roleproof_rpc(text,text,jsonb) TO anon;
COMMIT;
