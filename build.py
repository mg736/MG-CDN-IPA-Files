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

CSS = """:root{--bg:#f5f5f7;--card:#fff;--fg:#1d1d1f;--muted:#6e6e73;--accent:#0071e3;--line:#d2d2d7;--dead:#d70015}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#000;--card:#1c1c1e;--fg:#f5f5f7;--muted:#98989d;--line:#38383a;--dead:#ff453a}}
:root[data-theme="dark"]{--bg:#000;--card:#1c1c1e;--fg:#f5f5f7;--muted:#98989d;--line:#38383a;--dead:#ff453a}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);
color:var(--fg);margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px}
.card{background:var(--card);border-radius:20px;padding:40px 28px;max-width:420px;width:100%;
text-align:center;box-shadow:0 2px 20px rgba(0,0,0,.08)}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}
.ver{color:var(--muted);font-size:15px;margin:0 0 28px}
a.btn{display:block;background:var(--accent);color:#fff;padding:17px;border-radius:13px;
text-decoration:none;font-size:18px;font-weight:600}
ol{text-align:left;color:var(--muted);font-size:14px;line-height:1.7;margin:28px 0 0;padding-left:20px}
.note{border-top:1px solid var(--line);margin-top:24px;padding-top:16px;color:var(--muted);font-size:12.5px}
.exp{color:var(--muted);font-size:13px;margin-top:18px}
.dead{color:var(--dead);font-weight:600;font-size:19px;margin:6px 0 10px}
.hide{display:none}"""

PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Install {title}</title><style>{css}</style></head><body>
<div class="card" id="card" data-expires="{expires}">
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
    <p class="dead">This link has expired</p>
    <p class="note" style="border:none">The install link is no longer active.
    Contact the sender for a current one.</p>
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
          <key>url</key><string>{cf}/{appid}.ipa</string>
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
            new_pl = MANIFEST.format(cf=CF, appid=appid, bid=BID,
                                     build=a["build"], title=a["title"])
            if not os.path.exists(plist) or open(plist).read() != new_pl:
                open(plist, "w").write(new_pl); changed.append(appid + ".plist")

        rows.append((appid, a, dead))

    idx = ["""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>App Installs</title><style>%s
a.app{display:flex;justify-content:space-between;align-items:center;padding:16px 0;
border-bottom:1px solid var(--line);text-decoration:none;color:var(--fg)}
a.app:last-of-type{border-bottom:none}
.n{font-weight:600;font-size:16px}.v{color:var(--muted);font-size:13px}
.arrow{color:var(--accent);font-size:20px}.x{color:var(--dead);font-size:13px}
.card{text-align:left}</style></head><body>
<div class="card"><h1 style="margin-bottom:18px">App Installs</h1>""" % CSS]
    for appid, a, dead in rows:
        state = '<span class="x">expired</span>' if dead else '<span class="arrow">&rsaquo;</span>'
        idx.append(f'''  <a class="app" href="{appid}.html">
    <span><span class="n">{a["title"]}</span><br><span class="v">{a["short"]} ({a["build"]})</span></span>
    {state}
  </a>''')
    idx.append('''  <p class="note">Open in <strong>Safari</strong> on an iPhone or iPad. After installing,
  trust the developer under Settings &rsaquo; General &rsaquo; VPN &amp; Device Management.</p>
</div></body></html>''')
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
