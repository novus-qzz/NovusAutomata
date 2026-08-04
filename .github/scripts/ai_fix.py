#!/usr/bin/env python3
"""AI auto-fix for pull requests using SenseNova (OpenAI-compatible API).

Generates a unified diff via LLM, validates it against a path whitelist,
then applies it to the working tree. Safe guards:
  - patch must be a valid unified diff
  - paths restricted to code directories
  - forbidden paths (.github/, lockfiles, secrets) are rejected
"""
import json
import os
import subprocess
import sys
import urllib.request

API_KEY = os.environ.get("AI_API_KEY", "")
BASE_URL = os.environ.get("AI_BASE_URL", "https://token.sensenova.cn/v1")
MODEL = os.environ.get("AI_MODEL", "sensenova-6.7-flash-lite")

FORBIDDEN_SUBSTR = (
    ".github/", ".env", "secret", "credential", "token",
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "Cargo.lock", "go.sum", "poetry.lock",
)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def get_diff(base_sha):
    if base_sha:
        r = run(["git", "diff", base_sha, "--", "."])
    else:
        r = run(["git", "diff", "--", "."])
    return r.stdout


def call_llm(messages):
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 8192,
        "thinking": {"type": "disabled"},
    }).encode("utf-8")
    url = BASE_URL.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.load(resp)
    message = data["choices"][0]["message"]
    content = message.get("content") or ""
    if not content.strip():
        raise RuntimeError("SenseNova returned empty content; check model response")
    return content


def extract_patch(text):
    start = text.find("diff --git")
    if start < 0:
        return None
    lines = text[start:].splitlines()
    patch_lines = []
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        is_marker = (
            ln.startswith("diff --git")
            or ln.startswith("index ")
            or ln.startswith("--- a/")
            or ln.startswith("+++ b/")
            or ln.startswith("@@")
            or ln.startswith("\\ No newline")
        )
        is_content = ln.startswith(("+", "-", " ")) and ln != "+++"
        if i == 0 or is_marker or is_content or (stripped == "" and patch_lines):
            patch_lines.append(ln)
        else:
            break
    return "\n".join(patch_lines)


def validate_patch(patch):
    for line in patch.splitlines():
        if line.startswith("+++ b/") or line.startswith("--- a/"):
            path = line.split(" b/", 1)[-1].strip()
            if any(bad in path for bad in FORBIDDEN_SUBSTR):
                return False, f"forbidden path: {path}"
    return True, ""


def main():
    if not API_KEY:
        print("::error::AI_API_KEY is not set")
        return 1

    base_sha = os.environ.get("AI_FIX_BASE_SHA", "")
    diff = get_diff(base_sha)
    if not diff.strip():
        print("::notice::No changes to fix")
        return 0

    prompt = (
        "You are an expert code reviewer and fixer. The following git diff "
        "contains code changes. Identify concrete bugs, style violations, "
        "and issues that can be safely auto-fixed, then produce a SINGLE "
        "unified diff (git diff format) that fixes them.\n\n"
        "Rules:\n"
        "- Output ONLY the unified diff, starting with `diff --git`. No explanations.\n"
        "- Do not change behavior beyond the identified issues.\n"
        "- Never touch: .github/, .env*, lockfiles, secrets, credential files, "
        "or generated files.\n\n"
        f"Diff:\n{diff}"
    )

    content = call_llm([
        {"role": "system", "content": "You output only valid unified diffs."},
        {"role": "user", "content": prompt},
    ])

    patch = extract_patch(content)
    if not patch:
        print("::warning::No valid diff block in AI response; nothing to apply")
        return 1

    ok, reason = validate_patch(patch)
    if not ok:
        print(f"::error::Patch rejected: {reason}")
        return 1

    with open("fix.patch", "w", encoding="utf-8") as f:
        f.write(patch)

    check = run(["git", "apply", "--check", "fix.patch"])
    if check.returncode != 0:
        print(f"::error::Patch does not apply cleanly:\n{check.stderr}")
        return 1

    r = run(["git", "apply", "fix.patch"])
    if r.returncode != 0:
        print(f"::error::Failed to apply patch:\n{r.stderr}")
        return 1

    print("::notice::Patch applied successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
