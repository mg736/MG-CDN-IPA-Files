#!/usr/bin/env python3
"""Generate install pages + manifests from apps.json, honouring per-app expiry.

Past its `expires` timestamp an app's manifest is DELETED (so a saved
itms-services:// URL fails too) and its page renders an expired notice.
Run locally after editing apps.json, or hourly via .github/workflows/expire.yml
"""
import json, os, sys
from datetime import datetime, timezone

CF = "https://d2wuvg8krwnvon.cloudfront.net/customapps"
BASE = "https://mg736.github.io/MG-CDN-IPA-Files"
BID = "com.appypiellc.appypiellc"
ROOT = os.path.dirname(os.path.abspath(__file__))

CSS = """:root{
  --brand-blue:#1FC0F1; --brand-green:#2DB92D; --brand-yellow:#F6B32E;
  --brand-orange:#F5811F; --brand-red:#F04410;
  --bg:#f2f4f7; --card:#fff; --fg:#14161a; --muted:#6b7280;
  --line:#e5e7eb; --dead:#d70015; --shadow:0 10px 40px rgba(16,24,40,.10);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0b0d10; --card:#16191e; --fg:#f3f4f6; --muted:#9aa1ab;
  --line:#272b32; --dead:#ff453a; --shadow:0 10px 40px rgba(0,0,0,.5);
}}
:root[data-theme="dark"]{
  --bg:#0b0d10; --card:#16191e; --fg:#f3f4f6; --muted:#9aa1ab;
  --line:#272b32; --dead:#ff453a; --shadow:0 10px 40px rgba(0,0,0,.5);
}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
background:var(--bg);color:var(--fg);margin:0;min-height:100vh;
display:flex;align-items:center;justify-content:center;padding:16px;
-webkit-font-smoothing:antialiased}
.card{background:var(--card);border-radius:22px;max-width:420px;width:100%;
box-shadow:var(--shadow);overflow:hidden;text-align:center}
.bar{height:5px;background:linear-gradient(90deg,
var(--brand-blue) 0%,var(--brand-green) 33%,var(--brand-yellow) 66%,var(--brand-red) 100%)}
.inner{padding:30px 26px 32px}
.logowrap{display:inline-block;margin-bottom:24px;line-height:0}
.logo{height:30px;width:auto}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .logowrap{
background:#fff;padding:10px 16px;border-radius:12px}}
:root[data-theme="dark"] .logowrap{background:#fff;padding:10px 16px;border-radius:12px}
h1{font-size:25px;line-height:1.2;margin:0 0 5px;letter-spacing:-.021em;font-weight:700}
.ver{color:var(--muted);font-size:14.5px;margin:0 0 26px;font-variant-numeric:tabular-nums}
a.btn{display:block;background:linear-gradient(135deg,var(--brand-blue),#0aa3d4);
color:#fff;padding:16px;border-radius:14px;text-decoration:none;font-size:17.5px;
font-weight:650;letter-spacing:-.01em;box-shadow:0 6px 18px rgba(31,192,241,.34);
transition:transform .15s ease,box-shadow .15s ease}
a.btn:active{transform:translateY(1px);box-shadow:0 3px 10px rgba(31,192,241,.3)}
ol{text-align:left;color:var(--muted);font-size:13.5px;line-height:1.65;
margin:26px 0 0;padding-left:20px}
ol li{margin-bottom:5px}
ol strong{color:var(--fg);font-weight:600}
.note{border-top:1px solid var(--line);margin-top:24px;padding-top:16px;
color:var(--muted);font-size:12.5px;line-height:1.55}
.exp{color:var(--muted);font-size:12.5px;margin:18px 0 0}
.badge{display:inline-flex;align-items:center;gap:7px;background:rgba(240,68,16,.1);
color:var(--dead);font-weight:650;font-size:15px;padding:10px 18px;border-radius:11px;margin:4px 0 12px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--dead)}
.hide{display:none}"""

PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Install {title}</title><style>{css}</style></head><body>
<div class="card" id="card" data-expires="{expires}">
  <div class="bar"></div>
  <div class="inner">
    <span class="logowrap"><img class="logo" src="appypie-logo.png" alt="Appy Pie"></span>
    <h1>{title}</h1>
    <p class="ver">Version {short} ({build})</p>
    <div id="live" class="{live_cls}">
      <a class="btn" href="itms-services://?action=download-manifest&amp;url={base}/{appid}.plist">Install</a>
      <ol>
        <li>Open this page in <strong>Safari</strong> (not Chrome).</li>
        <li>Tap <strong>Install</strong>, then confirm.</li>
        <li>Go to <strong>Settings &rsaquo; General &rsaquo; VPN &amp; Device Management</strong>.</li>
        <li>Tap <strong>Appy Pie LLC</strong> &rsaquo; <strong>Trust</strong>.</li>
      </ol>
      <p class="exp">This link expires <strong><span id="exp"></span></strong>.</p>
    </div>
    <div id="gone" class="{gone_cls}">
      <span class="badge"><span class="dot"></span>Link expired</span>
      <p class="note" style="border:none;margin-top:0;padding-top:0">
      This install link is no longer active. Contact the sender for a current one.</p>
    </div>
  </div>
</div>
<script>
(function(){{
  var c=document.getElementById('card'),t=Date.parse(c.dataset.expires);
  var e=document.getElementById('exp');
  if(e)e.textContent=new Date(t).toLocaleString();
  function tick(){{
    var dead=Date.now()>=t;
    document.getElementById('live').classList.toggle('hide',dead);
    document.getElementById('gone').classList.toggle('hide',!dead);
  }}
  tick();setInterval(tick,30000);
}})();
</script>
</body></html>"""

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>items</key>
  <array>
    <dict>
      <key>assets</key>
      <array>
        <dict>
          <key>kind</key><string>software-package</string>
          <key>url</key><string>{ipa_url}</string>
        </dict>
      </array>
      <key>metadata</key>
      <dict>
        <key>bundle-identifier</key><string>{bid}</string>
        <key>bundle-version</key><string>{build}</string>
        <key>kind</key><string>software</string>
        <key>title</key><string>{title}</string>
      </dict>
    </dict>
  </array>
</dict>
</plist>
"""

def main():
    cfg = json.load(open(os.path.join(ROOT, "apps.json")))
    now = datetime.now(timezone.utc)
    rows, changed = [], []

    for appid, a in cfg["apps"].items():
        exp = datetime.fromisoformat(a["expires"].replace("Z", "+00:00"))
        dead = now >= exp
        html = os.path.join(ROOT, appid + ".html")
        plist = os.path.join(ROOT, appid + ".plist")

        new_html = PAGE.format(css=CSS, title=a["title"], short=a["short"],
                               build=a["build"], appid=appid, base=BASE,
                               expires=a["expires"],
                               live_cls="hide" if dead else "",
                               gone_cls="" if dead else "hide")
        if not os.path.exists(html) or open(html).read() != new_html:
            open(html, "w").write(new_html); changed.append(appid + ".html")

        if dead:
            if os.path.exists(plist):
                os.remove(plist); changed.append("removed " + appid + ".plist")
        else:
            ipa_url = a.get("ipa_url") or f"{CF}/{appid}.ipa"
            new_pl = MANIFEST.format(ipa_url=ipa_url, bid=BID,
                                     build=a["build"], title=a["title"])
            if not os.path.exists(plist) or open(plist).read() != new_pl:
                open(plist, "w").write(new_pl); changed.append(appid + ".plist")

        rows.append((appid, a, dead))

    idx = ["""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>App Installs</title><style>%s
.card{text-align:left}
.inner{padding:30px 24px 26px}
.head{text-align:center}
a.app{display:flex;justify-content:space-between;align-items:center;gap:12px;
padding:15px 0;border-bottom:1px solid var(--line);text-decoration:none;color:var(--fg)}
a.app:last-of-type{border-bottom:none}
.n{font-weight:620;font-size:15.5px;letter-spacing:-.01em}
.v{color:var(--muted);font-size:12.5px;font-variant-numeric:tabular-nums}
.go{color:var(--brand-blue);font-size:21px;line-height:1}
.x{color:var(--dead);font-size:11.5px;font-weight:600;background:rgba(240,68,16,.1);
padding:4px 9px;border-radius:7px;white-space:nowrap}
.dim .n,.dim .v{opacity:.5}</style></head><body>
<div class="card">
  <div class="bar"></div>
  <div class="inner">
    <div class="head">
      <span class="logowrap"><img class="logo" src="appypie-logo.png" alt="Appy Pie"></span>
      <h1 style="font-size:22px;margin-bottom:20px">App Installs</h1>
    </div>""" % CSS]
    for appid, a, dead in rows:
        state = '<span class="x">expired</span>' if dead else '<span class="go">&rsaquo;</span>'
        dim = " dim" if dead else ""
        idx.append(
            '    <a class="app%s" href="%s.html">\n'
            '      <span><span class="n">%s</span><br><span class="v">%s (%s)</span></span>\n'
            '      %s\n    </a>' % (dim, appid, a["title"], a["short"], a["build"], state))
    idx.append("""    <p class="note">Open in <strong>Safari</strong> on an iPhone or iPad. After installing,
    trust the developer under Settings &rsaquo; General &rsaquo; VPN &amp; Device Management.</p>
  </div>
</div></body></html>""")
    new_idx = "\n".join(idx)
    ip = os.path.join(ROOT, "index.html")
    if not os.path.exists(ip) or open(ip).read() != new_idx:
        open(ip, "w").write(new_idx); changed.append("index.html")

    print(f"now={now.isoformat()}")
    for appid, a, dead in rows:
        print(f"  {appid}  {a['title']:<20} expires {a['expires']}  {'EXPIRED' if dead else 'active'}")
    print("changed: " + (", ".join(changed) if changed else "nothing"))

if __name__ == "__main__":
    main()
