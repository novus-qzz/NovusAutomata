#!/usr/bin/env python3
"""Autonomous 100-iteration loop for the NovusAutomata AI-fix pipeline.

For each iteration:
  1. reset local to origin/main (clean base)
  2. inject a logic bug into app.py
  3. commit + push to main
  4. explicitly trigger 04 workflow via gh workflow run
  5. wait for 04 to auto-fix
  6. verify fixed code passes tests
  7. repeat until N iterations completed

Uses a log file for crash-resumability.
"""
import json
import os
import random
import subprocess
import sys
import time

REPO = subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True
).strip()
os.chdir(REPO)
REMOTE_URL = subprocess.check_output(
    ["git", "remote", "get-url", "origin"], text=True
).strip()
parts = [p for p in REMOTE_URL.rstrip("/").split("/") if p]
REPO_NAME = "/".join(parts[-2:]).replace(".git", "")

LOG_FILE = os.path.join(REPO, ".iterate_log.jsonl")
WF_NAME = "04 AI Fix - Auto Commit"
ITERATIONS = int(os.environ.get("ITERATIONS", "100"))
START_AT = int(os.environ.get("START_AT", "1"))
POLL_INTERVAL = 10
TIMEOUT_PER_ITER = 900
RETRY_PUSH = 40
RETRY_PUSH_WAIT = 10
RETRY_GH = 15

CORRECT = (
    "def add(a: int, b: int) -> int:\n"
    "    result = a + b\n"
    "    return result\n"
    "\n"
    "\n"
    "def multiply(a: int, b: int) -> int:\n"
    "    return a * b\n"
    "\n"
    "\n"
    "def greet(name: str) -> str:\n"
    '    return f"Hello, {name}!"\n'
)

ADD_BLOCK = "def add(a: int, b: int) -> int:\n    result = a + b\n    return result"
MUL_BLOCK = "def multiply(a: int, b: int) -> int:\n    return a * b"
GREET_BLOCK = 'def greet(name: str) -> str:\n    return f"Hello, {name}!"'

BUGS = [
    (ADD_BLOCK, "def add(a: int, b: int) -> int:\n    return a - b",
     "add uses subtraction"),
    (ADD_BLOCK, "def add(a: int, b: int) -> int:\n    return a * b",
     "add multiplies"),
    (ADD_BLOCK, "def add(a: int, b: int) -> int:\n    return b",
     "add returns second arg"),
    (MUL_BLOCK, "def multiply(a: int, b: int) -> int:\n    return a + b",
     "multiply adds"),
    (MUL_BLOCK, "def multiply(a: int, b: int) -> int:\n    return a - b",
     "multiply subtracts"),
    (GREET_BLOCK, 'def greet(name: str) -> str:\n    return f"Goodbye, {name}!"',
     "greet says Goodbye"),
    (GREET_BLOCK, 'def greet(name: str) -> str:\n    return f"Hello, {name}"',
     "greet drops exclamation"),
]

VERIFY_CODE = (
    "import app; "
    "assert app.add(2,3)==5 and app.add(-1,1)==0, 'add'; "
    "assert app.multiply(3,4)==12 and app.multiply(5,0)==0, 'mul'; "
    "assert app.greet('Novus')=='Hello, Novus!', 'greet'; "
    "print('OK')"
)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def git(*a):
    return run(["git", *a])


def gh_cli(*a):
    return run(["gh", "--repo", REPO_NAME, *a], cwd=REPO)


def push_verified(max_tries=RETRY_PUSH, wait=RETRY_PUSH_WAIT):
    """Push and verify by comparing HEAD vs origin/main."""
    for i in range(1, max_tries + 1):
        r = git("push")
        if r.returncode != 0:
            time.sleep(wait)
            continue
        time.sleep(2)
        git("fetch", "origin", "main")
        head = git("rev-parse", "HEAD").stdout.strip()
        remote = git("rev-parse", "origin/main").stdout.strip()
        if head == remote:
            return True
        time.sleep(wait)
    return False


def ensure_clean_base():
    """Reset local to origin/main; if app.py is not correct, self-heal by
    pushing the correct version (handles a previous AI-fix failure)."""
    git("fetch", "origin", "main")
    git("reset", "--hard", "origin/main")
    content = open("app.py", encoding="utf-8").read()
    if content.strip() == CORRECT.strip():
        return True, ""
    print("  self-healing: restoring correct app.py", flush=True)
    open("app.py", "w", encoding="utf-8", newline="\n").write(CORRECT)
    r = git("add", "app.py")
    if r.returncode:
        return False, "self-heal add failed"
    r = git("commit", "-m", "chore: restore clean base")
    if r.returncode:
        return False, "self-heal commit failed"
    if not push_verified():
        return False, "self-heal push failed"
    return True, ""


def inject_and_push(bug_desc, old_block, new_block):
    """Inject bug, commit, push, return (bug_sha, base_sha) or None."""
    buggy = CORRECT.replace(old_block, new_block)
    if buggy == CORRECT:
        return None  # template mismatch
    open("app.py", "w", encoding="utf-8", newline="\n").write(buggy)
    r = git("add", "app.py")
    if r.returncode:
        return None
    r = git("commit", "-m", f"bug: {bug_desc}")
    if r.returncode:
        return None
    bug_sha = git("rev-parse", "HEAD").stdout.strip()
    base_sha = git("rev-parse", "HEAD~1").stdout.strip()
    if not push_verified():
        return None
    return (bug_sha, base_sha)


def trigger_04(base_sha):
    """Trigger 04 workflow via workflow_dispatch with explicit base-ref."""
    for attempt in range(1, RETRY_GH + 1):
        r = gh_cli(
            "workflow", "run", WF_NAME,
            "--field", f"base-ref={base_sha}"
        )
        if r.returncode == 0:
            return True
        time.sleep(8)
    return False


def wait_04_run(runs_json, timeout=TIMEOUT_PER_ITER):
    """Parse gh run list JSON and wait for the latest success run."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            runs = json.loads(runs_json)
        except Exception:
            runs = []
        for rn in runs[:1]:
            if rn.get("status") == "completed":
                return rn.get("conclusion") == "success"
        time.sleep(POLL_INTERVAL)
    return None


def verify():
    r = run([sys.executable, "-c", VERIFY_CODE])
    if r.returncode:
        return False, r.stderr.strip()[:200]
    r2 = run([sys.executable, "-m", "pytest", "-q"])
    if r2.returncode:
        return False, (r2.stdout[-200:] + r2.stderr[-200:])[:200]
    return True, ""


def load_log():
    d = {}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                    d[row["iter"]] = row
                except Exception:
                    pass
    return d


def save_log(row):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    results = load_log()
    if START_AT > 1:
        results = {k: v for k, v in results.items() if k < START_AT}

    for i in range(START_AT, ITERATIONS + 1):
        if i in results:
            continue
        print(f"\n=== Iteration {i}/{ITERATIONS} ===", flush=True)

        ok, err = ensure_clean_base()
        if not ok:
            print(f"  [iter {i}] clean base check failed: {err}", flush=True)
            results[i] = {"iter": i, "status": "base_check_failed", "error": err[:200]}
            save_log(results[i])
            continue

        old_block, new_block, bug_desc = random.choice(BUGS)
        info = inject_and_push(bug_desc, old_block, new_block)
        if not info:
            print(f"  [iter {i}] push failed", flush=True)
            results[i] = {"iter": i, "status": "push_failed", "bug": bug_desc}
            save_log(results[i])
            continue
        bug_sha, base_sha = info
        print(f"  pushed bug {bug_sha[:8]} ({bug_desc})", flush=True)

        triggered = trigger_04(base_sha)
        if not triggered:
            print(f"  [iter {i}] 04 dispatch failed; push-triggered run will fire", flush=True)
        else:
            print(f"  04 triggered (dispatch)", flush=True)

        ok = None
        deadline = time.time() + TIMEOUT_PER_ITER
        while time.time() < deadline:
            r = gh_cli(
                "run", "list", "--workflow", WF_NAME, "--limit", "5",
                "--json", "databaseId,headSha,conclusion,status,event"
            )
            if r.returncode == 0:
                try:
                    runs = json.loads(r.stdout)
                    for rn in runs:
                        if rn.get("headSha") == bug_sha:
                            if rn.get("status") == "completed":
                                ok = rn.get("conclusion") == "success"
                                break
                except Exception:
                    pass
            if ok is not None:
                break
            time.sleep(POLL_INTERVAL)

        if ok is None:
            results[i] = {"iter": i, "status": "timeout", "bug": bug_desc}
            save_log(results[i])
            print(f"  [iter {i}] 04 timeout", flush=True)
            continue
        if not ok:
            results[i] = {"iter": i, "status": "ai_fix_failed", "bug": bug_desc}
            save_log(results[i])
            print(f"  [iter {i}] 04 failed to fix", flush=True)
            continue

        git("fetch", "origin", "main")
        git("reset", "--hard", "origin/main")
        pass_, err = verify()
        status = "verified" if pass_ else "verify_failed"
        results[i] = {
            "iter": i, "status": status, "bug": bug_desc,
            "error": err[:200] if err else "",
        }
        save_log(results[i])
        print(f"  [iter {i}] {status}", flush=True)

    counts = {}
    for row in results.values():
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print("\n=== SUMMARY ===", flush=True)
    print(json.dumps(counts, ensure_ascii=False), flush=True)
    return 0 if counts.get("verified", 0) >= ITERATIONS else 1


if __name__ == "__main__":
    sys.exit(main())
