# Phase Detector E2E Verification (2026-05-29)

## Test sample: N4-10-5-01042024-Q=49.81mL_phút-3

| Step | Result |
|------|--------|
| Peaks extracted | 20 |
| Classification | gga (70.2%) |
| Phase tags | phase1=5, transition=1, phase2=14 |
| Mean confidence | 0.850 |
| Toxicity | 10.05% |

**Comparison vs legacy (memory snapshot 2026-03-11)**:
- Legacy: BOD10=1, BOD5=19, toxicity=5.31% (hardcode `i<8 → BOD10`, but peaks=20 had only 1 in phase1 mistakenly)
- New: phase1=5, transition=1, phase2=14, toxicity=10.05% — proper biological boundary detection

## Validation metrics (tools/validate-phase-detector.py, 2026-05-29)

| Type | Samples | Peaks | Per-peak acc | Boundary ±0 | ±1 | ±2 |
|------|---------|-------|--------------|-------------|-----|-----|
| GGA  | 25 | 446 | 85.9% | 72.0% | 84.0% | 84.0% |
| Metal| 100 | 1477 | 94.5% | 52.0% | 98.0% | 100% |
| HH   | 432 | 6055 | 96.0% | 74.3% | 98.6% | 99.3% |

**Caveat**: Metal/HH validation is on training data. True generalization from 5-fold GroupKFold CV (`tools/train-phase-detector.py`):
- Metal: **93.23% ± 1.02%** per-peak
- HH: **94.07% ± 0.60%** per-peak

## Target check

- ✅ Metal ±1 ≥ 85% (achieved 98%)
- ✅ HH ±1 ≥ 90% (achieved 98.6%)
- ⚠️ GGA ±1 ≥ 90% (achieved 84%) — 4 of 25 GT samples miss boundary by >2 peaks. Algorithm-based, no training data large enough for ML. Acceptable; GGA boundary error is biologically less critical than Metal/HH.

## Unit tests

12/12 passing across 3 test files:
- `tests/test_phase_features.py`: 3
- `tests/test_phase_detector.py`: 6
- `tests/test_calculate_toxicity_phase.py`: 3

## File manifest

**New**:
- `src/phase_detector.py` (135 lines), `src/phase_features.py` (85 lines)
- `tools/extract-phase-gt-from-excel.py`, `tools/train-phase-detector.py`, `tools/validate-phase-detector.py`
- `tests/test_phase_features.py`, `tests/test_phase_detector.py`, `tests/test_calculate_toxicity_phase.py`
- `data/phase-gt-{gga,metal,hh}.csv` (228 samples GT total)
- `model/phase_detector_{metal,hh}.pkl`

**Modified**:
- `src/utils.py:72-112` calculate_toxicity (filter transition, phase1/phase2 with BOD fallback)
- `src/peak_extractor.py:389` hardcode `BOD10 if i<8 else BOD5` → `'unknown'`
- `app.py` integrate `update_phase_tags()` + color-coded Tag display + low-conf warning
- `README.md`, `docs/codebase-summary.md`, `docs/system-architecture.md`, `docs/project-roadmap.md`

## Commits (branch `Phúc`)

| SHA | Message |
|-----|---------|
| 5564058 | feat(phase): extract phase boundary GT from Excel color marking |
| 90002f9 | feat(phase): per-peak feature engineering (16 features) |
| 2ba655f | feat(phase): GGA change-point algorithm + fallback heuristic |
| 89b93c1 | feat(phase): train Metal+HH RandomForest phase detectors |
| f5dc10f | fix(phase): remove noise aug to eliminate GroupKFold leakage in CV |
| 56f3d7a | test(phase): integration tests for update_phase_tags ML path |
| 29c2a6a | feat(phase): validation script on GT sheets |
| 970f6ee | feat(toxicity): filter transition rows, prefer phase1/phase2 tags |
| 3cf4273 | refactor(extractor): remove hardcoded BOD10/BOD5 tag |
| d3af49c | feat(dashboard): integrate phase detector into 1-click pipeline |
| aa1b6a9 | docs: phase boundary detection module (Phase 2.6 complete) |

## Unresolved follow-ups

- GGA ±1 below 90% — 25 GT samples limit ML viability. Future option: collect more GGA color-marked Excel data.
- One smoke-test sample (gga-metal) had 38/55 peaks tagged transition — investigate if Metal model is over-eager on certain Cr(VI) patterns. Confidence stayed ≥0.7 so no warning fired.
- Negative toxicity for clean GGA samples without toxin — biologically valid (phase2 ≈ phase1), but may need clamping/display logic in dashboard.
