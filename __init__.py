"""
MattVsJapan Anki Reset Ease script

See: https://www.youtube.com/user/MATTvsJapan

Description:
    Some people (including me) found the updated red-pill ease values weren't
    getting pushed from desktop to AnkiWeb without forcing a one-way sync so
    this version of the script can remove the need to check "Settings >
    Network > On next sync..." every time. Enable this in the config below.

    Alternatively, just use it to sync automatically before and after ease
    reset to save a few clicks or keystrokes per day :)

Usage:
    1. Sync your other devices with AnkiWeb
    2. Run this script from Tools -> Refold Ease...
    3. If the force_after config option is set below, click "Upload to
       AnkiWeb" on Anki's sync dialog (your other devices can download on
       next sync)

Config option combinations (set them below):

1. Normal sync before and after reset
    * Set sync_before_reset and sync_after_reset to True

2. Force sync in one direction after reset
    * Set sync_after_reset and force_after to True
    * Might as well set sync_before_reset to True as well

3. Seen the reset ease dialog enough times?
    Set skip_reset_notification to True

4. Same as the original script (no sync)
    * Set all four options to False
"""

from . import refoldease, gui

refoldease.init()
gui.init()
