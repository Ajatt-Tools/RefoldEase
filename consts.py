from typing import NewType

EasePercent = NewType("EasePercent", int)

RUN_BUTTON_TEXT = "Run"
MIN_EASE = EasePercent(131)
MAX_EASE = EasePercent(1000)
ANKI_DEFAULT_EASE = EasePercent(250)
ANKI_SETUP_GUIDE = 'https://tatsumoto.neocities.org/blog/setting-up-anki.html'
