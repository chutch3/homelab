# Postal

Self-hosted outbound mail platform (<https://postalserver.io>). The house mail
API: services (beholder, kopia, etc.) send through Postal's HTTP API or SMTP
intake and get per-app credentials, queueing, DKIM signing, and per-message
delivery logs at `postal.${BASE_DOMAIN}`.

## Delivery path

```
app -> postal (API :5000 / SMTP :2525) -> relay sidecar -> smtp2go :587 -> inbox
```

Outbound-only. Two constraints force the relay sidecar:

- AT&T blocks outbound port 25 at the network level, so Postal can never
  deliver directly to recipient MX servers from here.
- Postal's `POSTAL_SMTP_RELAYS` supports no authentication (host/port/ssl_mode
  only), so a postfix sidecar carries the smtp2go login.

Inbound mail is not possible (no port 25 ingress on residential service) and
nothing here expects it. Bounce processing is sacrificed — acceptable for
alerting to known-good addresses.

## First-time setup

1. Data directories are created by the deploy pre-flight; the DKIM signing key
   generates itself on the web service's first boot. Nothing manual here.

2. `.env` additions:

   ```
   POSTAL_DB_PASSWORD=<openssl rand -hex 24>
   POSTAL_SECRET_KEY=<openssl rand -hex 64>
   SMTP2GO_USERNAME=<smtp2go SMTP user>
   SMTP2GO_PASSWORD=<smtp2go SMTP password>
   ```

3. **Required after first deploy** — the containers start fine without this,
   but the app is unusable until it's done. Initialize the database schema and
   create the admin user (one time, on the node running the web service):

   ```sh
   docker exec $(docker ps -qf name=postal_web) postal initialize
   docker exec -it $(docker ps -qf name=postal_web) postal make-user   # interactive
   ```

   Symptom of a missed `postal initialize`: every page 500s and the web logs
   show `Mysql2::Error: Table 'postal.authie_sessions' doesn't exist`.

4. In the web UI (`https://postal.${BASE_DOMAIN}`): create an organization and
   a mail server (mode: Live), add the sending domain, and create an API
   credential per client app.

5. DNS: see [Cloudflare setup](#cloudflare-setup) below. Postal's own UI will
   additionally show a DKIM TXT and a verification TXT per domain — add those
   too, though smtp2go's records are what actually matter for deliverability
   since its IPs do the final delivery.

## Cloudflare setup

All records live in the Cloudflare zone for the sending domain (`example.dev`
below). Everything email-related must be **DNS only (grey cloud)** — proxied
CNAMEs break verification lookups.

### Inbound forwarding (Email Routing)

The domain needs to *receive* mail (relay-provider signup and verification,
DMARC reports) without hosting anything. Cloudflare Email Routing does this
for free:

1. Zone → **Email → Email Routing** → enable (it adds the MX/TXT records
   itself).
2. **Destination addresses**: add your real mailbox, click the verification
   link it sends.
3. **Routing rules → Create address**: e.g. `admin@example.dev` → send to the
   verified destination. Enabling the catch-all instead is convenient for a
   personal domain: any address on the domain reaches you.

### Relay verification (smtp2go)

smtp2go's "verify sender domain" flow issues three CNAMEs with an
account-specific ID; add them exactly as given, DNS only:

| Name (example) | Target | Purpose |
| --- | --- | --- |
| `em<id>.example.dev` | `return.smtp2go.net` | return-path / bounce alignment |
| `link.example.dev` | `track.smtp2go.net` | click tracking |
| `s<id>._domainkey.example.dev` | `dkim.smtp2go.net` | DKIM signing |

### SPF — one record only

A domain may have exactly **one** `v=spf1` TXT record; multiple SPF records
make all of them invalid. Email Routing and smtp2go each want their include,
so merge them into a single TXT on the zone apex:

```
v=spf1 include:_spf.mx.cloudflare.net include:spf.smtp2go.com ~all
```

If either dashboard complains it can't find "its" record verbatim, ignore it —
the merged record is what real SPF checks evaluate.

### DMARC

With SPF and DKIM aligned, add an anti-spoofing policy as a TXT record named
`_dmarc`:

```
v=DMARC1; p=quarantine; rua=mailto:admin@example.dev; adkim=r; aspf=r
```

- `p=quarantine` sends spoofed mail to spam; tighten to `p=reject` after a few
  weeks of clean aggregate reports.
- `rua=` receives those reports — any address the Email Routing rules forward.
- Relaxed alignment (`adkim=r; aspf=r`) is required because the return-path
  rides on the `em<id>` subdomain.

## Notes

- SMTP intake listens on 2525 (swarm drops `cap_add`, so no binding 25) and is
  reachable only on the `postal-internal` overlay; apps on other stacks should
  use the HTTPS API via traefik instead.
- MariaDB runs as root for Postal because it creates one `postal-*` database
  per mail server; the DB is only reachable on the internal overlay.
- Suppression lists still work (5xx replies from smtp2go); full bounce-webhook
  fidelity does not, see above.
