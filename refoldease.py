# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import math
from typing import Callable, Iterable

from anki.cards import Card
from anki.decks import DeckConfigDict
from aqt import mw
from aqt.qt import QObject, pyqtSignal, qconnect
from aqt.utils import showInfo

from .config import config
from .consts import *


######################################################################
# Reset ease & other utils
######################################################################


def maybe_sync_before():
    # sync before resetting ease, if enabled
    if config['sync_before_reset'] is True:
        mw.on_sync_button_clicked()


def maybe_sync_after():
    # force a one-way sync if enabled
    if config['force_sync_in_one_direction'] is True:
        mw.col.mod_schema(check=False)

    # sync after resetting ease if enabled
    if config['sync_after_reset'] is True:
        mw.on_sync_button_clicked()


def form_msg() -> str:
    msg: list[str] = ["Ease has been reset to {}%."]

    if config.get('sync_after_reset'):
        msg.append("\nCollection will be synchronized")
        if config['force_sync_in_one_direction']:
            msg.append("in one direction.")
        else:
            msg.append(".")

    msg.append("\nDon't forget to check your Interval Modifier and Starting Ease.")

    return ''.join(msg)


def maybe_notify_done(ez_factor_human: int):
    if config['show_reset_notification']:
        showInfo(form_msg().format(ez_factor_human))


def whole_col_selected(decks: list[DeckNameId]) -> bool:
    return len(decks) == 1 and decks[0] is WHOLE_COLLECTION


def reset_ease_db(decks: list[DeckNameId], factor_anki: int):
    if whole_col_selected(decks):
        mw.col.db.execute("update cards set factor = ?", factor_anki)
    else:
        for deck in decks:
            mw.col.db.execute("update cards set factor = ? where did = ?", factor_anki, deck.id)


def get_cards_by_dids(decks: list[DeckNameId]) -> Iterable[Card]:
    if whole_col_selected(decks):
        card_ids = mw.col.db.list("SELECT id FROM cards WHERE factor != 0")
    else:
        card_ids = set()
        for deck in decks:
            card_ids.update(mw.col.db.list("SELECT id FROM cards WHERE factor != 0 AND did = ?", deck.id))

    return (mw.col.get_card(card_id) for card_id in card_ids)


def reset_ease_col(decks: list[DeckNameId], factor_anki: int):
    to_update: list[Card] = []
    for card in get_cards_by_dids(decks):
        if card.factor != factor_anki:
            card.factor = factor_anki
            to_update.append(card)
    return mw.col.update_cards(to_update)


def reset_ease(decks: list[DeckNameId], factor_human: int) -> None:
    if config['modify_db_directly'] is True:
        reset_ease_db(decks, ez_factor_anki(factor_human))
    else:
        reset_ease_col(decks, ez_factor_anki(factor_human))


def ez_factor_anki(ez_factor_human: int) -> int:
    return int(ez_factor_human * 10)


def ivl_factor_anki(ivl_fct_human: int) -> float:
    return float(ivl_fct_human / 100)


def adjust_im(new_ease: int, base_im: int = 100) -> int:
    return math.ceil(ANKI_DEFAULT_EASE * base_im / new_ease)


def update_group_settings(group_conf: DeckConfigDict, ease_human: int, im_human: int) -> None:
    # default = `2500`, LowKey target will be `1310`
    group_conf['new']['initialFactor'] = ez_factor_anki(ease_human)

    # default is `1.0`, LowKey target will be `1.92`
    group_conf['rev']['ivlFct'] = ivl_factor_anki(im_human)

    mw.col.decks.set_config_id_for_deck_dict(group_conf, group_conf['id'])
    print(f"Updated Option Group: {group_conf['name']}.")


def unique_options_groups(deck_confs: list[DeckConfigDict]) -> Iterable[DeckConfigDict]:
    return {group['id']: group for group in deck_confs}.values()


def maybe_update_groups(decks: list[DeckNameId], ease_human: int, im_human: int) -> None:
    if not config['update_options_groups']:
        return

    if whole_col_selected(decks):
        dconfs = mw.col.decks.all_config()
    else:
        dconfs = [mw.col.decks.config_dict_for_deck_id(deck.id) for deck in decks]

    for dconf in unique_options_groups(dconfs):
        update_group_settings(dconf, ease_human, im_human)


def get_decks_info() -> list[DeckNameId]:
    return [
        WHOLE_COLLECTION,
        *sorted(mw.col.decks.all_names_and_ids(), key=lambda deck: deck.name),
    ]


def emit_running(func: Callable[["RefoldEase"], None]):
    def wrapper(self: "RefoldEase"):
        self.running.emit(True)  # type: ignore
        func(self)
        self.running.emit(False)  # type: ignore

    return wrapper


class RefoldEase(QObject):
    running = pyqtSignal(bool)

    def __init__(self, decks: list[DeckNameId], factor_human: int, im_human: int):
        super().__init__()
        self._decks = decks
        self._factor_human = factor_human
        self._im_human = im_human
        qconnect(self.running, self.on_running)
        maybe_sync_before()

    @emit_running
    def run(self) -> None:
        reset_ease(self._decks, self._factor_human)
        maybe_update_groups(self._decks, self._factor_human, self._im_human)

    def on_running(self, running: bool) -> None:
        if not running:
            self.finalize()

    def finalize(self) -> None:
        maybe_notify_done(self._factor_human)
        maybe_sync_after()
