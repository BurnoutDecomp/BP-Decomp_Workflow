# CRLF-safe edits, byte-exact content, message files

## Why a `.bat` is CRLF-load-bearing and git cannot show the break

`.gitattributes` sets `*.bat text eol=crlf` and `*.cmd text eol=crlf` (and `*.sh text eol=lf`).
The object store keeps such files normalised to LF; git writes CRLF on checkout and strips it on
`git add`. So an LF working copy hashes exactly like the committed blob: `git status` and
`git diff` report the file **clean** while `cmd.exe` cannot parse it. A GitHub-hosted runner
shows the same break as an instant "exit 255" with no output. "Git says clean" is not "the file
on disk is correct".

Provenance: on 2026-08-27 a `sed -i` on `tools/build/build_game_exe.bat` rewrote every line to LF
(two other `.bat` files went the same way); the next wave's build died in cmd parse garbage and
had to find the invisible break first.

## The edit

Never `sed -i`, `tee`, or any Git-Bash tool that writes LF. Use Python that keeps the file's
own endings (write the script with your file-writing tool; run it by path):

```python
# edit_keep_eol.py FILE -- edit FILE without changing its line endings
import sys

path = sys.argv[1]
raw = open(path, "rb").read()
crlf = b"\r\n" in raw
text = raw.decode("utf-8").replace("\r\n", "\n")

# ... change `text` here; it holds LF-only lines ...

open(path, "wb").write((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
```

For mount lines use `work mount`, which edits the `.bat` CRLF-safely and checks the endings
after writing; `fold_partfiles.py fold` strips a fold's mount lines CRLF-safely on its own.

## The check, after any edit to a `.bat` or `.cmd`

One carriage return per line: the CR count equals the line count.

```bash
grep -c $'\r' tools/build/build_game_exe.bat      # must equal ...
wc -l < tools/build/build_game_exe.bat            # ... this
```

or, in any shell:

```bash
python -c "b=open('tools/build/build_game_exe.bat','rb').read(); print(b.count(b'\r\n'), b.count(b'\n'))"
```

The two numbers must be equal.

## The repair

- Nobody's uncommitted lines in the file: delete it, then `git checkout -- <file>`. Git restores
  CRLF from the blob; there is nothing to commit afterwards, because the blob was never wrong.
- The file carries uncommitted lines (yours or another agent's, as the shared `.bat` often does):
  do not `checkout`, which would discard them. Re-terminate it in place: read the bytes, replace
  `\r\n` with `\n`, then every `\n` with `\r\n`, write the bytes back, and run the check.

## Byte-exact content and the bash heredoc

The Bash tool's transport unescapes backslashes before the shell sees a heredoc, quoted or not:
`\\` collapses to `\` and `\n` becomes a real newline. Mount lines (`echo "%SRC%\..."`),
regexes and Windows paths are exactly the content that breaks.

- Anything containing backslashes goes through your file-writing tool and is then run or used by
  path.
- `SyntaxWarning: invalid escape sequence` from heredoc-fed Python is a transport-corruption
  warning, never noise. Re-read the file you wrote before trusting it.

## Commit messages come from a file

Write the message with your file-writing tool to a uniquely named file in your scratch folder
and commit with `git commit -F <file>` (or `commit-tree -F <file>`). Shell quoting and the
heredoc transport mangle multi-line messages, backslashes and the trailer. The message says what
was wrong and what the change does, cites the evidence (ARTIST addresses, the test's before and
after), and ends with the trailer as its last paragraph.
