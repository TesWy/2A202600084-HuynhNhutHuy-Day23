# Day 23 Lab Reflection

**Student:** Huynh Nhut Huy
**Submission date:** 2026-05-11
**Lab repo URL:** https://github.com/TesWy/2A202600084-HuynhNhutHuy-Day23

---

## 1. Hardware + Setup Output

`00-setup/setup-report.json` was generated and committed:

```json
{
  "docker": {"ok": true, "version": "28.3.2"},
  "compose_v2": {"ok": true, "version": "2.38.2-desktop.1"},
  "ram_gb_available": 11.39,
  "ram_ok": true,
  "required_ports": [8000, 9090, 9093, 3000, 3100, 16686, 4317, 4318, 8888],
  "bound_ports": [],
  "all_ports_free": true
}
```

The Day23 stack ran locally with FastAPI, Prometheus, Grafana, Alertmanager, Loki, Jaeger, and the OpenTelemetry Collector. Discord was used through a local alert relay because Slack workspace creation was not available.

---

## 2. Track 02 - Dashboards & Alerts

Evidence screenshots:

- `submission/screenshots/dashboard-overview.png`
- `submission/screenshots/slo-burn-rate.png`
- `submission/screenshots/cost-and-tokens.png`
- `submission/screenshots/alertmanager-firing.png`
- `submission/screenshots/alertmanager-resolved.png`

Alert drill:

| When | What | Evidence |
|---|---|---|
| T0 | stopped `day23-app` | `alertmanager-firing.png` |
| T0 + about 115s | `ServiceDown` fired | Alertmanager firing screenshot and Discord relay logs |
| T1 | restarted `day23-app` | app health returned |
| T1 + about 25s | alert resolved | `alertmanager-resolved.png` and Discord relay logs |

One thing that surprised me about Prometheus and Grafana was how easy it is to have a correct metric but an empty panel. The datasource UID and dashboard template value had to match exactly before the panels became useful. The dashboard was not useful until the queries, label filters, and datasource provisioning were treated as code.

---

## 3. Track 03 - Tracing & Logs

Evidence screenshots:

- `submission/screenshots/jaeger-trace.png`
- `submission/screenshots/jaeger-attrs.png`

The trace screenshot shows one `POST /predict` request with the application spans `predict`, `embed-text`, `vector-search`, and `generate-tokens`. The `generate-tokens` span includes GenAI semantic attributes such as input tokens, output tokens, and finish reason.

Structured JSON log line correlated to a trace:

```json
{
  "model": "llama3-mock",
  "input_tokens": 4,
  "output_tokens": 60,
  "quality": 0.837,
  "duration_seconds": 2.169,
  "trace_id": "dd462de6bd1ae76775c7c874ff8a857a",
  "event": "prediction served",
  "level": "info",
  "timestamp": "2026-05-11T05:11:01.780000Z"
}
```

Tail-sampling math: the collector policy keeps all error traces, all traces slower than 2000 ms, and 1% of healthy traces. If the service produced 100 traces/sec and none were errors or slow, the collector would keep `100 * 0.01 = 1 trace/sec`. If 2 traces/sec were slow or errors, it would keep those 2 plus about 1% of the remaining 98 healthy traces: `2 + 0.98 = 2.98 traces/sec`, or about 3%.

---

## 4. Track 04 - Drift Detection

`04-drift-detection/reports/drift-summary.json`:

```json
{
  "prompt_length": {"psi": 3.461, "kl": 1.7982, "ks_stat": 0.702, "ks_pvalue": 0.0, "drift": "yes"},
  "embedding_norm": {"psi": 0.0187, "kl": 0.0324, "ks_stat": 0.052, "ks_pvalue": 0.133853, "drift": "no"},
  "response_length": {"psi": 0.0162, "kl": 0.0178, "ks_stat": 0.056, "ks_pvalue": 0.086899, "drift": "no"},
  "response_quality": {"psi": 8.8486, "kl": 13.5011, "ks_stat": 0.941, "ks_pvalue": 0.0, "drift": "yes"}
}
```

For `prompt_length`, I would use PSI first because the main question is whether production prompt buckets shifted compared with the reference period. For `embedding_norm`, I would use KS because it is a continuous scalar where a distribution-shape change matters more than fixed buckets. For `response_length`, I would use KS or PSI depending on volume: KS for continuous sensitivity, PSI for operational dashboards that need stable bucketed interpretation. For `response_quality`, I would use KS for the continuous score and alert only after confirming the shift is sustained, because quality scores can be noisy.

---

## 5. Track 05 - Cross-Day Integration

Evidence screenshot:

- `submission/screenshots/cross-day-dashboard.png`

I connected a real prior-day source from Day20 Model Serving. Day20 runs native `llama-server.exe` on `localhost:8080`, and Day23 Prometheus scrapes it through `host.docker.internal:8080/metrics` using the `day20-llamacpp` job. The cross-day dashboard renders all 6 panels; the Day20 panel has real data from `llamacpp:predicted_tokens_seconds{job="day20-llamacpp"}`.

The hardest prior-day metric to expose was the Day20 llama.cpp metric because the Python fallback server does not expose the same `/metrics` endpoint. The native llama.cpp binary had to be used with `--metrics`, then Prometheus had to scrape from Docker through `host.docker.internal` rather than `localhost`.

---

## 6. The Single Change That Mattered Most

The single change that mattered most was making the `predict` span the current parent span while the child spans run. Before that, it was possible to emit spans but still lose the useful causal shape in Jaeger. Once `predict` became the active span, `embed-text`, `vector-search`, and `generate-tokens` appeared under one request trace, which made the system explainable instead of only instrumented.

That connects directly to the deck's observability point: telemetry is useful only when it answers an operational question. A flat list of spans says "work happened"; a parent-child trace says "this request spent time in embedding, retrieval, then generation." That structure is what lets an on-call engineer decide whether the issue is model generation, vector search, or the API wrapper.
