import { NextRequest } from "next/server";

const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";
const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade"
]);

type RouteContext = {
  params: Promise<{ path?: string[] }>;
};

function backendBaseUrl() {
  return (process.env.VIENEU_INTERNAL_API_BASE || process.env.NEXT_PUBLIC_VIENEU_API_BASE || DEFAULT_BACKEND_URL).replace(/\/$/, "");
}

function proxyHeaders(request: NextRequest) {
  const headers = new Headers(request.headers);
  for (const header of HOP_BY_HOP_HEADERS) {
    headers.delete(header);
  }
  headers.delete("host");
  return headers;
}

function responseHeaders(headers: Headers) {
  const nextHeaders = new Headers(headers);
  for (const header of HOP_BY_HOP_HEADERS) {
    nextHeaders.delete(header);
  }
  return nextHeaders;
}

async function proxy(request: NextRequest, context: RouteContext) {
  const params = await context.params;
  const path = params.path?.join("/") || "";
  const target = new URL(`${backendBaseUrl()}/${path}`);
  target.search = request.nextUrl.search;

  const response = await fetch(target, {
    method: request.method,
    headers: proxyHeaders(request),
    body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
    duplex: "half",
    redirect: "manual",
    cache: "no-store"
  } as RequestInit);

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders(response.headers)
  });
}

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
export const HEAD = proxy;
