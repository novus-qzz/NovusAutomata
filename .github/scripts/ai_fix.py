#!/usr/bin/env python3
"""AI auto-fix for pull requests using SenseNova (OpenAI-compatible API).

Generates fixed file contents via LLM (===FILE:...=== blocks), validates
the paths, then writes them to the working tree. Safe guards:
  - output must contain valid ===FILE blocks
  - forbidden paths (.github/, lockfiles, secrets) are rejected
  - files must be non-empty and must produce an actual change
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

FILE_BLOCK_RE = re.compile(r"===FILE:([^\s=]+)===\s*(.*?)\s*===END===", re.DOTALL)

API_KEY = os.environ.get("AI_REVIEW_API_KEY", "")
BASE_URL = os.environ.get("AI_REVIEW_BASE_URL", "https://token.sensenova.cn/v1")
MODEL = os.environ.get("AI_REVIEW_MODEL_STANDARD", "sensenova-6.7-flash-lite")
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = os.environ.get("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")

PROVIDERS = [
    {"name": "sensenova", "api_key": API_KEY, "base_url": BASE_URL, "model": MODEL},
    {"name": "nvidia", "api_key": NVIDIA_API_KEY, "base_url": NVIDIA_BASE_URL, "model": NVIDIA_MODEL},
]

FORBIDDEN_SUBSTR = (
    ".github/", ".env", "secret", "credential", "token",
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "Cargo.lock", "go.sum", "poetry.lock",
)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def get_diff(base_sha):
    args = ["git", "diff", "-U10"]
    if base_sha:
        args.append(base_sha)
    args += ["--", ".", ":(exclude).github"]
    r = run(args)
    return r.stdout


def call_llm(messages, provider):
    body = {
        "model": provider["model"],
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 8192,
    }
    if provider["name"] == "sensenova":
        body["thinking"] = {"type": "disabled"}
    payload = json.dumps(body).encode("utf-8")
    url = provider["base_url"].rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:  # nosec B310
        data = json.load(resp)
    message = data["choices"][0]["message"]
    content = message.get("content") or ""
    if not content.strip():
        raise RuntimeError(f"{provider['name']} returned empty content")
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
            print("::error::AI returned empty content for a file")
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


def get_active_provider():
    for p in PROVIDERS:
        if p["api_key"]:
            return p
    return None


def main():
    provider = get_active_provider()
    if not provider:
        print("::error::No AI provider configured (set AI_REVIEW_API_KEY or NVIDIA_API_KEY)")
        return 1

    base_sha = os.environ.get("AI_FIX_BASE_SHA", "")
    diff = get_diff(base_sha)
    if not diff.strip():
        print("::notice::No changes to fix")
        return 0

    prompt = (
        "You are an expert code reviewer and fixer. Below is a git diff "
        "(`git diff <base>`): lines starting with `-` are the OLD (base) "
        "version, lines starting with `+` are the CURRENT code in the PR. "
        "Find concrete bugs and safe auto-fixable issues in the CURRENT "
        "(`+`) code, then produce the FULL FIXED CONTENT of each affected "
        "file.\n\n"
        "Output format for each fixed file, EXACTLY:\n"
        "===FILE:<relative/path>===\n"
        "<complete fixed file content>\n"
        "===END===\n\n"
        "Rules:\n"
        "- Only output the ===FILE blocks. No explanations, no markdown fences.\n"
        "- Output the COMPLETE file content (not a diff, not a fragment).\n"
        "- Only fix real logic bugs and concrete issues that require code "
        "changes. Do NOT reformat code or touch whitespace / trailing "
        "newlines; those are handled by a separate formatter.\n"
        "- Never touch: .github/, .env*, lockfiles, secrets, credential files, "
        "or generated files.\n"
        "- If you find NO issues to fix, respond with exactly: NO_ISSUES\n\n"
        f"Diff:\n{diff}"
    )

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        print(f"::notice::AI fix attempt {attempt}/{max_attempts} via {provider['name']}", flush=True)
        try:
            content = call_llm([
                {"role": "system", "content": "You output only ===FILE blocks with "
                                              "complete file contents, or NO_ISSUES."},
                {"role": "user", "content": prompt},
            ], provider)
        except Exception as e:
            print(f"::warning::{provider['name']} attempt {attempt} failed: {e}", flush=True)
            # Try next provider in chain
            next_idx = PROVIDERS.index(provider) + 1
            if next_idx < len(PROVIDERS):
                provider = PROVIDERS[next_idx]
                print(f"::notice::Falling back to {provider['name']}", flush=True)
                continue
            print("::error::All AI providers failed")
            return 1

        if "NO_ISSUES" in content.upper():
            print("::notice::AI found no issues to fix", flush=True)
            return 0

        files = extract_files(content)
        if not files:
            print(f"::warning::No valid file blocks in AI response; retrying", flush=True)
            continue

        write_files(files)

        status = run(["git", "status", "--porcelain"])
        if not status.stdout.strip():
            print(f"::warning::AI produced no effective changes (no-op, attempt {attempt})", flush=True)
            if attempt == max_attempts:
                print("::notice::No effective change produced; treating as no-op", flush=True)
            continue

        print("::notice::AI fix applied successfully", flush=True)
        return 0

    print("::notice::AI fix did not produce usable output; treating as no-op", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
