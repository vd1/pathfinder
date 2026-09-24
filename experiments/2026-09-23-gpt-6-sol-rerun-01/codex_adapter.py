"""Translate the frozen engine's search flag for the installed Codex CLI."""
import os
import shutil
import sys

args = sys.argv[1:]
search = "live" if "--search" in args else "disabled"
args = [arg for arg in args if arg != "--search"]
binary = shutil.which("codex")
os.execv(binary, [binary, "-c", f'web_search="{search}"', *args])
