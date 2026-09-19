#!/bin/sh
# Subscription Squad example commands (reference, not a runner).
# Copy, paste, and edit the ALL-CAPS placeholders before running.
# Conventions used below:
#   SKILL   = this checkout (contains SKILL.md and scripts/)
#   CHECKOUT = the target Git checkout root you want edited (must be a
#              git checkout root for work/ask runs)
#   PROMPTS  = directory holding your brief files (outside CHECKOUT)
#   RUNS     = directory holding sibling run dirs (outside CHECKOUT)
# Every --run-dir must be fresh (must not already exist) and outside CHECKOUT.
set -eu

SKILL="/ABSOLUTE/subscription-squad"
CHECKOUT="/ABSOLUTE/checkout"
PROMPTS="/ABSOLUTE/prompts"
RUNS="/ABSOLUTE/task-runs"

# 1. Preflight: verify the exact model inventory behind your existing logins.
#    Success prints subscription_squad_check=ok; it is an inventory check,
#    not a quota guarantee.
python3 "$SKILL/scripts/worker.py" --provider muse --check
python3 "$SKILL/scripts/worker.py" --provider grok --check
python3 "$SKILL/scripts/worker.py" --provider grok-build --check
python3 "$SKILL/scripts/worker.py" --provider antigravity --check

# 2. Implementation (Muse via OpenCode, owned paths only).
#    --allow-path repeats; each entry is a literal workspace-relative file
#    or directory (no globs, no absolute paths, no '..', no .git).
#    --steps 5..120 is an explicit model-step override (default 60);
#    split oversized packages before raising it.
python3 "$SKILL/scripts/worker.py" --provider muse --mode work \
  --workspace "$CHECKOUT" --allow-path src/owned_file.py \
  --prompt-file "$PROMPTS/brief.txt" --run-dir "$RUNS/work-1" --timeout 900

# 3. Independent review (Grok via Cursor, read-only ask mode).
#    Ask mode takes no --allow-path. Use --trust only for a workspace that
#    is already authorized/trusted or a fixture you created.
python3 "$SKILL/scripts/worker.py" --provider grok --mode ask \
  --workspace "$CHECKOUT" --trust \
  --prompt-file "$PROMPTS/review.txt" --run-dir "$RUNS/review-1" --timeout 600

# 3b. Native review alternatives (read-only ask uses plan; no --trust).
#     Grok Build uses fixed xhigh reasoning; Antigravity uses fixed high
#     effort with gemini-3.8-flash-high (receipts record high, not xhigh).
python3 "$SKILL/scripts/worker.py" --provider grok-build --mode ask \
  --workspace "$CHECKOUT" \
  --prompt-file "$PROMPTS/review.txt" --run-dir "$RUNS/review-gb-1" --timeout 600
python3 "$SKILL/scripts/worker.py" --provider antigravity --mode ask \
  --workspace "$CHECKOUT" \
  --prompt-file "$PROMPTS/review.txt" --run-dir "$RUNS/review-agy-1" --timeout 600

# 3c. Native work alternatives (bounded edits only; ask stays read-only).
#     Grok Build work uses --permission-mode acceptEdits; Antigravity work
#     uses --mode accept-edits. Never add always-approve, bypass, dangerous
#     skip, yolo, or force flags.
python3 "$SKILL/scripts/worker.py" --provider grok-build --mode work \
  --workspace "$CHECKOUT" --allow-path src/owned_file.py \
  --prompt-file "$PROMPTS/brief.txt" --run-dir "$RUNS/work-gb-1" --timeout 900
python3 "$SKILL/scripts/worker.py" --provider antigravity --mode work \
  --workspace "$CHECKOUT" --allow-path src/owned_file.py \
  --prompt-file "$PROMPTS/brief.txt" --run-dir "$RUNS/work-agy-1" --timeout 900

# 4. Collect sibling runs without ingesting transcripts.
#    The state file must live outside every run directory. At most two new
#    terminal handoffs are delivered per call by default
#    (--max-new-results 1..10); repeat until new_results is empty.
#    Previews are capped (--max-result-chars 200..20000, default 4000);
#    read the full result_path file when a preview is truncated.
python3 "$SKILL/scripts/collect.py" "$RUNS" --state /ABSOLUTE/collection-state.json

# 5. Coordinator acceptance (you, not a worker): inspect the diff, run the
#    focused checks and the repository gate yourself, then integrate only
#    accepted changes. A receipt status of "candidate" means transport and
#    preservation checks passed; it is not acceptance.
