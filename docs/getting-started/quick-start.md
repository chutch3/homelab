# Quick Start

<div class="terminal-session" id="terminal-session">
<div class="terminal-chrome">
<span class="terminal-dot red"></span><span class="terminal-dot yellow"></span><span class="terminal-dot green"></span>
<span class="terminal-title">homelab — bash</span>
<span class="terminal-sections" id="terminal-sections"></span>
<button class="terminal-copy-all" id="copy-all-btn" title="Copy all commands">⎘ Copy All</button>
</div>
<div class="terminal-body" id="terminal-body">
<pre class="terminal-output" id="terminal-output"></pre>
</div>
</div>

<script>
(function() {
var lines = [
  {type:'section', text:'PREREQUISITES'},
  {type:'blank'},
  {type:'cmd', text:'docker --version'},
  {type:'out', text:'Docker version 27.4.1, build b9d17ea'},
  {type:'blank'},
  {type:'cmd', text:'python3 --version'},
  {type:'out', text:'Python 3.12.4'},
  {type:'blank'},
  {type:'cmd', text:'uv --version'},
  {type:'out', text:'uv 0.6.14'},
  {type:'blank'},
  {type:'cmd', text:'nslookup *.yourdomain.com'},
  {type:'out', text:'Name:    *.yourdomain.com'},
  {type:'out', text:'Address: 192.168.1.100'},
  {type:'blank'},
  {type:'comment', text:'# ✓ Docker (or let bootstrap install it)'},
  {type:'comment', text:'# ✓ Python + uv for Ansible'},
  {type:'comment', text:'# ✓ Wildcard DNS → server IP (Cloudflare, DNS-only)'},
  {type:'comment', text:'# ✓ Cloudflare API token (Zone:DNS:Edit)'},
  {type:'blank'},
  {type:'section', text:'CLONE'},
  {type:'blank'},
  {type:'cmd', text:'git clone https://github.com/chutch3/homelab.git && cd homelab'},
  {type:'out', text:'Cloning into \'homelab\'...'},
  {type:'out', text:'Receiving objects: 100% (4,218/4,218), 2.1 MiB, done.'},
  {type:'blank'},
  {type:'section', text:'CONFIGURE'},
  {type:'blank'},
  {type:'cmd', text:'cp .env.example .env'},
  {type:'blank'},
  {type:'comment', text:'# Set these required values in .env:'},
  {type:'cmd', text:'grep -E "^(BASE_DOMAIN|CF_Token|PRIMARY_DNS)" .env.example'},
  {type:'out', text:'BASE_DOMAIN=yourdomain.com'},
  {type:'out', text:'CF_Token=your_cloudflare_api_token'},
  {type:'out', text:'PRIMARY_DNS_API_KEY=your_dns_admin_password'},
  {type:'blank'},
  {type:'comment', text:'# Define your node(s):'},
  {type:'cmd', text:'cat ansible/inventory/02-hosts.yml'},
  {type:'out', text:'all:'},
  {type:'out', text:'  children:'},
  {type:'out', text:'    managers:'},
  {type:'out', text:'      hosts:'},
  {type:'out', text:'        manager-01:'},
  {type:'out', text:'          ansible_host: 192.168.1.100'},
  {type:'out', text:'          ansible_user: ubuntu'},
  {type:'blank'},
  {type:'section', text:'SSH'},
  {type:'blank'},
  {type:'cmd', text:'task ansible:install'},
  {type:'out', text:'✓ Dependencies installed'},
  {type:'blank'},
  {type:'cmd', text:'task ansible:ssh:generate'},
  {type:'out', text:'→ ~/.ssh/homelab_rsa'},
  {type:'blank'},
  {type:'cmd', text:'task ansible:ssh:distribute'},
  {type:'out', text:'ok: [manager-01] — key pushed'},
  {type:'blank'},
  {type:'cmd', text:'task ansible:ping'},
  {type:'out', text:'manager-01 | SUCCESS'},
  {type:'blank'},
  {type:'section', text:'BOOTSTRAP'},
  {type:'blank'},
  {type:'cmd', text:'task ansible:bootstrap'},
  {type:'out', text:'PLAY [Bootstrap cluster nodes] ********************************'},
  {type:'out', text:'TASK [Install Docker Engine] — changed: [manager-01]'},
  {type:'out', text:'TASK [Harden SSH] — ok: [manager-01]'},
  {type:'out', text:'PLAY RECAP — ok=14  changed=3  failed=0'},
  {type:'blank'},
  {type:'section', text:'DEPLOY'},
  {type:'blank'},
  {type:'cmd', text:'task ansible:deploy'},
  {type:'out', text:'PLAY [Deploy homelab cluster] **********************************'},
  {type:'out', text:'TASK [Initialize Docker Swarm] — ok'},
  {type:'out', text:'TASK [Deploy: reverse-proxy] — traefik + SSL'},
  {type:'out', text:'TASK [Deploy: dns] — technitium on :5380'},
  {type:'out', text:'TASK [Deploy: monitoring] — prometheus + grafana + loki'},
  {type:'out', text:'TASK [Deploy: applications] — 41 stacks deployed'},
  {type:'out', text:'TASK [Register DNS] — 41 CNAME records created'},
  {type:'out', text:'PLAY RECAP — ok=52  changed=41  failed=0'},
  {type:'blank'},
  {type:'section', text:'VERIFY'},
  {type:'blank'},
  {type:'cmd', text:'docker stack ls | head -6'},
  {type:'out', text:'NAME              SERVICES'},
  {type:'out', text:'authentik         3'},
  {type:'out', text:'dns               1'},
  {type:'out', text:'homepage          1'},
  {type:'out', text:'monitoring        8'},
  {type:'out', text:'reverse-proxy     1'},
  {type:'blank'},
  {type:'cmd', text:'curl -so /dev/null -w "%{http_code}" https://homepage.yourdomain.com'},
  {type:'out', text:'200'},
  {type:'blank'},
  {type:'section', text:'DONE'},
  {type:'blank'},
  {type:'comment', text:'# Dashboard:  https://homepage.yourdomain.com'},
  {type:'comment', text:'# Grafana:    https://grafana.yourdomain.com'},
  {type:'comment', text:'# DNS Admin:  https://dns.yourdomain.com:5380'},
  {type:'comment', text:'# Auth:       https://auth.yourdomain.com'},
  {type:'comment', text:'#'},
  {type:'comment', text:'# 41 services • SSL • DNS • SSO • monitoring'},
  {type:'blank'},
  {type:'comment', text:'# ─── Dig deeper ─────────────────────────────────────'},
  {type:'link', text:'Configuration Reference', href:'configuration/'},
  {type:'link', text:'Services Catalog', href:'../services/'},
  {type:'link', text:'Service Management', href:'../user-guide/service-management/'},
  {type:'link', text:'Storage Architecture', href:'../architecture/storage/'},
  {type:'link', text:'Tailscale VPN', href:'../user-guide/tailscale/'},
];

var output = document.getElementById('terminal-output');
var body = document.getElementById('terminal-body');
var sectionsBar = document.getElementById('terminal-sections');
if (!output) return;

var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
var lineIdx = 0;
var charIdx = 0;
var currentSpan = null;
var started = false;

// Build section nav in chrome bar
var sections = lines.filter(function(l) { return l.type === 'section'; });
sections.forEach(function(s) {
    var a = document.createElement('a');
    a.textContent = s.text;
    a.href = '#term-' + s.text.toLowerCase();
    a.addEventListener('click', function(e) {
        e.preventDefault();
        jumpToSection(s.text);
    });
    sectionsBar.appendChild(a);
});

function sectionId(text) {
    return 'term-' + text.toLowerCase().replace(/[^a-z0-9]+/g, '-');
}

function appendSpan(html, className) {
    var span = document.createElement('span');
    if (className) span.className = className;
    span.innerHTML = html;
    output.appendChild(span);
    body.scrollTop = body.scrollHeight;
    return span;
}

function renderInstant(line) {
    if (line.type === 'blank') { appendSpan('\n'); return; }
    if (line.type === 'section') {
        var id = sectionId(line.text);
        appendSpan('<a class="term-section-link" id="' + id + '">═══ ' + line.text + ' ═══════════════════════════════════════════════</a>\n', 'terminal-section');
        return;
    }
    if (line.type === 'cmd') { appendSpan('$ ' + line.text + '\n', 'terminal-cmd'); return; }
    if (line.type === 'comment') { appendSpan(line.text + '\n', 'terminal-comment'); return; }
    if (line.type === 'link') { appendSpan('  → <a href="' + line.href + '">' + line.text + '</a>\n', 'terminal-inline-link'); return; }
    appendSpan('  ' + line.text + '\n', 'terminal-out');
}

// Reduced motion: render everything immediately
if (reducedMotion) {
    lines.forEach(renderInstant);
    output.classList.add('done');
    return;
}

function renderLine() {
    if (lineIdx >= lines.length) { output.classList.add('done'); return; }

    var line = lines[lineIdx];

    if (line.type === 'blank') {
        appendSpan('\n');
        lineIdx++;
        setTimeout(renderLine, 50);
        return;
    }

    if (line.type === 'section') {
        var id = sectionId(line.text);
        appendSpan('<a class="term-section-link" id="' + id + '">═══ ' + line.text + ' ═══════════════════════════════════════════════</a>\n', 'terminal-section');
        lineIdx++;
        setTimeout(renderLine, 180);
        return;
    }

    if (line.type === 'link') {
        appendSpan('  → <a href="' + line.href + '">' + line.text + '</a>\n', 'terminal-inline-link');
        lineIdx++;
        setTimeout(renderLine, 80);
        return;
    }

    if (line.type === 'cmd') {
        if (charIdx === 0) {
            currentSpan = appendSpan('$ ', 'terminal-cmd');
        }
        if (charIdx < line.text.length) {
            var chunk = 1;
            if (line.text[charIdx] === ' ' || charIdx > 30) chunk = Math.min(2, line.text.length - charIdx);
            currentSpan.textContent += line.text.substring(charIdx, charIdx + chunk);
            charIdx += chunk;
            body.scrollTop = body.scrollHeight;
            setTimeout(renderLine, 14 + Math.random() * 12);
        } else {
            currentSpan.textContent += '\n';
            charIdx = 0;
            lineIdx++;
            setTimeout(renderLine, 220);
        }
        return;
    }

    // Output and comments — instant line
    if (line.type === 'comment') {
        appendSpan(line.text + '\n', 'terminal-comment');
    } else {
        appendSpan('  ' + line.text + '\n', 'terminal-out');
    }
    lineIdx++;
    setTimeout(renderLine, line.type === 'comment' ? 30 : 18);
}

function jumpToSection(sectionText) {
    var targetIdx = -1;
    for (var i = 0; i < lines.length; i++) {
        if (lines[i].type === 'section' && lines[i].text === sectionText) { targetIdx = i; break; }
    }
    if (targetIdx < 0) return;

    if (lineIdx <= targetIdx) {
        // Fast-forward: render everything up to target instantly
        for (var j = lineIdx; j <= targetIdx; j++) {
            if (lines[j].type === 'cmd' && charIdx > 0 && j === lineIdx) {
                // Finish current typing
                currentSpan.textContent += lines[j].text.substring(charIdx) + '\n';
                charIdx = 0;
            } else {
                renderInstant(lines[j]);
            }
        }
        lineIdx = targetIdx + 1;
        charIdx = 0;
        setTimeout(renderLine, 150);
    }

    var el = document.getElementById(sectionId(sectionText));
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Click-to-copy commands
output.addEventListener('click', function(e) {
    var cmdSpan = e.target.closest('.terminal-cmd');
    if (cmdSpan) {
        var txt = cmdSpan.textContent.replace(/^\$\s*/, '').trim();
        navigator.clipboard.writeText(txt).then(function() {
            cmdSpan.classList.add('copied');
            setTimeout(function() { cmdSpan.classList.remove('copied'); }, 1200);
        });
    }
});

// Copy all commands button
document.getElementById('copy-all-btn').addEventListener('click', function() {
    var allCmds = lines.filter(function(l) { return l.type === 'cmd'; }).map(function(l) { return l.text; }).join('\n');
    var btn = this;
    navigator.clipboard.writeText(allCmds).then(function() {
        btn.textContent = '✓ Copied';
        setTimeout(function() { btn.textContent = '⎘ Copy All'; }, 2000);
    });
});

// Start on scroll into view
var observer = new IntersectionObserver(function(entries) {
    if (entries[0].isIntersecting && !started) {
        started = true;
        setTimeout(renderLine, 300);
    }
}, {threshold: 0.1});
observer.observe(document.getElementById('terminal-session'));
})();
</script>
