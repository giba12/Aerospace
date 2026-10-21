# CR-25: Sidecar estimator keys before the Kalman filter exists

**Status: APPROVED and APPLIED, 2026-10-19** (owner decision in chat: "Write est_* keys as null").

| Field | Value |
|---|---|
| Severity · Type | Low · Gap (G) |
| Affects | Baseline §8.5 (sidecar contract), §8.3 (one housekeeping row), revision history |
| Found | Starting M2: §8.5 lists `est_q_m2ps3`, `est_r_m2`, `est_p0_pos_m2`, `est_p0_vel_m2ps2` as required keys, but the estimator parameters they record do not exist until M3 |

## 1. What it is
The contract requires four estimator keys that the M0 stand-in estimator has no values for. Options were: omit
them until M3 (key set differs between M2 and M3), add fake `--est-*` flags now, or write `null`.

## 2. Change
- **§8.5, append:** "An estimator key is `null` when the estimator in use has no such parameter (the M0/M2
  stand-in). The key set is the same in every `schema_version` 1 file."
- **§8.3, housekeeping (not part of the decision above):** the `--steps` row now reads `integer 0 to 100000`,
  matching the cap (`kMaxSteps`) added during the code review. The code already enforces it.
- **Revision history:** `0.3 · 2026-10-19 · CR-25 applied: sidecar estimator keys may be null (§8.5); §8.3 --steps range.`

## 3. Why, effect
`schema_version` 1 then means one thing at M2 and M3, and no flag exists that a stand-in would silently ignore.
At M3 the keys become numbers; `analyze.py` (M4) treats `null` as "no estimator parameters". No production-code
risk; `sidecar.cpp` already writes `null`, tested by `Sidecar.RecordsEffectiveSettingsAndTheSeed` and the system
test `test_sidecar_has_the_contract_keys_and_records_the_run`.
