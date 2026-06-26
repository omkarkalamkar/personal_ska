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
| 1 | `0059406b` | Callback: signal + **explicit push** | All False (liveliness alone not enough) |
| 2 | `90b376de` | + **init sync** | True by +5ms; **2nd subscribe → False** at +1079ms |
| 3 | `skb-1306-fix` step-3 | + **stale bus block** in `notify_emission` | `post_subscribe_2_read` True? |
| 3 | (next) | + **stale bus block** in `notify_emission` | True stable after subscribe |

## Step 0 result (skancra003)

- `immediate_after_context_start` → False
- `startup_poll_1` … `startup_poll_60` → all False
- `post_subscribe_1_read`, `post_subscribe_2_read` → False
- **Never True in 60s**

## Step 1 result (skancra003)

- All False for 60s — **callback push alone does not help** (nothing sets True at startup; liveliness path did not fix read in time)

## Step 2 result (skancra003)

- `immediate_after_context_start` → **True** (+3ms) — init sync works
- `startup_poll_1` → True
- `post_subscribe_1_read` → True
- `post_subscribe_2_read` → **False** — stale bus False on 2nd subscribe

## Step 3 — record your result here

```
first True at: startup_poll___ / never / post_subscribe___
```
