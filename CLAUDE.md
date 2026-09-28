# OSU CMS Analysis Workspace

Shared home base for the OSU CMS group's LPC analyses. Generic tooling and
conventions only -- anything specific to one analysis belongs in that analysis's own
`<analysis>/CLAUDE.md` and `<analysis>/.claude/skills/`.

| Analysis | Directory | Maintainer |
| --- | --- | --- |
| Disappearing tracks | `disappearing_tracks/` | Matt Joyce |

`displaced_leptons/` and `milliqan/` also exist as scaffolding for future analyses but
aren't filled in yet -- see their own `CLAUDE.md` files.

## Remote Servers

The FNAL LPC is reached over SSH via an alias in `~/.ssh/config`, conventionally named
`cmslpc` (pointing at `cmslpc-el9.fnal.gov`), plus a second, SSH-multiplexed alias
(conventionally `cmslpc-claude`) reserved for Claude's own repeated automated
connections so they reuse one authenticated connection instead of paying a fresh
Kerberos/GSSAPI handshake per command. `scripts/setup.py` checks for both and offers
to add them if missing. See the `lpc-remote-session` skill for the actual
login/grid-proxy/tmux mechanics once connected.

## EOS

LPC storage is only ever accessed through the xrootd redirector
(`root://cmseos.fnal.gov/`), never through the `/eos/uscms/...` mount path directly --
that's an FNAL LPC admin policy, not a style preference. See the `lpc-eos` skill for
the commands. Personal space lives at `/store/user/<lpc-username>`; any
analysis-specific shared EOS subdirectory (e.g. a production output area) is documented
in that analysis's own `CLAUDE.md`.

## FNAL Mount

Not in active use yet -- every documented workflow today runs over SSH (via
`lpc-remote-session`) rather than through a local sshfs mount. `mnt/` and
`scripts/mount_remote.py` exist as scaffolding for that if/when an analysis actually
needs one; there's no real mount table to configure until then.

## Style guidelines

TBD -- not yet decided whether style conventions (see the `python-style` skill) apply
group-wide or should be set per analysis.

## Group-wide references (`references/`)

Read-only, gitignored clones of general HEP context that isn't specific to one
analysis (see `references/README.md`). Currently:
`references/OSU-Agentic-Analysis` -- the JFC framework's HEP analysis methodology,
agent-behavior specs, and domain conventions (visualization standards, analysis
technique guidance). Consult it for general analysis-practice questions; an
analysis's own `CLAUDE.md` and skills win where they differ.

## Setup

Run `scripts/setup.py` once per machine: checks/suggests LPC SSH aliases (including a
multiplexed one for Claude's own automated connections -- see the `lpc-remote-session`
skill), clones an analysis's `ref/` reference clones, and records your LPC
username/sshfs-support -- plus, if you select `disappearing_tracks`, its
CRAB/NanoAOD-production CMSSW release work areas -- in `CLAUDE.local.md` and
`.mount-config.local.sh` (both gitignored -- see `.gitignore`). Deliberately doesn't
record a grid proxy path -- `lpc-remote-session` checks that live each session
instead of trusting a stored path that could go stale.
