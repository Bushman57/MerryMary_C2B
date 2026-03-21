"""One-off: minify Credentials.json into FIREBASE_CREDENTIALS_JSON in backend/.env"""
import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
cred_path = BACKEND / "Credentials.json"
env_path = BACKEND / ".env"

data = json.loads(cred_path.read_text(encoding="utf-8"))
minified = json.dumps(data, separators=(",", ":"))


def escape_for_dotenv_doublequoted(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


new_line = 'FIREBASE_CREDENTIALS_JSON="' + escape_for_dotenv_doublequoted(minified) + '"\n'

text = env_path.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)
out = [ln for ln in lines if not ln.startswith("FIREBASE_CREDENTIALS_JSON=")]

final = []
inserted = False
for line in out:
    final.append(line)
    if (not inserted) and line.strip() == "# Firebase credentials":
        final.append(new_line)
        inserted = True
if not inserted:
    final.append(new_line)

env_path.write_text("".join(final), encoding="utf-8")
print("OK: wrote FIREBASE_CREDENTIALS_JSON (%d chars minified JSON)" % len(minified))
