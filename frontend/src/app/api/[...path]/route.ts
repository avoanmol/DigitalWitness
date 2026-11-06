import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Resolve the binding only inside a request handler, never at build time.
async function forward(request: NextRequest): Promise<Response> {
  const base = process.env.BACKEND_URL;
  if (!base) {
    return Response.json({ error: { message: "Backend service binding is unavailable." } }, { status: 503 });
  }
  const target = new URL(base);
  // Assign pathname rather than resolving an untrusted path as a URL: a double
  // slash in a client path must never change the destination host.
  target.pathname = `${target.pathname.replace(/\/$/, "")}${request.nextUrl.pathname.slice(4)}`;
  target.search = request.nextUrl.search;
  const headers = new Headers();
  for (const name of ["accept", "authorization", "content-type", "range", "if-none-match"]) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  headers.set("accept-encoding", "identity");
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  try {
    const options: RequestInit & { duplex?: "half" } = {
      method: request.method, headers, redirect: "manual", cache: "no-store",
      signal: request.signal,
      ...(hasBody ? { body: request.body, duplex: "half" } : {}),
    };
    const upstream = await fetch(target, options);
    const responseHeaders = new Headers();
    for (const name of ["content-type", "content-disposition", "content-range", "accept-ranges", "etag", "www-authenticate", "retry-after", "x-report-sha256", "x-complaint-packet-sha256", "x-complaint-packet-format"]) {
      const value = upstream.headers.get(name);
      if (value !== null) responseHeaders.set(name, value);
    }
    // Keep redirects on the public API path and never expose the binding URL.
    const location = upstream.headers.get("location");
    if (location) {
      const redirect = new URL(location, target);
      if (redirect.origin === target.origin) {
        responseHeaders.set("location", `/api${redirect.pathname}${redirect.search}`);
      }
    }
    responseHeaders.set("cache-control", "no-store");
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return Response.json({ error: { message: "Backend service could not be reached." } }, { status: 502 });
  }
}

export { forward as GET, forward as POST, forward as PATCH, forward as PUT, forward as DELETE, forward as OPTIONS, forward as HEAD };
