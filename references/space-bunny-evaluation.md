# Space Bunny Free matched trial — 2026-09-23

This is a small routing trial, not a universal model leaderboard. The same synthetic prompts went to each distinct configured model family in fresh Git workspaces and sessions. All tasks were read-only except the final bounded edit, which compared the two OpenCode implementation routes. The underlying Grok Build route was not repeated because it is the same model family as Cursor Grok and has a separate known work-transport problem.

## Setup

- OpenCode 1.18.31: Space Bunny Free through the existing `opencode-go/space-bunny-free` login at its advertised `max` variant; Muse Spark 1.3 Contributor through `opencode-go/muse-spark-1.3-contributor` at its advertised highest `xhigh` variant.
- Cursor Grok 4.7 standard at `xhigh`; Antigravity Gemini 3.8 Flash at its CLI maximum `high` effort. Every request used the same substantive task packet and bounded worker handoff. No web or files outside synthetic fixtures were needed.
- One fresh run per model and task. Runs overlapped, so elapsed time includes current provider/server conditions. The requested effort flags and returned model metadata are transport evidence, not independent proof of hidden reasoning allocation.
- The coding tasks were checked locally. The review was scored against three independent defects in the supplied function. The routing task was scored against the supplied privacy constraints. No model judged its own output.

## Results

| Route | Pure code task | Security review | Privacy routing | Actual bounded edit | Observed elapsed seconds in task order |
| --- | ---: | ---: | ---: | ---: | --- |
| Muse `xhigh` | 11/11 | 3/3 | Correct | 16/16 | 16, 49, 17, 25 |
| Space Bunny `max` | 11/11 | 2/3 | Correct | 16/16 | 31, 66, 18, 28 |
| Cursor Grok `xhigh` | 11/11 | 2/3 | Correct | Not run; ask-only route | 62, 345, 35 |
| Antigravity Gemini `high` | 11/11 | 2/3 | Correct | Not run in this trial | 63, 94, 23 |

The pure code task implemented deterministic dependency batching with cycle, invalid-input, and no-mutation behavior. All four submitted runnable code; the same 11 local checks passed. The actual edit repaired a synthetic account-change function in owned `src/ledger.py`. Muse and Space Bunny changed only that file, each passed the same 16 local checks, and neither claimed to have run tests inside its shell-denied worker.

The review packet showed a ZIP extraction function with (1) a sibling-prefix escape from `startswith(root)`, (2) writes through existing symlinks, and (3) failure to reject non-regular ZIP entries. Muse identified all three. Space Bunny and Cursor Grok found the first two and proposed descriptor-relative no-follow writes, but missed the third. Antigravity found the first two; its suggested path checks still relied on a check-then-open sequence and did not address the non-regular entry. Each model correctly selected the sole zero-retention/no-training route for the synthetic private-record summarization and treated the public quality score as insufficient evidence about that job.

## Decision for this skill

**Task-specific ordering:** Muse first overall on this sample, Space Bunny second, Cursor Grok third, Antigravity fourth. The coding checks tie Muse and Space Bunny; the review result separates them. Cursor remains the default independent reviewer because this trial did not test sustained review quality and an implementation's reviewer should be independent. The 345-second Cursor review is a latency observation, not a quality verdict.

Add Space Bunny as a **provisional, selected OpenCode alternate** for small bounded implementation or a second opinion when its free capacity is useful. Keep Muse as the default implementation route and Cursor Grok as default independent review. Do not let Space Bunny review its own changes. A route-default change needs multiple real packages with accepted diffs, retries, review findings, latency, and provider usage tracked against the same acceptance criteria.

[OpenCode Go's current terms](https://opencode.ai/docs/go/) list Space Bunny as free for a limited period, zero-day retention, and no training; the local model catalog listed zero token price and `max` reasoning on 2026-09-23. The provider does not disclose the underlying model identity or the free-period end. Refresh inventory and terms before use. The trial used only synthetic data and does not expand the skill's permission to send secrets, excluded material, or private records. Muse Contributor remains marked training-enabled and not zero retention in the same provider documentation.

## Limits

There was one sample per route and task, and only one actual edit per OpenCode route. This does not test large refactors, multi-file integration, regression repair, long-context work, variance across repeated calls, or real cost savings. Each pure code output was checked by local examples and edge cases, while no model ran its own tests in ask mode. The actual edit's 16 checks establish behavior for that fixture only. The temporary run artifacts were kept outside the repository; the aggregate observations here are the durable record.

Separate read-only reviews of the larger runner integration diff returned no verdict: Grok Build timed out at 300 seconds and Antigravity at 180 seconds, each with zero changed paths. Those packets were larger than the matched benchmark prompts, so the timeouts are transport limits for that follow-up and are not included in the model ranking above. A narrower Cursor Grok 4.7 `xhigh` review of the runner diff completed in 130 seconds with no findings. The documentation and this report received structural/link checks, not a completed full-diff external review.
