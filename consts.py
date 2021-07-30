from typing import NewType

EasePercent = NewType("EasePercent", int)

MIN_EASE = EasePercent(131)
MAX_EASE = EasePercent(1000)
