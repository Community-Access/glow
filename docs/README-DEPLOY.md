# GLOW + Keycloak SSO Production Deployment Guide

This guide walks you through deploying GLOW with Keycloak SSO (Google & GitHub) on Ubuntu, including user/role automation, OIDC config, and secure transfer.

---

## 1. Files Provided
- `keycloak-setup.sh`: Automates Keycloak user/role creation and IdP setup
- `keycloak-users.json`: User/role batch config
- `glow-oidc-client.json`: OIDC client config for GLOW

Warning: `keycloak-users.json` and `glow-oidc-client.json` are tracked in
git. They must contain placeholders only. Before committing any edit to
them, re-scan for real values in `secret`, `password`, `clientSecret`, or
`credential` fields -- realm exports from a live Keycloak instance include
secrets by default.

---

## 2. Prepare Your Local Machine
- Place all scripts/configs in a folder (e.g., `glow-deploy/`)

---

## 3. Copy Files to Your Server (SCP)
Replace `ubuntu` and `myserver.bits-acb.org` with your actual username and server:

```sh
scp keycloak-setup.sh ubuntu@myserver.bits-acb.org:/home/ubuntu/
scp keycloak-users.json ubuntu@myserver.bits-acb.org:/home/ubuntu/
scp glow-oidc-client.json ubuntu@myserver.bits-acb.org:/home/ubuntu/
```

---

## 4. SSH Into Your Server
```sh
ssh ubuntu@myserver.bits-acb.org
```

---

## 5. Run the Keycloak Setup Script
```sh
chmod +x keycloak-setup.sh
./keycloak-setup.sh
```
- The script will prompt for your Keycloak admin password (unless set in the script).
- It will create users, assign roles, and configure Google & GitHub IdPs.

---

## 6. Place OIDC Client Config in GLOW
- Copy `glow-oidc-client.json` to your GLOW app config directory (e.g., `web/src/acb_large_print_web/`)
- Restart your GLOW app (Docker or systemd)

---

## 7. Test SSO
- Log in to https://glow.bits-acb.org with Google and GitHub for all users.
- Confirm admin/user roles are correct.

---

## 8. DNS & HTTPS Checklist
- Ensure DNS records for `glow.bits-acb.org` and `glow.bits-acb.org/auth` point to your server
- Use Let's Encrypt or similar for HTTPS (see Certbot docs)
- Update Keycloak and GLOW OIDC configs to use `https://` URLs

---

## 9. Troubleshooting
- Check Keycloak logs for errors: `docker logs <keycloak-container>`
- Check GLOW logs for OIDC errors
- For user/role issues, rerun the setup script or edit `keycloak-users.json`

---

## 10. Rollback
- To remove users/roles, use Keycloak admin console or CLI
- To reset IdPs, delete and recreate in Keycloak admin

---

**You are now ready for a secure, automated, production SSO deployment!**

For advanced help, see Keycloak and GLOW docs, or contact your technical lead.
