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
| `github/exp/step-3-add-bus-block` | signal + push | yes | **yes** | Full fix — 2nd subscribe should stay True |

---

## Results log (skancra003)

### step-0 — `0.45.0`
- All False 60s, both subscribes False

### step-1 — `exp/step-1-callback-push-only`
- All False 60s (callback never fired True at startup)

### step-2b — `exp/step-2b-init-sync-and-push` (was tested before step-2a existed)
- +3ms True, subscribe1 True, **subscribe2 False**

### step-2a — `exp/step-2a-init-sync-only`
```
(paste timeline here)
```

### step-3 — `exp/step-3-add-bus-block`
```
(paste timeline here)
```

---

## Production diff summary (final = step-3)

1. **Callback push** — liveliness + init sync path notifies Tango (0.45.1 idea, keep signal)
2. **Init sync** — dish responsive at startup → True before Subarray Assign
3. **Bus block** — ignore queued stale `False` after signal is `True`
