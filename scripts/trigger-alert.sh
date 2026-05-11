#!/usr/bin/env bash
## Trigger an alert by killing the app, wait for it to fire, then restore.
## Used in: deck §10 demo, lab Track 02 grading checkpoint.

set -euo pipefail

echo "Step 1: kill app container"
docker stop day23-app >/dev/null

echo "Step 2: wait up to 150s for ServiceDown alert to fire"
fired=0
for i in {1..30}; do
  sleep 5
  alerts=$(curl -fsS http://localhost:9093/api/v2/alerts 2>/dev/null | grep -c '"alertname":"ServiceDown"' || true)
  if [ "$alerts" -gt 0 ]; then
    echo "  alert fired (after ${i}*5s)"
    fired=1
    break
  fi
  echo "  no alert yet (${i}*5s)"
done

if [ "$fired" -ne 1 ]; then
  echo "ServiceDown did not fire within 150s" >&2
  docker start day23-app >/dev/null || true
  exit 1
fi

echo "Step 3: restart app"
docker start day23-app >/dev/null

echo "Step 4: wait up to 180s for alert to resolve"
for i in {1..36}; do
  sleep 5
  alerts=$(curl -fsS http://localhost:9093/api/v2/alerts 2>/dev/null | grep -c '"alertname":"ServiceDown"' || true)
  if [ "$alerts" -eq 0 ]; then
    echo "  alert resolved"
    exit 0
  fi
done

echo "alert did not resolve within 180s" >&2
exit 1
