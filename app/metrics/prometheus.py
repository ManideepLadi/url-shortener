"""Prometheus metric definitions and helpers."""

from prometheus_client import Counter, Gauge, Histogram

# HTTP observability
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Business metrics
URLS_CREATED_TOTAL = Counter(
    "url_shortener_urls_created_total",
    "Short URLs created",
    ["alias_source", "strategy"],
)

REDIRECTS_TOTAL = Counter(
    "url_shortener_redirects_total",
    "Redirect requests resolved",
    ["cache_result"],
)

METADATA_REQUESTS_TOTAL = Counter(
    "url_shortener_metadata_requests_total",
    "Metadata API requests",
)

REDIRECT_CACHE_ENTRIES = Gauge(
    "url_shortener_redirect_cache_entries",
    "Number of alias→URL mappings in the redirect cache",
)

REDIRECT_CACHE_PENDING_HITS = Gauge(
    "url_shortener_redirect_cache_pending_hits",
    "Total buffered redirect hit counts awaiting flush",
)


def normalize_metrics_path(path: str) -> str:
    """
    Map request paths to low-cardinality route labels.

    Avoids exploding metric cardinality from unbounded alias values.
    """
    if path in {"/health", "/metrics", "/openapi.json", "/docs", "/redoc"}:
        return path
    if path.startswith("/docs/"):
        return "/docs"
    if path == "/api/v1/urls":
        return "/api/v1/urls"
    if path.startswith("/api/v1/urls/"):
        return "/api/v1/urls/{alias}"
    if path.count("/") == 1 and len(path) > 1:
        return "/{alias}"
    return "other"


def record_url_created(*, alias_source: str, strategy: str) -> None:
    URLS_CREATED_TOTAL.labels(alias_source=alias_source, strategy=strategy).inc()


def record_redirect(*, cache_hit: bool) -> None:
    REDIRECTS_TOTAL.labels(cache_result="hit" if cache_hit else "miss").inc()


def record_metadata_request() -> None:
    METADATA_REQUESTS_TOTAL.inc()


def refresh_cache_gauges(*, redirect_entries: int, pending_hits: int) -> None:
    REDIRECT_CACHE_ENTRIES.set(redirect_entries)
    REDIRECT_CACHE_PENDING_HITS.set(pending_hits)
