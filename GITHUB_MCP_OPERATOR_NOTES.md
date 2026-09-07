# GitHub MCP Operator Notes — Content-Fetch Workaround & Write-Confirmation Protocol

> Added 2026-09-06 by the Saturday Research Crew after the semiconductors + economic-calendar run.
> Same spirit as BACKFILL_44.md: this exists because a real incident happened and the fix belongs in the docs, not just in one session's memory.

---

## Incident 1: `get_file_contents` returns no readable text for files

**Symptom:** Calling `get_file_contents` on any file in this repo — regardless of size, from a 19-byte `.gitignore` to a 35KB wiki page — returns only a confirmation string ("successfully downloaded text file (SHA: ...)") with **no actual file content** in the visible tool result. This happened for every single file tried in the 2026-09-06 session. Directory listings (`path` = a folder) work fine and return full JSON with `download_url` fields — it is specifically single-file content that goes missing.

**Do not assume this is fixed** in a future session without testing it first: call `get_file_contents` on a small known file (e.g. `limits.md`) and check whether real text comes back before relying on it for anything that matters.

**Workaround that works — commit-diff reconstruction:**

1. `list_commits(path=<file>, perPage=100)` to get every commit that touched the file, newest first, with commit messages and timestamps.
2. `get_commit(sha=<latest commit>, detail="full_patch")` — this returns the **unified diff** for that commit, which for a weekly full-rewrite wiki page effectively contains ~95% of the current file as `+` lines with `-` lines showing the prior week's version. This is usually enough on its own for wiki pages that get rewritten wholesale each week.
3. For append-only files (like `logs/cron.log`), a single commit's patch only shows a few new lines. To reconstruct the *whole* file:
   - Walk back through `list_commits` to find the very first commit (`status: "added"` in `get_commit`) — its patch is the full initial content.
   - Pull `full_patch` for enough subsequent commits to cover the timestamp range you need. Exact original line text is only recoverable this way; for older history where full patch-walking is too expensive, the **commit message itself** (from `list_commits`) is usually a close paraphrase of the log line and can stand in — **flag any such line explicitly** (e.g. `[reconstructed]`) so nobody mistakes it for a verbatim record.
   - Dedupe reconstructed entries against exact-text entries by comparing timestamps with a ~10-minute tolerance (commit timestamps lag the event timestamp embedded in the log line itself).

**Do not try:** `fetch_url` on `raw.githubusercontent.com` — it fails categorically in this environment (tested against a known-public repo, not just this one). Don't waste a call on it.

**Faster path if you only need a fragment:** `search_code(query='repo:OWNER/REPO filename:X')` with `fields: ["text_matches"]` returns a snippet around a match — useful for spot-checking a specific string, not for full reconstruction.

---

## Incident 2: `confirm_action` + placeholder content = accidental data-destroying write

**What happened:** Twice in the 2026-09-06 session, `logs/cron.log` was overwritten with literal placeholder text (e.g. `"FULL_LOG_CONTENT_WITH_NEW_START_LINE_APPENDED"`) instead of the real ~14KB log. Both times it happened the same way:

1. Called `confirm_action` with a **summarized or placeholder string** in `intended_arguments.content` (reasonable — you don't want to make the user read 20KB in a confirmation prompt).
2. User approved.
3. The next `call_external_tool` call was made **using that same placeholder string**, because muscle memory says "now execute the thing I just got approved" — but what got approved, verbatim, was the placeholder, and the write gate matches arguments *exactly*. Passing the placeholder string succeeds and writes garbage; passing the real content mismatches and gets rejected.

**The rule going forward:** `intended_arguments.content` in `confirm_action` must be the **exact, complete, final string** you intend to write — never a summary, a placeholder token, or a `[... see file ...]` shorthand. If the content is large, that is fine; put the whole thing in both the `confirm_action` call and the follow-up `call_external_tool` call, character for character. Use `placeholder` (a separate field) for the human-readable summary — that field is for display only and is not what gets matched.

**Recovery pattern used successfully:** if you do push placeholder text by mistake, immediately re-run the full reconstruction, build the correct complete string once (e.g. in a scratch file inside the code sandbox), and confirm+push that exact string — do not iterate with more placeholders "to test the gate," since a placeholder that matches will execute.

**Sandbox caveat:** the Python code-execution sandbox's filesystem and variables do **not** persist across user turns (they did appear to persist within a single tool-calling turn). Do not rely on writing a scratch file in one turn and reading it back in the next — rebuild the string in the same turn you use it, or keep the literal text in the conversation so it can be re-typed into the next tool call.

---

## Practical checklist for the next Saturday Crew run

- [ ] Test `get_file_contents` on a small file first. If it's still broken, budget extra calls for commit-diff reconstruction — it is slower but works.
- [ ] For wiki pages (rewritten weekly): one `get_commit(detail="full_patch")` on the last update commit usually gets you ~95% of the current file.
- [ ] For `logs/cron.log` (append-only): don't try to perfectly reconstruct ancient history from scratch every week — if a prior week already did the reconstruction (see the 2026-09-06 commits), you can fetch *that* commit's full content via `full_patch` diffed against its own parent, which is much shorter.
- [ ] Every `confirm_action` for a write must carry the real, complete, final content in `intended_arguments` — no placeholders, no summaries, no truncation markers.
- [ ] If a write pushes something wrong, fix it in the very next commit and say so plainly in the commit message (see this repo's own precedent: "Correct the backfill guidance that emptied the panel").
