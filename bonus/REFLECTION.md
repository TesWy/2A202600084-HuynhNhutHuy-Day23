# Bonus Reflection

What surprised me was that the hardest part was not scraping the Day20 model server. The harder part was deciding which signal would actually help during an incident. `up` only proves that the endpoint is reachable; the useful signal is generation throughput plus deferred requests, because those show whether llama.cpp is becoming slow while still technically alive.

If I had another 8 hours, I would add a small load generator that runs one fixed prompt every minute and records a stable synthetic SLI for Day20: success, latency, prompt tokens/sec, generation tokens/sec, and GPU memory. That would make the alert less dependent on opportunistic traffic and more useful for a real on-call loop.
