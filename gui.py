# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from gettext import gettext as _
from typing import Optional

from aqt import mw
from aqt.qt import *
from aqt.utils import openLink, restoreGeom, saveGeom

from .ajt_common.addon_config import AddonConfigManager
from .config import config
from .consts import *
from .refoldease import RefoldEase, get_decks_info, adjust_im


######################################################################
# UI
######################################################################

def expanding_combobox(min_width=200) -> QComboBox:
    box = QComboBox()
    box.setMinimumWidth(min_width)
    box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return box


class DialogUI(QDialog):
    _booleans = (
        "update_options_groups",
        "sync_after_reset",
        "force_sync_in_one_direction",
        "adjust_ease_when_reviewing",
    )

    @classmethod
    def make_checkboxes(cls):
        return {key: QCheckBox(key.replace('_', ' ').capitalize()) for key in cls._booleans}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._desired_new_ease_spinbox = QSpinBox()
        self._recommended_new_im_spinbox = QSpinBox()
        self._im_at_250_ease_spinbox = QSpinBox()
        self._checkboxes = self.make_checkboxes()
        self._deck_combobox = expanding_combobox()
        self._run_button = QPushButton(RUN_BUTTON_TEXT)
        self._advanced_opts_groupbox = self.create_advanced_options_group()
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Help
        )
        self._restore_settings_button = self._button_box.addButton(
            _("Restore &Defaults"), QDialogButtonBox.ButtonRole.ResetRole
        )
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(ADDON_NAME)
        self.setLayout(self.setup_outer_layout())
        self.add_tooltips()

    def setup_outer_layout(self):
        vbox = QVBoxLayout()
        vbox.setSpacing(10)
        vbox.addLayout(self.create_deck_selection_group())
        vbox.addWidget(self._advanced_opts_groupbox)
        vbox.addStretch(1)
        vbox.addWidget(self._button_box)
        return vbox

    def create_deck_selection_group(self):
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Deck"))
        hbox.addWidget(self._deck_combobox, stretch=1)
        hbox.addWidget(self._run_button)
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
        spinboxes = {
            "IM multiplier": self._im_at_250_ease_spinbox,
            "Desired new Ease": self._desired_new_ease_spinbox,
            "Recommended new IM": self._recommended_new_im_spinbox,
        }
        for y_idx, label in enumerate(spinboxes):
            for h_idx, widget in enumerate((QLabel(label), spinboxes[label], QLabel("%"))):
                grid.addWidget(widget, y_idx, h_idx)

        return grid

    def create_check_box_group(self):
        vbox = QVBoxLayout()
        for widget in self._checkboxes.values():
            vbox.addWidget(widget)
        return vbox

    def add_tooltips(self):
        self._im_at_250_ease_spinbox.setToolTip(
            "Your Interval Modifier when your Starting Ease was 250%.\n"
            "You can find it by going to \"Deck options\" > \"Reviews\" > \"Interval Modifier\"."
        )
        self._desired_new_ease_spinbox.setToolTip(
            "Your desired new Ease. The recommended value is 131%.\n"
            "Note: Because Anki resets Starting Ease back to 250% on each force sync if it's set to 130%,\n"
            "The lowest possible Ease supported by the add-on is 131%."
        )
        self._recommended_new_im_spinbox.setToolTip(
            "This is your new Interval Modifier after applying this Ease setup.\n\n"
            "The value updates automatically. Change IM multiplier to control it."
        )
        self._checkboxes['update_options_groups'].setToolTip(
            "Update Interval Modifier and Starting Ease in every Options Group\n"
            "or just in the Options Group associated with the deck you've selected."
        )
        self._checkboxes['sync_after_reset'].setToolTip(
            "Sync collection when the task is done."
        )
        self._checkboxes['force_sync_in_one_direction'].setToolTip(
            "Mark the collection as needing force sync."
        )
        self._checkboxes['adjust_ease_when_reviewing'].setToolTip(
            "When you review a card, its Ease is going to be adjusted back\n"
            "to the value you set here, if needed."
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setToolTip(
            "Save settings and close the dialog."
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Cancel).setToolTip(
            "Discard settings and close the dialog."
        )
        self._button_box.button(QDialogButtonBox.StandardButton.Help).setToolTip(
            "Open the Anki guide."
        )


######################################################################
# The addon's window
######################################################################


class RefoldEaseDialog(DialogUI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_minimums()
        self.set_maximums()
        self.set_default_values(config)
        self.connect_ui_elements()
        self.thread: Optional[QThread] = None
        self.worker: Optional[RefoldEase] = None

    def show(self) -> None:
        super().show()
        self.populate_decks()
        restoreGeom(self, ADDON_NAME)

    def set_minimums(self) -> None:
        self._im_at_250_ease_spinbox.setMinimum(0)
        self._recommended_new_im_spinbox.setMinimum(0)
        self._desired_new_ease_spinbox.setMinimum(MIN_EASE)

    def set_maximums(self) -> None:
        self._im_at_250_ease_spinbox.setMaximum(MAX_EASE)
        self._desired_new_ease_spinbox.setMaximum(MAX_EASE)
        self._recommended_new_im_spinbox.setMaximum(MAX_EASE)

    def set_default_values(self, c: AddonConfigManager) -> None:
        widget: QCheckBox

        for conf_key, widget in self._checkboxes.items():
            widget.setChecked(c.get(conf_key, False))

        self._im_at_250_ease_spinbox.setValue(c['im_multiplier'])
        self._advanced_opts_groupbox.setChecked(c['advanced_options'])
        self._desired_new_ease_spinbox.setValue(c['new_starting_ease_percent'])
        self.update_im_spin_box()

    def connect_ui_elements(self) -> None:
        qconnect(self._im_at_250_ease_spinbox.editingFinished, self.update_im_spin_box)
        qconnect(self._desired_new_ease_spinbox.editingFinished, self.update_im_spin_box)

        qconnect(self._im_at_250_ease_spinbox.valueChanged, self.update_im_spin_box)
        qconnect(self._desired_new_ease_spinbox.valueChanged, self.update_im_spin_box)

        qconnect(self._run_button.clicked, self.on_run)

        qconnect(self._button_box.accepted, self.accept)
        qconnect(self._button_box.rejected, self.reject)
        qconnect(self._button_box.helpRequested, lambda: openLink(ANKI_SETUP_GUIDE))
        qconnect(
            self._restore_settings_button.clicked,
            lambda: self.set_default_values(AddonConfigManager(default=True))
        )

    def populate_decks(self) -> None:
        self._deck_combobox.clear()
        for deck in get_decks_info():
            self._deck_combobox.addItem(*deck)

    def update_im_spin_box(self) -> None:
        self._recommended_new_im_spinbox.setValue(
            adjust_im(
                new_ease=self._desired_new_ease_spinbox.value(),
                base_im=self._im_at_250_ease_spinbox.value()
            )
        )

    def get_selected_dids(self) -> list[int]:
        selected_deck_name = self._deck_combobox.currentText()
        selected_dids = [self._deck_combobox.currentData()]

        for deck in mw.col.decks.all_names_and_ids():
            if deck.name.startswith(selected_deck_name + "::"):
                selected_dids.append(deck.id)

        return selected_dids

    def update_global_config(self) -> None:
        for conf_key, widget in self._checkboxes.items():
            config[conf_key] = widget.isChecked()

        config['im_multiplier'] = self._im_at_250_ease_spinbox.value()
        config['new_starting_ease_percent'] = self._desired_new_ease_spinbox.value()
        config['advanced_options'] = self._advanced_opts_groupbox.isChecked()

        config.write_config()

    def done(self, *args, **kwargs) -> None:
        saveGeom(self, ADDON_NAME)
        return super().done(*args, **kwargs)

    def accept(self):
        self.update_global_config()
        return super().accept()

    def reject(self):
        # If the user tweaked config parameters, set them to the previous values.
        self.set_default_values(config)
        return super().reject()

    def on_run(self) -> None:
        if self._run_button.isEnabled():
            self.update_global_config()
            self.thread = QThread()
            self.worker = RefoldEase(
                dids=self.get_selected_dids(),
                factor_human=self._desired_new_ease_spinbox.value(),
                im_human=self._recommended_new_im_spinbox.value(),
            )
            self.worker.moveToThread(self.thread)
            self.worker.running.connect(lambda running: self._run_button.setEnabled(not running))
            self.worker.running.connect(lambda running: self.thread.quit() if not running else None)
            self.thread.started.connect(self.worker.run)  # type:ignore
            self.thread.start()


######################################################################
# Entry point
######################################################################


def init():
    mw.ajt__refold_ease_dialog = dialog = RefoldEaseDialog(parent=mw)

    from .ajt_common.about_menu import menu_root_entry

    root_menu = menu_root_entry()

    # create a new menu item
    action = QAction(ADDON_NAME, root_menu)
    # set it to call testFunction when it's clicked
    qconnect(action.triggered, dialog.show)
    # and add it to the tools menu
    root_menu.addAction(action)
