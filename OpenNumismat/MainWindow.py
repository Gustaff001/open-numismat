import sys
import urllib.request

from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

from OpenNumismat.Collection.Collection import Collection
from OpenNumismat.Collection.Description import DescriptionDialog
from OpenNumismat.Collection.Password import PasswordSetDialog
from OpenNumismat.Reports import Report
from OpenNumismat.TabView import TabView
from OpenNumismat.Settings import Settings
from OpenNumismat.SettingsDialog import SettingsDialog
from OpenNumismat.LatestCollections import LatestCollections
from OpenNumismat.Tools.CursorDecorators import waitCursorDecorator
from OpenNumismat import version
from OpenNumismat.Collection.Export import ExportDialog
from OpenNumismat.StatisticsView import statisticsAvailable, importedQtWebKit
from OpenNumismat.SummaryDialog import SummaryDialog
from OpenNumismat.Collection.Import.Colnect import ColnectDialog, colnectAvailable
from OpenNumismat.Collection.Import.Ans import AnsDialog, ansAvailable
from OpenNumismat.Collection.CollectionPages import CollectionPageTypes

from OpenNumismat.Collection.Import import *


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setWindowIcon(QIcon(':/main.ico'))

        self.createStatusBar()
        menubar = self.menuBar()

        self.collectionActs = []

        self.tableViewAct = QAction(QIcon(':/application_view_list.png'),
                                    self.tr("Table view"), self)
        self.tableViewAct.setData(CollectionPageTypes.List)
        self.tableViewAct.triggered.connect(self.changeViewEvent)
        self.collectionActs.append(self.tableViewAct)

        self.iconViewAct = QAction(QIcon(':/application_view_icons.png'),
                                   self.tr("Icon view"), self)
        self.iconViewAct.setData(CollectionPageTypes.Icon)
        self.iconViewAct.triggered.connect(self.changeViewEvent)
        self.collectionActs.append(self.iconViewAct)

        self.cardViewAct = QAction(QIcon(':/application_view_tile.png'),
                                   self.tr("Card view"), self)
        self.cardViewAct.setData(CollectionPageTypes.Card)
        self.cardViewAct.triggered.connect(self.changeViewEvent)
        self.collectionActs.append(self.cardViewAct)

        viewMenu = QMenu(self.tr("Change view"), self)
        viewMenu.addAction(self.tableViewAct)
        viewMenu.addAction(self.iconViewAct)
        viewMenu.addAction(self.cardViewAct)

        self.viewButton = QToolButton()
        self.viewButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.viewButton.setMenu(viewMenu)
        self.viewButton.setDefaultAction(self.tableViewAct)

        colnectAct = QAction(QIcon(':/colnect.png'),
                             "Colnect", self)
        colnectAct.triggered.connect(self.colnectEvent)
        self.collectionActs.append(colnectAct)

        ansAct = QAction(QIcon(':/ans.png'),
                              "American Numismatic Society", self)
        ansAct.triggered.connect(self.ansEvent)
        self.collectionActs.append(ansAct)

        self.detailsAct = QAction(QIcon(':/application-form.png'),
                                  self.tr("Info panel"), self)
        self.detailsAct.setCheckable(True)
        self.detailsAct.triggered.connect(self.detailsEvent)
        self.collectionActs.append(self.detailsAct)

        if statisticsAvailable:
            self.statisticsAct = QAction(QIcon(':/chart-bar.png'),
                                         self.tr("Statistics"), self)
            self.statisticsAct.setCheckable(True)
            self.statisticsAct.triggered.connect(self.statisticsEvent)
            self.collectionActs.append(self.statisticsAct)

        if importedQtWebKit:
            self.mapAct = QAction(QIcon(':/world.png'),
                                  self.tr("Map"), self)
            self.mapAct.setCheckable(True)
            self.mapAct.triggered.connect(self.mapEvent)
            self.collectionActs.append(self.mapAct)

        summaryAct = QAction(self.tr("Summary"), self)
        summaryAct.triggered.connect(self.summaryEvent)
        self.collectionActs.append(summaryAct)

        settingsAct = QAction(QIcon(':/cog.png'),
                              self.tr("Settings..."), self)
        settingsAct.triggered.connect(self.settingsEvent)
        self.collectionActs.append(settingsAct)

        cancelFilteringAct = QAction(QIcon(':/funnel_clear.png'),
                                     self.tr("Clear all filters"), self)
        cancelFilteringAct.triggered.connect(self.cancelFilteringEvent)
        self.collectionActs.append(cancelFilteringAct)

        cancelSortingAct = QAction(QIcon(':/sort_clear.png'),
                                   self.tr("Clear sort order"), self)
        cancelSortingAct.triggered.connect(self.cancelSortingEvent)
        self.collectionActs.append(cancelSortingAct)

        saveSortingAct = QAction(QIcon(':/sort_save.png'),
                                   self.tr("Save sort order"), self)
        saveSortingAct.triggered.connect(self.saveSortingEvent)
        self.collectionActs.append(saveSortingAct)

        self.enableDragAct = QAction(QIcon(':/arrow_switch.png'),
                                     self.tr("Sort by drag-n-drop mode"), self)
        self.enableDragAct.setCheckable(True)
        self.enableDragAct.triggered.connect(self.enableDragEvent)
        self.collectionActs.append(self.enableDragAct)

        self.exitAct = QAction(QIcon(':/door_in.png'),
                               self.tr("E&xit"), self)
        self.exitAct.setShortcut(QKeySequence.StandardKey.Quit)
        self.exitAct.triggered.connect(self.close)

        newCollectionAct = QAction(self.tr("&New..."), self)
        newCollectionAct.triggered.connect(self.newCollectionEvent)

        style = QApplication.style()
        icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        openCollectionAct = QAction(icon, self.tr("&Open..."), self)
        openCollectionAct.setShortcut(QKeySequence.StandardKey.Open)
        openCollectionAct.triggered.connect(self.openCollectionEvent)

        backupCollectionAct = QAction(
                                    QIcon(':/database_backup.png'),
                                    self.tr("Backup"), self)
        backupCollectionAct.triggered.connect(self.backupCollectionEvent)
        self.collectionActs.append(backupCollectionAct)

        vacuumCollectionAct = QAction(
                                    QIcon(':/compress.png'),
                                    self.tr("Vacuum"), self)
        vacuumCollectionAct.triggered.connect(self.vacuumCollectionEvent)
        self.collectionActs.append(vacuumCollectionAct)

        descriptionCollectionAct = QAction(self.tr("Description"), self)
        descriptionCollectionAct.triggered.connect(
                                            self.descriptionCollectionEvent)
        self.collectionActs.append(descriptionCollectionAct)

        passwordCollectionAct = QAction(QIcon(':/key.png'),
                                        self.tr("Set password..."), self)
        passwordCollectionAct.triggered.connect(self.passwordCollectionEvent)
        self.collectionActs.append(passwordCollectionAct)

        importMenu = QMenu(self.tr("Import"), self)
        self.collectionActs.append(importMenu)

        if ImportExcel.isAvailable():
            importExcelAct = QAction(
                                    QIcon(':/excel.png'),
                                    "Excel", self)
            importExcelAct.triggered.connect(self.importExcel)
            self.collectionActs.append(importExcelAct)
            importMenu.addAction(importExcelAct)

        if ImportColnect.isAvailable():
            importColnectAct = QAction(
                                    QIcon(':/colnect.png'),
                                    "Colnect", self)
            importColnectAct.triggered.connect(self.importColnect)
            self.collectionActs.append(importColnectAct)
            importMenu.addAction(importColnectAct)

        if ImportNumista.isAvailable():
            importNumistaAct = QAction(
                                    QIcon(':/numista.png'),
                                    "Numista", self)
            importNumistaAct.triggered.connect(self.importNumista)
            self.collectionActs.append(importNumistaAct)
            importMenu.addAction(importNumistaAct)

        if ImportCoinManage.isAvailable():
            importCoinManageAct = QAction(
                                    QIcon(':/CoinManage.png'),
                                    "CoinManage 2021", self)
            importCoinManageAct.triggered.connect(self.importCoinManage)
            self.collectionActs.append(importCoinManageAct)
            importMenu.addAction(importCoinManageAct)

        if ImportCollectionStudio.isAvailable():
            importCollectionStudioAct = QAction(
                                    QIcon(':/CollectionStudio.png'),
                                    "Collection Studio 3.65", self)
            importCollectionStudioAct.triggered.connect(
                                                self.importCollectionStudio)
            self.collectionActs.append(importCollectionStudioAct)
            importMenu.addAction(importCollectionStudioAct)

        if ImportUcoin2.isAvailable():
            importUcoinAct = QAction(
                                    QIcon(':/ucoin.png'),
                                    "uCoin.net", self)
            importUcoinAct.triggered.connect(self.importUcoin2)
            self.collectionActs.append(importUcoinAct)
            importMenu.addAction(importUcoinAct)
        elif ImportUcoin.isAvailable():
            importUcoinAct = QAction(
                                    QIcon(':/ucoin.png'),
                                    "uCoin.net", self)
            importUcoinAct.triggered.connect(self.importUcoin)
            self.collectionActs.append(importUcoinAct)
            importMenu.addAction(importUcoinAct)

        if ImportTellico.isAvailable():
            importTellicoAct = QAction(
                                    QIcon(':/tellico.png'),
                                    "Tellico", self)
            importTellicoAct.triggered.connect(self.importTellico)
            self.collectionActs.append(importTellicoAct)
            importMenu.addAction(importTellicoAct)

        mergeCollectionAct = QAction(
                                    QIcon(':/refresh.png'),
                                    self.tr("Synchronize..."), self)
        mergeCollectionAct.triggered.connect(self.mergeCollectionEvent)
        self.collectionActs.append(mergeCollectionAct)

        exportMenu = QMenu(self.tr("Export"), self)
        self.collectionActs.append(exportMenu)

        exportMobileAct = QAction(self.tr("For Android version"), self)
        exportMobileAct.triggered.connect(self.exportMobile)
        self.collectionActs.append(exportMobileAct)
        exportMenu.addAction(exportMobileAct)

        exportJsonAct = QAction(QIcon(':/json.png'), "JSON", self)
        exportJsonAct.triggered.connect(self.exportJson)
        self.collectionActs.append(exportJsonAct)
        exportMenu.addAction(exportJsonAct)

        file = menubar.addMenu(self.tr("&File"))

        file.addAction(newCollectionAct)
        file.addAction(openCollectionAct)
        file.addSeparator()
        file.addAction(backupCollectionAct)
        file.addAction(vacuumCollectionAct)
        file.addAction(passwordCollectionAct)
        file.addAction(descriptionCollectionAct)
        file.addSeparator()
        file.addMenu(importMenu)
        file.addAction(mergeCollectionAct)
        file.addSeparator()
        file.addMenu(exportMenu)
        file.addSeparator()

        self.latestActions = []
        self.__updateLatest(file)

        file.addAction(settingsAct)
        file.addSeparator()

        file.addAction(self.exitAct)

        addCoinAct = QAction(QIcon(':/add.png'),
                             self.tr("Add"), self)
        addCoinAct.setShortcut('Insert')
        addCoinAct.triggered.connect(self.addCoin)
        self.collectionActs.append(addCoinAct)

        editCoinAct = QAction(QIcon(':/pencil.png'),
                              self.tr("Edit..."), self)
        editCoinAct.triggered.connect(self.editCoin)
        self.collectionActs.append(editCoinAct)

        style = QApplication.style()
        icon = style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        deleteCoinAct = QAction(icon,
                                self.tr("Delete"), self)
        deleteCoinAct.setShortcut(QKeySequence.StandardKey.Delete)
        deleteCoinAct.triggered.connect(self.deleteCoin)
        self.collectionActs.append(deleteCoinAct)

        copyCoinAct = QAction(QIcon(':/page_copy.png'),
                              self.tr("Copy"), self)
        copyCoinAct.setShortcut(QKeySequence.StandardKey.Copy)
        copyCoinAct.triggered.connect(self.copyCoin)
        self.collectionActs.append(copyCoinAct)

        pasteCoinAct = QAction(QIcon(':/page_paste.png'),
                               self.tr("Paste"), self)
        pasteCoinAct.setShortcut(QKeySequence.StandardKey.Paste)
        pasteCoinAct.triggered.connect(self.pasteCoin)
        self.collectionActs.append(pasteCoinAct)

        coin = menubar.addMenu(self.tr("Coin"))
        self.collectionActs.append(coin)
        coin.addAction(addCoinAct)
        coin.addAction(editCoinAct)
        coin.addSeparator()
        if colnectAvailable:
            coin.addAction(colnectAct)
        if ansAvailable:
            coin.addAction(ansAct)
        coin.addSeparator()
        coin.addAction(copyCoinAct)
        coin.addAction(pasteCoinAct)
        coin.addSeparator()
        coin.addAction(deleteCoinAct)

        detailsMenu = QMenu(self.tr("Details"), self)
        if statisticsAvailable or importedQtWebKit:
            detailsMenu.addAction(self.detailsAct)
            if statisticsAvailable:
                detailsMenu.addAction(self.statisticsAct)
            if importedQtWebKit:
                detailsMenu.addAction(self.mapAct)

        view = menubar.addMenu(self.tr("&View"))
        self.collectionActs.append(view)
        view.addMenu(detailsMenu)
        view.addMenu(viewMenu)

        viewBrowserAct = QAction(QIcon(':/page_white_world.png'),
                                 self.tr("View in browser"), self)
        viewBrowserAct.triggered.connect(self.viewBrowserEvent)
        self.collectionActs.append(viewBrowserAct)

        self.viewTab = TabView(self)

        actions = self.viewTab.actions()
        listMenu = menubar.addMenu(self.tr("List"))
        listMenu.addAction(actions['new'])
        listMenu.addMenu(actions['open'])
        listMenu.aboutToShow.connect(self.viewTab.updateOpenPageMenu)
        listMenu.addAction(actions['rename'])
        listMenu.addSeparator()
        listMenu.addAction(actions['select'])
        listMenu.addSeparator()
        listMenu.addAction(actions['close'])
        listMenu.addAction(actions['remove'])
        self.collectionActs.append(listMenu)

        self.referenceMenu = menubar.addMenu(self.tr("Reference"))
        self.collectionActs.append(self.referenceMenu)

        reportAct = QAction(self.tr("Report..."), self)
        reportAct.setShortcut(QKeySequence.StandardKey.Print)
        reportAct.triggered.connect(self.report)
        self.collectionActs.append(reportAct)

        saveTableAct = QAction(QIcon(':/table.png'),
                               self.tr("Save current list..."), self)
        saveTableAct.triggered.connect(self.saveTable)
        self.collectionActs.append(saveTableAct)

        report = menubar.addMenu(self.tr("Report"))
        self.collectionActs.append(report)
        report.addAction(reportAct)
        report.addAction(saveTableAct)
        default_template = Settings()['template']
        viewBrowserMenu = report.addMenu(QIcon(':/page_white_world.png'),
                                         self.tr("View in browser"))
        for template in Report.scanTemplates():
            act = QAction(template[0], self)
            act.setData(template[1])
            act.triggered.connect(self.viewBrowserEvent)
            viewBrowserMenu.addAction(act)
            if default_template == template[1]:
                viewBrowserMenu.setDefaultAction(act)
        self.collectionActs.append(exportMenu)
        report.addSeparator()
        report.addAction(summaryAct)

        helpAct = QAction(QIcon(':/help.png'),
                          self.tr("User manual"), self)
        helpAct.setShortcut(QKeySequence.StandardKey.HelpContents)
        helpAct.triggered.connect(self.onlineHelp)
        webAct = QAction(self.tr("Visit web-site"), self)
        webAct.triggered.connect(self.visitWeb)
        checkUpdatesAct = QAction(self.tr("Check for updates"), self)
        checkUpdatesAct.triggered.connect(self.manualUpdate)
        aboutAct = QAction(self.tr("About %s") % version.AppName, self)
        aboutAct.triggered.connect(self.about)

        help_ = menubar.addMenu(self.tr("&Help"))
        help_.addAction(helpAct)
        help_.addAction(webAct)
        help_.addSeparator()
        help_.addAction(checkUpdatesAct)
        help_.addSeparator()
        help_.addAction(aboutAct)

        toolBar = QToolBar(self.tr("Toolbar"), self)
        toolBar.setObjectName("Toolbar")
        toolBar.setMovable(False)
        toolBar.addAction(openCollectionAct)
        toolBar.addSeparator()
        toolBar.addAction(addCoinAct)
        toolBar.addAction(editCoinAct)
        toolBar.addAction(viewBrowserAct)
        toolBar.addSeparator()
        toolBar.addAction(cancelFilteringAct)
        toolBar.addAction(cancelSortingAct)
        toolBar.addAction(saveSortingAct)
        toolBar.addAction(self.enableDragAct)
        toolBar.addSeparator()
        toolBar.addAction(settingsAct)
        if statisticsAvailable or importedQtWebKit:
            toolBar.addSeparator()
            toolBar.addAction(self.detailsAct)
            if statisticsAvailable:
                toolBar.addAction(self.statisticsAct)
            if importedQtWebKit:
                toolBar.addAction(self.mapAct)
        if colnectAvailable or ansAvailable:
            toolBar.addSeparator()
        if colnectAvailable:
            toolBar.addAction(colnectAct)
        if ansAvailable:
            toolBar.addAction(ansAct)
        toolBar.addSeparator()
        toolBar.addWidget(self.viewButton)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolBar.addWidget(spacer)

        self.quickSearch = QLineEdit()
        self.quickSearch.setMaximumWidth(250)
        self.quickSearch.setClearButtonEnabled(True)
        self.quickSearch.setPlaceholderText(self.tr("Quick search"))
        self.quickSearch.textEdited.connect(self.quickSearchEdited)
        self.collectionActs.append(self.quickSearch)
        self.quickSearchTimer = QTimer(self)
        self.quickSearchTimer.setSingleShot(True)
        self.quickSearchTimer.timeout.connect(self.quickSearchClicked)
        toolBar.addWidget(self.quickSearch)

        self.addToolBar(toolBar)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        self.setWindowTitle(version.AppName)

        if len(sys.argv) > 1:
            fileName = sys.argv[1]
        else:
            latest = LatestCollections(self)
            fileName = latest.latest()

        self.collection = Collection(self)
        self.openCollection(fileName)

        self.setCentralWidget(self.viewTab)

        settings = QSettings()
        pageIndex = settings.value('tabwindow/page', 0)
        if pageIndex is not None:
            self.viewTab.setCurrentIndex(int(pageIndex))

        geometry = settings.value('mainwindow/geometry')
        if geometry:
            self.restoreGeometry(geometry)
        winState = settings.value('mainwindow/winState')
        if winState:
            self.restoreState(winState)

        self.autoUpdate()

    def createStatusBar(self):
        self.collectionFileLabel = QLabel()
        self.statusBar().addWidget(self.collectionFileLabel)

    def __updateLatest(self, menu=None):
        if menu:
            self.__menu = menu
        for act in self.latestActions:
            self.__menu.removeAction(act)

        self.latestActions = []
        latest = LatestCollections(self)
        for act in latest.actions():
            self.latestActions.append(act)
            act.triggered.connect(self.openLatestCollectionEvent)
            self.__menu.insertAction(self.exitAct, act)
        self.__menu.insertSeparator(self.exitAct)

    def cancelFilteringEvent(self):
        self.quickSearch.clear()

        listView = self.viewTab.currentListView()
        listView.clearAllFilters()

    def cancelSortingEvent(self):
        listView = self.viewTab.currentListView()
        listView.clearSorting()

    def saveSortingEvent(self):
        listView = self.viewTab.currentListView()
        listView.saveSorting()

    def enableDragEvent(self):
        listView = self.viewTab.currentListView()
        if self.enableDragAct.isChecked():
            res = listView.tryDragMode()
            self.enableDragAct.setChecked(res)
        else:
            self.enableDragAct.setChecked(False)
            listView.selectMode()

    def settingsEvent(self):
        dialog = SettingsDialog(self.collection, self)
        res = dialog.exec()
        if res == QDialog.DialogCode.Accepted:
            result = QMessageBox.question(self, self.tr("Settings"),
                        self.tr("The application will need to restart to apply "
                                "the new settings. Restart it now?"),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes)
            if result == QMessageBox.StandardButton.Yes:
                self.restart()

    def changeViewEvent(self):
        type_ = self.sender().data()
        page = self.viewTab.currentPageView().param
        self.viewTab.collection.pages().changeView(page, type_)

        self.viewTab.clearStatusBar()
        page = self.viewTab.currentPageView()
        page.changeView(type_)
        self.viewTab.updatePage(page)

    def colnectEvent(self):
        model = self.viewTab.currentModel()
        dialog = ColnectDialog(model, self)
        dialog.exec()

    def ansEvent(self):
        model = self.viewTab.currentModel()
        dialog = AnsDialog(model, self)
        dialog.exec()

    def updateInfoType(self, info_type):
        self.detailsAct.setChecked(False)
        if statisticsAvailable:
            self.statisticsAct.setChecked(False)
        if importedQtWebKit:
            self.mapAct.setChecked(False)

        if info_type == CollectionPageTypes.Statistics:
            self.statisticsAct.setChecked(True)
        elif info_type == CollectionPageTypes.Map:
            self.mapAct.setChecked(True)
        else:
            self.detailsAct.setChecked(True)

    def detailsEvent(self, checked):
        self.updateInfoType(CollectionPageTypes.Details)
        if checked:
            page = self.viewTab.currentPageView()
            self.collection.pages().changeInfoType(page.param,
                                                   CollectionPageTypes.Details)
            page.showInfo(CollectionPageTypes.Details)

    def statisticsEvent(self, checked):
        self.updateInfoType(CollectionPageTypes.Statistics)
        if checked:
            page = self.viewTab.currentPageView()
            self.collection.pages().changeInfoType(page.param,
                                                   CollectionPageTypes.Statistics)
            page.showInfo(CollectionPageTypes.Statistics)

    def mapEvent(self, checked):
        self.updateInfoType(CollectionPageTypes.Map)
        if checked:
            page = self.viewTab.currentPageView()
            self.collection.pages().changeInfoType(page.param,
                                                   CollectionPageTypes.Map)
            page.showInfo(CollectionPageTypes.Map)

    def summaryEvent(self):
        model = self.viewTab.currentModel()
        dialog = SummaryDialog(model, self)
        dialog.exec()

    def restart(self):
        self.close()
        program = sys.executable
        argv = []
        if program != sys.argv[0]:
            # Process running as Python arg
            argv.append(sys.argv[0])
        QProcess.startDetached(program, argv)

    def importCoinManage(self):
        defaultDir = ImportCoinManage.defaultDir()
        file, _selectedFilter = QFileDialog.getOpenFileName(self,
                                self.tr("Select file"), defaultDir, "*.mdb")
        if file:
            imp = ImportCoinManage(self)
            res = imp.importData(file, self.viewTab.currentModel())
            if not res:
                return

            btn = QMessageBox.question(self, self.tr("Importing"),
                                self.tr("Import pre-defined coins?"),
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No)
            if btn == QMessageBox.StandardButton.Yes:
                imp = ImportCoinManagePredefined(self)
                imp.importData(file, self.viewTab.currentModel())

    def importCollectionStudio(self):
        QMessageBox.information(self, self.tr("Importing"),
                self.tr("Before importing you should export existing "
                        "collection from Collection Studio to XML Table "
                        "(choose Collection Studio menu Tools > Export...)."))

        defaultDir = ImportCollectionStudio.defaultDir()
        file, _selectedFilter = QFileDialog.getOpenFileName(self,
                                self.tr("Select file"), defaultDir, "*.xml")
        if file:
            imp = ImportCollectionStudio(self)
            imp.importData(file, self.viewTab.currentModel())

    def importUcoin(self):
        QMessageBox.information(
            self, self.tr("Importing"),
            self.tr("Before importing you should export existing "
                    "collection from uCoin.net to Comma-Separated (CSV) "
                    "format."))

        defaultDir = ImportUcoin.defaultDir()
        file, _selectedFilter = QFileDialog.getOpenFileName(
            self, self.tr("Select file"), defaultDir,
            "Comma-Separated (*.csv)")
        if file:
            imp = ImportUcoin(self)
            imp.importData(file, self.viewTab.currentModel())

    def importUcoin2(self):
        QMessageBox.information(
            self, self.tr("Importing"),
            self.tr("Before importing you should export existing "
                    "collection from uCoin.net to Microsoft Excel (XLS) or "
                    "Comma-Separated (CSV) format."))

        defaultDir = ImportUcoin.defaultDir()
        file, selectedFilter = QFileDialog.getOpenFileName(
            self, self.tr("Select file"), defaultDir,
            "Microsoft Excel (*.xlsx);;Comma-Separated (*.csv)")
        if file:
            if selectedFilter == "Microsoft Excel (*.xlsx)":
                imp = ImportUcoin2(self)
                imp.importData(file, self.viewTab.currentModel())
            else:
                imp = ImportUcoin(self)
                imp.importData(file, self.viewTab.currentModel())

    def importTellico(self):
        defaultDir = ImportTellico.defaultDir()
        file, _selectedFilter = QFileDialog.getOpenFileName(
            self, self.tr("Select file"), defaultDir, "*.tc")
        if file:
            imp = ImportTellico(self)
            imp.importData(file, self.viewTab.currentModel())

    def importExcel(self):
        defaultDir = ImportExcel.defaultDir()
        file, _selectedFilter = QFileDialog.getOpenFileName(
            self, self.tr("Select file"), defaultDir, "*.xls *.xlsx")
        if file:
            imp = ImportExcel(self)
            imp.importData(file, self.viewTab.currentModel())

    def importColnect(self):
        defaultDir = ImportColnect.defaultDir()
        file, _selectedFilter = QFileDialog.getOpenFileName(
            self, self.tr("Select file"), defaultDir, "*.csv")
        if file:
            imp = ImportColnect(self)
            imp.importData(file, self.viewTab.currentModel())

    def importNumista(self):
        imp = ImportNumista(self)
        imp.importData('Numista', self.viewTab.currentModel())

    def exportMobile(self):
        dialog = ExportDialog(self.collection, self)
        res = dialog.exec()
        if res == QDialog.DialogCode.Accepted:
            self.collection.exportToMobile(dialog.params)

    def exportJson(self):
        self.collection.exportToJson()

    def addCoin(self):
        model = self.viewTab.currentModel()
        model.addCoin(model.record(), self)

    def editCoin(self):
        listView = self.viewTab.currentListView()
        indexes = listView.selectedCoins()
        if len(indexes) == 1:
            listView._edit(indexes[0])
        elif len(indexes) > 1:
            listView._multiEdit(indexes)

    def deleteCoin(self):
        listView = self.viewTab.currentListView()
        indexes = listView.selectedCoins()
        if len(indexes):
            listView._delete(indexes)

    def copyCoin(self):
        listView = self.viewTab.currentListView()
        indexes = listView.selectedCoins()
        if len(indexes):
            listView._copy(indexes)

    def pasteCoin(self):
        listView = self.viewTab.currentListView()
        listView._paste()

    def quickSearchEdited(self, _text):
        self.quickSearchTimer.start(180)

    def quickSearchClicked(self):
        listView = self.viewTab.currentListView()
        listView.search(self.quickSearch.text())

    def viewBrowserEvent(self):
        template = self.sender().data()
        listView = self.viewTab.currentListView()
        listView.viewInBrowser(template)

    def report(self):
        listView = self.viewTab.currentListView()
        listView.report()

    def saveTable(self):
        listView = self.viewTab.currentListView()
        listView.saveTable()

    def __workingDir(self):
        fileName = self.collection.fileName
        if not fileName:
            fileName = LatestCollections.DefaultCollectionName
        return QFileInfo(fileName).absolutePath()

    def openCollectionEvent(self):
        fileName, _selectedFilter = QFileDialog.getOpenFileName(self,
                self.tr("Open collection"), self.__workingDir(),
                self.tr("Collections (*.db)"))
        if fileName:
            self.openCollection(fileName)

    def newCollectionEvent(self):
        fileName, _selectedFilter = QFileDialog.getSaveFileName(self,
                self.tr("New collection"), self.__workingDir(),
                self.tr("Collections (*.db)"), "",
                QFileDialog.DontConfirmOverwrite)
        if fileName:
            self.__closeCollection()
            if self.collection.create(fileName):
                self.setCollection(self.collection)

    def descriptionCollectionEvent(self):
        dialog = DescriptionDialog(self.collection.getDescription(), self)
        dialog.exec()

    def passwordCollectionEvent(self):
        dialog = PasswordSetDialog(self.collection.settings, self)
        dialog.exec()

    def backupCollectionEvent(self):
        self.collection.backup()

    def vacuumCollectionEvent(self):
        self.collection.vacuum()

    def mergeCollectionEvent(self):
        fileName, _selectedFilter = QFileDialog.getOpenFileName(self,
                self.tr("Open collection"), self.__workingDir(),
                self.tr("Collections (*.db)"))
        if fileName:
            self.collection.merge(fileName)

    def openCollection(self, fileName):
        self.__closeCollection()
        if self.collection.open(fileName):
            self.setCollection(self.collection)
        else:
            # Remove wrong collection from latest collections list
            latest = LatestCollections(self)
            latest.delete(fileName)
            self.__updateLatest()

    def openLatestCollectionEvent(self):
        fileName = self.sender().data()
        self.openCollection(fileName)

    @waitCursorDecorator
    def setCollection(self, collection):
        self.collection.loadReference(Settings()['reference'])

        self.__setEnabledActs(True)

        self.collectionFileLabel.setText(collection.getFileName())
        title = "%s - %s" % (collection.getCollectionName(), version.AppName)
        self.setWindowTitle(title)

        latest = LatestCollections(self)
        latest.add(collection.getFileName())
        self.__updateLatest()

        self.viewTab.setCollection(collection)

        self.referenceMenu.clear()
        for action in self.collection.referenceMenu(self):
            self.referenceMenu.addAction(action)

    def __setEnabledActs(self, enabled):
        for act in self.collectionActs:
            act.setEnabled(enabled)

    def __closeCollection(self):
        self.__saveParams()

        self.__setEnabledActs(False)
        self.viewTab.clear()

        self.referenceMenu.clear()
        self.quickSearch.clear()

        self.collectionFileLabel.setText(
                self.tr("Create new collection or open one of the existing"))

        self.setWindowTitle(version.AppName)

    def closeEvent(self, e):
        self.__shutDown()

    def __shutDown(self):
        self.__saveParams()

        settings = QSettings()

        if self.collection.fileName:
            # Save latest opened page
            settings.setValue('tabwindow/page', self.viewTab.currentIndex())

        # Save main window size
        settings.setValue('mainwindow/geometry', self.saveGeometry())
        settings.setValue('mainwindow/winState', self.saveState())

    def __saveParams(self):
        if self.collection.isOpen():
            for param in self.collection.pages().pagesParam():
                param.listParam.save_lists(only_if_changed=True)

            self.viewTab.savePagePositions(only_if_changed=True)

            if Settings()['autobackup']:
                if self.collection.isNeedBackup():
                    self.collection.backup()

    def about(self):
        QMessageBox.about(self, self.tr("About %s") % version.AppName,
                        "%s %s\n\n" % (version.AppName, version.Version) +
                        "Copyright (C) 2011-2023 Vitaly Ignatov\n\n" +
                        self.tr("%s is freeware licensed under a GPLv3.") %
                        version.AppName)

    def onlineHelp(self):
        self._openUrl("http://opennumismat.github.io/open-numismat/manual.html")

    def visitWeb(self):
        self._openUrl(version.Web)

    def autoUpdate(self):
        if Settings()['updates']:
            settings = QSettings()
            lastUpdateDateStr = settings.value('mainwindow/last_update')
            if lastUpdateDateStr:
                lastUpdateDate = QDate.fromString(lastUpdateDateStr,
                                                  Qt.DateFormat.ISODate)
                currentDate = QDate.currentDate()
                if lastUpdateDate.addDays(10) < currentDate:
                    self.checkUpdates()
            else:
                self.checkUpdates()

    def manualUpdate(self):
        if not self.checkUpdates():
            QMessageBox.information(self, self.tr("Updates"),
                    self.tr("You already have the latest version."))

    def checkUpdates(self):
        currentDate = QDate.currentDate()
        currentDateStr = currentDate.toString(Qt.DateFormat.ISODate)
        settings = QSettings()
        settings.setValue('mainwindow/last_update', currentDateStr)

        newVersion = self.__getNewVersion()
        if newVersion and newVersion != version.Version:
            result = QMessageBox.question(self, self.tr("New version"),
                        self.tr("New version is available. Download it now?"),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes)
            if result == QMessageBox.StandardButton.Yes:
                self._openUrl(version.Web)

            return True
        else:
            return False

    def _openUrl(self, url):
        executor = QDesktopServices()
        executor.openUrl(QUrl(url))

    @waitCursorDecorator
    def __getNewVersion(self):
        from xml.dom.minidom import parseString

        newVersion = version.Version

        try:
            url = "http://opennumismat.github.io/data/pad.xml"
            req = urllib.request.Request(url)
            data = urllib.request.urlopen(req, timeout=10).read()
            xml = parseString(data)
            tag = xml.getElementsByTagName('Program_Version')[0]
            newVersion = tag.firstChild.nodeValue
        except:
            return None

        return newVersion
