# Tmux Terminal Dashboard

A browser dashboard for viewing and interacting with the tmux sessions owned by
the Unix user running the service. It uses Python's standard library for the
HTTP/WebSocket and PTY bridge, with xterm.js assets installed from npm.

## Local development

```bash
npm install
python3 -m py_compile tmux_terminal_dashboard.py
python3 tmux_terminal_dashboard.py 127.0.0.1:8765
```

Open `http://127.0.0.1:8765/`. The process must run as the user whose tmux
sessions should be exposed. The Personal Gateway deployment supplies the
authenticated public URL and a private Unix socket; gateway configuration and
credentials are intentionally not part of this repository.

## Mobile controls

The mobile tools drawer provides session selection, terminal keys, scrolling,
font sizing, pane selection, pane zoom, and layout cycling. The compact floating
control keeps the terminal maximized when the drawer is closed.

## Safety

Do not commit gateway state, service manifests, private keys, tokens, local
environment files, or runtime logs. The ignore rules cover these local-only
artifacts; review `git diff` before publishing changes.
