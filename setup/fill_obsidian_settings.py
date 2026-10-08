"""Write the Execute Code plugin settings for this computer (macOS or Windows).

  python setup/fill_obsidian_settings.py            (run from the kit folder, after the plugin is installed)

Reads obsidian/execute-code-data.json (paths as __HOME__), points Python at the vault's runner (tools/runpy on macOS,
tools\\runpy.cmd on Windows), and writes ~/StudyVault/.obsidian/plugins/execute-code/data.json. Quit Obsidian first.
Haskell/Racket paths are only set when those optional modules are installed (see vault/_modules/*/INSTALL.md).
"""
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
HOME = Path.home()
VAULT = HOME / "StudyVault"
WIN = sys.platform == "win32"

data = json.loads((KIT / "obsidian" / "execute-code-data.json").read_text(encoding="utf-8"))
tools = VAULT / "tools"
data["pythonPath"] = str(tools / ("runpy.cmd" if WIN else "runpy"))
data["pythonInteractive"] = False
# optional modules: plugin defaults unless installed
data.update({"runghcPath": "runghc", "ghcPath": "ghc", "ghciPath": "ghci", "racketPath": "racket"})
if (tools / "hsnote.py").exists():                                   # Haskell module installed
    ghcup = Path("C:/ghcup/bin") if WIN else HOME / ".ghcup" / "bin"
    data["runghcPath"] = str(tools / ("runhs.cmd" if WIN else "runhs"))
    data["ghcPath"] = str(ghcup / ("ghc.exe" if WIN else "ghc"))
    data["ghciPath"] = str(ghcup / ("ghci.exe" if WIN else "ghci"))
    data["haskellInject"] = "-- HSNOTE @vault_path @note_path"
    data["haskellInteractive"] = False
if (tools / ("runrkt.cmd" if WIN else "runrkt")).exists():           # Racket module installed
    data["racketPath"] = str(tools / ("runrkt.cmd" if WIN else "runrkt"))
# any remaining __HOME__ placeholders (unused languages) → this computer's home
text = json.dumps(data, indent=2).replace("__HOME__", str(HOME).replace("\\", "\\\\"))
out = VAULT / ".obsidian" / "plugins" / "execute-code" / "data.json"
if not out.parent.exists():
    sys.exit(f"{out.parent} doesn't exist: install and enable the Execute Code plugin in Obsidian first.")
out.write_text(text, encoding="utf-8")
print(f"wrote {out}\n  pythonPath = {data['pythonPath']}")
