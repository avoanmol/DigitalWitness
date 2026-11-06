import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(new URL("../src/app/api/[...path]/route.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const route = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);

test("binding proxy forwards uploads, auth, query and download metadata; handles outages", async () => {
  const savedFetch = globalThis.fetch;
  const savedBinding = process.env.BACKEND_URL;
  const req = new Request("https://public.example/api/evidence/upload?case_id=demo", {
    method: "POST", headers: { authorization: "Bearer test", "content-type": "multipart/form-data; boundary=demo" }, body: "fictional bytes",
  });
  req.nextUrl = new URL(req.url);
  try {
    delete process.env.BACKEND_URL;
    assert.equal((await route.POST(req)).status, 503);
    process.env.BACKEND_URL = "http://internal-backend/";
    globalThis.fetch = async (url, init) => {
      assert.equal(url.href, "http://internal-backend/evidence/upload?case_id=demo");
      assert.equal(init.headers.get("authorization"), "Bearer test");
      assert.equal(init.headers.get("content-type"), "multipart/form-data; boundary=demo");
      assert.equal(await new Response(init.body).text(), "fictional bytes");
      return new Response("report", { status: 201, headers: { "content-disposition": "attachment; filename=report.txt" } });
    };
    const response = await route.POST(req);
    assert.equal(response.status, 201);
    assert.equal(response.headers.get("content-disposition"), "attachment; filename=report.txt");
    assert.equal(await response.text(), "report");
    globalThis.fetch = async () => { throw new Error("offline"); };
    assert.equal((await route.POST(req)).status, 502);
  } finally {
    globalThis.fetch = savedFetch;
    if (savedBinding === undefined) delete process.env.BACKEND_URL;
    else process.env.BACKEND_URL = savedBinding;
  }
});
