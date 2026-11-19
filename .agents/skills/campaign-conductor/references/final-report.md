# Final report and RESUME file

Back to [the conductor skill](../SKILL.md).

## Final report

Written for the maintainer, not for agents: plain words, commits by sha, console addresses
wherever a follow-up needs them. State plainly what was not run, what is provisional, and why.
Keep it in the campaign folder (`<campaign dir>/FINAL_REPORT.md`) and give its summary in chat.

1. **Bottom line.** What landed on b5 `dev` (the commit range), how every fix is evidenced (a
   regression test that fails on the old body; independent reviews, and whether any FAIL is
   open), and the final exe (its sha and the b5 commit it was built from).
2. **The owner's symptoms against the evidence.** For each symptom, in the owner's words: what is
   now proven equal to the console and how; the real defects found that fed it (with commits);
   what is still unproven, and what evidence would close it (a console capture, for instance).
   "Inconclusive" is an honest verdict; "fixed" without evidence is not.
3. **Final live verification.** Run on the one frozen exe: each step with pass or fail and its
   numbers, assert and NaN counts, and every inconclusive step with its reason.
4. **What the player will see.** Each visible change, in player terms, with its commit.
5. **What the maintainer must do.** Every action nothing automates (data re-conversion on other
   installs, disk cleanup, decisions only the maintainer can take), each with the exact command.
6. **Handed to other contributors.** Findings in code someone else owns: the evidence, and where
   the handoff note is.
7. **Follow-ups.** What was not done, each with its console addresses and the lane or skill that
   should take it.

## RESUME file

Written when the maintainer pauses or stops the campaign (`<campaign dir>/RESUME_LATER.md`). It
is the first file anyone reads when the campaign resumes.

```markdown
# <campaign>: paused (<date time>)

The maintainer's instruction: "<verbatim>". Still running at the stop: <lanes>, finishing
<their current commit>.

## State at the stop
- b5 origin/dev: <sha>. Parent main: <sha>.
- The exe on disk: <sha>, built from b5 <sha>. It does NOT contain: <commits>.
- Verified live on that exe: <steps, with the report path>.
- Late commits not yet built or run: <sha>: <one line>; test <runner> <old N/M -> new M/M>;
  expected live result: <...>.

## To do, in order
1. <rebuild>: `<exact command>`
2. <live cases for the late fixes>: `<exact command>`; expected RED on <old exe>, GREEN on the new.
3. <runs that never ran>: `<exact command>`; first update <what a runner pins, e.g. an exe sha>.
4. <scan of every run>: `<exact command>`; then fill in the final report's <section>.
5. <deferred fix work>: <item>, <console addresses>, <where the notes are>.
6. <tidy-ups>: <untracked files to commit or drop>.
7. <maintainer actions>: <from the final report>.

## Hazards for whoever resumes
- <shared-tree work in progress and whose it is>
- <background runners or queues that may still be alive>
- <profile or save state the runs depend on>
```
