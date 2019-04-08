import json
import re
import os
import tempfile
import urllib.request

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QObject, QDate
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtSql import QSqlDatabase, QSqlQuery
from PyQt5.QtWidgets import *

from OpenNumismat import version
from OpenNumismat.Settings import Settings
from OpenNumismat.Tools.CursorDecorators import waitCursorDecorator
from OpenNumismat.Tools.DialogDecorators import storeDlgSizeDecorator
from OpenNumismat.Tools.Gui import createIcon, ProgressDialog

from OpenNumismat.private_keys import COLNECT_KEY


class ColnectCache(QObject):
    FILE_NAME = "opennumismat-colnect"

    Action = 1
    Item = 2
    Image = 3

    def __init__(self, parent=None):
        super().__init__(parent)

        self.db = self.open()
        self._compact()

    def open(self):
        db = QSqlDatabase.addDatabase('QSQLITE', 'cache')
        db.setDatabaseName(self._file_name())
        if not db.open():
            QMessageBox.warning(self,
                                "Colnect",
                                self.tr("Can't open Colnect cache"))
            return None

        QSqlQuery("PRAGMA synchronous=OFF", db)
        QSqlQuery("PRAGMA journal_mode=MEMORY", db)

        if 'cache' not in db.tables():
            sql = "CREATE TABLE cache (\
                id INTEGER PRIMARY KEY,\
                type INTEGER, url TEXT, data BLOB,\
                createdat TEXT)"
            QSqlQuery(sql, db)

        return db

    def close(self):
        if self.db:
            self.db.close()
            self.db = None
        QSqlDatabase.removeDatabase('cache')

    def get(self, type_, url):
        if not self.db:
            return None

        query = QSqlQuery(self.db)
        query.prepare("SELECT data FROM cache WHERE type=? AND url=?")
        query.addBindValue(type_)
        query.addBindValue(url)
        query.exec_()
        if query.next():
            record = query.record()
            return record.value('data')

        return None

    def set(self, type_, url, data):
        if not self.db:
            return

        if not data:
            return

        query = QSqlQuery(self.db)
        query.prepare("INSERT INTO cache (type, url, data, createdat)"
                      " VALUES (?, ?, ?, ?)")
        query.addBindValue(type_)
        query.addBindValue(url)
        query.addBindValue(data)
        currentDate = QDate.currentDate()
        days = QDate(2000, 1, 1).daysTo(currentDate)
        query.addBindValue(days)
        query.exec_()

    def _compact(self):
        if self.db:
            query = QSqlQuery(self.db)
            query.prepare("DELETE FROM cache WHERE"
                          " (createdat < ? AND type = 1) OR"
                          " (createdat < ? AND type = 2) OR"
                          " (createdat < ? AND type = 3)")
            currentDate = QDate.currentDate()
            days = QDate(2000, 1, 1).daysTo(currentDate)
            query.addBindValue(days - 30)  # actions older month
            query.addBindValue(days - 14)  # items older 2 weeks
            query.addBindValue(days - 7)  # images older week
            query.exec_()

    @staticmethod
    def _file_name():
        return os.path.join(tempfile.gettempdir(), ColnectCache.FILE_NAME)

    @staticmethod
    def clear():
        file_name = ColnectCache._file_name()
        if os.path.exists(file_name):
            os.remove(file_name)


@storeDlgSizeDecorator
class ColnectDialog(QDialog):
    HEIGHT = 62

    def __init__(self, model, parent=None):
        super().__init__(parent,
                         Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint)
        self.setWindowIcon(createIcon('colnect.png'))
        self.setWindowTitle("Colnect")

        fields = model.fields

        settings = Settings()
        self.lang = settings['colnect_locale']
        self.autoclose = settings['colnect_autoclose']
        self.skip_currency = settings['colnect_skip_currency']

        self.cache = ColnectCache()

        layout = QFormLayout()
        layout.setRowWrapPolicy(QFormLayout.WrapLongRows)

        self.colnectLabel = QLabel(self.tr(
            "Catalog information courtesy of"
            " <a href=\"https://colnect.com/\">Colnect</a>,"
            " an online collectors community."))
        self.colnectLabel.setTextFormat(Qt.RichText)
        self.colnectLabel.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.colnectLabel.setOpenExternalLinks(True)
        font = self.colnectLabel.font()
        font.setPointSize(11)
        self.colnectLabel.setFont(font)
        layout.addRow(self.colnectLabel)
        layout.addRow(QWidget())

        categories = (('coins', self.tr("Coins")),
                      ('banknotes', self.tr("Bankotes")),
                      ('stamps', self.tr("Stamps")))

        self.categorySelector = QComboBox()
        self.categorySelector.setSizePolicy(QSizePolicy.Fixed,
                                            QSizePolicy.Fixed)
        for category in categories:
            self.categorySelector.addItem(category[1], category[0])
        layout.addRow(self.tr("Category"), self.categorySelector)
        self.categorySelector.currentIndexChanged.connect(self.categoryChanged)

        self.countrySelector = QComboBox()
        self.countrySelector.setSizePolicy(QSizePolicy.Fixed,
                                           QSizePolicy.Fixed)
        self.countrySelector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.countrySelector.currentIndexChanged.connect(self.countryChanged)
        layout.addRow(fields.getCustomTitle('country'), self.countrySelector)

        self.seriesSelector = QComboBox()
        self.seriesSelector.setSizePolicy(QSizePolicy.Fixed,
                                          QSizePolicy.Fixed)
        self.seriesSelector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.seriesSelector.currentIndexChanged.connect(self.partChanged)
        layout.addRow(fields.getCustomTitle('series'), self.seriesSelector)

        self.yearSelector = QComboBox()
        self.yearSelector.setSizePolicy(QSizePolicy.Fixed,
                                        QSizePolicy.Fixed)
        self.yearSelector.currentIndexChanged.connect(self.partChanged)
        self.yearSelector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        layout.addRow(fields.getCustomTitle('year'), self.yearSelector)

        self.valueSelector = QComboBox()
        self.valueSelector.setSizePolicy(QSizePolicy.Fixed,
                                         QSizePolicy.Fixed)
        self.valueSelector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.valueSelector.currentIndexChanged.connect(self.partChanged)
        layout.addRow(fields.getCustomTitle('value'), self.valueSelector)

        self.currencySelector = QComboBox()
        self.currencySelector.setSizePolicy(QSizePolicy.Fixed,
                                            QSizePolicy.Fixed)
        self.currencySelector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.currencySelector.currentIndexChanged.connect(self.partChanged)
        layout.addRow(fields.getCustomTitle('unit'), self.currencySelector)

        self.parts = (self.seriesSelector, self.yearSelector,
                      self.valueSelector, self.currencySelector)

        self.table = QTableWidget(self)
        self.table.doubleClicked.connect(self.tableClicked)
        self.table.setColumnCount(9)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().sectionDoubleClicked.connect(
                                                self.sectionDoubleClicked)
        font = self.table.horizontalHeader().font()
        font.setBold(True)
        self.table.horizontalHeader().setFont(font)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(self.HEIGHT + 2)
        self.table.setColumnWidth(0, self.HEIGHT + 6)
        self.table.setColumnWidth(1, self.HEIGHT + 6)

        field_names = ('obverseimg', 'reverseimg', 'title', 'series',
                       'year', 'type', 'material', 'value', 'unit')
        field_titles = []
        for field_name in field_names:
            title = fields.getCustomTitle(field_name)
            field_titles.append(title)
        self.table.setHorizontalHeaderLabels(field_titles)

        self.addButton = QPushButton(self.tr("Add"))
        self.addButton.setEnabled(False)
        self.addCloseButton = QPushButton(self.tr("Add and close"))
        self.addCloseButton.setEnabled(False)
        if self.autoclose:
            self.addCloseButton.setDefault(True)
        else:
            self.addButton.setDefault(True)
        buttonBox = QDialogButtonBox(Qt.Horizontal, self)
        buttonBox.addButton(self.addButton, QDialogButtonBox.ActionRole)
        buttonBox.addButton(self.addCloseButton, QDialogButtonBox.ActionRole)
        buttonBox.addButton(QDialogButtonBox.Close)
        buttonBox.clicked.connect(self.clicked)

        self.table.hide()
        self.label = QLabel("Specify more parameters", self)

        vlayout = QVBoxLayout()
        vlayout.addLayout(layout)
        vlayout.addWidget(self.table)
        vlayout.addWidget(self.label)
        vlayout.addWidget(buttonBox)

        self.setLayout(vlayout)

        self._partsEnable(False)

        self.model = model
        self.settings = model.settings
        self.items = []

        default_category = self.settings['colnect_category']
        default_country = self.settings['colnect_country']

        index = self.categorySelector.findData(default_category)
        self.categorySelector.setCurrentIndex(index)
        self.categoryChanged(0)

        index = self.countrySelector.findData(default_country)
        if index >= 0:
            self.countrySelector.setCurrentIndex(index)
        self.countryChanged(0)

    def sectionDoubleClicked(self, index):
        self.table.resizeColumnToContents(index)

    def _partsEnable(self, enabled):
        for part in self.parts:
            part.setEnabled(enabled)

    def tableClicked(self, index):
        if not index:
            return

        self.addCoin(index, self.autoclose)

    def addCoin(self, index, close):
        columns = {'coins': (
            ('title', 0), ('country', 1), ('series', 2), ('year', 4),
            ('mintage', 6), ('unit', 12), ('value', 13), ('material', 19),
            ('diameter', 21), ('weight', 20), ('subject', 25), ('type', 14),
            ('issuedate', 4), ('edge', 15), ('shape', 17), ('obvrev', 16),
            ('catalognum1', 3), ('url', -1),
            # ('subjectshort', 24)
            ),
                'banknotes': (
            ('title', 0), ('country', 1), ('series', 2), ('year', 4),
            ('mintage', 6), ('unit', 12), ('value', 13), ('material', 17),
            ('diameter', 14), ('thickness', 15), ('subject', 20), ('mint', 18),
            ('issuedate', 4), ('catalognum1', 3), ('url', -1),
            # ('subjectshort', 24)
            ),
                'stamps': (
            ('title', 0), ('country', 1), ('series', 2), ('year', 4),
            ('mintage', 6), ('unit', 12), ('value', 13), ('material', 19),
            ('diameter', 21), ('thickness', 22), ('subject', 25), ('type', 15),
            ('quality', 17), ('obvrev', 18), ('edgelabel', 20),
            ('issuedate', 4), ('edge', 16), ('obversecolor', 23),
            ('format', 14), ('catalognum1', 3), ('url', -1),
            # ('subjectshort', 24)
            )}

        category = self.categorySelector.currentData()
        data = self.items[index.row()]

        newRecord = self.model.record()
        for column in columns[category]:
            value = data[column[1]]
            if column[0] == 'year' and isinstance(value, str):
                value = value[:4]
            elif column[0] == 'unit' and self.skip_currency:
                value = value.split('-', 1)[-1].strip()
            newRecord.setValue(column[0], value)

        image = self._getFullImage(int(data[8]), data[0])
        newRecord.setValue('obverseimg', image)
        image = self._getFullImage(int(data[9]), data[0])
        newRecord.setValue('reverseimg', image)
        if category == 'coins':
            ext_image_pos = 22
        elif category == 'banknotes':
            ext_image_pos = 16
        else:
            ext_image_pos = None
        if ext_image_pos:
            image = self._getFullImage(int(data[ext_image_pos]), data[0])
            newRecord.setValue('photo1', image)

        if close:
            self.accept()

        self.model.addCoin(newRecord, self)

    def _clearTable(self):
        self.addButton.setEnabled(False)
        self.addCloseButton.setEnabled(False)

        self.table.hide()
        self.label.show()
        self.table.setRowCount(0)
        self.items = []

    def categoryChanged(self, _index):
        self._clearTable()
        self.countrySelector.clear()

        category = self.categorySelector.currentData()
        countries = self.getCountries(category)
        for country in countries:
            self.countrySelector.addItem(country[1], country[0])

        self.settings['colnect_category'] = category

    def countryChanged(self, _index):
        self._clearTable()

        self._partsEnable(True)

        category = self.categorySelector.currentData()
        country = self.countrySelector.currentData()
        if not country:
            return

        series = self.getSeries(category, country)
        self.seriesSelector.clear()
        self.seriesSelector.addItem(self.tr("(All)"), None)
        for ser in series:
            self.seriesSelector.addItem(str(ser[1]), ser[0])

        years = self.getYears(category, country)
        self.yearSelector.clear()
        self.yearSelector.addItem(self.tr("(All)"), None)
        for year in years:
            self.yearSelector.addItem(str(year[0]), year[0])

        values = self.getValues(category, country)
        self.valueSelector.clear()
        self.valueSelector.addItem(self.tr("(All)"), None)
        for value in values:
            self.valueSelector.addItem(str(value[1]), value[0])

        currencies = self.getCurrencies(category, country)
        self.currencySelector.clear()
        self.currencySelector.addItem(self.tr("(All)"), None)
        for currency in currencies:
            self.currencySelector.addItem(str(currency[1]), currency[0])

        self.settings['colnect_country'] = country

    def partChanged(self, _index):
        self._clearTable()

        series = self.seriesSelector.currentData()
        year = self.yearSelector.currentData()
        value = self.valueSelector.currentData()
        currency = self.currencySelector.currentData()
        # TODO:
        # distribution (https://api.colnect.net/en/api/8xZqcX3b/distributions/cat/coins/producer/922/)
        # emissions (https://api.colnect.net/en/api/8xZqcX3b/emissions/cat/stamps/producer/8147)
        # mint_year (https://api.colnect.net/en/api/8xZqcX3b/list/cat/coins/producer/922/mint_year/2000)

        if series or year or value or currency:
            category = self.categorySelector.currentData()
            country = self.countrySelector.currentData()
            action = "list_id/cat/%s/producer/%d" % (category, country)
            if series:
                action += "/series/%s" % series
            if year:
                action += "/year/%s" % year
            if value:
                action += "/face_value/%s" % value
            if currency:
                action += "/currency/%s" % currency
            item_ids = self._getData(action)

            if (series and year and value and currency) or (len(item_ids) < 100):
                if item_ids:
                    self.addButton.setEnabled(True)
                    self.addCloseButton.setEnabled(True)
                self.table.show()
                self.label.hide()

                progressDlg = ProgressDialog(
                            self.tr("Downloading"),
                            self.tr("Cancel"), len(item_ids), self)

                self.table.setRowCount(len(item_ids))
                for i, item_id in enumerate(item_ids):
                    progressDlg.step()
                    if progressDlg.wasCanceled():
                        break

                    action = "item/cat/%s/producer/%d/id/%d" % (category, country, item_id)
                    data = self._getData(action)
                    data.append(self._itemUrl(category, item_id))
                    self.items.append(data)

                    image = self._getImage(int(data[8]), data[0])
                    pixmap = QPixmap.fromImage(image)
                    item = QTableWidgetItem()
                    item.setData(Qt.DecorationRole, pixmap)
                    self.table.setItem(i, 0, item)

                    image = self._getImage(int(data[9]), data[0])
                    pixmap = QPixmap.fromImage(image)
                    item = QTableWidgetItem()
                    item.setData(Qt.DecorationRole, pixmap)
                    self.table.setItem(i, 1, item)

                    item = QTableWidgetItem(data[0])
                    self.table.setItem(i, 2, item)
                    item = QTableWidgetItem(data[2])
                    self.table.setItem(i, 3, item)
                    item = QTableWidgetItem(str(data[4]))
                    self.table.setItem(i, 4, item)
                    item = QTableWidgetItem(data[14])
                    self.table.setItem(i, 5, item)
                    item = QTableWidgetItem(data[19])
                    self.table.setItem(i, 6, item)
                    item = QTableWidgetItem(str(data[13]))
                    self.table.setItem(i, 7, item)
                    item = QTableWidgetItem(data[12])
                    self.table.setItem(i, 8, item)

                progressDlg.reset()

    def getCountries(self, category):
        action = "countries/cat/%s" % category
        return self._getData(action)

    def getYears(self, category, country):
        action = "years/cat/%s/producer/%d" % (category, country)
        return self._getData(action)

    def getSeries(self, category, country):
        action = "series/cat/%s/producer/%d" % (category, country)
        return self._getData(action)

    def getValues(self, category, country):
        action = "face_values/cat/%s/producer/%d" % (category, country)
        return self._getData(action)

    def getCurrencies(self, category, country):
        action = "currencies/cat/%s/producer/%d" % (category, country)
        return self._getData(action)

    def _baseUrl(self):
        url = "https://api.colnect.net/%s/api/%s/" % (self.lang, COLNECT_KEY)
        return url

    @waitCursorDecorator
    def _getData(self, action):
        data = []

        url = self._baseUrl() + action
        raw_data = self.cache.get(ColnectCache.Action, url)
        if raw_data:
            data = json.loads(raw_data)
            return data

        try:
            req = urllib.request.Request(url,
                                    headers={'User-Agent': version.AppName})
            raw_data = urllib.request.urlopen(req).read().decode()
            self.cache.set(ColnectCache.Action, url, raw_data)
            data = json.loads(raw_data)
        except:
            pass

        return data

    def _getImage(self, image_id, name):
        image = QImage()

        if not image_id:
            return image

        url = self._imageUrl(image_id, name, False)
        raw_data = self.cache.get(ColnectCache.Image, url)
        if raw_data:
            result = image.loadFromData(raw_data)
            if result:
                return image

        try:
            req = urllib.request.Request(url,
                                    headers={'User-Agent': version.AppName})
            raw_data = urllib.request.urlopen(req).read()
            result = image.loadFromData(raw_data)
            if result:
                ba = QtCore.QByteArray()
                buffer = QtCore.QBuffer(ba)
                buffer.open(QtCore.QIODevice.WriteOnly)

                if image.height() > self.HEIGHT:
                    image = image.scaled(self.HEIGHT, self.HEIGHT,
                            Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image.save(buffer, 'png')

                self.cache.set(ColnectCache.Image, url, ba)
        except:
            pass

        return image

    @waitCursorDecorator
    def _getFullImage(self, image_id, name):
        data = None

        if not image_id:
            return data

        url = self._imageUrl(image_id, name, True)
        req = urllib.request.Request(url,
                                     headers={'User-Agent': version.AppName})
        try:
            data = urllib.request.urlopen(req).read()
        except:
            pass

        return data

    def _imageUrl(self, image_id, name, full):
        name = self._urlize(name)
        url = "https://i.colnect.net/%s/%d/%03d/%s.jpg" % (
            ('f' if full else 't'), image_id / 1000, image_id % 1000, name)
#            ('b' if full else 't'), image_id / 1000, image_id % 1000, name)
        return url

    def _itemUrl(self, category, item_id):
        url = "https://colnect.com/%s/%s/%s/%d" % (self.lang, category,
                                                   category[:-1], item_id)
        return url

    def _urlize(self, name):
        # change HTML elements to underscore
        name = re.sub(r"&[^;]+;", '_', name)

        name = re.sub(r"[.\"><\\:/?#\[\]@!$&'()\*\+,;=]", '', name)
        name = re.sub(r"[^\x00-\x7F]", '', name)

        # any space sequence becomes a single underscore
        name = re.sub(r"[\s_]+", '_', name)

        name = name.strip('_')

        return name

    def clicked(self, button):
        if button == self.addButton:
            index = self.table.currentIndex()
            self.addCoin(index, False)
        elif button == self.addCloseButton:
            index = self.table.currentIndex()
            self.addCoin(index, True)

            self.accept()
        else:
            self.accept()

    def accept(self):
        self.settings.save()
        self.cache.close()
        super().accept()
