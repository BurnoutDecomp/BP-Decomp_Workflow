# CLAUDE.md

This project is tool-agnostic. The canonical operating guide is **[AGENTS.md](AGENTS.md)**,
imported below so it is always in context — then read **[STRATEGY.md](STRATEGY.md)** and the
ledger in `progress/`.

@AGENTS.md

Everything that applies to Claude Code lives in `AGENTS.md` and in the skills under
[`.agents/skills/`](.agents/skills/README.md), so that every agent (Codex, Antigravity, API
loops) inherits the same rules. Claude Code sees the skills once `work skills link` has run
(`work bootstrap` does it). Do not duplicate guidance here; edit `AGENTS.md` or the skill.
