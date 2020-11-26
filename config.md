## Refold Ease configuration

**Anki needs to be restarted after changing the config.**

* `sync_before_reset` - If you would like to sync your Anki collection with an AnkiWeb account
before changing the Ease factors of your cards.
* `sync_after_reset` - Whether to sync your Anki collection after changing the Ease.
* `force_after` - Force changes in one direction on next sync.
Set to `true` if you notice that the updated ease values aren't
getting pushed from desktop to AnkiWeb.
"Full" sync causes a window to pop up asking whether you would like to "Upload to AnkiWeb"
or "Download from AnkiWeb". Choose **"Upload to AnkiWeb"**.
Your other devices can download on next sync.
* `skip_reset_notification` - Set to `true` if you've seen the reset ease dialog enough times or it bugs you.
