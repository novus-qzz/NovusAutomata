#!/usr/bin/env python3
"""Autonomous iteration driver for the NovusAutomata AI-fix loop.

Repeatedly:
  1. inject a logic bug into app.py
  2. commit + push to main (triggers 04 AI Fix on push)
  3. wait for the 04 workflow to auto-fix and push
  4. verify the fixed code passes tests
until N iterations are completed. Supports resuming from a log file.
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
REPO_NAME = subprocess.check_output(
    ["git", "remote", "get-url", "origin"], text=True
).strip()
REPO_NAME = REPO_NAME.rstrip("/").split("/")[-2:]

LOG_FILE = os.path.join(REPO, ".iterate_log.jsonl")
WF_NAME = "04 AI Fix - Auto Commit"
ITERATIONS = int(os.environ.get("ITERATIONS", "100"))
START_AT = int(os.environ.get("START_AT", "1"))
VERIFY_CMD = (
    "import app; "
    "assert app.add(2,3)==5 and app.add(-1,1)==0, 'add broken'; "
    "assert app.multiply(3,4)==12 and app.multiply(5,0)==0, 'multiply broken'; "
    "assert app.greet('Novus')=='Hello, Novus!', 'greet broken'; "
    "print('VERIFY OK')"
)

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

ADD_CORRECT = (
    "def add(a: int, b: int) -> int:\n"
    "    result = a + b\n"
    "    return result"
)
MUL_CORRECT = (
    "def multiply(a: int, b: int) -> int:\n"
    "    return a * b"
)
GREET_CORRECT = (
    "def greet(name: str) -> str:\n"
    '    return f"Hello, {name}!"'
)

BUGS = [
    (
        "add uses subtraction",
        ADD_CORRECT,
        "def add(a: int, b: int) -> int:\n"
        "    return a - b",
    ),
    (
        "add multiplies instead of adds",
        ADD_CORRECT,
        "def add(a: int, b: int) -> int:\n"
        "    return a * b",
    ),
    (
        "add returns second arg",
        ADD_CORRECT,
        "def add(a: int, b: int) -> int:\n"
        "    return b",
    ),
    (
        "multiply uses addition",
        MUL_CORRECT,
        "def multiply(a: int, b: int) -> int:\n"
        "    return a + b",
    ),
    (
        "multiply uses subtraction",
        MUL_CORRECT,
        "def multiply(a: int, b: int) -> int:\n"
        "    return a - b",
    ),
    (
        "multiply floor divides",
        MUL_CORRECT,
        "def multiply(a: int, b: int) -> int:\n"
        "    return a // b",
    ),
    (
        "greet says Goodbye",
        GREET_CORRECT,
        "def greet(name: str) -> str:\n"
        '    return f"Goodbye, {name}!"',
    ),
    (
        "greet drops exclamation mark",
        GREET_CORRECT,
        "def greet(name: str) -> str:\n"
        '    return f"Hello, {name}"',
    ),
]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def git(*args):
    return run(["git", *args])


def gh(*args):
    return run(["gh", "--repo", "/".join(REPO_NAME), *args])


def push_with_retry(max_tries=40, wait=12):
    for i in range(1, max_tries + 1):
        r = git("push")
        if r.returncode == 0:
            r2 = git("fetch", "origin", "main")
            if r2.returncode == 0:
                head = git("rev-parse", "HEAD").stdout.strip()
                remote = git("rev-parse", "origin/main").stdout.strip()
                if head == remote:
                    return True
            time.sleep(wait)
            continue
        time.sleep(wait)
    return False


def wait_for_04(bug_sha, timeout=1200, poll=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = gh(
            "run", "list", "--workflow", WF_NAME, "--limit", "25",
            "--json", "databaseId,headSha,conclusion,status",
        )
        if r.returncode == 0:
            try:
                runs = json.loads(r.stdout)
            except json.JSONDecodeError:
                runs = []
            for rn in runs:
                if rn.get("headSha") == bug_sha:
                    if rn.get("status") == "completed":
                        return rn.get("conclusion") == "success"
                    break
        time.sleep(poll)
    return None


def verify():
    r = run([sys.executable, "-c", VERIFY_CMD])
    if r.returncode != 0:
        return False, r.stderr.strip()
    r2 = run([sys.executable, "-m", "pytest", "-q"])
    if r2.returncode != 0:
        return False, r2.stdout[-300:] + r2.stderr[-300:]
    return True, ""


def make_buggy(old_block, new_block):
    if old_block not in CORRECT:
        raise ValueError("bug template does not match current app.py")
    return CORRECT.replace(old_block, new_block)


def load_log():
    results = {}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                    results[row["iter"]] = row
                except (json.JSONDecodeError, KeyError):
                    pass
    return results


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
        print(f"=== Iteration {i}/{ITERATIONS} ===", flush=True)
        bug_desc, old_block, new_block = random.choice(BUGS)

        buggy = make_buggy(old_block, new_block)
        with open("app.py", "w", encoding="utf-8", newline="\n") as f:
            f.write(buggy)

        git("add", "app.py")
        r = git("commit", "-m", f"bug: {bug_desc} [iter {i}]")
        if r.returncode != 0:
            print(f"  [iter {i}] commit failed: {r.stderr.strip()}", flush=True)
            results[i] = {"iter": i, "status": "commit_failed"}
            save_log(results[i])
            continue

        bug_sha = git("rev-parse", "HEAD").stdout.strip()
        if not push_with_retry():
            print(f"  [iter {i}] push failed", flush=True)
            results[i] = {"iter": i, "status": "push_failed", "bug": bug_desc}
            save_log(results[i])
            continue
        print(f"  pushed bug {bug_sha[:8]} ({bug_desc})", flush=True)

        ok = wait_for_04(bug_sha)
        if ok is None:
            results[i] = {"iter": i, "status": "timeout", "bug": bug_desc}
            save_log(results[i])
            print(f"  [iter {i}] 04 timed out", flush=True)
            continue
        if not ok:
            results[i] = {"iter": i, "status": "ai_fix_failed", "bug": bug_desc}
            save_log(results[i])
            print(f"  [iter {i}] 04 failed to fix", flush=True)
            continue

        r = git("fetch", "origin", "main")
        if r.returncode == 0:
            git("reset", "--hard", "origin/main")
        ok, err = verify()
        status = "verified" if ok else "verify_failed"
        results[i] = {
            "iter": i, "status": status, "bug": bug_desc,
            "error": err[:200] if err else "",
        }
        save_log(results[i])
        print(f"  [iter {i}] {status}", flush=True)

    counts = {}
    for row in results.values():
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print("=== SUMMARY ===", flush=True)
    print(json.dumps(counts, ensure_ascii=False), flush=True)
    return 0 if counts.get("verified", 0) == ITERATIONS else 1


if __name__ == "__main__":
    sys.exit(main())
