# Day20 Model Serving Observability

## Audience

The audience is the future maintainer of the Day20 local llama.cpp serving lab. The maintainer is debugging a real local model server, not the simulated Day23 API, and needs to know whether the model is down, slow, or losing generation throughput.

## System

Day20 runs `llama-server.exe` on `localhost:8080` with the OpenAI-compatible API and Prometheus metrics enabled at `/metrics`. Day23 Prometheus scrapes it through `host.docker.internal:8080`.

## Failure Mode

The failure mode I care about is silent model-serving degradation: the server still responds, but generation throughput falls or request backlog grows. A default uptime alert would miss this until users already experience slow responses.

## Three Metrics To Check First

1. `up{job="day20-llamacpp"}` tells whether Prometheus can scrape the real Day20 model server.
2. `llamacpp:predicted_tokens_seconds{job="day20-llamacpp"}` shows generation throughput in tokens per second.
3. `llamacpp:requests_deferred{job="day20-llamacpp"}` shows whether requests are waiting behind the available slots.

## Delivered Artifact

The cross-day Grafana dashboard includes a Day20 panel backed by the real llama.cpp metric `llamacpp:predicted_tokens_seconds`. The dedicated bonus dashboard and alert rule in this folder are kept as code artifacts for the portfolio-style challenge.
