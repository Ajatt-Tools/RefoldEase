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

from typing import List

from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, openLink

from . import refoldease
from .config import config, write_config
from .consts import *


######################################################################
# UI
######################################################################

class DialogUI(QDialog):
    def __init__(self, *args, **kwargs):
        super(DialogUI, self).__init__(parent=mw, *args, **kwargs)
        self.easeSpinBox = QSpinBox()
        self.imSpinBox = QSpinBox()
        self.defaultEaseImSpinBox = QSpinBox()
        self.syncCheckBox = QCheckBox("Sync immediately")
        self.forceSyncCheckBox = QCheckBox("Force sync in one direction")
        self.updateGroupsCheckBox = QCheckBox("Update Options Groups")
        self.deckComboBox = QComboBox()
        self.okButton = QPushButton("Ok")
        self.cancelButton = QPushButton("Cancel")
        self.help_button = QPushButton("Help")
        self.advanced_opts_groupbox = self.create_advanced_options_group()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle('Refold Ease')
        self.setLayout(self.setup_outer_layout())
        self.add_tooltips()

    def setup_outer_layout(self):
        vbox = QVBoxLayout()
        vbox.setSpacing(10)
        vbox.addLayout(self.create_deck_group())
        vbox.addWidget(self.advanced_opts_groupbox)
        vbox.addStretch(1)
        vbox.addLayout(self.create_bottom_group())
        return vbox

    def create_deck_group(self):
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Deck:"))
        hbox.addWidget(self.deckComboBox, 1)
        return hbox

    def create_advanced_options_group(self):
        groupbox = QGroupBox("Advanced Options")
        groupbox.setCheckable(True)

        vbox = QVBoxLayout()
        groupbox.setLayout(vbox)

        vbox.addLayout(self.create_ease_group())
        vbox.addLayout(self.create_check_box_group())

        return groupbox

    def create_ease_group(self):
        grid = QGridLayout()

        grid.addWidget(QLabel("Your IM at Ease=250%:"), 1, 0)
        grid.addWidget(self.defaultEaseImSpinBox, 1, 1)
        grid.addWidget(QLabel("%"), 1, 2)

        grid.addWidget(QLabel("Desired new Ease:"), 2, 0)
        grid.addWidget(self.easeSpinBox, 2, 1)
        grid.addWidget(QLabel("%"), 2, 2)

        grid.addWidget(QLabel("Recommended new IM:"), 3, 0)
        grid.addWidget(self.imSpinBox, 3, 1)
        grid.addWidget(QLabel("%"), 3, 2)

        return grid

    def create_check_box_group(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.syncCheckBox)
        vbox.addWidget(self.forceSyncCheckBox)
        vbox.addWidget(self.updateGroupsCheckBox)

        return vbox

    def create_bottom_group(self):
        hbox = QHBoxLayout()
        hbox.addWidget(self.okButton)
        hbox.addWidget(self.cancelButton)
        hbox.addStretch()
        hbox.addWidget(self.help_button)
        return hbox

    def add_tooltips(self):
        self.defaultEaseImSpinBox.setToolTip(
            "Your Interval Modifier when your Starting Ease was 250%.\n"
            "You can find it by going to `Deck options` -> `Reviews` -> `Interval Modifier`."
        )
        self.easeSpinBox.setToolTip(
            "Your desired new Ease. This value should be set to `131%`\n"
            "if you're following the new `“Low-key” Low-key Anki` setup,\n"
            "or to `250%` if you stick to the old `Low-key` setup.\n\n"
            "Note: Because Anki resets Starting Ease back to 250% on each force sync if it's set to 130%,\n"
            "The lowest possible Ease supported by the add-on is 131%."
        )
        self.imSpinBox.setToolTip(
            "This is your new Interval Modifier after applying this Ease setup."
        )
        self.updateGroupsCheckBox.setToolTip(
            "Update Interval Modifier and Starting Ease in every Options Group\n"
            "or just in the Options Group associated with the deck you've selected."
        )


######################################################################
# The addon's window
######################################################################

def set_enabled_text(button: QPushButton, state: bool, msg: str) -> None:
    button.setEnabled(state)
    button.setText(msg)
    button.repaint()


def dim_ok_button(f: Callable):
    def decorator(self: 'RefoldEaseDialog'):
        set_enabled_text(self.okButton, state=False, msg="Please wait...")
        f(self)
        set_enabled_text(self.okButton, state=True, msg="Ok")

    return decorator


class RefoldEaseDialog(DialogUI):
    def __init__(self):
        super().__init__()
        self.set_minimums()
        self.set_maximums()
        self.set_default_values()
        self.connect_ui_elements()

    def show(self) -> None:
        super(RefoldEaseDialog, self).show()
        self.populate_decks()

    def set_minimums(self) -> None:
        self.defaultEaseImSpinBox.setMinimum(0)
        self.imSpinBox.setMinimum(0)
        self.easeSpinBox.setMinimum(MIN_EASE)

    def set_maximums(self) -> None:
        self.defaultEaseImSpinBox.setMaximum(MAX_EASE)
        self.easeSpinBox.setMaximum(MAX_EASE)
        self.imSpinBox.setMaximum(MAX_EASE)

    def set_default_values(self) -> None:
        self.defaultEaseImSpinBox.setValue(100)
        self.easeSpinBox.setValue(config.get('new_default_ease'))
        self.syncCheckBox.setChecked(config.get('sync_after_reset', False))
        self.forceSyncCheckBox.setChecked(config.get('force_after', False))
        self.updateGroupsCheckBox.setChecked(config.get('update_option_groups', False))
        self.advanced_opts_groupbox.setChecked(config.get('advanced_options', False))
        self.update_im_spin_box()

    def connect_ui_elements(self) -> None:
        qconnect(self.defaultEaseImSpinBox.editingFinished, self.update_im_spin_box)
        qconnect(self.easeSpinBox.editingFinished, self.update_im_spin_box)

        qconnect(self.defaultEaseImSpinBox.valueChanged, self.update_im_spin_box)
        qconnect(self.easeSpinBox.valueChanged, self.update_im_spin_box)

        qconnect(self.okButton.clicked, self.on_confirm)
        qconnect(self.cancelButton.clicked, self.reject)
        qconnect(self.help_button.clicked, lambda: openLink(ANKI_SETUP_GUIDE))

    def populate_decks(self) -> None:
        self.deckComboBox.clear()
        for deck in refoldease.get_decks_info():
            self.deckComboBox.addItem(*deck)

    def update_im_spin_box(self) -> None:
        self.imSpinBox.setValue(refoldease.adjust_im(self.easeSpinBox.value(), self.defaultEaseImSpinBox.value()))

    def get_selected_dids(self) -> List[int]:
        selected_deck_name = self.deckComboBox.currentText()
        selected_dids = [self.deckComboBox.currentData()]

        for deck in mw.col.decks.all_names_and_ids():
            if deck.name.startswith(selected_deck_name + "::"):
                selected_dids.append(deck.id)

        return selected_dids

    def update_global_config(self) -> None:
        config['sync_after_reset'] = self.syncCheckBox.isChecked()
        config['force_after'] = self.forceSyncCheckBox.isChecked()
        config['update_option_groups'] = self.updateGroupsCheckBox.isChecked()
        config['advanced_options'] = self.advanced_opts_groupbox.isChecked()
        config['new_default_ease'] = self.easeSpinBox.value()

        write_config()

    @dim_ok_button
    def on_confirm(self) -> None:
        self.update_global_config()
        try:
            refoldease.run(
                dids=self.get_selected_dids(),
                factor_human=self.easeSpinBox.value(),
                im_human=self.imSpinBox.value(),
            )
        except Exception as ex:
            traceback.print_exc()
            showInfo(
                f"Sorry! Couldn't <b>refold</b> ease.<br>{str(ex)}.<br>"
                "Please <a href=\"https://github.com/Ajatt-Tools/RefoldEase\">fill an issue</a> on Github."
            )
        self.accept()


######################################################################
# Entry point
######################################################################

def menu_label():
    """Format menu label based on configuration."""

    label = "Refold Ease"

    if config.get('sync_before_reset') is True:
        label += " + Sync Before"
    if config.get('sync_after_reset') is True:
        label += f" + {'Force ' if config.get('force_after') else ''}Sync After"

    return label


dialog = RefoldEaseDialog()


def init():
    # create a new menu item
    action = QAction(menu_label(), mw)
    # set it to call testFunction when it's clicked
    qconnect(action.triggered, dialog.show)
    # and add it to the tools menu
    mw.form.menuTools.addAction(action)
    # adjust ease factor before review, if enabled
