// Public synthetic-data demo. No customer records, accounts or secrets.
// Each browser gets an opaque HttpOnly cookie; only its SHA-256 hash is stored.
const COOKIE = "rp_session";
const DAY = 86400;
const TTL = 7 * DAY;
const statuses = ["Open", "In progress", "Resolved"];
const categories = ["Account", "Billing", "Product", "Other"];
const priorities = ["High", "Medium", "Low"];
const security = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "X-Frame-Options": "DENY",
  "Content-Security-Policy":
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  "Cache-Control": "no-store",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
};
function json(status, value, headers = {}) {
  return new Response(JSON.stringify(value), {
    status,
    headers: {
      ...security,
      "Content-Type": "application/json; charset=utf-8",
      ...headers,
    },
  });
}
class Failure extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}
function fail(status, message) {
  throw new Failure(status, message);
}
async function hash(token) {
  const bytes = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(token),
  );
  return Array.from(new Uint8Array(bytes), (x) =>
    x.toString(16).padStart(2, "0"),
  ).join("");
}
async function session(request, db, timestamp) {
  const token = (request.headers.get("Cookie") || "")
    .split(";")
    .map((x) => x.trim())
    .find((x) => x.startsWith(COOKIE + "="))
    ?.slice(COOKIE.length + 1);
  if (!token || !/^[a-f0-9]{64}$/.test(token)) return null;
  return db
    .prepare("SELECT id, expires_at FROM sessions WHERE id=? AND expires_at>?")
    .bind(await hash(token), timestamp)
    .first();
}
async function body(request) {
  if (request.headers.get("X-RoleProof-Client") !== "desk")
    fail(400, "Missing client header.");
  if (request.headers.get("Content-Type")?.split(";")[0] !== "application/json")
    fail(400, "JSON content type required.");
  if (Number(request.headers.get("Content-Length") || 0) > 8192)
    fail(400, "Request is too large.");
  const reader = request.body?.getReader();
  if (!reader) fail(400, "JSON object required.");
  const chunks = [];
  let size = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > 8192) {
      await reader.cancel();
      fail(400, "Request is too large.");
    }
    chunks.push(value);
  }
  const all = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    all.set(chunk, offset);
    offset += chunk.length;
  }
  let value;
  try {
    value = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(all));
  } catch {
    fail(400, "Invalid JSON.");
  }
  if (!value || typeof value !== "object" || Array.isArray(value))
    fail(400, "JSON object required.");
  return value;
}
const sample = [
  [
    "Unable to update workspace name",
    "Fictional example: saving a new workspace name leaves the previous value visible.",
    "Account",
    "High",
    "Open",
  ],
  [
    "Invoice download returns an empty file",
    "Fictional example: the sample billing export downloads without any content.",
    "Billing",
    "High",
    "In progress",
  ],
  [
    "Keyboard focus skips the save button",
    "Fictional example: keyboard navigation jumps from the input to the footer.",
    "Product",
    "Medium",
    "Open",
  ],
  [
    "Add CSV export for the activity list",
    "Fictional example: export a filtered set of activity rows for offline review.",
    "Product",
    "Low",
    "Open",
  ],
  [
    "Clarify the demo data notice",
    "Fictional example: the notice clearly labels all records as synthetic.",
    "Other",
    "Low",
    "Resolved",
  ],
];
function publicTicket(row) {
  const { session_id, ...ticket } = row;
  return ticket;
}
async function startSession(request, db, timestamp) {
  await body(request);
  let current = await session(request, db, timestamp);
  if (current)
    return json(200, {
      mode: "hosted-isolated-demo",
      storage: "Cloudflare D1 (SQLite)",
      expires_at: current.expires_at,
    });
  // Bounded cleanup and capacity checks prevent an anonymous demo growing forever.
  await db.batch([
    db
      .prepare(
        "DELETE FROM tickets WHERE session_id IN (SELECT id FROM sessions WHERE expires_at<=?)",
      )
      .bind(timestamp),
    db.prepare("DELETE FROM sessions WHERE expires_at<=?").bind(timestamp),
  ]);
  const token = Array.from(crypto.getRandomValues(new Uint8Array(32)), (x) =>
    x.toString(16).padStart(2, "0"),
  ).join("");
  const id = await hash(token);
  const inserted = await db
    .prepare(
      "INSERT INTO sessions(id, expires_at, write_window, write_count) SELECT ?,?,0,0 WHERE (SELECT COUNT(*) FROM sessions)<100",
    )
    .bind(id, timestamp + TTL)
    .run();
  if (inserted.meta.changes !== 1)
    fail(
      503,
      "The free demo is at capacity. Please try again after sessions expire.",
    );
  const now = new Date().toISOString();
  await db.batch(
    sample.map((t) =>
      db
        .prepare(
          "INSERT INTO tickets(session_id,title,description,category,priority,status,version,created_at,updated_at) VALUES(?,?,?,?,?,?,1,?,?)",
        )
        .bind(id, ...t, now, now),
    ),
  );
  const secure = new URL(request.url).protocol === "https:" ? "; Secure" : "";
  return json(
    201,
    {
      mode: "hosted-isolated-demo",
      storage: "Cloudflare D1 (SQLite)",
      expires_at: timestamp + TTL,
    },
    {
      "Set-Cookie": `${COOKIE}=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${TTL}${secure}`,
    },
  );
}
async function writeGate(db, id, timestamp) {
  // This single statement increments atomically, including failed input attempts.
  const window = Math.floor(timestamp / 60);
  const result = await db
    .prepare(
      "UPDATE sessions SET write_count=CASE WHEN write_window=? THEN write_count+1 ELSE 1 END,write_window=? WHERE id=? AND (write_window!=? OR write_count<20)",
    )
    .bind(window, window, id, window)
    .run();
  if (result.meta.changes !== 1)
    fail(429, "Demo write limit reached. Try again in one minute.");
}
export default {
  async fetch(request, env) {
    const url = new URL(request.url),
      path = url.pathname;
    try {
      if (!path.startsWith("/api/")) {
        if (request.method !== "GET" && request.method !== "HEAD")
          return json(405, { error: "Method not allowed." });
        if (
          !(
            path === "/" ||
            path === "/index.html" ||
            /^\/assets\/[a-zA-Z0-9_.-]+$/.test(path)
          )
        )
          return json(404, { error: "Not found." });
        const response = await env.ASSETS.fetch(request);
        const headers = new Headers(response.headers);
        for (const [key, value] of Object.entries(security))
          headers.set(key, value);
        return new Response(response.body, {
          status: response.status,
          headers,
        });
      }
      if (path === "/api/health" && request.method === "GET") {
        // Read the actual bound database, not just a hardcoded healthy response.
        await env.DB.prepare("SELECT id FROM sessions LIMIT 1").all();
        return json(200, {
          status: "ok",
          mode: "hosted-isolated-demo",
          database: "D1 SQLite",
          retention_days: 7,
        });
      }
      if (!["GET", "POST", "PATCH"].includes(request.method))
        return json(405, { error: "Method not allowed." });
      if (
        request.method !== "GET" &&
        request.headers.get("Origin") !== url.origin
      )
        return json(403, { error: "Same-origin requests only." });
      const timestamp = Math.floor(Date.now() / 1000);
      if (path === "/api/session" && request.method === "POST")
        return await startSession(request, env.DB, timestamp);
      if (
        !(
          path === "/api/tickets" ||
          /^\/api\/tickets\/[1-9][0-9]{0,14}$/.test(path)
        )
      )
        return json(404, { error: "Route not found." });
      const current = await session(request, env.DB, timestamp);
      if (!current)
        return json(401, {
          error:
            "Demo session expired. Reload the page to start a fresh synthetic workspace.",
        });
      if (path === "/api/tickets" && request.method === "GET") {
        const { results } = await env.DB.prepare(
          "SELECT * FROM tickets WHERE session_id=? ORDER BY CASE status WHEN 'Resolved' THEN 1 ELSE 0 END, CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,id DESC LIMIT 40",
        )
          .bind(current.id)
          .all();
        return json(200, { tickets: results.map(publicTicket) });
      }
      if (path === "/api/tickets" && request.method === "POST") {
        await writeGate(env.DB, current.id, timestamp);
        const value = await body(request);
        if (
          Object.keys(value).sort().join(",") !==
            "category,description,priority,title" ||
          !Object.values(value).every((x) => typeof x === "string")
        )
          fail(
            400,
            "Expected title, description, category and priority strings.",
          );
        const title = value.title.trim(),
          description = value.description.trim();
        if (
          title.length < 3 ||
          title.length > 120 ||
          description.length < 5 ||
          description.length > 2000
        )
          fail(400, "Title must be 3-120 characters and description 5-2000.");
        if (
          !categories.includes(value.category) ||
          !priorities.includes(value.priority)
        )
          fail(400, "Invalid category or priority.");
        const now = new Date().toISOString();
        const row = await env.DB.prepare(
          "INSERT INTO tickets(session_id,title,description,category,priority,status,version,created_at,updated_at) SELECT ?,?,?,?,?,'Open',1,?,? WHERE (SELECT COUNT(*) FROM tickets WHERE session_id=?)<40 RETURNING *",
        )
          .bind(
            current.id,
            title,
            description,
            value.category,
            value.priority,
            now,
            now,
            current.id,
          )
          .first();
        if (!row) fail(429, "This demo workspace is limited to 40 tickets.");
        return json(201, { ticket: publicTicket(row) });
      }
      if (
        /^\/api\/tickets\/[1-9][0-9]{0,14}$/.test(path) &&
        request.method === "PATCH"
      ) {
        await writeGate(env.DB, current.id, timestamp);
        const value = await body(request);
        if (
          Object.keys(value).sort().join(",") !== "status,version" ||
          !statuses.includes(value.status) ||
          !Number.isSafeInteger(value.version) ||
          value.version < 1
        )
          fail(400, "Valid status and positive integer version required.");
        const id = Number(path.split("/").pop());
        const row = await env.DB.prepare(
          "UPDATE tickets SET status=?,version=version+1,updated_at=? WHERE id=? AND session_id=? AND version=? RETURNING *",
        )
          .bind(
            value.status,
            new Date().toISOString(),
            id,
            current.id,
            value.version,
          )
          .first();
        if (row) return json(200, { ticket: publicTicket(row) });
        const found = await env.DB.prepare(
          "SELECT id FROM tickets WHERE id=? AND session_id=?",
        )
          .bind(id, current.id)
          .first();
        return found
          ? json(409, {
              error: "This ticket changed. Refresh before updating.",
            })
          : json(404, { error: "Ticket not found." });
      }
      return json(405, { error: "Method not allowed." });
    } catch (error) {
      if (error instanceof Failure)
        return json(error.status, { error: error.message });
      // Never send database internals, SQL, cookies or stack traces to a client.
      return json(503, {
        error: "Demo storage is unavailable. Please try again later.",
      });
    }
  },
};
