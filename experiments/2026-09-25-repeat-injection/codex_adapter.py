"""Map the legacy search flag to the installed CLI's web_search setting."""
import os
import shutil
import sys

args = sys.argv[1:]
search = "live" if "--search" in args else "disabled"
args = [arg for arg in args if arg != "--search"]
binary = shutil.which("codex")
if not binary:
    raise SystemExit("codex is not installed")
os.execv(binary, [binary, "-c", f'web_search="{search}"', *args])
