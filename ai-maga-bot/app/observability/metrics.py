"""Prometheus metrics for AI-Maga."""

import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response


# Request counters
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['status', 'model']
)

tts_requests_total = Counter(
    'tts_requests_total', 
    'Total TTS requests',
    ['status', 'voice']
)

stt_requests_total = Counter(
    'stt_requests_total',
    'Total STT requests', 
    ['status']
)

telegram_requests_total = Counter(
    'telegram_requests_total',
    'Total Telegram requests',
    ['method', 'status']
)

# Error counters
llm_errors_total = Counter(
    'llm_errors_total',
    'Total LLM errors',
    ['error_type']
)

tts_errors_total = Counter(
    'tts_errors_total',
    'Total TTS errors', 
    ['error_type']
)

stt_errors_total = Counter(
    'stt_errors_total',
    'Total STT errors',
    ['error_type']
)

# Latency histograms
llm_latency_seconds = Histogram(
    'llm_latency_seconds',
    'LLM request latency',
    ['model'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

tts_latency_seconds = Histogram(
    'tts_latency_seconds',
    'TTS request latency',
    ['voice'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

stt_latency_seconds = Histogram(
    'stt_latency_seconds',
    'STT request latency',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

telegram_latency_seconds = Histogram(
    'telegram_latency_seconds',
    'Telegram request latency',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# Queue sizes
queue_size = Gauge(
    'queue_size',
    'Current queue size',
    ['queue_type']
)

# Active users
active_users = Gauge(
    'active_users',
    'Number of active users'
)

# Circuit breaker states
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state',
    ['service', 'state']  # state: 0=closed, 1=half-open, 2=open
)


class MetricsCollector:
    """Metrics collector for AI-Maga services."""
    
    def __init__(self):
        self.start_time = time.time()
    
    def record_llm_request(self, status: str, model: str, duration: float):
        """Record LLM request metrics."""
        llm_requests_total.labels(status=status, model=model).inc()
        llm_latency_seconds.labels(model=model).observe(duration)
        
        if status == "error":
            llm_errors_total.labels(error_type="api_error").inc()
    
    def record_tts_request(self, status: str, voice: str, duration: float):
        """Record TTS request metrics."""
        tts_requests_total.labels(status=status, voice=voice).inc()
        tts_latency_seconds.labels(voice=voice).observe(duration)
        
        if status == "error":
            tts_errors_total.labels(error_type="api_error").inc()
    
    def record_stt_request(self, status: str, duration: float):
        """Record STT request metrics."""
        stt_requests_total.labels(status=status).inc()
        stt_latency_seconds.observe(duration)
        
        if status == "error":
            stt_errors_total.labels(error_type="api_error").inc()
    
    def record_telegram_request(self, method: str, status: str, duration: float):
        """Record Telegram request metrics."""
        telegram_requests_total.labels(method=method, status=status).inc()
        telegram_latency_seconds.observe(duration)
    
    def record_cache_hit(self, cache_type: str):
        """Record cache hit."""
        cache_hits_total.labels(cache_type=cache_type).inc()
    
    def record_cache_miss(self, cache_type: str):
        """Record cache miss."""
        cache_misses_total.labels(cache_type=cache_type).inc()
    
    def set_queue_size(self, queue_type: str, size: int):
        """Set queue size."""
        queue_size.labels(queue_type=queue_type).set(size)
    
    def set_active_users(self, count: int):
        """Set active users count."""
        active_users.set(count)
    
    def set_circuit_breaker_state(self, service: str, state: str):
        """Set circuit breaker state."""
        state_value = {"closed": 0, "half-open": 1, "open": 2}.get(state, 0)
        circuit_breaker_state.labels(service=service, state=state).set(state_value)
    
    def get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time


# Global metrics collector
metrics_collector = MetricsCollector()


def get_metrics_response() -> Response:
    """Get Prometheus metrics response."""
    data = generate_latest()
    return Response(
        content=data,
        media_type=CONTENT_TYPE_LATEST
    )


def get_metrics_summary() -> Dict[str, Any]:
    """Get metrics summary for admin endpoints."""
    return {
        "uptime_seconds": metrics_collector.get_uptime(),
        "llm_requests": {
            "total": llm_requests_total._value.sum(),
            "errors": llm_errors_total._value.sum()
        },
        "tts_requests": {
            "total": tts_requests_total._value.sum(),
            "errors": tts_errors_total._value.sum()
        },
        "stt_requests": {
            "total": stt_requests_total._value.sum(),
            "errors": stt_errors_total._value.sum()
        },
        "cache": {
            "hits": cache_hits_total._value.sum(),
            "misses": cache_misses_total._value.sum()
        },
        "active_users": active_users._value,
        "queues": {
            "size": queue_size._value.sum()
        }
    }
