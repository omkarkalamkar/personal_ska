# SKB-1306 — one change at a time (isolated git branches)

Each branch changes **only** what the name says. Same probe every time.

```bash
cd ~/skb-1306/personal_ska
git fetch github --tags

# diagnostic tests (once)
git checkout github/skb-1306-fix -- \
  tests/integration/skb_1306_test_devices.py \
  tests/integration/test_is_subsystem_available_diagnostic_skb_1306.py \
  tests/unit/skb_1306_availability_timeline.py
```

## Run probe after each checkout

```bash
git checkout github/exp/step-XXXX   # see table below
poetry run pytest tests/integration/test_is_subsystem_available_diagnostic_skb_1306.py -v -s -o addopts="" 2>&1 | tee probe-<name>.log
grep -A20 'timeline' probe-<name>.log
```

---

## Experiment matrix (isolated)

| Checkout | Callback | Init sync | Bus block | What you learn |
|----------|----------|-----------|-----------|----------------|
| `0.45.0` or `github/release-0.45.0` | signal only | no | no | Baseline — all False ✅ done |
| `github/exp/step-1-callback-push-only` | signal + **push** | no | no | Push alone useless without True trigger ✅ done |
| `github/exp/step-2a-init-sync-only` | signal only | **yes** | no | **Does init alone make read True?** ← run this |
| `github/exp/step-2b-init-sync-and-push` | signal + push | yes | no | Both without bus block ✅ done |
| `github/exp/step-3-add-bus-block` | signal + push | yes | **yes** | Bus block alone — subscribe1 flaky (see step-3 result) |
| `github/exp/step-3b-repair-on-block` | signal + push + **cache repair** | yes | yes + repair | subscribe1 True, subscribe2 still False |
| `github/exp/step-3c-hook-repair` | step-3b + **always_executed_hook repair** | yes | yes + repair | Full fix — both subscribes should stay True |

---

## Results log (skancra003)

### step-0 — `0.45.0`
- All False 60s, both subscribes False

### step-1 — `exp/step-1-callback-push-only`
- All False 60s (callback never fired True at startup)

### step-2a — `exp/step-2a-init-sync-only` (init only, **no** callback push)
- +6ms True at startup — **init sync alone enough for early read**
- +15ms pre_subscribe True
- **+605ms post_subscribe_1 → False** — first subscribe breaks without push
- subscribe2 False

**Conclusion:** push in callback is required for subscribe/read stability (not for startup).

### step-2b — `exp/step-2b-init-sync-and-push`
- +3ms True, subscribe1 **True**, subscribe2 **False**

### step-3 — `exp/step-3-add-bus-block` (`3dc06441`, checkout verified on skancra003)
- +12ms True, pre_subscribe True
- **+584ms post_subscribe_1 → False** (same pattern as step-2a, not step-2b)
- subscribe2 False

**Note:** Code had push + bus block; step-2b subscribe1 True may have been timing. Reads use `__attr_values` (only updated by `on_emission`); explicit push does not sync that cache.

### step-3b — repair on block (skancra003)
- +5ms True, pre_subscribe True
- **+567ms post_subscribe_1 → True** (fixed vs step-3)
- between_subscribes True
- **+1079ms post_subscribe_2 → False** (same as step-2b)

### step-3c — `exp/step-3c-hook-repair`
```
(paste timeline here)
```

---

## Production diff summary (final = step-3c)

1. **Callback push** — liveliness + init sync path notifies Tango (0.45.1 idea, keep signal)
2. **Init sync** — dish responsive at startup → True before Subarray Assign
3. **Bus block + cache repair** — ignore queued stale `False`; sync `__attr_values` and re-push True
4. **Hook repair** — after every client request (incl. subscribe), re-sync cache from signal storage
