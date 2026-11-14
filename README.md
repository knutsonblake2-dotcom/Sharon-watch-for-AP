# Sharon Art Studio Watcher

Emails you about Sharon Art Studio (Golden Gate Park) classes:

- **New classes posted**, such as when the next session's catalog goes up.
- **Open to sign up**, when a class becomes open for registration or a spot
  frees up in a full class.

It reads class data directly from SF Rec & Park's registration system
(ActiveNet, Sharon Art Studio = location 170). It needs no browser and no login.

## When it checks

- **About every 2 hours, 7 AM to 11 PM Pacific.**
- **Saturday registration mornings:** Sharon opens registration on Saturdays
  at 10:00 AM (members first, then the general public a week later). Every
  Saturday the workflow checks every 30 seconds from about 9:40 to 10:30 AM.

The first run saves a baseline. Emails start from the second run on.

## Setup

1. **Add repo secrets.** Go to **Settings → Secrets and variables → Actions**
   and add the same three secrets that fjord-watch uses:
   `SMTP_USER`, `SMTP_PASSWORD` (Gmail app password), `NOTIFY_EMAIL`.
2. **Test email.** Go to **Actions → Check Sharon Art Studio classes → Run
   workflow**, tick "Send a test email", and run it.
3. **Baseline.** Run the workflow once more with nothing ticked.

## Reliable Saturday timing (optional, recommended)

GitHub can start scheduled runs late. Add a cron-job.org job like the one
for fjord-watch: **Saturdays at 9:45 AM Pacific**, POST to
`https://api.github.com/repos/knutsonblake2-dotcom/Sharon-watch-for-AP/actions/workflows/check.yml/dispatches`
with body `{"ref":"main","inputs":{"saturday_poll":"true"}}`, using the same
headers and token as the Fjord job. If the token is limited to specific
repos, add this repo to it.
