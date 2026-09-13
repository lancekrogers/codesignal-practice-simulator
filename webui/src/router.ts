/**
 * A small validated route model (D004). Routes live in the URL path so reload,
 * back and forward reconstruct the screen; the capability token never enters
 * route state (it is captured from the fragment and removed by `api.ts`), and
 * no source text is ever encoded in a route.
 */

export type Route =
  | { kind: "library" }
  | { kind: "attempt"; attemptId: string }
  | { kind: "history" }
  | { kind: "review"; attemptId: string }
  | { kind: "unknown"; path: string };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

export function parseRoute(pathname: string): Route {
  const path = pathname.replace(/\/+$/, "") || "/";
  if (path === "/") return { kind: "library" };
  if (path === "/history") return { kind: "history" };
  const attempt = /^\/attempt\/([^/]+)$/.exec(path);
  if (attempt && UUID.test(attempt[1])) return { kind: "attempt", attemptId: attempt[1] };
  const review = /^\/history\/review\/([^/]+)$/.exec(path);
  if (review && UUID.test(review[1])) return { kind: "review", attemptId: review[1] };
  return { kind: "unknown", path };
}

export function routePath(route: Route): string {
  switch (route.kind) {
    case "library":
      return "/";
    case "attempt":
      return `/attempt/${route.attemptId}`;
    case "history":
      return "/history";
    case "review":
      return `/history/review/${route.attemptId}`;
    default:
      return route.path;
  }
}

type RouteHandler = (route: Route) => void;

let handler: RouteHandler | null = null;
let listening = false;
let attemptOpener: ((attemptId: string) => void) | null = null;

/**
 * The application registers how an explicitly chosen attempt opens (route
 * change plus reconnect). Attempt-level code calls `openAttempt` after a
 * confirmed action such as restart, so the replacement opens directly instead
 * of stopping at the route's continue screen.
 */
export function registerAttemptOpener(opener: (attemptId: string) => void): void {
  attemptOpener = opener;
}

export function openAttempt(attemptId: string): void {
  if (attemptOpener) attemptOpener(attemptId);
  else navigateTo({ kind: "attempt", attemptId });
}

export function installRouter(next: RouteHandler): void {
  handler = next;
  if (listening) return;
  listening = true;
  window.addEventListener("popstate", () => {
    handler?.(parseRoute(window.location.pathname));
  });
}

export function currentRoute(): Route {
  return parseRoute(window.location.pathname);
}

/**
 * Push (or replace) a route. With `silent`, the caller renders the screen
 * itself and only the history entry changes; back/forward still route
 * normally because they arrive through `popstate`.
 */
export function navigateTo(
  route: Route,
  options: { replace?: boolean; silent?: boolean } = {},
): void {
  const path = routePath(route);
  if (window.location.pathname !== path) {
    // The fragment carries only non-secret view state (attempt id, level, tab)
    // once the capability was captured; keeping it lets a resumed attempt
    // restore its selected level and tab.
    const target = `${path}${window.location.hash}`;
    if (options.replace) window.history.replaceState(null, "", target);
    else window.history.pushState(null, "", target);
  }
  if (!options.silent) handler?.(route);
}
