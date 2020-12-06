# import the main window object (mw) from aqt
from aqt import mw
# import the "show info" tool from utils.py
from aqt.utils import showInfo
# import all of the Qt GUI library
from aqt.qt import *

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

config = mw.addonManager.getConfig(__name__)

new_default_ease: int = config['new_default_ease'] if 'new_default_ease' in config else 131
sync_before_reset: bool = config['sync_before_reset'] if 'sync_before_reset' in config else False
sync_after_reset: bool = config['sync_after_reset'] if 'sync_after_reset' in config else False
force_after: bool = config['force_after'] if 'force_after' in config else False
skip_reset_notification: bool = config['skip_reset_notification'] if 'skip_reset_notification' in config else False
update_option_groups: bool = config['update_option_groups'] if 'update_option_groups' in config else True
modify_db_directly: bool = config['modify_db_directly'] if 'modify_db_directly' in config else False


######################################################################
# Reset ease & other utils
######################################################################

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


def notify(ez_factor_human: int):
    # show a message box
    if not skip_reset_notification:
        msg = f"Ease has been reset to {ez_factor_human}%."
        if sync_after_reset:
            msg += f"\nCollection will be synchronized{' in one direction' if force_after else ''}."
        msg += "\nDon't forget to check your Interval Modifier and Starting Ease."
        showInfo(msg)


def resetEaseDb(ez_factor: int):
    mw.col.db.execute("update cards set factor = ?", ez_factor)


def resetEaseCol(ez_factor: int):
    card_ids = mw.col.db.list("SELECT id FROM cards WHERE factor != 0")
    for card_id in card_ids:
        card = mw.col.getCard(card_id)
        if card.factor != ez_factor:
            card.factor = ez_factor
            card.flush()


def resetEase(ez_factor_human: int = 250):
    ez_factor_anki = ez_factor_human * 10
    if modify_db_directly is True:
        resetEaseDb(ez_factor_anki)
    else:
        resetEaseCol(ez_factor_anki)


def adjustIM(new_ease: int, base_im: int = 100) -> int:
    default_ease = 250
    return int(default_ease * base_im / new_ease)


def updateGroups(new_starting_ease: int, new_interval_modifier: int) -> None:
    if not update_option_groups:
        return

    dconfs = mw.col.decks.all_config()

    def updateGroupSettings(group_id: int) -> None:
        group_conf = mw.col.decks.get_config(group_id)

        # default = `2500`, LowKey target will be `1310`
        group_conf['new']['initialFactor'] = int(new_starting_ease * 10)

        # default is `1.0`, LowKey target will be `1.92`
        group_conf['rev']['ivlFct'] = float(new_interval_modifier / 100)

        mw.col.decks.setConf(group_conf, group_id)
        print(f"Updated Option Group: {group_conf['name']}.")

    for dconf in dconfs:
        updateGroupSettings(dconf['id'])


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
        self.updateGroupsCheckBox = QCheckBox("Update Option Groups")
        self.okButton = QPushButton("Ok")
        self.cancelButton = QPushButton("Cancel")
        self._setupUI()

    def _setupUI(self):
        self.setWindowTitle('Refold Ease')
        self.setLayout(self.setupOuterLayout())

    def setupOuterLayout(self):
        vbox = QVBoxLayout()
        vbox.setSpacing(10)
        vbox.addLayout(self.createEaseGroup())
        vbox.addLayout(self.createCheckBoxGroup())
        vbox.addStretch(1)
        vbox.addWidget(self.createLearnMoreLink())
        vbox.addLayout(self.createBottomGroup())
        return vbox

    def createEaseGroup(self):
        grid = QGridLayout()

        grid.addWidget(QLabel("Your IM at Ease=250%:"), 1, 0)
        grid.addWidget(self.defaultEaseImSpinBox, 1, 1)
        grid.addWidget(QLabel("%"), 1, 2)
        self.defaultEaseImSpinBox.setToolTip(
            "Your Interval Modifier before using this Ease setup.\n"
            "You can find it by going to `Deck options` -> `Reviews` -> `Interval Modifier`."
        )

        grid.addWidget(QLabel("Desired new Ease:"), 2, 0)
        grid.addWidget(self.easeSpinBox, 2, 1)
        grid.addWidget(QLabel("%"), 2, 2)
        self.easeSpinBox.setToolTip(
            "Your desired new Ease. This value should be set to `131%`\n"
            "if you're following the new `“Low-key” Low-key Anki` setup,\n"
            "or to `250%` if you stick to the old `Low-key` setup.\n\n"
            "Note: Because Anki resets Starting Ease back to 250% on each force sync if it's set to 130%,\n"
            "The lowest possible Ease supported by the add-on is 131%."
        )

        grid.addWidget(QLabel("Recommended new IM:"), 3, 0)
        grid.addWidget(self.imSpinBox, 3, 1)
        grid.addWidget(QLabel("%"), 3, 2)
        self.imSpinBox.setToolTip(
            "This is your new Interval Modifier after applying this Ease setup."
        )

        return grid

    def createCheckBoxGroup(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.syncCheckBox)
        vbox.addWidget(self.forceSyncCheckBox)
        vbox.addWidget(self.updateGroupsCheckBox)
        self.updateGroupsCheckBox.setToolTip(
            "Update Interval Modifier and Starting Ease in every options group."
        )
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


######################################################################
# The addon's window
######################################################################

class ResetEaseWindow(DialogUI):
    def __init__(self):
        super().__init__()
        self.setMinimums()
        self.setMaximums()
        self.setDefaultValues()
        self.connectUIElements()

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
        self.cancelButton.clicked.connect(self.close)

    def updateImSpinBox(self):
        self.imSpinBox.setValue(adjustIM(self.easeSpinBox.value(), self.defaultEaseImSpinBox.value()))

    def onConfirm(self):
        self.okButton.setText("Please wait...")
        self.okButton.repaint()

        global sync_after_reset, force_after, update_option_groups
        sync_after_reset = self.syncCheckBox.isChecked()
        force_after = self.forceSyncCheckBox.isChecked()
        update_option_groups = self.updateGroupsCheckBox.isChecked()

        syncBefore()
        resetEase(self.easeSpinBox.value())
        updateGroups(self.easeSpinBox.value(), self.imSpinBox.value())
        notify(self.easeSpinBox.value())
        syncAfter()

        self.close()


######################################################################
# Entry point
######################################################################

def showDialog():
    dialog = ResetEaseWindow()
    dialog.exec_()


# create a new menu item
action = QAction(menu_label, mw)
# set it to call testFunction when it's clicked
action.triggered.connect(showDialog)
# and add it to the tools menu
mw.form.menuTools.addAction(action)
