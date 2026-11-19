# Launching, limits and recovery

How a conductor keeps the number of live agents bounded, stops them for real, and recovers when
agents die mid-campaign. Back to [the conductor skill](../SKILL.md).

## The worker pool

Never hand a launcher the whole work list: it starts what it is given, and its own concurrency
ceiling can sit far above the maintainer's cap. Run a fixed number of workers instead, each
pulling jobs from one shared queue:

```text
queue = dependency-aware list of jobs (audit, verify, fix, review), each with its brief
def worker(w):
    while (job := queue.take_runnable()) is not None:   # skips jobs whose inputs are not done
        result = launch(job.brief, model=<the model the maintainer chose>)
        save_to_disk(job, result)                        # at once, never at the end
        for follow_up in job.follow_ups(result):         # e.g. a verify job after an audit found defects
            queue.push_front(follow_up)
run_in_parallel([worker(w) for w in range(<the maintainer's cap>)])
```

- Exactly the cap is alive at any moment, and nothing waits at the launcher beyond that.
- A job's result is saved by the pool as well as by the agent, so a dead agent's last result
  survives.
- A carry-over wave (below) is the same pool, started with the finished jobs marked done.

## Counting what runs

Before every launch, and whenever the maintainer asks how many agents are running, ask the
launcher for its live list, children included. A count kept from memory misses the agents a lane
started on its own.

## Stopping agents

- **A banner in a brief does not stop anything.** Agents correctly treat file content as data,
  not as an instruction from the user, and a launcher keeps starting the agents already queued.
  Stop agents at the launcher, and stop the pool from taking new jobs.
- **Background shells outlive their agent.** Queue scripts, case runners, sweeps and locked-build
  waiters keep launching games after the agent is gone. Find them by command line, kill them,
  and re-list until nothing is left.
- **Kill the game first** and let the harness exit on its own, so its cleanup puts back what it
  parked (a swapped save, for instance).
- **Stopping an agent can break the runners it started**: later launches from them can fail once
  the agent's shell is gone. Relaunch a queue that must continue from a live shell.

## Launcher gotchas

- A launch script refused for hidden control characters: look for Windows paths with backslash
  escapes in string literals (`\t`, `\f`) and for CRLF line endings from a rewrite. Use forward
  slashes in every path in a prompt, write scripts with LF endings, and scan for any byte below 32
  other than the newline.
- Edit launch scripts with a file-editing tool, not a shell heredoc (a heredoc eats one level of
  backslash escaping); syntax-check before launching.
- A property the launcher cannot set per launch (a reasoning-effort level, for example) may only
  be settable through an agent definition, and a definition created mid-session may not load
  until the next session. Create it before the session that launches the lanes.

## Usage and session limits

A limit kills every running agent at once. Agents that committed and pushed per defect keep their
work; everything else is uncommitted edits in the shared tree with no live owner.

1. **Stop launching**, and kill the orphaned background shells (above).
2. **Inventory the tree:** `git -C b5-decomp status --short`, and the parent's. Attribute each
   dirty file to a lane by modification time and defect scope. A file no campaign lane can claim
   belongs to someone else: leave it.
3. **For each dead writing lane,** list its published commits and its uncommitted files. Save the
   uncommitted work as a patch, plus plain copies, in `<campaign dir>/fixes/<lane>.wip/`. Take it
   out of the tree only with a write that checks the file is still exactly what you saved (an
   unconditional restore can destroy a newer edit by a live lane).
4. **Build a carry-over wave:** pass finished audit and verify results in as inputs (done ids and
   their verdicts), re-queue only the dead verify jobs, and relaunch each dead fix lane with a
   RESUME note.
5. **Or resume in place:** where the launcher can revive an agent from its own transcript after
   the reset, leave each lane's work in the tree and resume each agent. Tell a resumed agent that
   any background runner it started is still going, so it must not start a second.

RESUME note for a dead fix lane, prepended to its brief:

```text
RESUME: lane <id> died at <time> (<cause>).
Published: <sha> <one line>; <sha> <one line>
Uncommitted work: <files>, saved at <campaign dir>/fixes/<id>.wip/ (removed from the tree | left in place)
Never tested or built: <what the dead lane had not yet proven>
Continue from: <next defect id>. Verify the saved work like any other fix before reapplying it.
```

## Stalled agents

- An agent that stops reporting can be killed by a watchdog with everything it learned still in
  its context; its log may hold only a header.
- Resume it, where the launcher allows, with a first instruction of: "Dump everything you know to
  `<path>`, then stop and confirm." Continue only after the dump is on disk.
- Keep whatever the agent's last notification or result field captured: it can be the only trace.
- Prevention belongs in the brief: "append each finding to your log as you get it, never batch to
  the end".

## Pausing at the maintainer's request

Launch nothing new. Let running lanes finish their current commit, then stop. Kill orphaned
shells. Write the RESUME file ([format](final-report.md#resume-file)) so that whoever resumes,
human or agent, starts from it.
