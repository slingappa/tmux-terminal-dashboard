#!/usr/bin/env python3
import asyncio
import base64
import hashlib
import html
import json
import os
import pty
import signal
import struct
import subprocess
import sys
import termios
import fcntl
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


APP_DIR = Path(__file__).resolve().parent
SESSION_RE = re.compile(r"^[A-Za-z0-9_.:@-]{1,80}$")


INDEX_HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>tmux Terminal Dashboard</title>
  <link rel="stylesheet" href="./assets/xterm.css">
  <style>
    :root { color-scheme: dark; --bg:#0b1020; --panel:#121a2e; --panel2:#17223a; --line:#27344f; --text:#e6edf7; --muted:#9aa8bd; --accent:#38bdf8; --ok:#22c55e; --warn:#f59e0b; }
    * { box-sizing:border-box; }
    html, body { height:100%; min-height:100%; }
    body { margin:0; background:var(--bg); color:var(--text); font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; overflow:hidden; overscroll-behavior:none; }
    .shell { height:100vh; height:100dvh; min-height:320px; display:grid; grid-template-rows:auto minmax(0,1fr); }
    .topbar { display:grid; grid-template-columns:auto minmax(0,1fr) auto; gap:14px; align-items:center; min-height:62px; padding:10px 14px; padding-top:max(10px, env(safe-area-inset-top)); background:var(--panel); border-bottom:1px solid var(--line); }
    .brand { min-width:182px; display:grid; gap:2px; }
    .title { margin:0; font-size:15px; line-height:1.2; font-weight:700; white-space:nowrap; }
    .subtitle { color:var(--muted); font-size:12px; line-height:1.2; white-space:nowrap; }
    .tabs { display:flex; flex:1 1 auto; gap:8px; overflow-x:auto; min-width:0; scrollbar-width:auto; -webkit-overflow-scrolling:touch; overscroll-behavior-x:contain; touch-action:pan-x; scroll-snap-type:x proximity; }
    .tab { flex:0 0 auto; border:1px solid var(--line); color:var(--text); background:var(--panel2); height:44px; min-width:52px; max-width:180px; padding:0 12px; border-radius:8px; display:inline-flex; align-items:center; justify-content:center; gap:8px; cursor:pointer; font-weight:700; white-space:nowrap; scroll-snap-align:start; }
    .tab[aria-selected="true"] { border-color:var(--accent); box-shadow:inset 0 -2px 0 var(--accent); }
    .tab .name { min-width:0; overflow:hidden; text-overflow:ellipsis; }
    .tab .meta { color:var(--muted); font-weight:500; font-size:12px; flex:0 0 auto; }
    .actions { display:flex; gap:8px; align-items:center; }
    .icon-button { border:1px solid var(--line); background:var(--panel2); color:var(--text); width:38px; height:38px; border-radius:8px; cursor:pointer; display:grid; place-items:center; font-size:18px; line-height:1; }
    .status { min-width:92px; padding:8px 10px; border:1px solid var(--line); border-radius:8px; color:var(--muted); font-size:12px; text-align:center; white-space:nowrap; }
    .status[data-state="connected"] { color:var(--ok); }
    .status[data-state="warning"] { color:var(--warn); }
    .terminal-wrap { min-height:0; padding:10px; padding-bottom:max(10px, env(safe-area-inset-bottom)); display:grid; grid-template-rows:auto auto auto minmax(0,1fr); gap:8px; overflow:hidden; background:#050814; }
    .terminal-toolbar { display:flex; align-items:center; justify-content:space-between; gap:8px; min-height:38px; }
    .terminal-tools { display:none; align-items:center; gap:6px; margin-left:auto; }
    .terminal-tools button, .mobile-session select { min-height:40px; border:1px solid var(--line); border-radius:8px; background:var(--panel2); color:var(--text); padding:0 10px; font:inherit; font-weight:700; }
    .mobile-session { display:none; align-items:center; gap:8px; color:var(--muted); font-size:12px; }
    .keybar { display:none; gap:6px; overflow-x:auto; min-width:0; padding-bottom:1px; -webkit-overflow-scrolling:touch; overscroll-behavior-x:contain; touch-action:pan-x; }
    .keybar button { flex:0 0 auto; min-width:42px; min-height:40px; border:1px solid var(--line); border-radius:8px; background:var(--panel2); color:var(--text); padding:0 10px; font:inherit; font-weight:700; }
    .pane-tools { display:none; gap:6px; min-width:0; }
    .pane-tools button { flex:1 1 0; min-width:0; min-height:40px; border:1px solid var(--line); border-radius:8px; background:var(--panel2); color:var(--text); padding:0 8px; font:inherit; font-weight:700; }
    #terminal { width:100%; height:100%; min-height:0; border:1px solid var(--line); border-radius:8px; overflow:hidden; background:#000; touch-action:pan-y pinch-zoom; }
    .empty { height:100%; display:grid; place-items:center; color:var(--muted); border:1px dashed var(--line); border-radius:8px; font-size:14px; text-align:center; padding:24px; }
    @media (max-width:720px) {
      .topbar { grid-template-columns:1fr auto; gap:8px; padding-left:max(8px, env(safe-area-inset-left)); padding-right:max(8px, env(safe-area-inset-right)); }
      .brand { min-width:0; }
      .title { font-size:14px; }
      .subtitle { overflow:hidden; text-overflow:ellipsis; }
      .tabs { grid-column:1/-1; order:3; display:none; }
      .status { min-width:76px; padding:7px 8px; }
      .terminal-wrap { padding:6px; padding-bottom:max(6px, env(safe-area-inset-bottom)); gap:6px; }
      .mobile-session { display:flex; flex:1 1 150px; min-width:0; }
      .mobile-session select { width:100%; min-width:0; }
      .terminal-tools { display:flex; flex:0 0 auto; }
      .terminal-tools button { min-width:40px; padding:0 8px; }
      .keybar { display:flex; }
      .pane-tools { display:flex; }
    }
    @media (min-width:721px) { .terminal-toolbar { min-height:0; } }
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand"><h1 class="title">tmux Terminal Dashboard</h1><div class="subtitle" id="session-count">Loading sessions</div></div>
      <nav class="tabs" id="tabs" aria-label="tmux sessions"></nav>
      <div class="actions"><div class="status" id="status" data-state="warning">Loading</div><button class="icon-button" id="refresh" type="button" title="Refresh sessions" aria-label="Refresh sessions">&#x21bb;</button></div>
    </header>
    <main class="terminal-wrap">
      <div class="terminal-toolbar">
        <label class="mobile-session">Session <select id="session-select" aria-label="Select tmux session"></select></label>
        <div class="terminal-tools" aria-label="Terminal controls">
          <button id="scroll-up" type="button" title="Scroll terminal up" aria-label="Scroll terminal up">&#x25B2;</button>
          <button id="scroll-down" type="button" title="Scroll terminal down" aria-label="Scroll terminal down">&#x25BC;</button>
          <button id="font-down" type="button" title="Decrease terminal text size" aria-label="Decrease terminal text size">A&#x2212;</button>
          <button id="font-up" type="button" title="Increase terminal text size" aria-label="Increase terminal text size">A+</button>
        </div>
      </div>
      <div class="keybar" aria-label="Mobile terminal keys">
        <button type="button" data-key="up" aria-label="Send Up arrow">&#x2191;</button>
        <button type="button" data-key="down" aria-label="Send Down arrow">&#x2193;</button>
        <button type="button" data-key="left" aria-label="Send Left arrow">&#x2190;</button>
        <button type="button" data-key="right" aria-label="Send Right arrow">&#x2192;</button>
        <button type="button" data-key="escape" aria-label="Send Escape">Esc</button>
        <button type="button" data-key="tab" aria-label="Send Tab">Tab</button>
        <button type="button" data-key="enter" aria-label="Send Enter">Enter</button>
        <button type="button" data-key="ctrl-c" aria-label="Send Control C">Ctrl-C</button>
      </div>
      <div class="pane-tools" aria-label="Mobile tmux pane controls">
        <button type="button" data-pane="previous" aria-label="Select previous tmux pane">&#x25C0; Pane</button>
        <button type="button" data-pane="zoom" aria-label="Maximize or restore tmux pane">Zoom</button>
        <button type="button" data-pane="next" aria-label="Select next tmux pane">Pane &#x25B6;</button>
        <button type="button" data-pane="layout" aria-label="Cycle tmux pane layout">Layout</button>
      </div>
      <div id="terminal"></div>
    </main>
  </div>
  <script src="./assets/xterm.js"></script>
  <script src="./assets/xterm-addon-fit.js"></script>
  <script>
    // The public gateway adds /u/<owner>/<profile> before the service path.
    // Resolve requests from the actual browser URL so that prefix is retained.
    const routePath = location.pathname.replace(/\/+$/, "");
    const tabsEl = document.getElementById("tabs");
    const sessionSelect = document.getElementById("session-select");
    const statusEl = document.getElementById("status");
    const countEl = document.getElementById("session-count");
    const terminalEl = document.getElementById("terminal");
    const refreshButton = document.getElementById("refresh");
    const savedFontSize = Number.parseInt(localStorage.getItem("tmux-dashboard-font-size") || "14", 10);
    let fontSize = Number.isFinite(savedFontSize) ? Math.max(10, Math.min(savedFontSize, 22)) : 14;
    const term = new Terminal({cursorBlink:true, convertEol:true, fontFamily:"Menlo, Consolas, monospace", fontSize, theme:{background:"#000", foreground:"#d8dee9", cursor:"#38bdf8", selectionBackground:"#334155"}});
    const fit = new FitAddon.FitAddon();
    term.loadAddon(fit);
    term.open(terminalEl);
    fit.fit();
    let sessions = [];
    let activeSession = "";
    let socket = null;
    let resizeTimer = null;
    let touchState = null;
    let reconnectTimer = null;
    let reconnectDelay = 1000;
    function setStatus(text, state) { statusEl.textContent = text; statusEl.dataset.state = state || "warning"; }
    function wsURL(session) { const proto = location.protocol === "https:" ? "wss:" : "ws:"; return `${proto}//${location.host}${routePath}/ws?session=${encodeURIComponent(session)}`; }
    function sendResize() { if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({type:"resize", cols:term.cols, rows:term.rows})); }
    function renderTabs() {
      tabsEl.innerHTML = "";
      for (const session of sessions) {
        const button = document.createElement("button");
        button.className = "tab"; button.type = "button"; button.setAttribute("role", "tab"); button.setAttribute("aria-selected", session.name === activeSession ? "true" : "false"); button.title = `${session.name} (${session.windows} windows)`;
        const name = document.createElement("span"); name.className = "name"; name.textContent = session.name;
        const meta = document.createElement("span"); meta.className = "meta"; meta.textContent = session.attached > 0 ? "live" : `${session.windows}w`;
        button.append(name, meta); button.addEventListener("click", () => connect(session.name)); tabsEl.appendChild(button);
      }
      sessionSelect.replaceChildren(...sessions.map(session => {
        const option = document.createElement("option"); option.value = session.name; option.textContent = session.name; return option;
      }));
      sessionSelect.value = activeSession;
      tabsEl.querySelector('[aria-selected="true"]')?.scrollIntoView({block:"nearest", inline:"nearest"});
    }
    function scheduleReconnect() {
      if (reconnectTimer || document.hidden || !activeSession) return;
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connect(activeSession, true);
      }, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, 30000);
    }
    function connect(session, preserveTerminal = false) {
      activeSession = session; renderTabs();
      if (socket) { socket.onclose = null; socket.close(); }
      if (!preserveTerminal) { term.reset(); term.write(`Connecting to tmux session ${session}...\r\n`); }
      setStatus(preserveTerminal ? "Reconnecting" : "Connecting", "warning");
      const currentSocket = new WebSocket(wsURL(session));
      currentSocket.binaryType = "arraybuffer";
      socket = currentSocket;
      currentSocket.onopen = () => {
        if (socket !== currentSocket) return;
        reconnectDelay = 1000;
        setStatus("Connected", "connected"); fit.fit(); sendResize();
      };
      currentSocket.onmessage = event => { if (socket === currentSocket) term.write(event.data instanceof ArrayBuffer ? new Uint8Array(event.data) : event.data); };
      currentSocket.onclose = () => {
        if (socket !== currentSocket) return;
        socket = null;
        setStatus("Reconnecting", "warning");
        scheduleReconnect();
      };
      currentSocket.onerror = () => { if (socket === currentSocket) setStatus("Reconnecting", "warning"); };
    }
    function sendWheel(deltaY) {
      const element = term.element;
      if (!element) return;
      element.dispatchEvent(new WheelEvent("wheel", {deltaY, deltaMode:0, bubbles:true, cancelable:true}));
    }
    function sendInput(data) {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({type:"input", data}));
        term.focus();
      }
    }
    function keySequence(key) {
      const cursorPrefix = term.modes.applicationCursorKeysMode ? "\x1bO" : "\x1b[";
      return ({up:cursorPrefix+"A", down:cursorPrefix+"B", right:cursorPrefix+"C", left:cursorPrefix+"D", escape:"\x1b", tab:"\t", enter:"\r", "ctrl-c":"\x03"})[key] || "";
    }
    function setFontSize(next) {
      fontSize = Math.max(10, Math.min(next, 22));
      term.options.fontSize = fontSize;
      localStorage.setItem("tmux-dashboard-font-size", String(fontSize));
      scheduleFit();
    }
    function scheduleFit() {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (window.visualViewport && window.visualViewport.scale > 1.01) return;
        fit.fit(); sendResize();
      }, 80);
    }
    function handleTouchStart(event) {
      if (event.touches.length !== 1) { touchState = null; return; }
      touchState = {lastY:event.touches[0].clientY, remainder:0};
    }
    function handleTouchMove(event) {
      if (!touchState || event.touches.length !== 1) return;
      const currentY = event.touches[0].clientY;
      const delta = currentY - touchState.lastY;
      touchState.lastY = currentY;
      touchState.remainder += delta;
      const steps = Math.trunc(Math.abs(touchState.remainder) / 18);
      if (!steps) return;
      sendWheel(-Math.sign(touchState.remainder) * steps * 40);
      touchState.remainder -= Math.sign(touchState.remainder) * steps * 18;
      event.preventDefault();
    }
    function clearTouch() { touchState = null; }
    sessionSelect.addEventListener("change", () => connect(sessionSelect.value));
    document.getElementById("scroll-up").addEventListener("click", () => sendWheel(-120));
    document.getElementById("scroll-down").addEventListener("click", () => sendWheel(120));
    document.getElementById("font-down").addEventListener("click", () => setFontSize(fontSize - 1));
    document.getElementById("font-up").addEventListener("click", () => setFontSize(fontSize + 1));
    document.querySelectorAll(".keybar [data-key]").forEach(button => button.addEventListener("click", () => sendInput(keySequence(button.dataset.key))));
    document.querySelectorAll(".pane-tools [data-pane]").forEach(button => button.addEventListener("click", () => {
      if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({type:"pane", action:button.dataset.pane}));
    }));
    terminalEl.addEventListener("touchstart", handleTouchStart, {capture:true, passive:true});
    terminalEl.addEventListener("touchmove", handleTouchMove, {capture:true, passive:false});
    terminalEl.addEventListener("touchend", clearTouch, {capture:true, passive:true});
    terminalEl.addEventListener("touchcancel", clearTouch, {capture:true, passive:true});
    if (window.ResizeObserver) new ResizeObserver(scheduleFit).observe(terminalEl);
    window.addEventListener("resize", scheduleFit);
    window.visualViewport?.addEventListener("resize", scheduleFit);
    window.visualViewport?.addEventListener("scroll", scheduleFit);
    term.onData(data => { if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({type:"input", data})); });
    term.onResize(() => sendResize());
    async function keepAlive() {
      try {
        const response = await fetch(`${routePath}/api/sessions`, {cache:"no-store", credentials:"same-origin"});
        const contentType = response.headers.get("content-type") || "";
        if (!response.ok || response.redirected || !contentType.includes("application/json")) {
          throw new Error("authentication session expired");
        }
        await response.json();
      } catch (error) {
        setStatus("Sign-in required", "warning");
      }
    }
    setInterval(() => { if (!document.hidden) keepAlive(); }, 240000);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) { keepAlive(); scheduleFit(); if (!socket || socket.readyState !== WebSocket.OPEN) scheduleReconnect(); }
    });
    window.addEventListener("online", () => { keepAlive(); if (!socket || socket.readyState !== WebSocket.OPEN) scheduleReconnect(); });
    async function loadSessions(preferred) {
      setStatus("Loading", "warning");
      const response = await fetch(`${routePath}/api/sessions`, {cache:"no-store"});
      if (!response.ok) throw new Error(`session list failed: ${response.status}`);
      sessions = await response.json(); countEl.textContent = `${sessions.length} tmux session${sessions.length === 1 ? "" : "s"}`;
      if (!sessions.length) { tabsEl.innerHTML = ""; terminalEl.innerHTML = '<div class="empty">No tmux sessions are currently running.</div>'; setStatus("No sessions", "warning"); return; }
      const next = preferred && sessions.some(s => s.name === preferred) ? preferred : sessions[0].name;
      renderTabs();
      if (next !== activeSession || !socket || socket.readyState > WebSocket.OPEN) connect(next); else setStatus("Connected", "connected");
    }
    refreshButton.addEventListener("click", () => loadSessions(activeSession).catch(err => { setStatus("Error", "warning"); term.writeln(`\r\n${err.message}`); }));
    loadSessions("").catch(err => { setStatus("Error", "warning"); terminalEl.innerHTML = `<div class="empty">${err.message}</div>`; });
  </script>
</body>
</html>'''


def http_response(status, body=b"", content_type="text/plain; charset=utf-8", extra=None):
    reasons = {200:"OK", 400:"Bad Request", 404:"Not Found", 405:"Method Not Allowed", 500:"Internal Server Error"}
    if isinstance(body, str): body = body.encode()
    headers = [f"HTTP/1.1 {status} {reasons.get(status, 'OK')}", f"Content-Length: {len(body)}", f"Content-Type: {content_type}", "Cache-Control: no-store", "Connection: close"]
    if extra: headers.extend(extra)
    return ("\r\n".join(headers) + "\r\n\r\n").encode() + body


def list_sessions():
    proc = subprocess.run(["tmux", "list-sessions", "-F", "#{session_name}\t#{session_windows}\t#{session_attached}\t#{session_created}"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0: return []
    result = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 4: continue
        try: windows, attached, created = (int(x or 0) for x in parts[1:])
        except ValueError: continue
        result.append({"name":parts[0], "windows":windows, "attached":attached, "created":created})
    return result


def session_exists(name):
    return bool(SESSION_RE.match(name)) and subprocess.run(["tmux", "has-session", "-t", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0


def resize_pty(fd, rows, cols):
    rows = max(8, min(int(rows), 200)); cols = max(20, min(int(cols), 400))
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def spawn_tmux(name):
    pid, fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = "xterm-256color"; os.environ.pop("TMUX", None)
        os.execlp("tmux", "tmux", "attach-session", "-t", name)
    os.set_blocking(fd, False)
    return pid, fd


def tmux_prefix_bytes():
    proc = subprocess.run(["tmux", "show-options", "-gqv", "prefix"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    value = proc.stdout.strip()
    if len(value) == 1:
        return value.encode()
    if value.startswith("C-") and len(value) == 3:
        char = value[2].upper()
        if "@" <= char <= "_":
            return bytes([ord(char) & 0x1F])
    if value.startswith("M-") and len(value) == 3:
        return b"\x1b" + value[2].encode()
    return b"\x02"


def send_tmux_action(fd, action):
    keys = {"previous": b";", "next": b"o", "zoom": b"z", "layout": b" "}
    key = keys.get(action)
    if key is None:
        return
    os.write(fd, tmux_prefix_bytes() + key)


async def read_ws_frame(reader):
    head = await reader.readexactly(2); b1, b2 = head; opcode = b1 & 0x0F; length = b2 & 0x7F
    if length == 126: length = struct.unpack("!H", await reader.readexactly(2))[0]
    elif length == 127: length = struct.unpack("!Q", await reader.readexactly(8))[0]
    mask = await reader.readexactly(4) if b2 & 0x80 else b""; payload = await reader.readexactly(length) if length else b""
    if mask: payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
    return opcode, payload


def ws_frame(payload, opcode=2):
    if isinstance(payload, str): payload = payload.encode(); opcode = 1
    size = len(payload); header = bytearray([0x80 | opcode])
    if size < 126: header.append(size)
    elif size < 65536: header.extend([126]); header.extend(struct.pack("!H", size))
    else: header.extend([127]); header.extend(struct.pack("!Q", size))
    return bytes(header) + payload


async def terminal_ws(reader, writer, target):
    name = unquote(parse_qs(urlsplit(target).query).get("session", [""])[0])
    if not session_exists(name):
        writer.write(http_response(404, "Unknown tmux session\n")); await writer.drain(); writer.close(); return
    pid, fd = spawn_tmux(name); loop = asyncio.get_running_loop(); closed = asyncio.Event()
    def close_pty():
        if closed.is_set(): return
        closed.set()
        try: loop.remove_reader(fd)
        except Exception: pass
        try: os.close(fd)
        except OSError: pass
        try: os.kill(pid, signal.SIGHUP)
        except OSError: pass
    def on_readable():
        try:
            data = os.read(fd, 65536)
            if data: writer.write(ws_frame(data))
            else: close_pty()
        except (BlockingIOError, InterruptedError): pass
        except OSError: close_pty()
    loop.add_reader(fd, on_readable)
    try:
        while not closed.is_set():
            opcode, payload = await read_ws_frame(reader)
            if opcode == 8: break
            if opcode == 9: writer.write(ws_frame(payload, 10)); await writer.drain(); continue
            if opcode not in (1, 2): continue
            try: message = json.loads(payload.decode())
            except Exception: continue
            if message.get("type") == "input":
                try: os.write(fd, str(message.get("data", "")).encode("utf-8", "ignore"))
                except OSError: break
            elif message.get("type") == "resize":
                try: resize_pty(fd, message.get("rows", 24), message.get("cols", 80))
                except OSError: break
            elif message.get("type") == "pane":
                try: send_tmux_action(fd, str(message.get("action", "")))
                except OSError: break
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError): pass
    finally:
        close_pty()
        try: writer.write(ws_frame(b"", 8)); await writer.drain()
        except Exception: pass
        try:
            writer.close(); await writer.wait_closed()
        except Exception:
            pass


def static_asset(path):
    assets = {
        "/assets/xterm.js": APP_DIR / "node_modules/@xterm/xterm/lib/xterm.js",
        "/assets/xterm.css": APP_DIR / "node_modules/@xterm/xterm/css/xterm.css",
        "/assets/xterm-addon-fit.js": APP_DIR / "node_modules/@xterm/addon-fit/lib/addon-fit.js",
    }
    target = assets.get(path)
    if not target or not target.exists(): return None
    mime = "text/javascript; charset=utf-8" if target.suffix == ".js" else "text/css; charset=utf-8"
    return http_response(200, target.read_bytes(), mime, ["Cache-Control: public, max-age=3600"])


async def handle(reader, writer):
    try: raw = await reader.readuntil(b"\r\n\r\n")
    except Exception: writer.close(); return
    try:
        request_line, *header_lines = raw.decode("iso-8859-1").split("\r\n"); method, target, _ = request_line.split(" ", 2)
    except Exception:
        writer.write(http_response(400, "Bad request\n")); await writer.drain(); writer.close(); return
    headers = {}
    for line in header_lines:
        if ":" in line: key, value = line.split(":", 1); headers[key.lower()] = value.strip()
    parsed = urlsplit(target); path = parsed.path.rstrip("/") or "/"; base = os.environ.get("BASE_PATH", "").rstrip("/")
    if base and path.startswith(base): path = path[len(base):].rstrip("/") or "/"
    if headers.get("upgrade", "").lower() == "websocket" and path == "/ws":
        key = headers.get("sec-websocket-key")
        if not key: writer.write(http_response(400, "Missing websocket key\n")); await writer.drain(); writer.close(); return
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        writer.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n" + f"Sec-WebSocket-Accept: {accept}\r\n\r\n").encode()); await writer.drain()
        await terminal_ws(reader, writer, target); return
    if method != "GET": response = http_response(405, "Method not allowed\n")
    elif path in ("/", "/index.html"):
        safe_base = html.escape(base, quote=True); response = http_response(200, INDEX_HTML.replace("__BASE__", safe_base), "text/html; charset=utf-8")
    elif path == "/api/sessions": response = http_response(200, json.dumps(list_sessions()).encode(), "application/json; charset=utf-8")
    else: response = static_asset(path) or http_response(404, "Not found\n")
    writer.write(response); await writer.drain(); writer.close(); await writer.wait_closed()


async def main():
    endpoint = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:8765"
    if endpoint.startswith("/"):
        try: os.unlink(endpoint)
        except FileNotFoundError: pass
        server = await asyncio.start_unix_server(handle, path=endpoint); os.chmod(endpoint, 0o600); print(f"listening on unix:{endpoint}", flush=True)
    else:
        host, port_text = endpoint.rsplit(":", 1) if ":" in endpoint else ("127.0.0.1", endpoint); port = int(port_text)
        if host not in ("127.0.0.1", "localhost"): raise SystemExit("TCP mode must bind only to 127.0.0.1/localhost")
        server = await asyncio.start_server(handle, host=host, port=port); print(f"listening on http://{host}:{port}", flush=True)
    async with server: await server.serve_forever()


if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
