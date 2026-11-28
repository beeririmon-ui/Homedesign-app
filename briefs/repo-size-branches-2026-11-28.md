# Brief: a lean repo and a branch flow to `main` (general-purpose, 2026-11-28)

## Why
The owner (FB30 and FB31, `docs/studio-rules.md`) wants everything in the repo, `main` as the real state, and a branch per piece of work merged through a PR, if that is right and economical.

What we found:
- **All the work is on one long branch,** `claude/agent-system-brand-launch-ax87dv`. `main` holds only its root commit, which that branch already contains, so a PR would fast-forward.
- **The tracked tree is about 12 GB,** almost all of it `assets/`:
  - `renders/living-room` 2.95 GB;
  - `blockout/house` 1.25 GB;
  - `renders/poses` 1.10 GB;
  - `video/transitions` 1.04 GB.

  Raw kling takes, intermediate stills, both 1920 and 1080 frame folders, npy files and old versions are all in git. One file is 55 MB (`assets/video/transitions/warm-modern/route-fb21/leg3/k3c2.earlyblend.mp4`).
- **The CI workflow** (`.github/workflows/site-ci.yml`) runs on every PR touching `site/**` or `data/**`. Each run does a full checkout, `prepare:data`, the builds and e2e. With 12 GB that is slow, and it may fail on runner disk.

## The task: a proposal, `docs/proposals/repo-lean-branches-2026-11-28.md` (0 tokens)
1. **What must stay in git:**
   - what the site build and the tour truly read (`site/tools/**`, the manifests and configs);
   - the approved finals;
   - what binding docs or QA need.

   Measure each class of file, with sizes.
2. **What can stop being tracked from now on,** without breaking the build or losing anything owed to the owner:
   - raw takes, intermediate stills and frames that can be regenerated;
   - npy files and superseded versions.

   Propose `.gitignore` rules and where those files live instead (for example the scratchpad only, or a Release or artifact store). Say what the owner loses, if anything.
3. **History:**
   - **No rewriting.** Never propose a force-push or filtering of the shared branch without listing the risks.
   - Estimate what the repo would weigh with history kept, and say whether Git LFS for future large finals is worth it (cost and limits on GitHub).
4. **CI:** make the PR check lean and reliable. Consider:
   - a sparse or partial checkout of only what each step reads;
   - path filters;
   - which heavy steps run on PR and which only on `main`.

   Write the exact workflow change as a patch in the proposal. Don't apply it.
5. **The branch flow:**
   - one branch per work round (between owner approval points), from `main`;
   - PR to `main` when the round is approved and the checks are green.

   Say how parallel agents work inside one round branch (one working tree, no per-agent worktrees, because of disk). Say how the first PR, from the current branch to `main`, should go.

## Fixed rules
- **Read-only:** don't edit files outside the proposal. No git commands that change anything: never `git stash`, `checkout`, `reset`, `rm`, `filter-*` or `commit`.
- No network except reading GitHub docs if needed. No keys.
- **Your summary:** Hebrew, at most 10 lines, with the size today, the size going forward, the CI change, and the first steps.
