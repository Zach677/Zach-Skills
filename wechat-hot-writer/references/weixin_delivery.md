# Weixin Delivery Flow

## Default path

V1 assumes:

- personal or unverified account
- human final review is mandatory
- no forced final publish click

So the practical goal is:

1. prepare article assets
2. verify the browser bridge
3. get the editor session ready
4. stop at draft/review-ready state

## Baoyu path

If `baoyu-post-to-wechat` is installed and healthy, treat it as the preferred article-entry backend.

Why:

- it already knows the WeChat article editor
- it can convert markdown to WeChat-friendly HTML with image placeholders
- it can paste HTML, replace placeholders with real images, and save to draft

Important distinction:

- `browser` path: saves into the public account editor draft flow
- `api` path: calls `draft/add` and creates a draft by API
- neither path means “immediately send to subscribers”

Method selection:

- if `WECHAT_APP_ID` and `WECHAT_APP_SECRET` are configured, prefer `api`
- otherwise use `browser`

For the API route:

- validate credentials by fetching an access token first
- use `wechat-api.ts`
- understand that success here means “draft created”, not “article sent to subscribers”

For the browser route:

- use `wechat-article.ts`
- save to draft in the editor UI

## opencli guardrails

For this skill, browser work must stay on `opencli`.

Discovery order:

1. `opencli list -f yaml`
2. `opencli weixin --help`
3. `opencli doctor`
4. `opencli explore https://mp.weixin.qq.com --goal "understand draft editor flow for article creation"`

If the site still has no usable adapter and the user is already logged in:

1. `opencli record https://mp.weixin.qq.com --site weixin-mp-draft --out out/opencli-record`
2. `opencli generate https://mp.weixin.qq.com --site weixin-mp-draft --goal "open new article draft and populate title digest body"`

Use recording or generation only after the session is known-good. Do not fake it.

## Delivery checklist

- Chrome is running
- OpenCLI Browser Bridge is connected
- `mp.weixin.qq.com` is already logged in
- the package has 3 titles, summary, body HTML, keywords, sources
- body images are staged as local files for upload
- cover image is either local or intentionally left for manual upload

## Optional Baoyu interop

If local `baoyu-post-to-wechat` is installed and healthy:

- run its `check-permissions.ts` as an extra preflight
- include a ready-to-run browser draft command in the manifest
- still keep the opencli flow documented as the neutral baseline

Reason:

- `opencli` stays the default browser automation layer in this environment
- `baoyu-post-to-wechat` is useful as a specialized fallback for actual editor input and image placeholder replacement

## Dry-run output

`deliver-weixin --dry-run` should produce:

- `delivery-manifest.json`
- staged local body images
- `body.weixin.html`
- an `opencli_steps` array with the exact preflight commands and manual gate

Dry-run is successful even if it does not click publish. The required stop point is “ready for an operator to review and continue”.
