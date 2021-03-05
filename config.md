## Refold Ease configuration

**Anki needs to be restarted after changing the config.**

* `new_default_ease` - Your desired new Ease. This value should be set to `131`
if you're following the new `“Low-key” Low-key Anki` setup,
or to `250` if you stick to the old `Low-key` setup.
Learn more about Low Key Anki [here](https://refold.la/roadmap/stage-1/a/anki-setup/).
* `sync_before_reset` - If you would like to sync your Anki collection with an AnkiWeb account
before changing the Ease factors of your cards.
* `sync_after_reset` - Sync your Anki collection after changing the Ease.
* `force_after` - Force changes in one direction on next sync.
Set to `true` if you notice that the updated ease values aren't
getting pushed from desktop to AnkiWeb.
"Full" sync causes a window to pop up asking whether you would like to "Upload to AnkiWeb"
or "Download from AnkiWeb". Choose **"Upload to AnkiWeb"**.
Your other devices can download on next sync.
* `skip_reset_notification` - Set to `true` if you've seen the reset ease dialog enough times or it bugs you.
* `update_option_groups` - Whether to go through each `Options Group`
and update its `Starting Ease` and `Interval Modifier` after the Ease reset.
* `modify_db_directly` - Change ease factors of cards directly through `mw.col.db.execute`.
This method may be faster but it always requires a full sync afterwards
because Anki won't know that card properties have been changed.
* `adjust_on_review` - Just before you answer each card,
the add-on checks its Ease factor and sets it back to `new_default_ease` if needed.
