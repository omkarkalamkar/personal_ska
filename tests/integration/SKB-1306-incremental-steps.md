# SKB-1306 incremental probe (run on skancra003)

Base: tag **0.45.0** + diagnostic tests from `github/skb-1306-fix`.

After each step, run:

```bash
poetry run pytest tests/integration/test_is_subsystem_available_diagnostic_skb_1306.py -v -s -o addopts="" 2>&1 | tee probe-stepN.log
grep -E 'SKB-1306 probe|timeline' probe-stepN.log
```

Look for **first `True`** in the timeline (`startup_poll_N` or `post_subscribe_*`).

| Step | Branch commit | Production change | Expected |
|------|---------------|-------------------|----------|
| 0 | `0.45.0` tag | None (signal assign only) | All False (confirmed) |
| 1 | `skb-1306-fix` step-1 | Callback: signal + **explicit push** | True after liveliness? |
| 2 | (next) | + **init sync** on startup | True early in `startup_poll_1`? |
| 3 | (next) | + **stale bus block** in `notify_emission` | True stable after subscribe |

## Step 0 result (skancra003)

- `immediate_after_context_start` → False
- `startup_poll_1` … `startup_poll_60` → all False
- `post_subscribe_1_read`, `post_subscribe_2_read` → False
- **Never True in 60s**

## Step 1 — record your result here

```
first True at: startup_poll___ / never / post_subscribe___
```
