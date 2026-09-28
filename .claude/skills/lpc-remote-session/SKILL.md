---
name: lpc-remote-session
description: Start and manage a long-running interactive session on the FNAL LPC over SSH -- checking (never creating) grid proxy validity, using tmux so work survives a dropped connection, and checking on or reattaching to a job later. Use whenever a task requires actually logging into and running something on cmslpc (not just producing a command for the user to run themselves), especially anything that takes more than a few seconds: batch job submission, Dask/Condor jobs, long builds. Do not use this to create or refresh a grid proxy -- that step is the user's alone.
---

# LPC Remote Sessions

Generic mechanics for actually doing something on the LPC over SSH, as opposed to just
telling the user a command to run themselves. Analysis- or tool-specific skills (CRAB,
PocketCoffea, EOS) build on top of this.

## SSH login

Use the host alias from the user's `~/.ssh/config` rather than guessing a raw hostname
or username -- check it first:

```bash
grep -A3 -i "host cmslpc" ~/.ssh/config
```

A common setup aliases `cmslpc` to `cmslpc-el9.fnal.gov` with a specific `User`. If no
alias exists, or several conflicting ones do, ask rather than guessing which
host/username to use.

**Prefer a dedicated, SSH-multiplexed alias for Claude's own connections, if one
exists** -- check for a `Host` block containing `ControlMaster`/`ControlPersist`
pointing at the same LPC host (`grep -B2 -A5 -i controlpersist ~/.ssh/config`), often
named something like `cmslpc-claude`. Use it instead of the user's own personal alias
when running commands within this skill: it reuses one authenticated connection across
repeated commands in a session instead of paying a fresh Kerberos/GSSAPI handshake for
each one, which matters when a task involves many small checks (proxy check, tmux
status, log tailing). If no such alias exists, use the regular personal alias and
mention that a multiplexed one (`scripts/setup.py` can suggest and add it) would speed
up repeated commands.

FNAL LPC login typically relies on Kerberos/GSSAPI (`GSSAPIAuthentication yes`,
`GSSAPIDelegateCredentials yes` in the ssh config), which needs a valid local Kerberos
ticket (`kinit`) rather than a per-connection password. If `ssh` hangs or unexpectedly
prompts for a password, that usually means an expired or missing Kerberos ticket --
say so and ask the user to `kinit`, rather than retrying the same command.

## Grid proxy: check, never create

CMS grid operations (CRAB, EOS `xrdcp`/`eos`, some PocketCoffea/Dask submission paths)
need a valid VOMS proxy. **Never run `voms-proxy-init` or attempt to supply a
certificate passphrase** -- that command is interactively gated for a reason, and
Claude has no secure way to provide the passphrase even if asked to. Before doing
something that needs a proxy, check without creating one:

```bash
ssh <lpc-host-alias> "bash -lc 'voms-proxy-info --exists --valid 1:00'"
```

Exit code `0` means a proxy valid for at least the next hour exists. Use a login
shell (`bash -lc '...'`), not a bare `ssh <host> "cmd"` -- a non-login shell never
sources `.bash_profile`/`.bashrc`, so a custom `X509_USER_PROXY` set there is
invisible to it even though the proxy is real (a confirmed case: the user's actual
path only ever showed up once they ran `voms-proxy-info` themselves and shared the
output). A login shell sees the same environment their own terminal would, with
nothing to guess, and still falls back to the plain default
(`/tmp/x509up_u$(id -u)`) if their profile sets nothing.

If that fails, retry the LPC-conventional home-directory path before concluding
there's no proxy -- some users keep it there without exporting `X509_USER_PROXY`
anywhere, precisely because `/tmp` is node-local and a proxy left there isn't
visible from a different login node:

```bash
ssh <lpc-host-alias> "X509_USER_PROXY=\$HOME/x509up_u\$(id -u) voms-proxy-info --exists --valid 1:00"
```

Only after *both* checks fail should you treat the proxy as actually missing/expired
-- stop and ask the user to run `voms-proxy-init` themselves (typically
`voms-proxy-init --voms cms --valid 192:00`) in their own terminal, then continue
once they confirm it's done. Don't work around a missing proxy with a fallback that
avoids the check -- surface it.

If both checks fail and the user reports (e.g. via their own interactive
`voms-proxy-info`) that a valid proxy exists somewhere else, ask where rather than
insisting there's no valid proxy at all -- `path:` in their `voms-proxy-info` output
names the actual location to check.

## tmux for anything long-running

Anything that takes more than roughly a minute, or that needs checking on later,
should run inside tmux so a dropped SSH connection doesn't kill it:

```bash
ssh <lpc-host-alias> "tmux new -d -s <session-name> '<command>'"
```

- Check for an existing relevant session first (`ssh <alias> tmux ls`) and reuse it if
  the same job is already running. Never kill a session that wasn't created for this
  task -- it may be the user's own unrelated work.
- Name the session for what it's doing (e.g. `signal-acceptance-2022efg`), not
  something generic like `job` or `run`, so the user can identify it later outside this
  conversation too.
- To check progress without disturbing the session: `ssh <alias> "tmux capture-pane -t
  <session-name> -p"` prints the current pane contents. Prefer this over attaching --
  Claude doesn't need an interactive attach to check status, and attaching can be
  disruptive if the user is also watching the same session.
- Don't `tmux kill-session` a still-running job unless asked -- stopping a
  partially-complete production job can waste significant compute/queue time. If a job
  needs to be stopped, say so and ask first.
- **tmux sessions are pinned to the specific login node they were created on, but the
  `cmslpc` alias is load-balanced across several nodes** -- a fresh `ssh <alias>`
  connection in a later turn (or a later session entirely) can land on a *different*
  node than the one holding your tmux session, making `tmux ls` come back empty even
  though the session is still alive. Before concluding a session is gone, check
  `ssh <alias> hostname` against the node you created it on (worth noting in your own
  tracking when you create the session), and if they differ, retry against that
  specific node directly (e.g. `ssh <lpc-username>@cmslpc373.fnal.gov` rather than the
  round-robin alias) -- `ssh` to a bare hostname needs the username spelled out
  explicitly since the alias's `User` mapping doesn't apply.

## Checking on a long job without blocking

For a job expected to take minutes to hours (a typical Dask/Condor submission), don't
sit in a tight poll loop waiting for it. Check once, report what's known, and either
schedule a follow-up check or tell the user how to ask again -- treat it like any other
long-running background work.

**`condor_q` spans multiple schedds at the LPC -- a plain `condor_q <username>` with
no `-name` queries whichever schedd is default for your login node, which is not
necessarily the one your jobs actually landed on.** A real session checked
`condor_q mjoyce` right after submitting ~26 jobs, got back "0 jobs," and concluded
the jobs were stuck -- when in fact they were sitting exactly where expected (5200
jobs, mostly idle) on a *different* schedd the default query never reached. Query
every known schedd explicitly rather than trusting the unqualified default, e.g.:

```bash
for schedd in lpcschedd4.fnal.gov lpcschedd5.fnal.gov lpcschedd6.fnal.gov; do
  ssh <lpc-host-alias> "condor_q -name $schedd <username> -totals"
done
```

(`condor_q <username> -totals` with no `-name` at all also works and prints a
per-schedd breakdown in one call -- use that first; fall back to explicit `-name`
queries, or ask the user, if the schedd list above goes stale.) Don't declare a job
"stuck" or "not found" from a single schedd's empty result.

## Gotchas seen in practice

- **`ssh` suddenly fails to authenticate (`Permission denied (gssapi-...)`) or hangs**:
  the Kerberos ticket expired. Ask the user to `kinit` -- don't retry. If they say they
  did and `klist` still shows the old ticket, the ticket landed in a *different credential
  cache* than the one your shell reads (e.g. a `KCM:` cache from their desktop session vs.
  the `FILE:/tmp/krb5cc_<uid>` your tool's `KRB5CCNAME` points at; a conda env can change
  which one `kinit` writes to). Compare the `Ticket cache:` line, and have them run
  `kinit -c FILE:/tmp/krb5cc_<uid>` (a `KCM:` cache is often unreachable from a sandboxed
  subprocess even when `klist` can read it).
- **`REMOTE HOST IDENTIFICATION HAS CHANGED`**: the `cmslpc` alias round-robins across login
  nodes with different host keys, so this recurs. It's benign here, but only remove the
  stale line once the user has said so (`ssh-keygen -R cmslpc-el9.fnal.gov`, then reconnect
  with `-o StrictHostKeyChecking=accept-new`).
- **`bash -l script.sh arg1 arg2` clobbers positional parameters**: the LPC login-profile
  scripts `set --`, so `$1`/`$2` come out wrong (one run wrote to a file literally named
  `=`). Pass values as environment variables (`VAR=x bash -l script.sh`) instead.
- **`pkill -f <pattern>` inside an `ssh` command kills its own shell** when the pattern
  appears in that command line. Use `ps aux | grep '[p]attern' | awk '{print $2}' | xargs kill`.
- **Backgrounding over ssh**: `ssh host "nohup cmd > log 2>&1 &"` keeps the ssh session
  attached to the child's output and the tool call blocks; use `ssh -f host "nohup cmd >
  log 2>&1 < /dev/null &"`, then poll the log with fresh short `ssh` calls.
- **Never clean up with a bare glob** (`rm ... *.json`) in a working area you didn't
  create. One did exactly that and deleted untracked estimate JSONs it had never listed. Name
  the files you made, or work in a fresh subdirectory you can `rm -rf` whole.
