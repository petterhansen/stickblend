import pathlib, re
def key():
    env = next((p / ".env" for p in pathlib.Path(__file__).resolve().parents if (p / ".env").exists()), None)   # naechste .env nach oben
    if env is None: raise SystemExit("GEMINI_API_KEY fehlt (.env im Repo-Root anlegen)")
    for line in env.read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r"\s*GEMINI_API_KEY\s*=\s*(.+)", line)
        if m: return m.group(1).strip().strip('"\'')
    raise SystemExit("GEMINI_API_KEY fehlt")
