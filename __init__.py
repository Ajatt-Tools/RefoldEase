from typing import List, Tuple

from anki import hooks
from anki.cards import Card
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

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

######################################################################
# Configuration
######################################################################

config: dict = mw.addonManager.getConfig(__name__)

new_default_ease: int = config.get('new_default_ease', 131)
sync_before_reset: bool = config.get('sync_before_reset', False)
sync_after_reset: bool = config.get('sync_after_reset', False)
force_after: bool = config.get('force_after', False)
skip_reset_notification: bool = config.get('skip_reset_notification', False)
update_option_groups: bool = config.get('update_option_groups', True)
modify_db_directly: bool = config.get('modify_db_directly', False)


######################################################################
# Reset ease & other utils
######################################################################

def wholeCollectionID() -> int:
    return -1


def syncBefore():
    # sync before resetting ease, if enabled
    if sync_before_reset:
        mw.onSync()


def syncAfter():
    # force a one-way sync if enabled
    if force_after:
        mw.col.scm += 1
        mw.col.setMod()

    # sync after resetting ease if enabled
    if sync_after_reset:
        mw.onSync()


def notifyDone(ez_factor_human: int):
    # show a message box
    if not skip_reset_notification:
        msg = f"Ease has been reset to {ez_factor_human}%."
        if sync_after_reset:
            msg += f"\nCollection will be synchronized{' in one direction' if force_after else ''}."
        msg += "\nDon't forget to check your Interval Modifier and Starting Ease."
        showInfo(msg)


def whole_col_selected(dids: List[int]) -> bool:
    return len(dids) == 1 and dids[0] == wholeCollectionID()


def resetEaseDb(dids: List[int], ez_factor: int):
    if whole_col_selected(dids):
        mw.col.db.execute("update cards set factor = ?", ez_factor)
    else:
        for did in dids:
            mw.col.db.execute("update cards set factor = ? where did = ?", ez_factor, did)


def resetEaseCol(dids: List[int], ez_factor: int):
    card_ids = []
    if whole_col_selected(dids):
        card_ids.extend(mw.col.db.list("SELECT id FROM cards WHERE factor != 0"))
    else:
        for did in dids:
            card_ids.extend(mw.col.db.list("SELECT id FROM cards WHERE factor != 0 AND did = ?", did))

    for card_id in card_ids:
        card = mw.col.getCard(card_id)
        if card.factor != ez_factor:
            card.factor = ez_factor
            card.flush()


def ezFactorAnki(ez_factor_human: int) -> int:
    return int(ez_factor_human * 10)


def ivlFactorAnki(ivl_fct_human: int) -> float:
    return float(ivl_fct_human / 100)


def resetEase(dids: List[int], ez_factor_human: int = 250):
    ez_factor_anki = ezFactorAnki(ez_factor_human)
    if modify_db_directly is True:
        resetEaseDb(dids, ez_factor_anki)
    else:
        resetEaseCol(dids, ez_factor_anki)


def decideAdjustOnReview(card: Card):
    if config.get('adjust_on_review', False) is False:
        # the user disabled the feature
        return

    if card.factor < ezFactorAnki(130):
        # the card is brand new
        return

    if not (card.type == 2 and card.queue == 2):
        # skip cards in learning
        return

    required_factor = ezFactorAnki(new_default_ease)
    if card.factor != required_factor:
        card.factor = required_factor
        print(f"RefoldEase: Card #{card.id}'s Ease has been adjusted to {new_default_ease}%.")


def adjustIM(new_ease: int, base_im: int = 100) -> int:
    default_ease = 250
    return int(default_ease * base_im / new_ease)


def updateGroups(dids: List[int], new_starting_ease: int, new_interval_modifier: int) -> None:
    if not update_option_groups:
        return

    if whole_col_selected(dids):
        dconfs = mw.col.decks.allConf()
    else:
        dconfs = [mw.col.decks.confForDid(did) for did in dids]

    def updateGroupSettings(group_conf: dict) -> None:
        # default = `2500`, LowKey target will be `1310`
        group_conf['new']['initialFactor'] = ezFactorAnki(new_starting_ease)

        # default is `1.0`, LowKey target will be `1.92`
        group_conf['rev']['ivlFct'] = ivlFactorAnki(new_interval_modifier)

        mw.col.decks.setConf(group_conf, group_conf['id'])
        print(f"Updated Option Group: {group_conf['name']}.")

    for dconf in dconfs:
        updateGroupSettings(dconf)


def getDecksInfo() -> List[Tuple]:
    decks = sorted(mw.col.decks.all_names_and_ids(), key=lambda deck: deck["name"])
    result = [(deck["name"], deck["id"]) for deck in decks]
    result.insert(0, ('Whole Collection', wholeCollectionID()))
    return result


def setEnabledText(button: QPushButton, state: bool, msg: str) -> None:
    button.setEnabled(state)
    button.setText(msg)
    button.repaint()


# format menu item based on configuration
menu_label = "Refold Ease"
if sync_before_reset:
    menu_label += " + Sync Before"
if sync_after_reset:
    menu_label += f" + {'Force ' if force_after else ''}Sync After"


######################################################################
# UI
######################################################################

class DialogUI(QDialog):
    def __init__(self):
        QDialog.__init__(self, parent=mw)
        self.easeSpinBox = QSpinBox()
        self.imSpinBox = QSpinBox()
        self.defaultEaseImSpinBox = QSpinBox()
        self.syncCheckBox = QCheckBox("Sync immediately")
        self.forceSyncCheckBox = QCheckBox("Force sync in one direction")
        self.updateGroupsCheckBox = QCheckBox("Update Options Groups")
        self.deckComboBox = QComboBox()
        self.okButton = QPushButton("Ok")
        self.cancelButton = QPushButton("Cancel")
        self._setupUI()

    def _setupUI(self):
        self.setWindowTitle('Refold Ease')
        self.setLayout(self.setupOuterLayout())
        self.addToolTips()

    def setupOuterLayout(self):
        vbox = QVBoxLayout()
        vbox.setSpacing(10)
        vbox.addLayout(self.createDeckGroup())
        vbox.addWidget(self.createAdvancedOptionsGroup())
        vbox.addStretch(1)
        vbox.addWidget(self.createLearnMoreLink())
        vbox.addLayout(self.createBottomGroup())
        return vbox

    def createDeckGroup(self):
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Deck:"))
        hbox.addWidget(self.deckComboBox, 1)
        return hbox

    def createAdvancedOptionsGroup(self):
        groupbox = QGroupBox("Advanced Options")
        groupbox.setCheckable(True)
        groupbox.setChecked(False)

        vbox = QVBoxLayout()
        groupbox.setLayout(vbox)

        vbox.addLayout(self.createEaseGroup())
        vbox.addLayout(self.createCheckBoxGroup())

        return groupbox

    def createEaseGroup(self):
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

    def createCheckBoxGroup(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.syncCheckBox)
        vbox.addWidget(self.forceSyncCheckBox)
        vbox.addWidget(self.updateGroupsCheckBox)

        return vbox

    @staticmethod
    def createLearnMoreLink():
        label = QLabel('<a href="https://refold.la/roadmap/stage-1/a/anki-setup">Learn more</a>')
        label.setOpenExternalLinks(True)
        return label

    def createBottomGroup(self):
        hbox = QHBoxLayout()
        hbox.addWidget(self.okButton)
        hbox.addWidget(self.cancelButton)
        hbox.addStretch()
        return hbox

    def addToolTips(self):
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

class RefoldEaseDialog(DialogUI):
    def __init__(self):
        super().__init__()
        self.setMinimums()
        self.setMaximums()
        self.setDefaultValues()
        self.connectUIElements()
        QPushButton.setEnabledText = setEnabledText

    def setMinimums(self):
        self.defaultEaseImSpinBox.setMinimum(0)
        self.easeSpinBox.setMinimum(131)
        self.imSpinBox.setMinimum(0)

    def setMaximums(self):
        self.defaultEaseImSpinBox.setMaximum(10000)
        self.easeSpinBox.setMaximum(10000)
        self.imSpinBox.setMaximum(10000)

    def setDefaultValues(self):
        self.defaultEaseImSpinBox.setValue(100)
        self.easeSpinBox.setValue(new_default_ease)
        self.updateImSpinBox()
        self.syncCheckBox.setChecked(sync_after_reset)
        self.forceSyncCheckBox.setChecked(force_after)
        self.updateGroupsCheckBox.setChecked(update_option_groups)

    def connectUIElements(self):
        self.defaultEaseImSpinBox.editingFinished.connect(self.updateImSpinBox)
        self.easeSpinBox.editingFinished.connect(self.updateImSpinBox)

        self.defaultEaseImSpinBox.valueChanged.connect(self.updateImSpinBox)
        self.easeSpinBox.valueChanged.connect(self.updateImSpinBox)

        self.okButton.clicked.connect(self.onConfirm)
        self.cancelButton.clicked.connect(self.hide)

    def populateDecks(self):
        self.deckComboBox.clear()
        for deck in getDecksInfo():
            self.deckComboBox.addItem(*deck)

    def show(self):
        super().show()
        self.populateDecks()

    def updateImSpinBox(self):
        self.imSpinBox.setValue(adjustIM(self.easeSpinBox.value(), self.defaultEaseImSpinBox.value()))

    def get_selected_dids(self) -> List[int]:
        selected_deck_name = self.deckComboBox.currentText()
        deck_names_and_ids = mw.col.decks.all_names_and_ids()
        selected_dids = [self.deckComboBox.currentData()]

        for deck in deck_names_and_ids:
            if deck['name'].startswith(selected_deck_name + "::"):
                selected_dids.append(deck['id'])

        return selected_dids

    def onConfirm(self):
        global sync_after_reset, force_after, update_option_groups
        sync_after_reset = self.syncCheckBox.isChecked()
        force_after = self.forceSyncCheckBox.isChecked()
        update_option_groups = self.updateGroupsCheckBox.isChecked()

        self.okButton.setEnabledText(False, "Please wait...")
        try:
            syncBefore()
            resetEase(self.get_selected_dids(), self.easeSpinBox.value())
            updateGroups(self.get_selected_dids(), self.easeSpinBox.value(), self.imSpinBox.value())
            notifyDone(self.easeSpinBox.value())
            syncAfter()
        except Exception as ex:
            showInfo(
                f"Sorry! Couldn't <b>refold</b> ease.<br>{ex}.<br>"
                "Please <a href=\"https://github.com/Ajatt-Tools/RefoldEase\">fill an issue</a> on Github."
            )
        self.okButton.setEnabledText(True, "Ok")
        self.hide()


######################################################################
# Entry point
######################################################################

# init dialog
dialog = RefoldEaseDialog()
# create a new menu item
action = QAction(menu_label, mw)
# set it to call testFunction when it's clicked
action.triggered.connect(dialog.show)
# and add it to the tools menu
mw.form.menuTools.addAction(action)
# subscribe to the flush event
hooks.card_will_flush.append(decideAdjustOnReview)
