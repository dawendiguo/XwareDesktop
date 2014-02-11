# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSlot, pyqtSignal, QObject

from PyQt5.QtWidgets import QDialog, QTableWidgetItem
from ui_settings import Ui_Dialog
import configparser
import constants

DEFAULT_SETTINGS = {
    "account": {
        "username": None,
        "password": None,
        "autologin": True
    },
    "frontend": {
        "enabledeveloperstools": False,
        "allowflash": True
    },
    "xwared": {
        "startetm": True,
        "startetmwhen": 1
    }
}

class SettingsAccessor(QObject):
    applySettings = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config.read(constants.CONFIG_FILE)

    def get(self, section, key):
        return self.config.get(section, key, fallback = DEFAULT_SETTINGS[section][key])

    def set(self, section, key, value):
        try:
            self.config.set(section, key, value)
        except configparser.NoSectionError:
            self.config.add_section(section)
            self.config.set(section, key, value)

    def getint(self, section, key):
        return int(self.get(section, key))

    def setint(self, section, key, value):
        assert type(value) is int
        self.set(section, key, str(value))

    def getbool(self, section, key):
        return True if self.get(section, key) == "1" else False

    def setbool(self, section, key, value):
        assert type(value) is bool
        self.set(section, key, "1" if value else "0")

    def save(self):
        with open(constants.CONFIG_FILE, 'w') as configfile:
            self.config.write(configfile)

class SettingsDialog(QDialog, Ui_Dialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.mainWin = parent
        self.settings = self.mainWin.settings # shorthand
        self.setupUi(self)

        self.lineEdit_loginUsername.setText(self.settings.get("account", "username"))
        self.lineEdit_loginPassword.setText(self.settings.get("account", "password"))
        self.checkBox_autoLogin.setChecked(self.settings.getbool("account", "autologin"))
        self.checkBox_enableDevelopersTools.setChecked(
            self.settings.getbool("frontend", "enabledeveloperstools"))
        self.checkBox_allowFlash.setChecked(self.settings.getbool("frontend", "allowflash"))

        from PyQt5.QtWidgets import QButtonGroup
        self.btngrp_etmStartWhen = QButtonGroup()
        self.btngrp_etmStartWhen.addButton(self.radio_backendStartWhen1, 1)
        self.btngrp_etmStartWhen.addButton(self.radio_backendStartWhen2, 2)
        self.btngrp_etmStartWhen.addButton(self.radio_backendStartWhen3, 3)
        self.btngrp_etmStartWhen.button(self.settings.getint("xwared", "startetmwhen")).setChecked(True)

        self.rejected.connect(lambda: self.close())
        self.accepted.connect(self.writeSettings)

        # Mounts
        self.setupMounts()

    def setupMounts(self):
        self.btn_addMount.clicked.connect(self.slotAddMount)
        self.btn_removeMount.clicked.connect(self.slotRemoveMount)

        mountsMapping = self.mainWin.mountsFaker.getMountsMapping()
        for i, mount in enumerate(self.mainWin.mountsFaker.mounts):
            # mounts = ['/path/to/1', 'path/to/2', ...]
            self.table_mounts.insertRow(i)
            self.table_mounts.setItem(i, 0, QTableWidgetItem(mount))
            drive1 = chr(ord('C') + i) + ":" # the drive letter it should map to, by alphabetical order
            self.table_mounts.setItem(i, 1, QTableWidgetItem(drive1))
            drive2 = mountsMapping.get(mount, "无") # the drive letter it actually is assigned to

            errors = []
            # check 1: owned by xware group?
            import os, grp
            statinfo = os.stat(mount) #.st_gid
            ownergrp = grp.getgrgid(statinfo.st_gid)[0] # 0: gr_name, 3: all members
            if ownergrp != "xware":
                errors.append("警告：{unixpath}的所有组不是'xware'，请修正后重启后端。".format(unixpath = mount))

            # check 2: mounting
            if drive1 != drive2:
                errors.append("警告：盘符映射在'{actual}'，而不是'{should}'。".format(actual = drive2, should = drive1))

            from PyQt5.Qt import Qt
            from PyQt5.QtGui import QBrush

            brush = QBrush()
            if errors:
                brush.setColor(Qt.red)
                errString = "\n".join(errors)
            else:
                brush.setColor(Qt.darkGreen)
                errString = "正常"
            errWidget = QTableWidgetItem(errString)
            errWidget.setForeground(brush)

            self.table_mounts.setItem(i, 2, errWidget)
            self.table_mounts.resizeColumnsToContents()
            del brush, errWidget

    @pyqtSlot()
    def slotAddMount(self):
        import os
        from PyQt5.QtWidgets import QFileDialog
        from PyQt5.Qt import Qt

        fileDialog = QFileDialog(self, Qt.Dialog)
        fileDialog.setFileMode(QFileDialog.Directory)
        fileDialog.setOption(QFileDialog.ShowDirsOnly, True)
        fileDialog.setViewMode(QFileDialog.List)
        fileDialog.setDirectory(os.environ["HOME"])
        if (fileDialog.exec()):
            selected = fileDialog.selectedFiles()[0]
            if selected in self.newMounts:
                return
            row = self.table_mounts.rowCount()
            self.table_mounts.insertRow(row)
            self.table_mounts.setItem(row, 0, QTableWidgetItem(selected))
            self.table_mounts.setItem(row, 1, QTableWidgetItem("新近添加"))
            self.table_mounts.setItem(row, 2, QTableWidgetItem("新近添加"))

    @pyqtSlot()
    def slotRemoveMount(self):
        row = self.table_mounts.currentRow()
        self.table_mounts.removeRow(row)

    @pyqtSlot()
    def writeSettings(self):
        self.settings.set("account", "username", self.lineEdit_loginUsername.text())
        self.settings.set("account", "password", self.lineEdit_loginPassword.text())
        self.settings.setbool("account", "autologin", self.checkBox_autoLogin.isChecked())
        self.settings.setbool("frontend", "enabledeveloperstools",
                                self.checkBox_enableDevelopersTools.isChecked())
        self.settings.setbool("frontend", "allowflash",
                                self.checkBox_allowFlash.isChecked())

        self.settings.setint("xwared", "startetmwhen",
                          self.btngrp_etmStartWhen.id(self.btngrp_etmStartWhen.checkedButton()))

        startETMWhen = self.settings.getint("xwared", "startetmwhen")
        if startETMWhen == 1:
            self.settings.setbool("xwared", "startetm", True)

        self.settings.save()

        self.mainWin.mountsFaker.setMounts(self.newMounts)
        self.settings.applySettings.emit()

    @property
    def newMounts(self):
        return list(map(lambda row: self.table_mounts.item(row, 0).text(),
                        range(self.table_mounts.rowCount())))

