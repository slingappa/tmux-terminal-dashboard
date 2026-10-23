# Personal Gateway Deployment

The dashboard is deployed behind Qualcomm Personal Gateway as an owner-only,
path-routed service. Gateway authentication and TLS are handled outside the
application; the dashboard itself does not store LDAP, SSO, or gateway
credentials.

## Published route

The current authenticated route is:

`https://personal-gateway.qualcomm.com/u/slingapp/default/s/tmux-terminals/`

Unauthenticated requests are redirected to the corporate SSO flow.

## Service shape

The active `default/prod` service uses a private Unix socket and the gateway's
base-path placeholder:

```toml
[[services]]
name = "tmux-terminals"
title = "tmux Terminal Dashboard"
description = "Browser terminal dashboard for tmux sessions."
allow_users = []
allow_lists = []
socket_path = "tmux-terminals.sock"
health_path = "/s/tmux-terminals"
routing = "path"

[services.start]
command = [
  "/usr/bin/python3",
  "/absolute/path/tmux-terminal-dashboard/tmux_terminal_dashboard.py",
  "$PERSONAL_GATEWAY_SERVICE_SOCKET",
]

[services.start.environment]
BASE_PATH = "$PERSONAL_GATEWAY_SERVICE_BASE_PATH"
```

`allow_users = []` and `allow_lists = []` keep the service owner-only. Add
explicit grants only through the gateway sharing controls when access is
intended for another user or LDAP list.

## Persistence

On the deployment host, the gateway is kept available with user-scoped systemd
units and user lingering:

- `personal-gateway.service` starts the `default/prod` profile.
- `personal-gateway-keepalive.timer` checks the profile every two minutes.
- `loginctl enable-linger slingapp` permits startup without an interactive
  login.

The local unit files and gateway state remain outside this repository. They may
contain host-specific paths and runtime state and must not be committed here.

## Verification

Run these commands as the deployment Unix owner:

```bash
personal-gateway --profile default --environment prod status
personal-gateway --profile default --environment prod service list
personal-gateway --profile default --environment prod doctor
```

The expected state is `Gateway: UP`, `Configuration: OK`, and
`tmux-terminals` `RUNNING`. Test the public route in a browser to complete the
SSO and WebSocket checks; unauthenticated `curl` requests should return an SSO
redirect rather than dashboard content.
