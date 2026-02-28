# Deployment & Networking Guide

> How to serve, expose, and connect frontend/backend services inside the sandbox.

---

## 1. Sandbox Environment Overview

Every agent runs inside an isolated sandbox with its own networking stack. Services you start (web servers, APIs, etc.) bind to **local ports** inside the sandbox. An **external reverse proxy** (outside the sandbox, not visible in your nginx config) maps these local ports to public HTTPS URLs.

**You cannot see or configure the external proxy.** It is fully managed. Your job is to:
1. Start your service on a port
2. Know the public URL pattern
3. Configure your app's CORS / API base URLs accordingly

### Sandbox Metadata

The file `/dev/shm/sandbox_metadata.json` contains your sandbox identity:

```json
{
  "environment": "beta",
  "thread_id": "134212d3-8907-4593-8090-b21ec7365c33"
}
```

| Field         | Description                          | Example                                      |
|---------------|--------------------------------------|----------------------------------------------|
| `environment` | Deployment stage                     | `beta`                                       |
| `thread_id`   | Unique sandbox identifier (UUID)     | `134212d3-8907-4593-8090-b21ec7365c33`       |

---

## 2. Public URL Pattern

When you start a service on a port, the external proxy makes it available at:

```
https://<PORT>-<SANDBOX_ID>.app.super.<STAGE>myninja.ai
```

**Example:** A server on port `3000` in the sandbox above becomes:

```
https://3000-134212d3-8907-4593-8090-b21ec7365c33.app.super.betamyninja.ai
```

### How to Build the URL Programmatically

**Python:**
```python
import json

def get_public_url(port: int) -> str:
    with open("/dev/shm/sandbox_metadata.json") as f:
        meta = json.load(f)
    sandbox_id = meta["thread_id"]
    stage = meta["environment"]
    return f"https://{port}-{sandbox_id}.app.super.{stage}myninja.ai"

# Usage
api_url = get_public_url(8000)
frontend_url = get_public_url(3000)
```

**Bash:**
```bash
SANDBOX_ID=$(jq -r '.thread_id' /dev/shm/sandbox_metadata.json)
STAGE=$(jq -r '.environment' /dev/shm/sandbox_metadata.json)
PORT=3000

PUBLIC_URL="https://${PORT}-${SANDBOX_ID}.app.super.${STAGE}myninja.ai"
echo "$PUBLIC_URL"
```

**Node.js:**
```javascript
const fs = require('fs');

function getPublicUrl(port) {
  const meta = JSON.parse(fs.readFileSync('/dev/shm/sandbox_metadata.json', 'utf8'));
  return `https://${port}-${meta.thread_id}.app.super.${meta.environment}myninja.ai`;
}

// Usage
const apiUrl = getPublicUrl(8000);
const frontendUrl = getPublicUrl(3000);
```

---

## 3. Starting Services

### Available Runtimes

| Runtime    | Version | Command                        |
|------------|---------|--------------------------------|
| Python     | 3.11    | `python3 -m http.server 8085`  |
| Node.js    | 20.x    | `npm run dev` / `npx serve`    |

### Quick Start Examples

**Static files (Python):**
```bash
cd /workspace/ninja-squad/frontend
python3 -m http.server 8085
```

**Static files (Node.js):**
```bash
npx serve -l 8085 /workspace/ninja-squad/frontend
```

**Express API:**
```bash
cd /workspace/ninja-squad/backend
node server.js  # Listening on port 8000
```

**FastAPI / Flask:**
```bash
cd /workspace/ninja-squad/backend
uvicorn main:app --host 0.0.0.0 --port 8000
# or
flask run --host 0.0.0.0 --port 8000
```

### Important: Bind to `0.0.0.0`

Always bind your server to `0.0.0.0` (all interfaces), **not** `127.0.0.1` or `localhost`. The external proxy forwards traffic to your sandbox's network interface — if you bind to localhost only, the proxy cannot reach your service.

```python
# ✅ Correct — accessible via proxy
app.run(host="0.0.0.0", port=8000)

# ❌ Wrong — only accessible inside sandbox
app.run(host="127.0.0.1", port=8000)
```

---

## 4. Frontend + Backend Architecture

A typical setup uses two ports — one for the frontend, one for the backend API. Each gets its own public URL.

### Example Layout

```
Port 3000 → Frontend (React/Next.js)
Port 8000 → Backend API (FastAPI/Express)
```

Public URLs:
```
Frontend: https://3000-<SANDBOX_ID>.app.super.<STAGE>myninja.ai
Backend:  https://8000-<SANDBOX_ID>.app.super.<STAGE>myninja.ai
```

### Connecting Frontend to Backend

The frontend and backend run on **different origins** (different port subdomains), so this is a **cross-origin** setup. You must:

1. **Set the API base URL in the frontend** to the backend's public URL
2. **Enable CORS on the backend** to allow requests from the frontend's origin

---

## 5. CORS Configuration

Since frontend and backend are on different origins (different port prefixes in the URL), CORS headers are **required** on the backend.

### Reading Sandbox Metadata for CORS

The backend should read `/dev/shm/sandbox_metadata.json` at startup to build the correct allowed origins dynamically.

### Python (FastAPI)

```python
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Build allowed origins from sandbox metadata
def get_allowed_origins():
    try:
        with open("/dev/shm/sandbox_metadata.json") as f:
            meta = json.load(f)
        sandbox_id = meta["thread_id"]
        stage = meta["environment"]
        base = f"{sandbox_id}.app.super.{stage}myninja.ai"
        return [
            f"https://3000-{base}",   # React/Next.js default
            f"https://8085-{base}",   # Static file server
            f"https://4200-{base}",   # Angular default
        ]
    except Exception:
        # Fallback: allow all (development only)
        return ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok"}
```

### Python (Flask)

```python
import json
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

def get_allowed_origins():
    try:
        with open("/dev/shm/sandbox_metadata.json") as f:
            meta = json.load(f)
        sandbox_id = meta["thread_id"]
        stage = meta["environment"]
        base = f"{sandbox_id}.app.super.{stage}myninja.ai"
        return [
            f"https://3000-{base}",
            f"https://8085-{base}",
        ]
    except Exception:
        return ["*"]

CORS(app, origins=get_allowed_origins(), supports_credentials=True)

@app.route("/api/health")
def health():
    return {"status": "ok"}
```

### Node.js (Express)

```javascript
const express = require('express');
const cors = require('cors');
const fs = require('fs');

const app = express();

function getAllowedOrigins() {
  try {
    const meta = JSON.parse(fs.readFileSync('/dev/shm/sandbox_metadata.json', 'utf8'));
    const base = `${meta.thread_id}.app.super.${meta.environment}myninja.ai`;
    return [
      `https://3000-${base}`,
      `https://8085-${base}`,
      `https://4200-${base}`,
    ];
  } catch (e) {
    return ['*']; // Fallback for development
  }
}

app.use(cors({
  origin: getAllowedOrigins(),
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.listen(8000, '0.0.0.0', () => {
  console.log('API server running on 0.0.0.0:8000');
});
```

---

## 6. Frontend API Base URL Configuration

The frontend must know the backend's public URL. **Never use `localhost` or `0.0.0.0` in frontend code** — the browser runs on the user's machine, not inside the sandbox.

### Dynamic API URL Detection (Recommended)

Instead of hardcoding, detect the API URL from the current browser URL:

```javascript
/**
 * Derive the backend API URL from the current frontend URL.
 * 
 * If the frontend is at:
 *   https://3000-<sandbox_id>.app.super.betamyninja.ai
 * 
 * The backend (on port 8000) is at:
 *   https://8000-<sandbox_id>.app.super.betamyninja.ai
 */
function getApiBaseUrl(backendPort = 8000) {
  const hostname = window.location.hostname;
  // Match: <port>-<rest_of_hostname>
  const match = hostname.match(/^\d+-(.+)$/);
  if (match) {
    return `https://${backendPort}-${match[1]}`;
  }
  // Fallback for local development
  return `http://localhost:${backendPort}`;
}

// Usage
const API_URL = getApiBaseUrl(8000);
fetch(`${API_URL}/api/health`);
```

### Next.js

In `next.config.js` you can set up rewrites to proxy API calls, but in the sandbox environment it's simpler to call the backend directly:

```javascript
// lib/api.js
function getApiBaseUrl() {
  if (typeof window !== 'undefined') {
    const match = window.location.hostname.match(/^\d+-(.+)$/);
    if (match) return `https://8000-${match[1]}`;
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

export const API_URL = getApiBaseUrl();
```

### Angular

In `environment.ts`:
```typescript
function getApiUrl(): string {
  if (typeof window !== 'undefined') {
    const match = window.location.hostname.match(/^\d+-(.+)$/);
    if (match) return `https://8000-${match[1]}`;
  }
  return 'http://localhost:8000';
}

export const environment = {
  production: false,
  apiUrl: getApiUrl(),
};
```

### Svelte / SvelteKit

```javascript
// src/lib/config.js
export function getApiBaseUrl(backendPort = 8000) {
  if (typeof window !== 'undefined') {
    const match = window.location.hostname.match(/^\d+-(.+)$/);
    if (match) return `https://${backendPort}-${match[1]}`;
  }
  return `http://localhost:${backendPort}`;
}
```

---

## 7. Next.js Configuration

```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required: allow the external proxy hostname
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

Start with:
```bash
npx next dev -H 0.0.0.0 -p 3000
```

---

## 8. Common Port Assignments

Use these conventions to avoid conflicts between agents:

| Port  | Service                  | Agent  |
|-------|--------------------------|--------|
| 3000  | Frontend (React/Next.js) | Bolt   |
| 4200  | Frontend (Angular)       | Bolt   |
| 8000  | Backend API              | Bolt   |
| 8001  | Secondary API            | Bolt   |
| 8085  | Static file server       | Any    |
| 8086  | Documentation server     | Any    |
| 9000  | Test/preview server      | Scout  |

> **Avoid these reserved ports:** 22 (SSH), 2222 (ttyd terminal), 3222 (terminal proxy), 4000 (code-server), 5000 (VS Code proxy), 5900-5901 (VNC), 6080 (noVNC), 8002 (internal), 8080 (auth proxy).

---

## 9. Sharing URLs in Slack

The `slack_interface.py` automatically converts `0.0.0.0:<port>` references in messages to clickable public URLs. When you post a message like:

```
Server running at 0.0.0.0:3000
```

It becomes:

```
Server running at https://3000-134212d3-8907-4593-8090-b21ec7365c33.app.super.betamyninja.ai
```

This conversion happens automatically in `send_message()` — no extra work needed.

---

## 10. Troubleshooting

### Service not accessible via public URL

1. **Check binding:** Make sure your server binds to `0.0.0.0`, not `127.0.0.1`
2. **Check port:** Verify the service is actually listening: `ss -tlnp | grep <PORT>`
3. **Check reserved ports:** Don't use ports listed in section 8 as reserved
4. **Wait a moment:** The external proxy may take a few seconds to detect new services

### CORS errors in browser console

1. **Check origin:** The `Access-Control-Allow-Origin` header must include the frontend's full origin (e.g., `https://3000-<sandbox_id>.app.super.betamyninja.ai`)
2. **Check credentials:** If using cookies/auth, set `allow_credentials=True` and list specific origins (not `*`)
3. **Check preflight:** Ensure your backend handles `OPTIONS` requests (most CORS middleware does this automatically)
4. **Check headers:** If sending custom headers (e.g., `Authorization`), include them in `allow_headers`

### Frontend can't reach backend API

1. **Don't use `localhost` in frontend code** — the browser is on the user's machine, not in the sandbox
2. **Use the public URL** for the backend port (see section 6 for dynamic detection)
3. **Check CORS** on the backend (see section 5)
4. **Test the backend directly:** Open the backend's public URL in a browser to verify it responds

### Port already in use

```bash
# Find what's using the port
ss -tlnp | grep :<PORT>

# Kill the process
kill <PID>

# Or use fuser
fuser -k <PORT>/tcp
```

---

## 11. Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│                    SANDBOX NETWORKING                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Inside Sandbox          External Proxy          Browser        │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────┐   │
│  │ 0.0.0.0:3000 │──────▶│  HTTPS proxy │──────▶│  User    │   │
│  │ (frontend)   │       │  (managed)   │       │  Browser │   │
│  └──────────────┘       └──────────────┘       └──────────┘   │
│                                │                               │
│  ┌──────────────┐              │                               │
│  │ 0.0.0.0:8000 │──────────────┘                               │
│  │ (backend)    │                                              │
│  └──────────────┘                                              │
│                                                                 │
│  URL Pattern:                                                   │
│  https://<PORT>-<SANDBOX_ID>.app.super.<STAGE>myninja.ai       │
│                                                                 │
│  Metadata: /dev/shm/sandbox_metadata.json                      │
│  ┌─────────────────────────────────────────────┐               │
│  │ { "environment": "beta",                    │               │
│  │   "thread_id": "134212d3-...-b21ec7365c33" }│               │
│  └─────────────────────────────────────────────┘               │
│                                                                 │
│  Rules:                                                         │
│  ✅ Bind to 0.0.0.0 (all interfaces)                           │
│  ✅ Use public URL in frontend API calls                        │
│  ✅ Configure CORS on backend for frontend origin               │
│  ❌ Don't use localhost/127.0.0.1 in frontend code              │
│  ❌ Don't use reserved ports (22, 2222, 3222, 4000, 5000, etc) │
│  ❌ Don't try to configure the external proxy                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```