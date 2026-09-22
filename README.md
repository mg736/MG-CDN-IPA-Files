# MG CDN IPA Files

Static OTA install pages for enterprise-signed iOS builds, with **time-limited links**.
IPAs stay on CloudFront; only the manifest and landing page live here.

## Adding an app

1. Confirm the IPA is at `https://d2wuvg8krwnvon.cloudfront.net/customapps/<appid>.ipa`
2. Add an entry to `apps.json`:

```json
"<appid>": {
  "title": "App Name",
  "short": "4.1",
  "build": "834",
  "expires": "2026-09-30T16:00:00Z"
}
```

3. `python3 build.py` — generates `<appid>.html`, `<appid>.plist`, and `index.html`
4. Commit and push. Pages rebuilds in ~1-2 min.

Read title/version out of an IPA with:
`unzip -p <ipa> 'Payload/*.app/Info.plist' | plutil -p -`

## Expiry

Two layers:

- **In the page** — JavaScript compares `data-expires` against the clock and swaps the
  Install button for an expired notice. Immediate, but cosmetic.
- **In the repo** — `.github/workflows/expire.yml` runs `build.py` hourly. Past its
  `expires` timestamp an app's `.plist` is **deleted**, so a saved `itms-services://`
  URL fails too. This is the real enforcement.

To extend a link, change `expires` in `apps.json` and push; the manifest is regenerated.

## Why this repo exists

`cdncloudfront.com` serves its manifests over TLS 1.2 **without** the Extended Master
Secret extension (RFC 7627). Since iOS 27, Apple blocks those connections for app
installation — silently, with no error on the device.
See https://support.apple.com/en-us/126655

GitHub Pages supports TLS 1.3 + EMS, so manifests served here install correctly on iOS 27.

## Notes

- The `itms-services://` link only works when tapped in **Safari**.
- Enterprise builds require trusting the developer certificate on first launch.
- Every Appy Pie iOS app shares bundle id `com.appypiellc.appypiellc`, so only **one**
  can be installed per device — a second install replaces the first.
- The embedded provisioning profile expires **6 Feb 2027**; after that the IPAs will not
  install regardless of these links. The signing certificate is valid until Feb 2029.
