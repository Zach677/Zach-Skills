# WeChat API Publish

Publishing means creating a WeChat draft through `draft/add`; it does not send
the article to subscribers.

## Credential Resolution

The script checks:

- environment variables: `WECHAT_APP_ID`, `WECHAT_APP_SECRET`
- `./.baoyu-skills/.env`
- `~/.baoyu-skills/.env`

Do not store credentials in this skill.

## API Steps

1. Fetch access token from `/cgi-bin/token`.
2. Upload the cover through `/cgi-bin/material/add_material?type=image`.
3. Render Markdown to HTML if needed.
4. Upload local inline images through `/cgi-bin/media/uploadimg`.
5. Create draft through `/cgi-bin/draft/add`.

Payload includes `need_open_comment` and `only_fans_can_comment`.

## Failure Policy

If token fetch, image upload, or draft creation fails because of network,
credentials, IP whitelist, permission, captcha, QR scan, or manual confirmation,
write a blocker log and stop. Do not use browser fallback.
