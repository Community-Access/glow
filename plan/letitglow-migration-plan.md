# GLOW Domain Migration Plan
## Migrating to `letitglow.app`

**Goal:** Make `letitglow.app` the canonical URL for GLOW. All historical domains
(`lp.csedesigns.com`, `glow.bits-acb.org`) should issue permanent `301` redirects
to `letitglow.app`, preserving paths and query strings so no existing links break.

---

## Current Domain Landscape

| Domain | Purpose | Action |
|---|---|---|
| `letitglow.app` | 🆕 New canonical GLOW URL | Serve the app here |
| `lp.csedesigns.com` | Old primary GLOW URL | 301 → `letitglow.app` |
| `glow.bits-acb.org` | Old secondary GLOW URL | 301 → `letitglow.app` |
| `csedesigns.com` / `www.csedesigns.com` | CSE Designs static site | No change |
| `ggg.csedesigns.com` | GGG podcast site | No change |

---

## Todo Checklist

### Phase 1 — DNS
- [ ] **1.1** Add an **A record** for `letitglow.app` → server's public IP at your domain registrar
- [ ] **1.2** Add an **A record** for `www.letitglow.app` → same IP (optional but recommended)
- [ ] **1.3** Wait for DNS propagation (5–60 min). Verify with: `dig letitglow.app` or `nslookup letitglow.app`

---

### Phase 2 — Caddyfile (`app/web/Caddyfile`)
- [ ] **2.1** Rename the existing GLOW server block to lead with `letitglow.app` as the primary domain, keeping `lp.csedesigns.com` and `glow.bits-acb.org` in the same block temporarily during cutover
- [ ] **2.2** After confirming the new domain works, replace the old domain entries in the GLOW block with a **separate redirect block**:
  ```
  lp.csedesigns.com, www.letitglow.app, glow.bits-acb.org {
      redir https://letitglow.app{uri} permanent
  }
  ```
- [ ] **2.3** Reload Caddy (`docker compose -f docker-compose.prod.yml exec caddy caddy reload --config /etc/caddy/Caddyfile`) — Caddy will auto-provision a TLS cert for `letitglow.app` via Let's Encrypt on first request

---

### Phase 3 — Keycloak OAuth (most critical)
> ⚠️ Keycloak must be updated **together** with the Caddyfile change or logins will break.

- [ ] **3.1** Update `app/web/.env`:
  - `KEYCLOAK_BASE_URL` → `https://letitglow.app/auth`
  - `KEYCLOAK_REDIRECT_URI` → `https://letitglow.app/authorize`
  - `KEYCLOAK_HOSTNAME` → `letitglow.app`
- [ ] **3.2** Update `app/web/docker-compose.prod.yml`:
  - `KC_HOSTNAME` env var → `letitglow.app`
- [ ] **3.3** In the **Keycloak Admin Console** (`https://lp.csedesigns.com/auth` → Admin → `glow` realm → Clients → `glow-web` → Settings):
  - Add `https://letitglow.app/*` to **Valid Redirect URIs**
  - Add `https://letitglow.app` to **Web Origins**
  - *(Keep old entries for now — remove in Phase 6 cleanup)*
- [ ] **3.4** Rebuild and restart containers: `docker compose -f docker-compose.prod.yml up -d --build`

---

### Phase 4 — Firebase Auth
- [ ] **4.1** In **Firebase Console** → Authentication → Settings → **Authorized domains**: add `letitglow.app`
  - URL: `https://console.firebase.google.com/project/glow-754e6/authentication/settings`
  - *(Keep old domains for now)*

---

### Phase 5 — GitHub OAuth App
- [ ] **5.1** In **GitHub → Settings → Developer settings → OAuth Apps**: find the app using `GITHUB_CLIENT_ID=Ov23li7l5O1nwh1dw9vG`
- [ ] **5.2** Add `https://letitglow.app/authorize` as an authorized callback URL
  - *(Keep old callback for now)*

---

### Phase 6 — Application Code
- [ ] **6.1** Update `app/web/src/acb_large_print_web/app.py` (line ~966):
  - Change `"HTTP-Referer": "https://glow.bits-acb.org"` → `"https://letitglow.app"`
- [ ] **6.2** Decide on email sender address for Postmark reports:
  - **Option A:** Keep `reports@glow.bits-acb.org` (no Postmark changes needed)
  - **Option B:** Switch to `reports@letitglow.app` — requires adding `letitglow.app` as a verified Sender Domain in Postmark first, then update `_DEFAULT_FROM` in `app/web/src/acb_large_print_web/email.py` or set `POSTMARK_FROM_EMAIL` in `.env`

---

### Phase 7 — Smoke Testing
- [ ] **7.1** `https://letitglow.app` loads the GLOW app correctly
- [ ] **7.2** `https://letitglow.app/health` returns `200 OK`
- [ ] **7.3** Full login flow works on `letitglow.app` (Keycloak + GitHub OAuth)
- [ ] **7.4** `https://lp.csedesigns.com` → `301` redirects to `https://letitglow.app` (path preserved)
- [ ] **7.5** `https://glow.bits-acb.org` → `301` redirects to `https://letitglow.app` (path preserved)
- [ ] **7.6** Test a deep link: `https://lp.csedesigns.com/some/path?query=1` → lands on `https://letitglow.app/some/path?query=1`
- [ ] **7.7** TLS cert for `letitglow.app` is valid (green padlock / no browser warnings)

---

### Phase 8 — Cleanup (wait 2–4 weeks after go-live)
- [ ] **8.1** Remove `lp.csedesigns.com` and `glow.bits-acb.org` from Keycloak Valid Redirect URIs and Web Origins
- [ ] **8.2** Remove old domains from Firebase Authorized Domains (optional — low risk to keep)
- [ ] **8.3** Remove old GitHub OAuth callback URLs
- [ ] **8.4** Decide whether to keep renewing `glow.bits-acb.org` DNS (recommended: keep for 1 year as a courtesy redirect)
- [ ] **8.5** Update any public documentation, README files, or links pointing to the old domains

---

## Key Files Reference

| File | What to Change |
|---|---|
| `~/app/web/Caddyfile` | Add `letitglow.app`, convert old domains to redirect block |
| `~/app/web/.env` | `KEYCLOAK_BASE_URL`, `KEYCLOAK_REDIRECT_URI`, `KEYCLOAK_HOSTNAME` |
| `~/app/web/docker-compose.prod.yml` | `KC_HOSTNAME` env var |
| `~/app/web/src/acb_large_print_web/app.py` | `HTTP-Referer` header (~line 966) |
| `~/app/web/src/acb_large_print_web/email.py` | `_DEFAULT_FROM` (if switching email domain) |

## External Services Reference

| Service | Where to Update |
|---|---|
| Domain registrar | DNS A record for `letitglow.app` |
| Keycloak Admin UI | `glow` realm → Clients → `glow-web` → Valid Redirect URIs + Web Origins |
| Firebase Console | Authentication → Settings → Authorized Domains |
| GitHub OAuth App | Developer Settings → OAuth Apps → Callback URLs |
| Postmark (optional) | Sender Signatures / Domains (only if changing From email) |

---

## ⚠️ Important Notes

- **Do Phase 3 (Keycloak) and Phase 2 (Caddy) in the same deployment window** — if Caddy serves `letitglow.app` but Keycloak still expects `lp.csedesigns.com`, logins will fail with a redirect URI mismatch error.
- **Keep old domains redirecting** as long as you keep paying for them. Users' bookmarks and shared links will continue to work.
- **DNS must propagate before Caddy can obtain a TLS cert** — don't trigger the Caddy reload until `dig letitglow.app` resolves to your server.
