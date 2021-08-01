# -*- coding: utf-8 -*-
#
# RefoldEase add-on for Anki 2.1
# Copyright (C) 2021  Ren Tatsumoto. <tatsu at autistici.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Any modifications to this file must keep this entire header intact.

import math
from typing import List, Tuple, Literal

from anki.cards import Card
from aqt import mw, gui_hooks
from aqt.reviewer import Reviewer
from aqt.utils import showInfo

from .config import config
from .consts import *


######################################################################
# Reset ease & other utils
######################################################################

def whole_collection_id() -> int:
    return -1


def maybe_sync_before():
    # sync before resetting ease, if enabled
    if config.get('sync_before_reset') is True:
        mw.on_sync_button_clicked()


def maybe_sync_after():
    # force a one-way sync if enabled
    if config.get('force_after') is True:
        mw.col.mod_schema(check=False)

    # sync after resetting ease if enabled
    if config.get('sync_after_reset') is True:
        mw.on_sync_button_clicked()


def notify_done(ez_factor_human: int):
    # show a message box
    if not config.get('skip_reset_notification'):
        msg = f"Ease has been reset to {ez_factor_human}%."
        if config.get('sync_after_reset'):
            msg += f"\nCollection will be synchronized{' in one direction' if config.get('force_after') else ''}."
        msg += "\nDon't forget to check your Interval Modifier and Starting Ease."
        showInfo(msg)


def whole_col_selected(dids: List[int]) -> bool:
    return len(dids) == 1 and dids[0] == whole_collection_id()


def reset_ease_db(dids: List[int], ez_factor: int):
    if whole_col_selected(dids):
        mw.col.db.execute("update cards set factor = ?", ez_factor)
    else:
        for did in dids:
            mw.col.db.execute("update cards set factor = ? where did = ?", ez_factor, did)


def reset_ease_col(dids: List[int], ez_factor: int):
    if whole_col_selected(dids):
        card_ids = mw.col.db.list("SELECT id FROM cards WHERE factor != 0")
    else:
        card_ids = []
        for did in dids:
            card_ids.extend(mw.col.db.list("SELECT id FROM cards WHERE factor != 0 AND did = ?", did))

    for card_id in card_ids:
        card = mw.col.get_card(card_id)
        if card.factor != ez_factor:
            card.factor = ez_factor
            card.flush()


def ez_factor_anki(ez_factor_human: int) -> int:
    return int(ez_factor_human * 10)


def ivl_factor_anki(ivl_fct_human: int) -> float:
    return float(ivl_fct_human / 100)


def reset_ease(dids: List[int], ez_factor_human: int = 250):
    if config.get('modify_db_directly') is True:
        reset_ease_db(dids, ez_factor_anki(ez_factor_human))
    else:
        reset_ease_col(dids, ez_factor_anki(ez_factor_human))


def decide_adjust_on_review(ease_tuple: Tuple[bool, Literal[1, 2, 3, 4]], _: Reviewer, card: Card):
    if config.get('adjust_on_review', False) is False:
        # the user disabled the feature
        return ease_tuple

    if card.factor < ez_factor_anki(130):
        # the card is brand new
        return ease_tuple

    if not (card.type == 2 and card.queue == 2):
        # skip cards in learning
        return ease_tuple

    required_factor = ez_factor_anki(nde := config.get('new_default_ease'))

    if required_factor != card.factor:
        card.factor = required_factor
        print(f"RefoldEase: Card #{card.id}'s Ease has been adjusted to {nde}%.")

    return ease_tuple


def adjust_im(new_ease: int, base_im: int = 100) -> int:
    return math.ceil(ANKI_DEFAULT_EASE * base_im / new_ease)


def unique(_list: List[dict], key) -> List[dict]:
    added_ids = set()
    result = []
    for item in _list:
        if not item[key] in added_ids:
            result.append(item)
            added_ids.add(item['id'])
    return result


def update_group_settings(group_conf: dict, ease_human, im_human) -> None:
    # default = `2500`, LowKey target will be `1310`
    group_conf['new']['initialFactor'] = ez_factor_anki(ease_human)

    # default is `1.0`, LowKey target will be `1.92`
    group_conf['rev']['ivlFct'] = ivl_factor_anki(im_human)

    mw.col.decks.set_config_id_for_deck_dict(group_conf, group_conf['id'])
    print(f"Updated Option Group: {group_conf['name']}.")


def maybe_update_groups(dids: List[int], ease_human: int, im_human: int) -> None:
    if not config.get('update_option_groups'):
        return

    if whole_col_selected(dids):
        dconfs = mw.col.decks.all_config()
    else:
        dconfs = [mw.col.decks.config_dict_for_deck_id(did) for did in dids]

    for dconf in unique(dconfs, 'id'):
        update_group_settings(dconf, ease_human, im_human)


def get_decks_info() -> List[Tuple]:
    decks = sorted(mw.col.decks.all_names_and_ids(), key=lambda deck: deck.name)
    result = [(deck.name, deck.id) for deck in decks]
    result.insert(0, ('Whole Collection', whole_collection_id()))
    return result


def run(dids: List[int], factor_human: int, im_human: int) -> None:
    maybe_sync_before()
    reset_ease(dids, factor_human)
    maybe_update_groups(dids, factor_human, im_human)
    notify_done(factor_human)
    maybe_sync_after()


######################################################################
# Entry point
######################################################################

def init():
    gui_hooks.reviewer_will_answer_card.append(decide_adjust_on_review)
