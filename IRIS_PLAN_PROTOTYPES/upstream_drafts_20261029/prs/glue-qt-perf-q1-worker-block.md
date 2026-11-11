# ComputeWorker: block on the work queue instead of polling

- Upstream: glue-viz/glue-qt
- Fork branch: `nabobalis:perf-q1-worker-block` at `f9021842ab` (on the fork, not rebuilt)
- Label: enhancement

## Body

~~~~~markdown
`ComputeWorker` sleeps for 1/25 s at the top of every loop before it drains its work queue. A queued job waits up to 40 ms to start, and `compute_end` is emitted only after a second sleep finds the queue empty, so every threaded histogram or profile computation ends 40 to 80 ms later than it needs to. Every histogram and profile layer has one of these workers, and each wakes 25 times a second for as long as the layer exists.

The worker now blocks on the queue while idle and, once a job has run, looks for more work without sleeping. Requests that arrive while a job runs are still merged into one follow-up job, and `'stop'` still ends the thread.

One difference: the sleep also merged requests made within 40 ms of each other while the worker was idle. Now the first starts at once and the rest are merged into one follow-up job, so two state changes made back to back outside `delay_callback` run two jobs where they ran one. The final result is the same. Adding data, changing one viewer setting, and creating or editing a subset run as many jobs as before.

Time from queuing a 0.5 ms job to `compute_end` (median of 30, PyQt5, macOS): 88 ms before, 0.8 ms after.

`test_compute_worker_blocks_when_idle` in the new `glue_qt/viewers/matplotlib/tests/test_compute_worker.py` fails without the change.
~~~~~

## Notes for the owner (not to paste)

- Not rebuilt: the fork's branch as it is, 2 files, +48 -4. The body is drawn from its commit message.
- Checked today: its test passes on the branch (1 passed) and fails on main (`assert False` on `wait(timeout=5)` of the queue's `blocking` event). My timing probe for `perf-q2` gave 15.0 ms from a subset change to the first profile with this branch, 73.6 ms on main. The macOS number in the body is the commit's own; the job-count claim is the review's check, not mine.
- Open before `perf-q2-slice-profile-sync`, whose numbers are stated on top of this.
