# Runbook: Day20 llama.cpp Serving Degradation

## Alert

`Day20LlamaCppDegraded` means the Day20 llama.cpp target is unreachable, generation throughput is too low, or requests are being deferred.

## First Checks

1. Open `http://localhost:8080/health` or `http://localhost:8080/metrics`.
2. Check whether `llama-server.exe` is still running.
3. Open the Day23 cross-day dashboard and confirm the Day20 tokens/sec panel.
4. Inspect Day20 server logs for CUDA memory, model load, or slot saturation messages.

## Mitigation

If the server is down, restart it from the Day20 repo:

```powershell
.\02-llama-cpp-server\start-server.ps1
```

If throughput is low but the server is up, reduce concurrency, lower `LAB_PARALLEL`, or switch to the smaller Q2_K model for a quick recovery. After recovery, run the Day20 smoke test and confirm Prometheus target `day20-llamacpp` is `up`.

## Follow-up

If this repeats, compare `llamacpp:predicted_tokens_seconds`, `llamacpp:requests_deferred`, and GPU memory usage before changing model quantization, context size, or parallel slot count.
