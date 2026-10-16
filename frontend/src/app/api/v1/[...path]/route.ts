import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://api:8000";

async function proxy(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const pathStr = path.join("/");
  const url = new URL(request.url);
  const targetUrl = `${BACKEND_URL}/v1/${pathStr}${url.search}`;

  const headers = new Headers();
  const auth = request.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  const org = request.headers.get("x-org-id");
  if (org) headers.set("x-org-id", org);
  const ct = request.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  const acc = request.headers.get("accept");
  if (acc) headers.set("accept", acc);

  const body =
    request.method !== "GET" && request.method !== "HEAD"
      ? await request.arrayBuffer()
      : undefined;

  try {
    const res = await fetch(targetUrl, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
    });

    const resData = await res.text();
    return new NextResponse(resData, {
      status: res.status,
      statusText: res.statusText,
      headers: {
        "content-type": res.headers.get("content-type") || "application/json",
      },
    });
  } catch (err) {
    console.error(`[API Proxy] Error forwarding ${request.method} to ${targetUrl}:`, err);
    return NextResponse.json(
      { detail: `Failed to connect to backend: ${err instanceof Error ? err.message : String(err)}` },
      { status: 502 }
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
