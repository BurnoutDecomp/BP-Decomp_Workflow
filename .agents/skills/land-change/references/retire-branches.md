# Retire landed branches

A delivered branch is deleted, remote and local, as part of the same delivery, once its changes
are on the repository's integration branch (`dev` for b5-decomp, `main` for the parent). The
examples use `dev`; for the parent read `main` and drop the `-C b5-decomp`.

## 1. Prove the work landed

Matching names prove nothing. Use one of these:

- **Ancestry (merged or fast-forwarded):**
  `git -C b5-decomp fetch origin && git -C b5-decomp merge-base --is-ancestor <branch> origin/dev`
  (exit 0 = landed).
- **Patch equivalence (cherry-picked):** `git -C b5-decomp cherry -v origin/dev <branch>` lists
  the branch's commits; `-` = an equivalent change is upstream, `+` = it is not. Every line must
  be `-`.
- **Exact changed-path equivalence (squashed, or cherry-picked with edits):** every path the
  branch changed is identical on the integration branch.

  ```bash
  base=$(git -C b5-decomp merge-base origin/dev <branch>)
  git -C b5-decomp diff --name-only "$base" <branch>            # the paths the branch changed
  git -C b5-decomp diff --stat <branch> origin/dev -- <those paths>   # empty = identical upstream
  ```

  If upstream edited those paths again after the work landed, the diff is not empty even though
  the work is there: find the landing commit (`git -C b5-decomp log origin/dev -- <path>`) and
  confirm it carries the branch's hunks before you call it landed. When in doubt, keep the branch.

## 2. Delete

```bash
git -C b5-decomp push origin --delete <branch>
git -C b5-decomp branch -d <branch>        # -D only after an equivalence proof: squashed work is not an ancestor
```

- Duplicate or older refs: retire them only when a retained, published successor preserves
  their complete work.
- Unmerged work stays. A branch you cannot prove landed is not retired.

## 3. Worktrees and checkouts

- `git -C b5-decomp worktree list` shows every checkout of the repository.
- Never remove a dirty or active checkout (another agent may be working in it).
- A clean retired checkout may be detached at its exact existing commit before its branch is
  removed: `git -C <worktree> switch --detach <that commit>`. Keep any files and evidence it
  still holds that are needed.
- Do not accumulate completed campaign branches.
