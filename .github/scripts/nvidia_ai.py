import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

NVIDIA_BASE_URL = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")

MODEL_REVIEW = os.environ.get("NVIDIA_REVIEW_MODEL", "deepseek-ai/deepseek-v4-pro")
MODEL_FIX = os.environ.get("NVIDIA_FIX_MODEL", "deepseek-ai/deepseek-v4-flash")
MODEL_DESCRIBE = os.environ.get("NVIDIA_DESCRIBE_MODEL", "deepseek-ai/deepseek-v4-flash")
MODEL_TRIAGE = os.environ.get("NVIDIA_TRIAGE_MODEL", "nvidia/nemotron-3-super-120b-a12b")
MODEL_QUALITY = os.environ.get("NVIDIA_QUALITY_MODEL", "deepseek-ai/deepseek-v4-pro")
MODEL_CHANGELOG = os.environ.get("NVIDIA_CHANGELOG_MODEL", "deepseek-ai/deepseek-v4-flash")
MODEL_SUMMARY = os.environ.get("NVIDIA_SUMMARY_MODEL", "deepseek-ai/deepseek-v4-flash")

MAX_RETRIES = 3
RETRY_DELAY = 2


def call_nvidia(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str | None:
    """Call NVIDIA NIM API and return the response text."""
    if not NVIDIA_API_KEY:
        print("Error: NVIDIA_API_KEY not set", file=sys.stderr)
        return None
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(
                f"{NVIDIA_BASE_URL.rstrip('/')}/v1/chat/completions",
                data=json.dumps(data).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {NVIDIA_API_KEY}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read())
                choices = result.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content")
                    if content is not None:
                        return content
                print(f"Unexpected API response shape: {list(result.keys())}", file=sys.stderr)
                return None
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code}: {e.reason}", file=sys.stderr)
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return None
        except urllib.error.URLError as e:
            print(f"Connection error: {e.reason}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return None
        except Exception as e:
            print(f"API call failed: {e}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return None
    return None


def gh_run(*args: str) -> str:
    """Run a GitHub CLI command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"gh command failed: {' '.join(args)}\n{result.stderr}", file=sys.stderr)
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"gh command timed out: {' '.join(args)}", file=sys.stderr)
        return ""


def get_git_diff(base_ref: str = "origin/main") -> str:
    """Get git diff against a base ref."""
    result = subprocess.run(
        ["git", "diff", base_ref, "--", ":!.github"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout


def get_pr_diff(pr_number: int) -> str:
    """Get the diff for a specific PR."""
    return gh_run("pr", "diff", str(pr_number))


def get_commit_log(
    since: str | None = None, from_tag: str | None = None, to_tag: str | None = None
) -> str:
    """Get git log between refs or since a date."""
    if from_tag and to_tag:
        result = subprocess.run(
            ["git", "log", "--oneline", f"{from_tag}..{to_tag}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    elif since:
        result = subprocess.run(
            ["git", "log", "--oneline", f"--since={since}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    else:
        result = subprocess.run(
            ["git", "log", "--oneline", "-50"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    return result.stdout


def parse_json_from_llm(text: str) -> dict | None:
    """Parse JSON from LLM response, stripping markdown code fences."""
    cleaned = text.strip()
    cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def is_safe_path(path: str) -> bool:
    """Check if a resolved path is safe to write to."""
    root = os.path.abspath(os.getcwd())
    resolved = os.path.abspath(os.path.join(root, path))
    if not resolved.startswith(root + os.sep) and resolved != root:
        print(f"Path traversal blocked: {path} -> {resolved}", file=sys.stderr)
        return False
    parts = resolved.replace(os.sep, "/").lower().split("/")
    for part in parts:
        if part in (".github", ".env", "node_modules"):
            print(f"Protected path skipped: {path}", file=sys.stderr)
            return False
        if part.startswith((".env.", "secret", "credential", "token")):
            print(f"Protected path skipped: {path}", file=sys.stderr)
            return False
    return True


def write_fix_files(output: str, backup: bool = True) -> None:
    """Write fixed files from AI output blocks, with path safety and optional backup."""
    pattern = re.compile(r"===FILE:(.+?)===\n(.*?)\n===END===", re.DOTALL)
    written = []
    for match in pattern.finditer(output):
        path = match.group(1).strip()
        content = match.group(2)
        if not is_safe_path(path):
            continue
        full_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        if backup and os.path.exists(full_path):
            backup_path = full_path + ".bak"
            shutil.copy2(full_path, backup_path)
            print(f"Backup created: {backup_path}", file=sys.stderr)
        with open(full_path, "w") as f:
            f.write(content)
        written.append(path)
        print(f"Fixed: {path}")
    if not written:
        print("No files were written. Check AI output format.", file=sys.stderr)


def cmd_review(args: argparse.Namespace) -> int:
    """Review a PR diff using AI."""
    pr_num = args.pr_number
    diff = get_pr_diff(pr_num) if pr_num else get_git_diff()
    if not diff.strip():
        print("No diff to review")
        return 0
    system_prompt = (
        "You are a senior software engineer conducting a thorough code review. "
        "Analyze the diff for: logic errors, edge cases, security vulnerabilities, "
        "performance issues, code style violations, and missing tests. "
        "For each issue, provide: the exact line number, severity (CRITICAL/WARNING/SUGGESTION), "
        "and a concrete fix suggestion. "
        "Format your response as a clear list."
    )
    result = call_nvidia(MODEL_REVIEW, system_prompt, f"Review this diff:\n\n{diff}")
    if result and pr_num:
        gh_run("pr", "review", str(pr_num), "--comment", "--body", result)
    elif result:
        print(result)
    return 0 if result else 1


def cmd_describe(args: argparse.Namespace) -> int:
    """Generate a PR description using AI."""
    pr_num = args.pr_number
    diff = get_pr_diff(pr_num) if pr_num else get_git_diff()
    commits = gh_run("pr", "diff", str(pr_num), "--name-only") if pr_num else ""
    system_prompt = (
        "You are a technical writer. Generate a PR description based on the diff. "
        "Include: a title (Conventional Commits format), summary of changes, "
        "list of modified files with descriptions, change type, and testing suggestions. "
        "Format as markdown."
    )
    context = f"Diff:\n{diff}\n\nFiles changed:\n{commits}"
    result = call_nvidia(MODEL_DESCRIBE, system_prompt, context)
    if result and pr_num:
        title = result.split("\n")[0].strip("# ")
        gh_run("pr", "edit", str(pr_num), "--title", title, "--body", result)
    elif result:
        print(result)
    return 0 if result else 1


def cmd_fix(args: argparse.Namespace) -> int:
    """Auto-fix code issues in a PR diff."""
    pr_num = args.pr_number
    diff = get_pr_diff(pr_num) if pr_num else get_git_diff()
    if not diff.strip():
        print("No diff to fix")
        return 0
    system_prompt = (
        "You are an expert programmer. Fix the issues in the following diff. "
        "Output each file change in this exact format:\n"
        "===FILE:path/to/file.py===\n<fixed code>\n===END===\n"
        "Only output files that need changes."
    )
    result = call_nvidia(MODEL_FIX, system_prompt, f"Fix this diff:\n\n{diff}")
    if not result:
        return 1
    write_fix_files(result)
    test_result = subprocess.run(
        [sys.executable, "-m", "pytest"], capture_output=True, text=True, timeout=60
    )
    print(test_result.stdout)
    if test_result.returncode != 0:
        print("Tests failed after fix, attempting second pass...", file=sys.stderr)
        result2 = call_nvidia(
            MODEL_FIX,
            "The previous fix failed tests. Fix the code to make all tests pass.",
            f"Test output:\n{test_result.stdout}\n{test_result.stderr}\n\nDiff:\n{diff}",
        )
        if result2:
            write_fix_files(result2)
            test_result2 = subprocess.run(
                [sys.executable, "-m", "pytest"], capture_output=True, text=True, timeout=60
            )
            print(test_result2.stdout)
            return test_result2.returncode
        return 1
    return 0


def cmd_triage(args: argparse.Namespace) -> int:
    """Triage an issue: classify, label, and prioritize."""
    issue_num = args.issue_number
    title = args.title or gh_run(
        "issue", "view", str(issue_num), "--json", "title", "--jq", ".title"
    )
    body = args.body or gh_run("issue", "view", str(issue_num), "--json", "body", "--jq", ".body")
    if not title:
        print(f"Failed to fetch issue #{issue_num}", file=sys.stderr)
        return 1
    system_prompt = (
        "You are an issue triage assistant. Analyze the issue and output a JSON object "
        "with these fields (no other text):\n"
        '{"labels": ["bug"], "priority": "high|medium|low", '
        '"is_duplicate": false, "needs_more_info": false, '
        '"estimated_complexity": "low|medium|high", "summary": "brief description"}'
    )
    result = call_nvidia(
        MODEL_TRIAGE, system_prompt, f"Title: {title}\n\nBody: {body}", temperature=0.0
    )
    if not result:
        return 1
    data = parse_json_from_llm(result)
    if data:
        labels = data.get("labels", [])
        if labels:
            gh_run("issue", "edit", str(issue_num), "--add-label", ",".join(labels))
        comment = (
            f"## AI Triage Summary\n\n"
            f"- **Priority**: {data.get('priority', 'unknown')}\n"
            f"- **Complexity**: {data.get('estimated_complexity', 'unknown')}\n"
            f"- **Duplicate**: {data.get('is_duplicate', False)}\n"
            f"- **Needs more info**: {data.get('needs_more_info', False)}\n\n"
            f"{data.get('summary', '')}"
        )
        gh_run("issue", "comment", str(issue_num), "--body", comment)
    else:
        gh_run("issue", "comment", str(issue_num), "--body", f"## AI Triage\n\n{result}")
    return 0


def cmd_respond(args: argparse.Namespace) -> int:
    """Respond to an issue comment using AI."""
    issue_num = args.issue_number
    comment_body = args.comment
    if args.comment_file:
        with open(args.comment_file) as f:
            comment_body = f.read().strip()
    if not comment_body:
        print("No comment body provided", file=sys.stderr)
        return 1
    context = args.context or gh_run(
        "issue", "view", str(issue_num), "--json", "title", "--jq", ".title"
    )
    system_prompt = (
        "You are a helpful AI assistant. Respond to the user's comment with "
        "helpful technical advice. If suggesting code, format it as markdown code blocks."
    )
    result = call_nvidia(
        MODEL_FIX,
        system_prompt,
        f"Issue context: {context}\n\nUser comment: {comment_body}",
    )
    if result:
        gh_run("issue", "comment", str(issue_num), "--body", result)
        return 0
    return 1


def cmd_quality(args: argparse.Namespace) -> int:
    """Run AI quality gate on a PR."""
    pr_num = args.pr_number
    diff = get_pr_diff(pr_num) if pr_num else get_git_diff()
    if not diff.strip():
        print("No diff to check")
        return 0
    system_prompt = (
        "You are a code quality auditor. Analyze the diff and output a JSON object "
        "with these exact fields (no other text):\n"
        '{"score": 85, "checks": {'
        '"code_style": {"score": 90, "issues": ["..."]}, '
        '"type_safety": {"score": 80, "issues": ["..."]}, '
        '"test_coverage": {"score": 70, "issues": ["..."]}, '
        '"complexity": {"score": 85, "issues": ["..."]}, '
        '"security": {"score": 95, "issues": ["..."]}, '
        '"duplication": {"score": 90, "issues": ["..."]}'
        '}, "summary": "brief overview"}'
    )
    result = call_nvidia(MODEL_QUALITY, system_prompt, f"Diff:\n\n{diff}")
    if not result:
        return 1
    data = parse_json_from_llm(result)
    if data:
        score = data.get("score", 0)
        checks = data.get("checks", {})
        summary = data.get("summary", "")
        lines = [
            f"## AI Quality Gate: **{score}/100**",
            "",
            "| Check | Score | Issues |",
            "|-------|-------|--------|",
        ]
        for check_name, check_data in checks.items():
            name = check_name.replace("_", " ").title()
            s = check_data.get("score", 0)
            issues = "; ".join(check_data.get("issues", [])) or "None"
            lines.append(f"| {name} | {s}/100 | {issues} |")
        lines.append(f"\n**Summary**: {summary}")
        body = "\n".join(lines)
        if pr_num:
            gh_run("pr", "review", str(pr_num), "--comment", "--body", body)
            if score < 60:
                gh_run("pr", "edit", str(pr_num), "--add-label", "quality-fail")
                print(f"Quality gate FAILED: score {score} < 60")
            elif score < 80:
                print(f"Quality gate PASSED with warnings: score {score}")
            else:
                print(f"Quality gate PASSED: score {score}")
        else:
            print(body)
    else:
        print(result)
    return 0


def cmd_simplify(args: argparse.Namespace) -> int:
    """Analyze code for simplification opportunities."""
    diff = args.diff or get_git_diff()
    if not diff.strip():
        print("No diff to analyze")
        return 0
    system_prompt = (
        "You are a code simplification expert. Analyze the diff and suggest simplifications: "
        "redundant conditions, mergeable loops, replaceable utility functions, "
        "overly long functions that should be split. "
        "For each suggestion, provide the file, line number, and the simplified version."
    )
    result = call_nvidia(MODEL_FIX, system_prompt, f"Diff:\n\n{diff}")
    if result:
        print(result)
        return 0
    return 1


def cmd_issue2pr(args: argparse.Namespace) -> int:
    """Generate a fix PR from an issue description."""
    title = ""
    body = ""
    if args.title_file:
        with open(args.title_file) as f:
            title = f.read().strip()
    if args.body_file:
        with open(args.body_file) as f:
            body = f.read().strip()
    if not title:
        print("No issue title provided", file=sys.stderr)
        return 1
    system_prompt = (
        "You are an expert programmer. Given an issue description, generate the "
        "code changes needed to fix it. Output each file change in this exact format:\n"
        "===FILE:path/to/file.py===\n<fixed code>\n===END===\n"
        "Only output files that need changes."
    )
    result = call_nvidia(MODEL_FIX, system_prompt, f"Issue title: {title}\n\nIssue body: {body}")
    if not result:
        return 1
    write_fix_files(result)
    test_result = subprocess.run(
        [sys.executable, "-m", "pytest"], capture_output=True, text=True, timeout=60
    )
    print(test_result.stdout)
    if test_result.returncode != 0:
        print("Tests failed after fix", file=sys.stderr)
        return test_result.returncode
    return 0


def cmd_deps(args: argparse.Namespace) -> int:
    """Review dependency changes in a PR."""
    pr_num = args.pr_number
    diff = get_pr_diff(pr_num) if pr_num else get_git_diff()
    if not diff.strip():
        print("No dependency diff to review")
        return 0
    system_prompt = (
        "You are a dependency security reviewer. Analyze the dependency changes "
        "and check for: known vulnerabilities, license compatibility, "
        "breaking changes, and version compatibility issues. "
        "For each issue, provide the severity and concrete recommendations."
    )
    result = call_nvidia(MODEL_QUALITY, system_prompt, f"Dependency diff:\n\n{diff}")
    if result and pr_num:
        gh_run("pr", "review", str(pr_num), "--comment", "--body", result)
    elif result:
        print(result)
    return 0 if result else 1


def cmd_changelog(args: argparse.Namespace) -> int:
    """Generate a CHANGELOG entry from git log."""
    from_tag = args.from_tag
    to_tag = args.to_tag
    log = get_commit_log(from_tag=from_tag, to_tag=to_tag)
    if not log.strip():
        print("No commits found")
        return 0
    system_prompt = (
        "You are a release manager. Generate a CHANGELOG entry from the commit log. "
        "Group commits by type (feat/fix/chore/docs/refactor/test/perf). "
        "Format as markdown with sections."
    )
    result = call_nvidia(MODEL_CHANGELOG, system_prompt, f"Commits:\n\n{log}")
    if result:
        header = f"## {to_tag or 'Unreleased'}\n\n"
        if os.path.exists("CHANGELOG.md"):
            with open("CHANGELOG.md") as f:
                existing = f.read()
            content = header + result + "\n\n" + existing
        else:
            content = "# Changelog\n\n" + header + result
        with open("CHANGELOG.md", "w") as f:
            f.write(content)
        print("CHANGELOG.md updated")
        return 0
    return 1


def cmd_summary(args: argparse.Namespace) -> int:
    """Generate a weekly code summary."""
    since = args.since or "1 week ago"
    log = get_commit_log(since=since)
    prs = gh_run(
        "pr",
        "list",
        "--state",
        "merged",
        "--search",
        f"merged:>={since}",
        "--json",
        "number,title,author",
        "--jq",
        "length",
    )
    issues = gh_run(
        "issue",
        "list",
        "--state",
        "all",
        "--search",
        f"created:>={since}",
        "--json",
        "number,title",
        "--jq",
        "length",
    )
    stats = subprocess.run(
        ["git", "diff", "--shortstat", f"@{{{since}}}"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    system_prompt = (
        "You are a project manager. Generate a weekly summary from the data. "
        "Format as markdown with sections: Overview, Key Metrics, Notable Changes, Recommendations."
    )
    context = (
        f"## Commits\n{log}\n\n"
        f"## Merged PRs: {prs}\n"
        f"## New Issues: {issues}\n"
        f"## Code Changes: {stats.stdout}"
    )
    result = call_nvidia(MODEL_SUMMARY, system_prompt, context)
    if result:
        body = f"# Weekly Code Summary\n\n**Period**: {since} to now\n\n{result}"
        gh_run(
            "issue",
            "create",
            "--title",
            f"Weekly Summary ({since})",
            "--label",
            "weekly-summary",
            "--body",
            body,
        )
        return 0
    return 1


def cmd_stale(args: argparse.Namespace) -> int:
    """Identify and mark stale issues and PRs."""
    days = args.days or 30
    cutoff = f"{days} days ago"
    all_items = []
    for cmd in ["issue", "pr"]:
        raw = gh_run(
            cmd,
            "list",
            "--state",
            "open",
            "--search",
            f"updated:<={cutoff} -label:stale",
            "--json",
            "number,title,labels,updatedAt",
            "--limit",
            "50",
        )
        if raw:
            for item in json.loads(raw):
                item["type"] = cmd
                all_items.append(item)
    if not all_items:
        print("No items to check or gh command failed")
        return 0
    marked = 0
    for item in all_items:
        labels = [label["name"] for label in item.get("labels", [])]
        if "bug" in labels or "enhancement" in labels:
            continue
        system_prompt = (
            "You are a project maintainer. Decide if this issue/PR should be marked as stale. "
            "Reply with only 'yes' or 'no'."
        )
        title = item.get("title", "")
        num = item.get("number", 0)
        result = call_nvidia(MODEL_TRIAGE, system_prompt, f"Issue #{num}: {title}")
        if result and "yes" in result.lower():
            item_type = item.get("type", "issue")
            gh_run(item_type, "edit", str(num), "--add-label", "stale")
            gh_run(
                item_type,
                "comment",
                str(num),
                "--body",
                f"This {item_type} has been inactive for {days} days. "
                f"Marking as stale. It will be closed in 7 days if no activity.",
            )
            print(f"Marked #{num} ({item_type}) as stale: {title}")
            marked += 1
    print(f"Stale check complete: {marked} items marked")
    return 0


def cmd_readme(args: argparse.Namespace) -> int:
    """Sync README with recent code changes."""
    files = args.files or ""
    current_readme = ""
    if os.path.exists("README.md"):
        with open("README.md") as f:
            current_readme = f.read()
    diff = get_git_diff()
    system_prompt = (
        "You are a technical documentation writer. Analyze the code changes and suggest "
        "README updates. If the README needs updating, output the full new README.md content. "
        "If no update is needed, output 'NO_UPDATE'."
    )
    context = (
        f"Current README:\n{current_readme}\n\nRecent changes:\n{diff}\n\nFiles changed:\n{files}"
    )
    result = call_nvidia(MODEL_FIX, system_prompt, context)
    if result and result.strip() != "NO_UPDATE":
        backup_path = "README.md.bak"
        if os.path.exists("README.md"):
            shutil.copy2("README.md", backup_path)
            print(f"README backup: {backup_path}")
        with open("README.md", "w") as f:
            f.write(result)
        print("README.md updated")
        return 0
    print("No README update needed")
    return 0


def main() -> int:
    """Main entry point for the NVIDIA AI automation script."""
    parser = argparse.ArgumentParser(description="NVIDIA NIM AI automation")
    sub = parser.add_subparsers(dest="command", required=True)

    p_review = sub.add_parser("review", help="PR code review")
    p_review.add_argument("--pr-number", type=int, required=True)

    p_describe = sub.add_parser("describe", help="Generate PR description")
    p_describe.add_argument("--pr-number", type=int, required=True)

    p_fix = sub.add_parser("fix", help="Auto-fix code issues")
    p_fix.add_argument("--pr-number", type=int)

    p_issue2pr = sub.add_parser("issue2pr", help="Generate fix from issue")
    p_issue2pr.add_argument("--title-file", default="")
    p_issue2pr.add_argument("--body-file", default="")

    p_deps = sub.add_parser("deps", help="Review dependency changes")
    p_deps.add_argument("--pr-number", type=int, required=True)

    p_triage = sub.add_parser("triage", help="Triage an issue")
    p_triage.add_argument("--issue-number", type=int, required=True)
    p_triage.add_argument("--title")
    p_triage.add_argument("--body")

    p_respond = sub.add_parser("respond", help="Respond to an issue comment")
    p_respond.add_argument("--issue-number", type=int, required=True)
    p_respond.add_argument("--comment", default="")
    p_respond.add_argument("--comment-file", default="")
    p_respond.add_argument("--context", default="")

    p_quality = sub.add_parser("quality", help="PR quality gate")
    p_quality.add_argument("--pr-number", type=int, required=True)

    p_simplify = sub.add_parser("simplify", help="Suggest code simplifications")
    p_simplify.add_argument("--diff")

    p_changelog = sub.add_parser("changelog", help="Generate CHANGELOG")
    p_changelog.add_argument("--from-tag", required=True)
    p_changelog.add_argument("--to-tag", required=True)

    p_summary = sub.add_parser("summary", help="Generate weekly summary")
    p_summary.add_argument("--since", default="1 week ago")

    p_stale = sub.add_parser("stale", help="Manage stale issues/PRs")
    p_stale.add_argument("--days", type=int, default=30)

    p_readme = sub.add_parser("readme", help="Sync README with code changes")
    p_readme.add_argument("--files")

    args = parser.parse_args()

    commands = {
        "review": cmd_review,
        "describe": cmd_describe,
        "fix": cmd_fix,
        "issue2pr": cmd_issue2pr,
        "deps": cmd_deps,
        "triage": cmd_triage,
        "respond": cmd_respond,
        "quality": cmd_quality,
        "simplify": cmd_simplify,
        "changelog": cmd_changelog,
        "summary": cmd_summary,
        "stale": cmd_stale,
        "readme": cmd_readme,
    }

    cmd_fn = commands.get(args.command)
    if cmd_fn:
        return cmd_fn(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
