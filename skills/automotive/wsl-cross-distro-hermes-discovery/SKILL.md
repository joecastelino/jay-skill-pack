---
name: wsl-cross-distro-hermes-discovery
description: Reach and inspect OTHER WSL distros on this same Windows computer from inside the main Ubuntu-Migrated distro — e.g. to hunt for a "different Hermes install" hosting an agent (number_5 case, 2026-07-14). Includes the /init interop workaround when wsl.exe fails with Exec format error.
triggers:
  - different hermes terminal
  - other wsl distro
  - agent on a different install
  - wsl.exe exec format error
  - check other installs on this computer
---

# WSL Cross-Distro Discovery (find agents/Hermes on "other installs")

The AMG fleet lives in WSL distro **Ubuntu-Migrated** (`/home/itadmin`, imported
2026-06-26 from `C:\AgentMigration\joe-agent-stack-Ubuntu.tar`, 50GB). When Joe says an
agent was on a "different hermes terminal / different install" on the SAME computer,
check the other WSL distros before assuming a different machine.

## Step 1 — Enumerate distros
```sh
/mnt/c/Windows/System32/wsl.exe -l -v | tr -d '\0'
```
Known layout (2026-07-14): `Ubuntu-Migrated` (default, us) + `Ubuntu` (secondary, ~1.5GB
near-fresh). Distro disks: `C:\WSL\Ubuntu-Migrated\ext4.vhdx` (66GB) and
`C:\Users\joeca\AppData\Local\wsl\{guid}\ext4.vhdx` (secondary).

## Step 2 — THE INTEROP TRAP: "cannot execute binary file: Exec format error"
`wsl.exe` may work once and then fail with Exec format error mid-session (binfmt_misc
WSLInterop entry vanishes — `/proc/sys/fs/binfmt_misc/` shows only register/status; no
sudo to re-register). **Workaround: invoke through `/init` directly.**

CRITICAL QUIRK: `/init` consumes the argument after the exe path as argv[0], so you MUST
duplicate the program name:
```python
# WRONG: ['/init','/mnt/c/Windows/System32/wsl.exe','-l','-v']  -> prints version info (eats '-l')
# RIGHT:
args = ['/init','/mnt/c/Windows/System32/wsl.exe','wsl.exe','-l','-v']
```
Reusable runner (subprocess, NOT bash -c — quoting through bash re-breaks it):
```python
def wsl(cmd, distro='Ubuntu', user='root'):
    args = ['/init','/mnt/c/Windows/System32/wsl.exe','wsl.exe',
            '-d',distro,'--cd','/tmp','-u',user,'--','sh','-c',cmd]
    r = subprocess.run(args, capture_output=True, text=True, timeout=120)
    return (r.stdout + r.stderr).replace('\x00','').strip()
```
- Output is UTF-16-ish: always strip `\x00`.
- Use `--cd /tmp`: default cwd translation fails across distros
  (`chdir(-Migrated/home/itadmin) failed`).
- `-u root` avoids "Failed to start systemd user session" noise for other users.
- First command to a Stopped distro auto-starts it (few seconds).

## Step 3 — Hunt for Hermes in the other distro
```python
wsl('ls /home; find /home /root -maxdepth 4 -iname "*hermes*" 2>/dev/null; which hermes')
wsl('tail -40 /home/<user>/.bash_history')   # shows what was actually done there
```
The bash_history is the goldmine — the secondary Ubuntu's history showed the whole story:
tar hash-check → `wsl --import Ubuntu-Migrated` → `hermes` → `hermes auth` (never
completed; no .hermes dir ever created). Conclusion: number_5 was an ABANDONED install
attempt — no brain/memory to migrate, rebuild fresh in the main fleet instead.

## Step 4 — Also rule out Windows-native installs
```sh
ls -d /mnt/c/Users/*/.hermes /mnt/c/Users/*/hermes* 2>/dev/null
```

## Pitfalls
- Do NOT `find /mnt/c -name ext4.vhdx` — scanning the whole C: drive over 9p times out
  (>120s). Check the known locations (`C:\WSL\`, `AppData/Local/wsl/`) directly.
- Interop can WORK at first and break later in the same session — if wsl.exe suddenly
  throws Exec format error, switch to the /init form; don't burn retries.
- An empty-looking distro can still hold data under other users — always `ls /home` and
  `/root` as root, not just the default user.
