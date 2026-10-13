# Phase 8A.3 Windows readiness

Status: TASK_ACCOUNT_NOT_VERIFIED; unattended deployment not ready.

The available interactive identity is recorded in `validation/windows_environment.json`. No intended unattended identity or credentials were supplied, so this run cannot establish that account's file permissions, network, certificates or environment.

`run_collection.bat` sets the repository working directory from its own absolute location, checks `.venv\Scripts\python.exe`, invokes that pinned environment relative to the fixed directory, sets UTF-8/no-bytecode, and propagates the Python exit code. The resolved absolute Python path is recorded in the environment evidence. The launcher and engine were not modified.

Two executions of the supported `run_collection.bat --dry-run` completed. The explicit cmd.exe invocation returned 2, matching COLLECTION_DEGRADED; see `validation/launcher_exit_code.txt`. The final run took 26.89386 seconds. The first tool's PowerShell wrapper reported exit 1 on native-command failure, so the batch exit was separately captured with cmd.exe and LASTEXITCODE rather than inferred from the wrapper.

The available account could read sealed inputs, create receipts/evidence directories and a 23-file staged snapshot, and acquire/release the shared writer lock. No lock remains. Run manifests record UTC and Asia/Tashkent (+05:00) consistently. The supported scheduling days remain 1, 11 and 21. No task was installed or clock time selected.

HTTP attempts are bounded at three for transient connection/timeout/429/5xx failures, with (15,45)-second connect/read timeouts and backoff. Proxy and TLS failures fail immediately. This is a per-request bound, not a global runtime deadline; archive traversal and FX history can take longer with a functioning network. This run cannot estimate a successful full live collection runtime.

Regression evidence covers competing locks, interruption/recovery, hash validation and exit states using isolated synthetic roots. No live interruption or competing production writer was induced. Readiness still requires task-account connectivity, permissions, runtime measurement and exit-code monitoring.
