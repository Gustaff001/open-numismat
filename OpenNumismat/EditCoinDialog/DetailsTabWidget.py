# -*- coding: utf-8 -*-

import re

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDoubleValidator, QDesktopServices
from PySide6.QtWidgets import *

from OpenNumismat.EditCoinDialog.FormItems import DoubleValidator, GraderLineEdit, NativeYearEdit
from OpenNumismat.EditCoinDialog.BaseFormLayout import BaseFormLayout, BaseFormGroupBox, ImageFormLayout
from OpenNumismat.EditCoinDialog.BaseFormLayout import DesignFormLayout, FormItem
from OpenNumismat.EditCoinDialog.YearCalculator import YearCalculatorDialog
from OpenNumismat.Collection.CollectionFields import FieldTypes as Type
from OpenNumismat.Collection.CollectionFields import ImageFields
from OpenNumismat.Collection.CollectionFields import TitleTemplateFields
from OpenNumismat.Tools.Converters import numberWithFraction, stringToMoney
from OpenNumismat.Settings import Settings
from OpenNumismat.EditCoinDialog.MapWidget import get_map_widget
from OpenNumismat.TagsDialog import TagsDialog, TagsTreeWidget


class DetailsTabWidget(QTabWidget):
    Stretch = 'stretch item'

    def __init__(self, model, direction, parent=None):
        super().__init__(parent)

        self.direction = direction
        self.model = model
        self.reference = model.reference
        self.settings = model.settings
        self.map_item = None
        self.tags_item = None
        # pas
        self.uid = None
        # self.rec = None
        self.quantity = None
        self.totalsum = None

        self.createItems()
        self.createPages()

    def createPages(self):
        self.createCoinPage()
        self.createTrafficPage()
        if self.settings['tags_used']:
            self.createTagsPage()
        self.createMapPage()
        self.createParametersPage()
        self.createDesignPage()
        self.createClassificationPage()

    def createCoinPage(self):
        main = self.mainDetailsLayout()
        state = self.stateLayout()
        title = self.settings['coin_group_title']
        price = self.priceLayout()
        self.addTabPage(title, [main, self.Stretch, state, price])

    def createTagsPage(self):
        self.tags_item = self.tagsLayout()
        title = self.settings['tags_group_title']

        self.addTabPage(title, [self.tags_item, ])

    def createMapPage(self):
        coordinates = self.coordinatesLayout()
        if not coordinates.isEmpty():
            title = self.settings['map_group_title']
            map_ = self.mapLayout()
            if map_:
                self.addTabPage(title, [coordinates, self.Stretch, map_])
            else:
                self.addTabPage(title, [coordinates, ])

    def createTrafficPage(self):
        title = self.settings['market_group_title']
        self.addTabPage(title, [])

    def createParametersPage(self):
        parameters = self.parametersLayout()
        minting = self.mintingLayout()
        specificity = self.specificityLayout()
        note = self.noteLayout()

        if not parameters.isEmpty() or not minting.isEmpty() or not note.isEmpty():
            title = self.settings['parameters_group_title']
            self.addTabPage(title, [parameters, specificity, self.Stretch, minting, note])

    def createDesignPage(self):
        obverse = self.obverseDesignLayout()
        reverse = self.reverseDesignLayout()
        edge = self.edgeDesignLayout()
        subject = self.subjectLayout()

        if not obverse.isEmpty() or not reverse.isEmpty() or not edge.isEmpty() or not subject.isEmpty():
            title = self.settings['design_group_title']
            self.addTabPage(title, [obverse, reverse, self.Stretch, edge, subject])

    def createClassificationPage(self):
        catalogue = self.catalogueLayout()
        rarity = self.rarityLayout()
        # price = self.priceLayout()
        variation = self.variationLayout()
        url = self.urlLayout()

        if not catalogue.isEmpty() or not rarity.isEmpty() or not variation.isEmpty() or not url.isEmpty():
            title = self.settings['classification_group_title']
            self.addTabPage(title, [catalogue, rarity, url, self.Stretch,
                                    variation])

    def _layoutToWidget(self, layout):
        widget = QWidget(self)
        widget.setLayout(layout)
        return widget

    def createTabPage(self, parts):
        # Remove all empty parts
        for part in parts:
            if isinstance(part, BaseFormGroupBox):
                if part.isEmpty():
                    parts.remove(part)

        if self.direction == QBoxLayout.LeftToRight:
            newParts = []
            layout = QVBoxLayout()
            stretchNeeded = True
            count = 0
            for part in parts:
                if part == self.Stretch:
                    if count > 0:
                        newParts.append(layout)
                        if stretchNeeded:
                            layout.insertStretch(-1)
                        layout = QVBoxLayout()
                    stretchNeeded = True
                    count = 0
                else:
                    if isinstance(part, QWidget):
                        layout.addWidget(part)
                        if part.sizePolicy().verticalPolicy() in (QSizePolicy.Preferred, QSizePolicy.Expanding):
                            stretchNeeded = False
                    else:
                        layout.addLayout(part)
                    count += 1
            if count > 0:
                newParts.append(layout)
                if stretchNeeded:
                    layout.insertStretch(-1)
            parts = newParts
        else:
            for part in parts:
                if part == self.Stretch:
                    parts.remove(part)

        pageLayout = QBoxLayout(self.direction, self)
        # Fill layout with it's parts
        stretchNeeded = True
        for part in parts:
            if isinstance(part, QWidget):
                pageLayout.addWidget(part)
                if part.sizePolicy().verticalPolicy() in (QSizePolicy.Preferred, QSizePolicy.Expanding):
                    stretchNeeded = False
            else:
                pageLayout.addLayout(part)
                if isinstance(part, ImageFormLayout):
                    stretchNeeded = False

        if self.direction == QBoxLayout.TopToBottom and stretchNeeded:
            pageLayout.insertStretch(-1)

        return self._layoutToWidget(pageLayout)

    def addTabPage(self, title, parts):
        page = self.createTabPage(parts)
        self.addTab(page, title)

    def addItem(self, field):
        # Skip image fields for not a form
        if field.type in Type.ImageTypes:
            return

        item = FormItem(self.settings, field.name, field.title,
                        field.type | Type.Disabled, reference=self.reference)
        if not field.enabled:
            item.setHidden()
        self.items[field.name] = item

    def createItems(self):
        self.items = {}

        fields = self.model.fields
        for field in fields:
            if field not in fields.systemFields:
                self.addItem(field)

    def fillItems(self, record):
        if not record.isEmpty():
            # pas
            # self.rec = record
            self.uid = record.value('uid')

            # Fields with commission dependent on status field and should be
            # filled after it and in right order
            ordered_item_keys = ('status', 'payprice', 'totalpayprice',
                                 'saleprice', 'totalsaleprice',
                                 'region', 'country')
            for key in ordered_item_keys:
                if key in self.items:
                    item = self.items[key]
                    self._fillItem(record, item)

            for item in self.items.values():
                if item.field() in ordered_item_keys:
                    continue

                self._fillItem(record, item)

            if self.map_item:
                lat = record.value('latitude')
                lng = record.value('longitude')
                self.map_item.setMarker(lat, lng)

            if self.tags_item:
                self.tags_item.fill(record)

    def _calcPaySaleStat(self):
        from PySide6.QtSql import QSqlQuery
        query = QSqlQuery()
        query.prepare("""select coin_id,
                                round(sum(cost*quantity*(case oper_name when 'Продал' then 1 else -1 end)),2) as ts,
                                sum(quantity*(case oper_name when 'Продал' then -1 else 1 end)) as tq
                                from coins_paysales
                                where coin_id = ?
                                group by coin_id""")
        query.addBindValue(self.uid)
        query.exec_()
        ts = tq = 0
        while query.next():
            record = query.record()
            ts = record.value('ts')
            tq = record.value('tq')
        return tq, ts

    def _fillItem(self, record, item):
        if not record.isNull(item.field()):
            # pas
            if item.field() == 'quantity':
                _tq, _ts = self._calcPaySaleStat()
                value = _tq
            elif item.field() == 'totalsum':
                _tq, _ts = self._calcPaySaleStat()
                value = _ts
            else:
                value = record.value(item.field())
            item.setValue(value)
        else:
            item.widget().clear()

    def clear(self):
        for item in self.items.values():
            item.widget().clear()

    def mainDetailsLayout(self):
        title = self.settings['coin_main_group_title']
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['category'])
        layout.addRow(self.items['title'])
        layout.addRow(self.items['region'])
        layout.addRow(self.items['country'])
        layout.addRow(self.items['period'])
        layout.addRow(self.items['emitent'])
        layout.addRow(self.items['ruler'])
        layout.addRow(self.items['value'], self.items['unit'])
        layout.addRow(self.items['year'], self.items['native_year'])
        layout.addRow(self.items['mintmark'], self.items['mint'])
        layout.addRow(self.items['type'])
        layout.addRow(self.items['series'])
        layout.addRow(self.items['subjectshort'])

        return layout

    def stateLayout(self):
        title = self.settings['coin_state_group_title']
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['status'], self.items['grade'])
        self.items['status'].widget().currentIndexChanged.connect(self.indexChangedState)
        layout.addRow(self.items['rating'])
        # pas
        self.quantity = self.items['quantity']
        self.totalsum = self.items['totalsum']

        layout.addRow(self.quantity, self.items['format'])
        layout.addRow(self.totalsum)
        layout.addRow(self.items['condition'])
        layout.addRow(self.items['seat'], self.items['storage'])
        layout.addRow(self.items['barcode'], self.items['grader'])
        if isinstance(self.items['grader'].widget(), GraderLineEdit):
            self.items['grader'].widget().clickedButton.connect(self.clickedButtonGrader)
        layout.addRow(self.items['defect'])
        layout.addRow(self.items['features'])

        return layout

    def emptyMarketLayout(self):
        text = QApplication.translate('DetailsTabWidget',
                "Nothing to show. Change the coin status on previous tab")
        label = QLabel(text)
        layout = QHBoxLayout()
        layout.addWidget(label)

        return layout

    # def payLayout(self):
    #     title = self.settings['market_buy_group_title']
    #     layout = BaseFormGroupBox(title)
    #
    #     layout.addRow(self.items['paydate'], self.items['payprice'])
    #
    #     # Add auxiliary field
    #     if self.items['payprice'].hidden or self.items['totalpayprice'].hidden:
    #         item = None
    #     else:
    #         item = self.addPayCommission()
    #
    #     layout.addRow(self.items['totalpayprice'], item)
    #     layout.addRow(self.items['saller'])
    #     layout.addRow(self.items['payplace'])
    #     layout.addRow(self.items['buying_invoice'])
    #     layout.addRow(self.items['payinfo'])
    #
    #     return layout

    # def saleLayout(self):
    #     title = self.settings['market_sale_group_title']
    #     layout = BaseFormGroupBox(title)
    #
    #     layout.addRow(self.items['saledate'], self.items['saleprice'])
    #
    #     # Add auxiliary field
    #     if self.items['saleprice'].hidden or self.items['totalsaleprice'].hidden:
    #         item = None
    #     else:
    #         item = self.addSaleCommission()
    #
    #     layout.addRow(self.items['totalsaleprice'], item)
    #     layout.addRow(self.items['buyer'])
    #     layout.addRow(self.items['saleplace'])
    #     layout.addRow(self.items['sale_invoice'])
    #     layout.addRow(self.items['saleinfo'])
    #
    #     return layout

    # pas
    def paySaleLayout(self, uid):
        from OpenNumismat.PaySaleModule import PaySaleLayout

        title = self.settings['market_paysale_group_title']

        places = self.reference.section('place')

        #
        _t1 = self.quantity
        _t2 = self.totalsum
        # _r = self.rec
        _f = type(self).__name__
        #

        layout = PaySaleLayout(title, uid, places, _f, _t1, _t2)

        return layout

    def passLayout(self):
        title = QApplication.translate('DetailsTabWidget', "Pass")
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['saledate'], self.items['saleprice'])

        # Add auxiliary field
        if self.items['saleprice'].hidden or self.items['totalpayprice'].hidden:
            item = None
        else:
            item = self.addPayCommission()
        layout.addRow(self.items['totalpayprice'], item)
        self.items['saleprice'].widget().textChanged.connect(self.items['payprice'].widget().setText)

        # Add auxiliary field
        if self.items['saleprice'].hidden or self.items['totalsaleprice'].hidden:
            item = None
        else:
            item = self.addSaleCommission()
        layout.addRow(self.items['totalsaleprice'], item)

        layout.addRow(self.items['saller'])
        layout.addRow(self.items['buyer'])
        layout.addRow(self.items['saleplace'])
        layout.addRow(self.items['saleinfo'])

        return layout

    def parametersLayout(self):
        title = self.settings['parameters_parameters_group_title']
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['composition'])
        layout.addRow(self.items['material'], self.items['material2'])
        layout.addRow(self.items['fineness'], self.items['weight'])
        layout.addRow(self.items['diameter'], self.items['thickness'])
        layout.addRow(self.items['width'], self.items['height'])
        layout.addRow(self.items['shape'], self.items['obvrev'])

        return layout

    def specificityLayout(self):
        title = self.settings['parameters_specificity_group_title']
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['modification'])
        layout.addRow(self.items['real_diameter'], self.items['real_weight'])

        item = self.items['axis']
        layout.addHalfRow(item)
        item.widget().setSizePolicy(QSizePolicy.Preferred,
                                    QSizePolicy.Fixed)

        return layout

    def mintingLayout(self):
        title = self.settings['parameters_minting_group_title']
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['issuedate'], self.items['mintage'])
        layout.addRow(self.items['dateemis'])

        layout.addRow(self.items['quality'], self.items['technique'])

        return layout

    def noteLayout(self):
        layout = BaseFormLayout()

        layout.addRow(self.items['note'])

        return layout

    def obverseDesignLayout(self):
        title = self.settings['design_obverse_group_title']
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['obversedesign'])
        layout.addRow(self.items['obversedesigner'])
        layout.addRow(self.items['obverseengraver'])
        layout.addRow(self.items['obversecolor'])

        return layout

    def reverseDesignLayout(self):
        title = self.settings['design_reverse_group_title']
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['reversedesign'])
        layout.addRow(self.items['reversedesigner'])
        layout.addRow(self.items['reverseengraver'])
        layout.addRow(self.items['reversecolor'])

        return layout

    def edgeDesignLayout(self):
        title = self.settings['design_edge_group_title']
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['edge'])
        layout.addRow(self.items['edgelabel'])

        layout.addRow(self.items['signaturetype'])
        layout.addRow(self.items['signature'])

        return layout

    def subjectLayout(self):
        layout = BaseFormLayout()

        layout.addRow(self.items['subject'])

        return layout

    def rarityLayout(self):
        layout = BaseFormLayout()

        item = self.items['rarity']
        layout.addHalfRow(item)
        item.widget().setSizePolicy(QSizePolicy.Preferred,
                                    QSizePolicy.Fixed)

        return layout

    def catalogueLayout(self):
        title = self.settings['classification_catalogue_group_title']
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['catalognum1'], self.items['catalognum2'])
        layout.addRow(self.items['catalognum3'], self.items['catalognum4'])

        return layout

    def priceLayout(self):
        title = self.settings['classification_price_group_title']
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['price4'], self.items['price3'])
        layout.addRow(self.items['price2'], self.items['price1'])

        return layout

    def variationLayout(self):
        title = self.settings['classification_variation_group_title']
        layout = BaseFormGroupBox(title)

        layout.addRow(self.items['variety'])
        item = self.items['varietydesc']
        layout.addRow(item)
        item.widget().setSizePolicy(QSizePolicy.Preferred,
                                    QSizePolicy.Minimum)
        layout.addRow(self.items['obversevar'], self.items['reversevar'])
        layout.addHalfRow(self.items['edgevar'])

        return layout

    def urlLayout(self):
        layout = BaseFormLayout()
        layout.setAlignment(Qt.AlignTop)

        layout.addRow(self.items['url'])

        return layout

    def tagsLayout(self):
        self.tags_item = TagsTreeWidget(self.model.database(), True, self)
        return self.tags_item

    def coordinatesLayout(self):
        layout = BaseFormLayout()

        layout.addRow(self.items['address'])
        layout.addRow(self.items['latitude'], self.items['longitude'])

        return layout

    def mapLayout(self):
        self.map_item = None

        coordinates_enabled = not (self.items['latitude'].isHidden() or
                                   self.items['longitude'].isHidden())

        if coordinates_enabled:
            settings = Settings()
            self.map_item = get_map_widget(self, settings['map_type'], False)

        return self.map_item

    def _createTrafficParts(self, status, uid):
        stretch_widget = QWidget()
        stretch_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.payCommission = None
        self.saleCommission = None

        pageParts = []
        if status == 'pass':
            pass_ = self.passLayout()
            pageParts.extend([pass_, self.Stretch, stretch_widget])
        elif status in ('owned', 'ordered', 'sale', 'missing',
                        'bidding', 'duplicate', 'replacement'):
            # pay = self.payLayout()
            # pageParts.extend([pay, self.Stretch, stretch_widget])
            pay_sale = self.paySaleLayout(uid)
            pageParts.extend([pay_sale, self.Stretch, stretch_widget])
        elif status == 'sold':
            # pay = self.payLayout()
            # sale = self.saleLayout()
            # pageParts.extend([pay, self.Stretch, sale])
            pay_sale = self.paySaleLayout(uid)
            pageParts.extend([pay_sale, self.Stretch, stretch_widget])
        else:
            layout = self.emptyMarketLayout()
            pageParts.append(layout)

        return pageParts

    def indexChangedState(self, index):
        pageIndex = self.currentIndex()

        self.removeTab(1)
        status = self.items['status'].widget().currentData()
        # pas
        uid = self.uid
        pageParts = self._createTrafficParts(status, uid)
        page = self.createTabPage(pageParts)

        title = self.settings['market_group_title']
        self.insertTab(1, page, title)
        self.setCurrentIndex(pageIndex)
        
    def clickedButtonGrader(self):
        grader = self.items['grader'].value().upper()
        barcode = self.items['barcode'].value()
        grade = self.items['grade'].value()
        grade = ''.join(filter(lambda i: i.isdigit(), grade))
        if grader == 'ANACS':
            url = 'https://www.anacs.com/Verify/CertVerification.aspx?cert=%s' % barcode
        elif grader == 'ICCS':
            url = 'https://iccscoin.ca'
        elif grader == 'ICG':
            url = 'https://www.icgcoin.com/load_SNSearch.php?ctn=%s' % barcode
        elif grader == 'NGC':
            url = 'https://www.ngccoin.com/certlookup/%s/%s/' % (barcode, grade)
        elif grader == 'PCGS':
            url = 'https://www.pcgs.com/cert/%s' % barcode
        elif grader == 'PMG':
            url = 'https://www.pmgnotes.com/certlookup/%s/%s' % (barcode, grade)
        elif grader == 'RNGA':
            url = 'https://rngacoin.ru/rnga-data-base/%s.html' % barcode
        elif grader == 'ННР':
            url = 'https://nreestr.ru/coins/search/%s' % barcode
        else:
            return

        executor = QDesktopServices()
        executor.openUrl(QUrl(url))

    def addPayCommission(self):
        title = QApplication.translate('DetailsTabWidget', "Commission")
        item = FormItem(self.settings, None, title, Type.Money | Type.Disabled)
        self.payCommission = item.widget()

        self.items['payprice'].widget().textChanged.connect(self.payPriceChanged)
        self.items['totalpayprice'].widget().textChanged.connect(self.payPriceChanged)

        return item

    def payPriceChanged(self, text):
        if self.payCommission:
            totalPriceValue = self.items['totalpayprice'].value()
            if totalPriceValue:
                price = textToFloat(self.items['payprice'].value())
                totalPrice = textToFloat(totalPriceValue)
                self.payCommission.setText(floatToText(totalPrice - price))
            else:
                self.payCommission.setText('')

    def addSaleCommission(self):
        title = QApplication.translate('DetailsTabWidget', "Commission")
        item = FormItem(self.settings, None, title, Type.Money | Type.Disabled)
        self.saleCommission = item.widget()

        self.items['saleprice'].widget().textChanged.connect(self.salePriceChanged)
        self.items['totalsaleprice'].widget().textChanged.connect(self.salePriceChanged)

        return item

    def salePriceChanged(self, text):
        if self.saleCommission:
            totalPriceValue = self.items['totalsaleprice'].value()
            if totalPriceValue:
                price = textToFloat(self.items['saleprice'].value())
                totalPrice = textToFloat(totalPriceValue)
                self.saleCommission.setText(floatToText(price - totalPrice))
            else:
                self.saleCommission.setText('')


class FormDetailsTabWidget(DetailsTabWidget):
    def __init__(self, model, parent=None, usedFields=None):
        self.usedFields = usedFields

        super().__init__(model, QBoxLayout.TopToBottom, parent)

    def createPages(self):
        self.createCoinPage()
        self.oldStatus = 'demo'
        self.createTrafficPage()
        if self.settings['tags_used']:
            self.createTagsPage()
        self.createMapPage()
        self.createParametersPage()
        self.createDesignPage()
        self.createClassificationPage()
        self.createImagePage()

    def createTagsPage(self):
        tags = self.tagsLayout()
        title = self.settings['tags_group_title']

        btn = QPushButton(self.tr("Edit..."))
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.clicked.connect(self.clickEditTags)

        self.addTabPage(title, [tags, btn])

    def tagsLayout(self):
        self.tags_item = TagsTreeWidget(self.model.database(), False, self)
        return self.tags_item

    def clickEditTags(self):
        dialog = TagsDialog(self.model.database(), self)
        res = dialog.exec_()
        if res == QDialog.Accepted:
            self.tags_item.update()
            self.model.tagsChanged.emit()

    def createImagePage(self):
        images = self.imagesLayout()
        if not images.isEmpty():
            self.addTabPage(self.settings['images_group_title'], [images, ])

    def addItem(self, field):
        checkable = 0
        if self.usedFields:
            checkable = Type.Checkable

        section = None
        if self.reference:
            section = self.reference.section(field.name)

        item = FormItem(self.settings, field.name, field.title,
                        field.type | checkable, section=section)
        if not field.enabled:
            item.setHidden()
        self.items[field.name] = item

    def createItems(self):
        super().createItems()

        if self.reference:
            if self.reference.section('country'):
                country = self.items['country'].widget()
                if self.reference.section('region'):
                    region = self.items['region'].widget()
                    region.addDependent(country)
                if self.reference.section('period'):
                    country.addDependent(self.items['period'].widget())
                if self.reference.section('emitent'):
                    country.addDependent(self.items['emitent'].widget())
                if self.reference.section('ruler'):
                    country.addDependent(self.items['ruler'].widget())
                if self.reference.section('unit'):
                    country.addDependent(self.items['unit'].widget())
                if self.reference.section('mint'):
                    country.addDependent(self.items['mint'].widget())
                if self.reference.section('series'):
                    country.addDependent(self.items['series'].widget())

        for image_field_src in ImageFields:
            for image_field_dst in ImageFields:
                if image_field_dst != image_field_src:
                    if not self.items[image_field_dst].isHidden():
                        src = self.items[image_field_src].widget()
                        dst = self.items[image_field_dst].widget()
                        title = self.items[image_field_dst].title()
                        src.connectExchangeAct(dst, title)

    def fillItems(self, record):
        super().fillItems(record)

        if self.usedFields:
            for item in self.items.values():
                if self.usedFields[record.indexOf(item.field())] == Qt.Checked:
                    item.label().setCheckState(Qt.Checked)

        for image_field in ImageFields:
            title = record.value(image_field + '_title')
            if title:
                self.items[image_field].widget().setTitle(title)

    def mainDetailsLayout(self):
        title = self.settings['coin_main_group_title']
        layout = BaseFormGroupBox(title)
        layout.layout.columnCount = 6

        layout.addRow(self.items['category'])

        btn = QPushButton(self.tr("Generate"))
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.clicked.connect(self.clickGenerateTitle)
        layout.addRow(self.items['title'], btn)

        layout.addRow(self.items['region'])
        layout.addRow(self.items['country'])
        layout.addRow(self.items['period'])
        layout.addRow(self.items['emitent'])
        layout.addRow(self.items['ruler'])
        layout.addRow(self.items['value'], self.items['unit'])
        layout.addRow(self.items['year'], self.items['native_year'])
        layout.addRow(self.items['mintmark'], self.items['mint'])
        layout.addRow(self.items['type'])
        layout.addRow(self.items['series'])
        layout.addRow(self.items['subjectshort'])

        if not self.items['year'].isHidden() and not self.items['native_year'].isHidden():
            native_year_widget = self.items['native_year'].widget()
            if isinstance(native_year_widget, NativeYearEdit):
                native_year_widget.clickedButton.connect(self.clickedButtonNativeYear)

        return layout

    def obverseDesignLayout(self):
        title = self.settings['design_obverse_group_title']
        layout = DesignFormLayout(title)
        layout.defaultHeight = 60

        layout.addImage(self.items['obverseimg'])
        layout.addRow(self.items['obversedesign'])
        layout.addRow(self.items['obversedesigner'])
        layout.addRow(self.items['obverseengraver'])
        layout.addRow(self.items['obversecolor'])

        return layout

    def reverseDesignLayout(self):
        title = self.settings['design_reverse_group_title']
        layout = DesignFormLayout(title)
        layout.defaultHeight = 60

        layout.addImage(self.items['reverseimg'])
        layout.addRow(self.items['reversedesign'])
        layout.addRow(self.items['reversedesigner'])
        layout.addRow(self.items['reverseengraver'])
        layout.addRow(self.items['reversecolor'])

        return layout

    def edgeDesignLayout(self):
        title = self.settings['design_edge_group_title']
        layout = DesignFormLayout(title)

        layout.addImage(self.items['edgeimg'], 2)
        layout.addRow(self.items['edge'])
        layout.addRow(self.items['edgelabel'])

        layout.addImage(self.items['signatureimg'], 2)
        layout.addRow(self.items['signaturetype'])
        layout.addRow(self.items['signature'])

        return layout

    def variationLayout(self):
        title = self.settings['classification_variation_group_title']
        layout = DesignFormLayout(title)

        layout.addImage(self.items['varietyimg'], 2)
        layout.addRow(self.items['variety'])
        item = self.items['varietydesc']
        layout.addRow(item)
        item.widget().setSizePolicy(QSizePolicy.Preferred,
                                    QSizePolicy.Minimum)
        layout.addRow(self.items['obversevar'], self.items['reversevar'])
        layout.addHalfRow(self.items['edgevar'])

        return layout

    def mapLayout(self):
        self.map_item = None

        coordinates_enabled = not (self.items['latitude'].isHidden() or
                                   self.items['longitude'].isHidden())

        if coordinates_enabled:
            settings = Settings()
            self.map_item = get_map_widget(self, settings['map_type'], False, False)

            self.map_item.markerMoved.connect(self.mapMarkerMoved)
            self.map_item.markerRemoved.connect(self.mapMarkerRemoved)
            self.items['address'].widget().findClicked.connect(self.map_item.geocode)
            self.items['latitude'].widget().textChanged.connect(self.mapChanged)
            self.items['longitude'].widget().textChanged.connect(self.mapChanged)

        return self.map_item

    def mapChanged(self):
        lat = textToFloat(self.items['latitude'].value())
        lng = textToFloat(self.items['longitude'].value())
        self.map_item.moveMarker(lat, lng)

    def mapMarkerMoved(self, lat, lng, address_changed):
        self.items['latitude'].widget().textChanged.disconnect(self.mapChanged)
        self.items['longitude'].widget().textChanged.disconnect(self.mapChanged)

        self.items['latitude'].setValue("%.4f" % lat)
        self.items['longitude'].setValue("%.4f" % lng)
        if address_changed:
            address = self.map_item.reverseGeocode(lat, lng)
            self.items['address'].setValue(address)

        self.items['latitude'].widget().textChanged.connect(self.mapChanged)
        self.items['longitude'].widget().textChanged.connect(self.mapChanged)

    def mapMarkerRemoved(self):
        self.items['latitude'].widget().textChanged.disconnect(self.mapChanged)
        self.items['longitude'].widget().textChanged.disconnect(self.mapChanged)

        self.items['latitude'].clear()
        self.items['longitude'].clear()

        self.items['latitude'].widget().textChanged.connect(self.mapChanged)
        self.items['longitude'].widget().textChanged.connect(self.mapChanged)

    def imagesLayout(self):
        layout = ImageFormLayout()
        layout.addImages([self.items['photo1'], self.items['photo2'],
                          self.items['photo3'], self.items['photo4'],
                          self.items['photo5'], self.items['photo6']])
        return layout

    def clickGenerateTitle(self):
        template = self.settings['title_template']
        title = template
        for field in TitleTemplateFields:
            if '<' + field + '>' in template:
                value = self.items[field].value()
                if not isinstance(value, str):
                    value = str(value)
                value = value.strip()
                if value:
                    if field == 'unit':
                        value = value.lower()
                    elif field == 'value':
                        value, _ = numberWithFraction(value, self.settings['convert_fraction'])
                    elif field == 'subjectshort':
                        if len(value.split()) > 1:
                            value = '"' + value + '"'

                title = title.replace('<' + field + '>', value)

        title = re.sub(' +', ' ', title)
        self.items['title'].setValue(title)
        
    def clickedButtonNativeYear(self):
        year = self.items['year'].widget().text()
        native_year = self.items['native_year'].widget().text()
        country = self.items['country'].widget().text()
        if country == self.tr("Israel"):
            calendar = YearCalculatorDialog.CALENDARS.HEBREW
        elif country in (self.tr("Bahrain"), self.tr("Jordan"), self.tr("Iraq"),
                         self.tr("Yemen"), self.tr("Qatar"), self.tr("Kuwait"),
                         self.tr("Maldives"), self.tr("Oman"), self.tr("Syria"),
                         self.tr("United Arab Emirates"), self.tr("Saudi Arabia"),
                         self.tr("Turkey"), self.tr("Algeria"), self.tr("Egypt"),
                         self.tr("Libya"), self.tr("Mauritania"),
                         self.tr("Morocco"), self.tr("Sudan"), self.tr("Tunisia")):
            calendar = YearCalculatorDialog.CALENDARS.ISLAMIC
        elif country in (self.tr("Afghanistan"), self.tr("Iran")):
            calendar = YearCalculatorDialog.CALENDARS.SOLAR_HIJRI
        elif country == self.tr("Japan"):
            calendar = YearCalculatorDialog.CALENDARS.JAPAN
        elif country in (self.tr("Nepal"), self.tr("India")):
            calendar = YearCalculatorDialog.CALENDARS.NEPAL
        elif country == self.tr("Thailand"):
            calendar = YearCalculatorDialog.CALENDARS.THAI
        elif country in (self.tr("Burma"), self.tr("Myanmar")):
            calendar = YearCalculatorDialog.CALENDARS.BURMESE
        else:
            calendar = YearCalculatorDialog.CALENDARS.DEFAULT
        dlg = YearCalculatorDialog(year, native_year, calendar, self)
        if dlg.exec_() == QDialog.Accepted:
            self.items['year'].widget().setText(dlg.year())
            self.items['native_year'].widget().setText(dlg.nativeYear())

    def _createTrafficParts(self, status, uid):
        if self.oldStatus == 'pass':
            if self.payCommission:
                self.items['payprice'].widget().textChanged.disconnect(self.payCommissionChanged)
                self.items['totalpayprice'].widget().textChanged.disconnect(self.payTotalPriceChanged)
                self.payCommission.textChanged.disconnect(self.payCommissionChanged)
            if self.saleCommission:
                self.items['saleprice'].widget().textChanged.disconnect(self.saleCommissionChanged)
                self.items['totalsaleprice'].widget().textChanged.disconnect(self.saleTotalPriceChanged)
                self.saleCommission.textChanged.disconnect(self.saleCommissionChanged)
                self.items['saleprice'].widget().textChanged.disconnect(self.items['payprice'].widget().setText)
        elif self.oldStatus in ('owned', 'ordered', 'sale', 'missing',
                                'bidding', 'duplicate', 'replacement'):
            if self.payCommission:
                self.items['payprice'].widget().textChanged.disconnect(self.payCommissionChanged)
                self.items['totalpayprice'].widget().textChanged.disconnect(self.payTotalPriceChanged)
                self.payCommission.textChanged.disconnect(self.payCommissionChanged)
        elif self.oldStatus == 'sold':
            if self.payCommission:
                self.items['payprice'].widget().textChanged.disconnect(self.payCommissionChanged)
                self.items['totalpayprice'].widget().textChanged.disconnect(self.payTotalPriceChanged)
                self.payCommission.textChanged.disconnect(self.payCommissionChanged)
            if self.saleCommission:
                self.items['saleprice'].widget().textChanged.disconnect(self.saleCommissionChanged)
                self.items['totalsaleprice'].widget().textChanged.disconnect(self.saleTotalPriceChanged)
                self.saleCommission.textChanged.disconnect(self.saleCommissionChanged)
        else:
            pass

        pageParts = super()._createTrafficParts(status, uid)

        self.oldStatus = status

        return pageParts

    def indexChangedState(self, index):
        super().indexChangedState(index)

        if self.oldStatus in ('owned', 'ordered', 'sale', 'missing',
                              'bidding', 'duplicate', 'replacement'):
            self.payPriceChanged('')
        elif self.oldStatus in ('sold', 'pass'):
            self.payPriceChanged('')
            self.salePriceChanged('')

    def addPayCommission(self):
        item = FormItem(self.settings, None, self.tr("Commission"), Type.Money)
        self.payCommission = item.widget()
        self.payCommission.setToolTip(self.tr("Available format 12.5 or 10%"))

        validator = CommissionValidator(0, 9999999999., 2, self)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.payCommission.setValidator(validator)

        self.items['payprice'].widget().textChanged.connect(self.payCommissionChanged)
        self.payCommission.textChanged.connect(self.payCommissionChanged)
        self.items['totalpayprice'].widget().textChanged.connect(self.payTotalPriceChanged)

        return item

    def addSaleCommission(self):
        item = FormItem(self.settings, None, self.tr("Commission"), Type.Money)
        self.saleCommission = item.widget()
        self.saleCommission.setToolTip(self.tr("Available format 12.5 or 10%"))

        validator = CommissionValidator(0, 9999999999., 2, self)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.saleCommission.setValidator(validator)

        self.items['saleprice'].widget().textChanged.connect(self.saleCommissionChanged)
        self.saleCommission.textChanged.connect(self.saleCommissionChanged)
        self.items['totalsaleprice'].widget().textChanged.connect(self.saleTotalPriceChanged)

        return item

    def payCommissionChanged(self, text):
        self.items['totalpayprice'].widget().textChanged.disconnect(self.payTotalPriceChanged)

        price = textToFloat(self.items['payprice'].value())
        text = self.payCommission.text().strip()
        if len(text) > 0 and text[-1] == '%':
            commission = price * textToFloat(text[0:-1]) / 100
        else:
            commission = textToFloat(text)
        self.items['totalpayprice'].widget().setText(floatToText(price + commission))

        self.items['totalpayprice'].widget().textChanged.connect(self.payTotalPriceChanged)

    def payTotalPriceChanged(self, text):
        self.payCommission.textChanged.disconnect(self.payCommissionChanged)

        if text:
            price = textToFloat(self.items['payprice'].value())
            totalPrice = textToFloat(self.items['totalpayprice'].value())
            self.payCommission.setText(floatToText(totalPrice - price))
        else:
            self.payCommission.clear()

        self.payCommission.textChanged.connect(self.payCommissionChanged)

    def saleCommissionChanged(self, text):
        self.items['totalsaleprice'].widget().textChanged.disconnect(self.saleTotalPriceChanged)

        price = textToFloat(self.items['saleprice'].value())
        text = self.saleCommission.text().strip()
        if len(text) > 0 and text[-1] == '%':
            commission = price * textToFloat(text[0:-1]) / 100
        else:
            commission = textToFloat(text)
        self.items['totalsaleprice'].widget().setText(floatToText(price - commission))

        self.items['totalsaleprice'].widget().textChanged.connect(self.saleTotalPriceChanged)

    def saleTotalPriceChanged(self, text):
        self.saleCommission.textChanged.disconnect(self.saleCommissionChanged)

        if text:
            price = textToFloat(self.items['saleprice'].value())
            totalPrice = textToFloat(self.items['totalsaleprice'].value())
            self.saleCommission.setText(floatToText(price - totalPrice))
        else:
            self.saleCommission.clear()

        self.saleCommission.textChanged.connect(self.saleCommissionChanged)


def textToFloat(text):
    if text:
        return stringToMoney(text)
    else:
        return 0


def floatToText(value):
    if value > 0:
        return str(int((value) * 100 + 0.5) / 100)
    else:
        return str(int((value) * 100 - 0.5) / 100)


# Reimplementing DoubleValidator for replace comma with dot and accept %
class CommissionValidator(DoubleValidator):
    def validate(self, input_, pos):
        hasPercent = False
        numericValue = input_
        if len(input_) > 0 and input_[-1] == '%':
            numericValue = input_[0:-1]  # trim percent sign
            hasPercent = True
        state, validatedValue, pos = super().validate(numericValue, pos)
        if hasPercent:
            validatedValue = validatedValue + '%'  # restore percent sign
        return state, validatedValue, pos
