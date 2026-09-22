# MG CDN IPA Files

Static install pages for enterprise-signed iOS builds. The IPAs stay on CloudFront;
only the manifest and landing page live here.

## Why this exists

`cdncloudfront.com` serves its manifests over TLS 1.2 **without** the Extended Master
Secret extension (RFC 7627). Since iOS 27, Apple blocks those connections outright for
app installation — silently, with no error shown on the device.
See https://support.apple.com/en-us/126655

GitHub Pages supports TLS 1.3 + EMS, so manifests served here install correctly on iOS 27.

## Adding an app

Drop two files in the repo root, named after the app id:

- `<appid>.plist`  — manifest, with `url` pointing at the CloudFront IPA
- `<appid>.html`   — install page, linking to `<appid>.plist` over **https**

Then add a row to `index.html`. No build step.

## Notes

- Manifests must be reachable over HTTPS on a host that passes Apple's TLS rules.
- The `itms-services://` link only works when tapped in Safari.
- Enterprise builds still require trusting the developer certificate on first launch.
