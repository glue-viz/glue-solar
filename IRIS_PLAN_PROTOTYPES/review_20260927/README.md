# Plan review and restructure evidence, 2026-09-27

This folder backs the restructured [plan](../../IRIS_GLUE_GAP_PLAN.md) and
its [feature map](../../IRIS_CRISPEX_FEATURES.md). Finding ids cited in the
plan (for example `wp4-quicklook-1`, `followup-2-1`) resolve here.

| File | Contents |
| --- | --- |
| `iris-plan-review.md` | Human-readable report of the review: every finding and its adversarial verification, the 203-row CRISPEX coverage matrix, commands run, and claims confirmed correct |
| `findings.json` | The 203 verified findings (area, kind, severity, verdict, verified statement, recommendation, evidence) |
| `features.json` | The 203 CRISPEX and IRIS-SolarSoft features with coverage status, priority, Glue evidence and scope (in scope, excluded, covered by an equivalent) |
| `feas.json` | Feasibility of the must-have features and M0 blockers: approach, upstream dependencies, effort, risks and the verifier's corrections (the corrections win) |
| `protos.json` | Port, keep or archive verdict for each prototype, with the verifier's corrections |
| `work.json` | Work items proposed per feature, before they were edited into the plan's checkboxes, plus the critic's issues |
| `dispo.json` | How the restructure handles each finding (new or modified checkbox, text fix, decision, history) |
| `probes/` | Probe scripts cited as evidence: the WCS thread race, slider cost, index-free -TAB WCS, large-data modal, memory, load time and ROI probes (`wp10/`), the link-graph permutation matrix (`linkgraph/`), the WP8 verifier tests (`wp8/`) and the fill/mask patch (`data-quality/patch.diff`). Paths inside were rewritten to `~/` or `<session-scratch>`; adjust them before running. |
| `gen_features_map.py` | Regenerates `IRIS_CRISPEX_FEATURES.md` from the plan's checkboxes and `features.json` |
| `restructure-drafts/` | `skeleton.md` (the agreed milestones, decisions D1–D15 and writing rules used for the restructure) and `result3.json` (the work-package writers' feature maps, read by the generator for 'Available today' notes); `result4.json` holds the reconciliation edits |

## How the review was done

1. Four independent inventories of CRISPEX and the IRIS SolarSoft quicklook
   family, built from source code, documentation, the IRIS-9 exercises and
   the SolarSoft tools. They were merged into 203 features.
2. Each feature was checked against glue-core, glue-qt, glue-solar and the
   open PRs, and against the previous plan. A second agent re-checked every
   classification.
3. Eleven reviewers checked the previous plan's claims, re-ran the recorded
   prototype tests and probed real data in `~/DATA/IRIS`. Every finding was
   re-checked by an agent instructed to refute it; 4 were refuted.
4. A completeness critic added four follow-up investigations: the combined
   link graph, real-data scale, a CRISPEX replay in Glue, and a range of
   observation types.
5. The feasibility of each must-have feature and the prototype verdicts were
   probed in the micromamba env `iris-plan` (released glue-core 1.27.0,
   glue-qt 0.4.2, irispy 0.9.0), again with adversarial verification.

Probe scripts ran from a temporary session directory, which paths in these
files show as `<session-scratch>`. Those scripts were not kept. The commands
and measured results are recorded in the JSON and the report. Paths under
the user's home directory are written as `~/`.

The first review pass ran in the solar `.venv` (glue-qt editable at Qt #74,
irispy 0.8.1). The feasibility and prototype passes ran in `iris-plan`. Where
the two disagree, the `iris-plan` results and the plan text win.
