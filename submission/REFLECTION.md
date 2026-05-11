# Day 23 Lab Reflection

**Sinh viên:** Huynh Nhut Huy
**Ngày nộp:** 2026-05-11
**Lab repo URL:** https://github.com/TesWy/2A202600084-HuynhNhutHuy-Day23

---

## 1. Hardware + Setup Output

File `00-setup/setup-report.json` đã được tạo và commit:

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

Stack Day23 đã chạy local với FastAPI, Prometheus, Grafana, Alertmanager, Loki, Jaeger và OpenTelemetry Collector. Vì không tạo được Slack workspace riêng, em dùng Discord thông qua một local alert relay để nhận alert fire và resolve.

---

## 2. Track 02 - Dashboards & Alerts

Các ảnh evidence đã nộp:

- `submission/screenshots/dashboard-overview.png`
- `submission/screenshots/slo-burn-rate.png`
- `submission/screenshots/cost-and-tokens.png`
- `submission/screenshots/alertmanager-firing.png`
- `submission/screenshots/alertmanager-resolved.png`
- `submission/screenshots/discord-alerts.png`

Quy trình thử alert:

| Thời điểm | Hành động / trạng thái | Evidence |
|---|---|---|
| T0 | Dừng container `day23-app` | `alertmanager-firing.png` |
| T0 + khoảng 115s | Alert `ServiceDown` fire | `discord-alerts.png` có message `[FIRING]` trên Discord |
| T1 | Khởi động lại `day23-app` | app health trở lại bình thường |
| T1 + khoảng 25s | Alert resolved | `discord-alerts.png` có message `[RESOLVED]` trên Discord |

Điều làm em bất ngờ nhất ở Prometheus và Grafana là metric đúng chưa chắc dashboard đã hữu ích. Datasource UID, template variable và label filter phải khớp chính xác thì panel mới có data. Từ đó em thấy dashboard cũng nên được xem như code: query, label, provisioning và screenshot evidence đều cần version control rõ ràng.

---

## 3. Track 03 - Tracing & Logs

Các ảnh evidence đã nộp:

- `submission/screenshots/jaeger-trace.png`
- `submission/screenshots/jaeger-attrs.png`

Ảnh Jaeger trace cho thấy một request `POST /predict` với các span ứng dụng gồm `predict`, `embed-text`, `vector-search` và `generate-tokens`. Span `generate-tokens` có các GenAI semantic attributes như input tokens, output tokens và finish reason.

Một JSON log line có thể correlate với trace:

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

Tail-sampling math: policy của collector giữ toàn bộ error traces, toàn bộ traces chậm hơn 2000 ms, và 1% healthy traces. Nếu service tạo 100 traces/sec và không có trace nào error hoặc slow, collector sẽ giữ `100 * 0.01 = 1 trace/sec`. Nếu có 2 traces/sec là slow hoặc error, collector sẽ giữ 2 trace đó cộng thêm khoảng 1% của 98 healthy traces còn lại: `2 + 0.98 = 2.98 traces/sec`, xấp xỉ 3%.

---

## 4. Track 04 - Drift Detection

Nội dung `04-drift-detection/reports/drift-summary.json`:

```json
{
  "prompt_length": {"psi": 3.461, "kl": 1.7982, "ks_stat": 0.702, "ks_pvalue": 0.0, "drift": "yes"},
  "embedding_norm": {"psi": 0.0187, "kl": 0.0324, "ks_stat": 0.052, "ks_pvalue": 0.133853, "drift": "no"},
  "response_length": {"psi": 0.0162, "kl": 0.0178, "ks_stat": 0.056, "ks_pvalue": 0.086899, "drift": "no"},
  "response_quality": {"psi": 8.8486, "kl": 13.5011, "ks_stat": 0.941, "ks_pvalue": 0.0, "drift": "yes"}
}
```

Với `prompt_length`, em sẽ ưu tiên PSI vì câu hỏi chính là production prompt có bị lệch theo các bucket so với reference period không. Với `embedding_norm`, em chọn KS vì đây là scalar liên tục, thay đổi hình dạng phân phối quan trọng hơn việc chia bucket cố định. Với `response_length`, em sẽ chọn KS hoặc PSI tùy volume: KS nhạy hơn với phân phối liên tục, còn PSI dễ đọc hơn trong dashboard vận hành. Với `response_quality`, em chọn KS cho score liên tục và chỉ alert khi shift kéo dài, vì quality score thường nhiễu.

---

## 5. Track 05 - Cross-Day Integration

Ảnh evidence:

- `submission/screenshots/cross-day-dashboard.png`

Em đã kết nối một source thật từ lab ngày trước: Day20 Model Serving. Day20 chạy native `llama-server.exe` trên `localhost:8080`, còn Day23 Prometheus scrape metric qua `host.docker.internal:8080/metrics` với job `day20-llamacpp`. Cross-day dashboard render đủ 6 panel; panel Day20 có data thật từ metric `llamacpp:predicted_tokens_seconds{job="day20-llamacpp"}`.

Metric prior-day khó expose nhất là metric của Day20 llama.cpp, vì Python fallback server không expose cùng endpoint `/metrics`. Để có metric thật, em phải dùng native llama.cpp binary với flag `--metrics`, sau đó để Prometheus trong Docker scrape qua `host.docker.internal` thay vì `localhost`.

---

## 6. Thay Đổi Quan Trọng Nhất

Thay đổi quan trọng nhất là làm cho span `predict` trở thành current parent span trong lúc các child span chạy. Trước đó hệ thống vẫn có thể emit spans, nhưng Jaeger không thể hiện rõ quan hệ nhân quả giữa các bước. Khi `predict` là active span, các span `embed-text`, `vector-search` và `generate-tokens` nằm dưới cùng một request trace, giúp hệ thống trở nên giải thích được thay vì chỉ có telemetry rời rạc.

Điều này liên hệ trực tiếp với ý chính của observability trong deck: telemetry chỉ hữu ích khi nó trả lời được câu hỏi vận hành. Một danh sách span phẳng chỉ nói rằng "có việc đã chạy"; một parent-child trace nói rõ request đã đi qua embedding, retrieval rồi generation. Cấu trúc đó giúp người on-call quyết định vấn đề nằm ở generation của model, vector search, hay API wrapper.
