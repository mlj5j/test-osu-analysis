#!/usr/bin/env python3
"""One-time local setup for this workspace. Run once per machine.

Modeled on the group's earlier workstation/scripts/setup.sh (bash), rewritten
in Python to match this repo's scripts/ convention (setup.py, mount_remote.py).

Does three things:
  1. Checks ~/.ssh/config for an LPC host alias and a dedicated,
     SSH-multiplexed alias for Claude's own repeated automated connections
     (so those don't each pay a fresh Kerberos/GSSAPI handshake); offers to
     add one if missing. Never silently edits the file without asking.
  2. Asks which analyses to set up, then clones that analysis's reference
     clones into <analysis>/ref/ (skipped if something -- a clone or a
     symlink to an existing checkout -- is already there).
  3. Asks for your LPC username, whether sshfs mounting works on this
     machine, and (if disappearing_tracks was selected) whichever of the
     CMSSW_13/15/16 release work areas used for its CRAB-based NanoAOD
     production you have set up -- leave any/all blank if you don't have
     them yet and use the disapptrks-lpc-working-area-setup skill to create
     one first. Records everything in CLAUDE.local.md (prose, for Claude to
     read) and .mount-config.local.sh (shell variables, for fnal-mount.sh /
     scripts/mount_remote.py once that's implemented). Deliberately doesn't
     ask for a grid proxy path -- the lpc-remote-session skill checks the
     voms-proxy-init default and the LPC home-directory convention live,
     each session, rather than trusting a path recorded once and possibly
     gone stale.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SSH_CONFIG = Path.home() / ".ssh" / "config"

# Extend this as each analysis's own CLAUDE.md fills in its real
# reference-clone table. Only disappearing_tracks has one as of this writing --
# see disappearing_tracks/CLAUDE.md's "Reference clones (ref/)" section.
ANALYSIS_REF_CLONES: dict[str, list[tuple[str, str]]] = {
    "disappearing_tracks": [
        ("git@github.com:OSU-CMS/DisappTrks_Nano.git", "ref/DisappTrks_Nano"),
        ("git@github.com:OSU-CMS/DisappTrks.git", "ref/DisappTrks"),
        ("git@github.com:OSU-CMS/OSUNano.git", "ref/OSUNano"),
        ("git@github.com:PocketCoffea/PocketCoffea.git", "ref/PocketCoffea"),
    ],
}

# Group-wide read-only references (not tied to one analysis), cloned into the
# root references/ directory. See references/README.md.
ROOT_REF_CLONES: list[tuple[str, str]] = [
    ("git@github.com:OSU-CMS/OSU-Agentic-Analysis.git", "references/OSU-Agentic-Analysis"),
]


def discover_analyses() -> list[str]:
    return sorted(
        p.name
        for p in ROOT.iterdir()
        if p.is_dir() and (p / "CLAUDE.md").exists()
    )


def clone_if_missing(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"Already exists, skipping: {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", url, str(dest)], check=True)


def _find_cmslpc_username(text: str) -> str | None:
    """Find the ``User`` value from the first Host block whose pattern mentions
    cmslpc, scoped strictly to that one block (up to but not including the next
    ``Host`` line).

    A single regex spanning the whole file (the previous approach) is a trap here:
    with DOTALL a greedy ``.*cmslpc`` locks onto the *last* ``cmslpc`` occurrence
    in the file, not the first, and a lazy scan from there for the next ``User``
    line can land on an unrelated Host block entirely (confirmed in practice --
    it picked up a pixel-readout testbed's username instead of the real LPC one).
    Walking block-by-block can't wander past a block boundary like that.
    """
    in_cmslpc_block = False
    for line in text.splitlines():
        stripped = line.strip()
        host_match = re.match(r"(?i)^host\b(.*)$", stripped)
        if host_match:
            in_cmslpc_block = "cmslpc" in host_match.group(1).lower()
            continue
        if in_cmslpc_block:
            user_match = re.match(r"(?i)^user\s+(\S+)", stripped)
            if user_match:
                return user_match.group(1)
    return None


def check_ssh_config() -> None:
    text = SSH_CONFIG.read_text() if SSH_CONFIG.exists() else ""

    has_lpc_alias = re.search(r"(?im)^\s*host\s+.*cmslpc", text) is not None
    has_multiplex_alias = re.search(r"(?im)controlpersist", text) is not None

    if has_lpc_alias and has_multiplex_alias:
        print("~/.ssh/config already has an LPC alias and a multiplexed alias.")
        return

    # Reuse the username from an existing cmslpc-pointing Host block if one is
    # found, so the suggested snippet doesn't need a placeholder.
    username = _find_cmslpc_username(text) or "<your-username>"

    print()
    if not has_lpc_alias:
        print("No LPC host alias found in ~/.ssh/config.")
    if not has_multiplex_alias:
        print(
            "No SSH-multiplexed alias found. Claude's own automated LPC "
            "commands will each pay a fresh Kerberos/GSSAPI handshake "
            "without one -- see the lpc-remote-session skill."
        )

    # GSSAPIAuthentication/GSSAPIDelegateCredentials go inline in each alias
    # block below, *in addition to* the raw-hostname block further down -- SSH
    # matches `Host` patterns against the alias typed on the command line, not
    # the HostName it resolves to, so the raw-hostname block alone silently
    # never applies to an alias like cmslpc-claude (the bug a real session hit
    # and had to hand-fix -- see git history). The raw-hostname block is still
    # needed on its own for anyone/anything that SSHes to the literal hostname
    # directly (e.g. the CMSSW_13/el8 steps in disapptrks-lpc-working-area-setup).
    snippet = f"""
Host cmslpc
    HostName cmslpc-el9.fnal.gov
    User {username}
    GSSAPIAuthentication yes
    GSSAPIDelegateCredentials yes

Host cmslpc-claude
    HostName cmslpc-el9.fnal.gov
    User {username}
    GSSAPIAuthentication yes
    GSSAPIDelegateCredentials yes
    ControlMaster auto
    ControlPath ~/.ssh/cm-claude-%r@%h:%p
    ControlPersist 10m

Host cmslpc-el9.fnal.gov cmslpc-el8.fnal.gov
    GSSAPIAuthentication yes
    GSSAPIDelegateCredentials yes
"""
    print("Suggested ~/.ssh/config addition:")
    print(snippet)
    if input("Append this to ~/.ssh/config now? [y/N] ").strip().lower() == "y":
        with SSH_CONFIG.open("a") as f:
            f.write(snippet)
        print(f"Appended to {SSH_CONFIG}.")
    else:
        print("Skipped -- add it yourself later if you want the cmslpc-claude alias.")


def setup_analyses() -> list[str]:
    analyses = discover_analyses()
    if not analyses:
        print("No analysis directories with a CLAUDE.md found.")
        return []

    for url, rel_dest in ROOT_REF_CLONES:
        clone_if_missing(url, ROOT / rel_dest)

    print("\nAnalyses available:", ", ".join(analyses))
    chosen = input("Which do you want to set up? (comma-separated, or 'all') ").strip()
    selected = analyses if chosen.lower() == "all" else [
        name.strip() for name in chosen.split(",") if name.strip()
    ]

    valid_selected = []
    for name in selected:
        if name not in analyses:
            print(f"Skipping unknown analysis: {name}")
            continue
        valid_selected.append(name)
        ref_clones = ANALYSIS_REF_CLONES.get(name)
        if not ref_clones:
            print(
                f"{name}: no reference-clone table defined yet in this script -- "
                f"check {name}/CLAUDE.md and add entries to ANALYSIS_REF_CLONES "
                "once its lead has filled that table in."
            )
            continue
        for url, rel_dest in ref_clones:
            clone_if_missing(url, ROOT / name / rel_dest)

    return valid_selected


def setup_local_config(selected_analyses: list[str]) -> None:
    print()
    username = input("LPC username (blank to skip this section): ").strip()
    if not username:
        return
    sshfs_works = input(
        "Does sshfs mounting work on this machine? [y/N] "
    ).strip().lower() == "y"

    disapptrks_cmssw_paths: dict[str, str] = {}
    if "disappearing_tracks" in selected_analyses:
        print(
            "\ndisappearing_tracks NanoAOD production uses up to three CMSSW "
            "releases (CMSSW_13/15/16 -- see disappearing_tracks/CLAUDE.md for the "
            "standardized layout and exact versions). Enter the src/ path for "
            "whichever ones you use; blank to skip a release you don't need. If you "
            "don't have any of these yet, leave all three blank and ask Claude to "
            "run the disapptrks-lpc-working-area-setup skill first, then re-run this "
            "script."
        )
        for release in ("13", "15", "16"):
            path = input(f"  CMSSW_{release} src/ path (blank to skip): ").strip()
            if path:
                disapptrks_cmssw_paths[release] = path

    claude_local = ROOT / "CLAUDE.local.md"
    claude_local_text = (
        "(Generated by scripts/setup.py -- machine-specific, not shared.)\n\n"
        f"- LPC username: {username}\n"
        "- sshfs mounting on this machine: "
        + ("works" if sshfs_works else "does not work -- use the LPC-side fallback")
        + "\n"
    )
    if disapptrks_cmssw_paths:
        claude_local_text += (
            "- disappearing_tracks CMSSW release work areas (NanoAOD production, "
            "see disappearing_tracks/CLAUDE.md):\n"
        )
        for release, path in disapptrks_cmssw_paths.items():
            claude_local_text += f"  - CMSSW_{release}: {path}\n"
    claude_local.write_text(claude_local_text)
    print(f"Wrote {claude_local}.")

    mount_config = ROOT / ".mount-config.local.sh"
    mount_config_text = (
        "# Generated by scripts/setup.py -- per-machine, gitignored.\n"
        f'LPC_USERNAME="{username}"\n'
        f'SSHFS_WORKS={"1" if sshfs_works else "0"}\n'
    )
    for release in ("13", "15", "16"):
        mount_config_text += (
            f'DISAPPTRKS_CMSSW{release}_PATH="{disapptrks_cmssw_paths.get(release, "")}"\n'
        )
    mount_config_text += (
        "\n# Mount-table entries go here once scripts/mount_remote.py defines\n"
        "# their expected format -- not yet implemented.\n"
    )
    mount_config.write_text(mount_config_text)
    print(f"Wrote {mount_config}.")


def main() -> None:
    check_ssh_config()
    selected_analyses = setup_analyses()
    setup_local_config(selected_analyses)
    print("\nDone.")


if __name__ == "__main__":
    main()
