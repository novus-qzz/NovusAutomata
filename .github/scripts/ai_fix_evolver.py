#!/usr/bin/env python3
"""
AI Fix Evolver - 基于控制论进化器的修复策略优化
根据历史修复成功率，自适应调整 temperature、retry 次数、prompt 风格等参数。
依赖: numpy
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from evolver_core import CyberneticEvolver

WS = os.path.dirname(os.path.dirname(SCRIPT_DIR))
EVOLVER_DIR = os.path.join(WS, "evolver")

API_KEY = os.environ.get("AI_API_KEY", "")
BASE_URL = os.environ.get("AI_BASE_URL", "https://token.sensenova.cn/v1")
MODEL = os.environ.get("AI_MODEL", "sensenova-6.7-flash-lite")

FILE_BLOCK_RE = re.compile(r"===FILE:([^\s=]+)===\s*(.*?)\s*===END===", re.DOTALL)

FORBIDDEN_SUBSTR = (
    ".github/", ".env", "secret", "credential", "token",
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "Cargo.lock", "go.sum", "poetry.lock",
)

STRATEGIES = {
    0: {"name": "standard", "temperature": 0.2, "max_attempts": 3, "prompt_style": "standard"},
    1: {"name": "precise", "temperature": 0.1, "max_attempts": 5, "prompt_style": "strict"},
    2: {"name": "creative", "temperature": 0.4, "max_attempts": 2, "prompt_style": "relaxed"},
    3: {"name": "fallback", "temperature": 0.2, "max_attempts": 4, "prompt_style": "lenient"},
}

PROMPTS = {
    "standard": (
        "You are an expert code reviewer and fixer. Below is a git diff. "
        "Find concrete bugs and safe auto-fixable issues in the CURRENT code, "
        "then produce the FULL FIXED CONTENT of each affected file.\n\n"
        "Output format:\n===FILE:<relative/path>===\n<complete fixed file content>\n===END===\n\n"
        "Rules:\n- Only output ===FILE blocks. No explanations.\n"
        "- Output COMPLETE file content.\n- Only fix real logic bugs.\n"
        "- Never touch: .github/, .env*, lockfiles, secrets.\n"
        "- If NO issues, respond with: NO_ISSUES\n\nDiff:\n{diff}"
    ),
    "strict": (
        "You are a strict code reviewer. Below is a git diff. "
        "Focus on REAL bugs and logic errors ONLY.\n\n"
        "Output format:\n===FILE:<relative/path>===\n<complete fixed file content>\n===END===\n\n"
        "Rules:\n- Only output ===FILE blocks.\n- Output COMPLETE files.\n"
        "- Fix ONLY: syntax errors, undefined variables, type mismatches, logic bugs.\n"
        "- Never touch: .github/, .env*, lockfiles, secrets.\n"
        "- If NO real bugs: respond with: NO_ISSUES\n\nDiff:\n{diff}"
    ),
    "relaxed": (
        "You are a code reviewer. Below is a git diff. "
        "Find any issues including logic bugs, edge cases, missing error handling.\n\n"
        "Output format:\n===FILE:<relative/path>===\n<complete fixed file content>\n===END===\n\n"
        "Rules:\n- Only output ===FILE blocks.\n- Output COMPLETE file content.\n"
        "- Never touch: .github/, .env*, lockfiles, secrets.\n"
        "- If no issues: respond with: NO_ISSUES\n\nDiff:\n{diff}"
    ),
    "lenient": (
        "You are a code reviewer. Below is a git diff. "
        "Check for obvious issues. Be lenient - only flag clear problems.\n\n"
        "Output format:\n===FILE:<relative/path>===\n<complete fixed file content>\n===END===\n\n"
        "Rules:\n- Only output ===FILE blocks.\n- Output COMPLETE file content.\n"
        "- Never touch: .github/, .env*, lockfiles, secrets.\n"
        "- If no issues: respond with: NO_ISSUES\n\nDiff:\n{diff}"
    ),
}


def _load_evolver():
    cfg_file = os.path.join(EVOLVER_DIR, "config.json")
    st_file = os.path.join(EVOLVER_DIR, "state.json")
    cfg = {}
    if os.path.exists(cfg_file):
        with open(cfg_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    ev = CyberneticEvolver(
        target=cfg.get("target", 1.0),
        state_dim=cfg.get("state_dim", 4),
        action_dim=cfg.get("action_dim", 4),
        epsilon_start=cfg.get("epsilon_start", 1.0),
        epsilon_end=cfg.get("epsilon_end", 0.01),
        epsilon_decay=cfg.get("epsilon_decay", 0.995),
        learning_rate=cfg.get("learning_rate", 0.02),
        adaptation_threshold=cfg.get("adaptation_threshold", 1.0),
        mutation_trigger=cfg.get("mutation_trigger", 100),
    )
    if os.path.exists(st_file):
        try:
            ev.load(st_file)
        except Exception as e:
            print(f"::warning::Failed to load state: {e}")
    mn = cfg.get("trigger", {}).get("min_history", 3)
    cd = cfg.get("trigger", {}).get("consecutive_decline", 3)
    si = cfg.get("trigger", {}).get("suggested_iterations", 20)
    def _tr(fn):
        def _inner(hist):
            if len(hist) < mn:
                return {"should_optimize": False, "reason": "Insufficient data", "suggested_iterations": 0}
            recent = hist[-cd:]
            if len(recent) >= cd and all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
                return {"should_optimize": True, "reason": f"Performance declined for {cd} runs", "suggested_iterations": si}
            return {"should_optimize": False, "reason": "Stable", "suggested_iterations": 0}
        return _inner
    ev.set_trigger_condition(_tr(mn))
    return ev


def _save_state(ev):
    path = os.path.join(EVOLVER_DIR, "state.json")
    os.makedirs(EVOLVER_DIR, exist_ok=True)
    ev.save(path)


def _record(score):
    path = os.path.join(EVOLVER_DIR, "performance_log.json")
    os.makedirs(EVOLVER_DIR, exist_ok=True)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"history": []}
    data["history"].append(score)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data["history"]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def get_diff(base_sha):
    args = ["git", "diff", "-U10"]
    if base_sha:
        args.append(base_sha)
    args += ["--", ".", ":(exclude).github"]
    return run(args).stdout


def call_llm(messages, temperature=0.2, max_tokens=8192):
    body = json.dumps({
        "model": MODEL, "messages": messages,
        "temperature": temperature, "max_tokens": max_tokens,
        "thinking": {"type": "disabled"},
    }).encode("utf-8")
    url = BASE_URL.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.load(resp)
    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    if not content.strip():
        raise RuntimeError("Empty response")
    return content


def extract_files(text):
    blocks = FILE_BLOCK_RE.findall(text)
    if not blocks:
        return None
    files = {}
    for path, content in blocks:
        path = path.strip()
        if not path or any(bad in path for bad in FORBIDDEN_SUBSTR):
            print(f"::error::Rejected path: {path!r}")
            return None
        content = content.strip("\n")
        if not content:
            print("::error::Empty content")
            return None
        if not content.endswith("\n"):
            content += "\n"
        files[path] = content
    return files


def write_files(files):
    for path, content in files.items():
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)


def main():
    if not API_KEY:
        print("::error::AI_API_KEY is not set")
        return 1

    try:
        ev = _load_evolver()
        st = ev.get_best_strategy()
        print(f"::notice::Evolver loaded | v{st['strategy_version']} | "
              f"errors: {len(ev.error_history)} | Q: {ev.Q_values}")
    except Exception as e:
        print(f"::warning::Evolver init failed: {e}")
        ev = None

    base_sha = os.environ.get("AI_FIX_BASE_SHA", "")
    diff = get_diff(base_sha)
    if not diff.strip():
        print("::notice::No changes to fix")
        return 0

    diff_size = len(diff.encode("utf-8"))
    print(f"::notice::Diff size: {diff_size} bytes")

    if ev:
        st = ev.get_best_strategy()
        action = st["best_action"]
        confidence = st["confidence"]
    else:
        action = 0
        confidence = 0.0

    strat = STRATEGIES.get(action, STRATEGIES[0])
    print(f"::notice::Strategy: {strat['name']} (action={action}, "
          f"confidence={confidence:.1%}, temp={strat['temperature']})")

    prompt = PROMPTS[strat["prompt_style"]].format(diff=diff)
    sys_msg = "You output only ===FILE blocks with complete file contents, or NO_ISSUES."

    start_time = time.time()
    success = False
    attempts_used = 0
    files_fixed = 0

    for attempt in range(1, strat["max_attempts"] + 1):
        attempts_used = attempt
        print(f"::notice::Fix attempt {attempt}/{strat['max_attempts']} [{strat['name']}]")
        try:
            content = call_llm([
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt},
            ], temperature=strat["temperature"])
        except Exception as e:
            print(f"::warning::LLM call failed: {e}")
            continue

        if "NO_ISSUES" in content.upper():
            print("::notice::AI found no issues")
            success = True
            break

        files = extract_files(content)
        if not files:
            print(f"::warning::No valid file blocks; retrying")
            continue

        write_files(files)
        files_fixed = len(files)
        status = run(["git", "status", "--porcelain"])
        if not status.stdout.strip():
            print(f"::warning::No effective changes (no-op, attempt {attempt})")
            if attempt == strat["max_attempts"]:
                print("::notice::No effective change produced")
            continue

        success = True
        print(f"::notice::Fix applied: {files_fixed} files")
        break

    elapsed = time.time() - start_time

    if ev:
        if success:
            penalty = 0.1 * (attempts_used - 1) / strat["max_attempts"]
            score = max(0.1, 1.0 - penalty)
        else:
            score = 0.0
        perf = _record(score)
        print(f"::notice::Score: {score:.2f} | history: {len(perf)} entries")
        trigger = ev.check_trigger(perf)
        if trigger["should_optimize"]:
            print(f"::notice::Evolver triggered: {trigger['reason']}")
            ctx = {
                "diff_size": diff_size, "files_fixed": files_fixed,
                "attempts_used": attempts_used, "strategy_used": action,
                "last_result": {"score": score},
            }
            result = ev.optimize(ctx, n_iterations=trigger["suggested_iterations"])
            print(f"::notice::Optimized: best_action={result['best_action']}, "
                  f"best_error={result['best_error']:.4f}")
        _save_state(ev)
        print("::notice::Evolver state saved")

    if success:
        print(f"::notice::AI fix completed: {files_fixed} files, {attempts_used} attempts, {elapsed:.1f}s")
    else:
        print(f"::notice::AI fix failed after {attempts_used} attempts ({elapsed:.1f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())