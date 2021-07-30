from typing import NewType

EasePercent = NewType("EasePercent", int)

MIN_EASE = EasePercent(131)
MAX_EASE = EasePercent(1000)
ANKI_DEFAULT_EASE = EasePercent(250)
