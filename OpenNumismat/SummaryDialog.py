# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QDate, QLocale
from PyQt6.QtSql import QSqlQuery
from PyQt6.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QDialogButtonBox

from OpenNumismat.Tools.DialogDecorators import storeDlgSizeDecorator
from OpenNumismat.Tools.Converters import stringToMoney


@storeDlgSizeDecorator
class SummaryDialog(QDialog):

    def __init__(self, model, parent=None):
        super().__init__(parent,
                         Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowSystemMenuHint)

        self.setWindowTitle(self.tr("Summary"))

        buttonBox = QDialogButtonBox(Qt.Orientation.Horizontal)
        buttonBox.addButton(QDialogButtonBox.StandardButton.Ok)
        buttonBox.accepted.connect(self.accept)

        self.textBox = QTextEdit(self)
        self.textBox.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.textBox)
        layout.addWidget(buttonBox)

        self.setLayout(layout)

        lines_all = self.fillSummary(model)
        lines_selected = self.fillSummary(model, model.filter())

        lines = [self.tr("[Selected]")] + lines_selected + ["", self.tr("[All]")] + lines_all
        self.textBox.setText('\n'.join(lines))

    def makeSql(self, sql, filter_):
        if filter_:
            if 'WHERE' in sql:
                sql = "%s AND %s" % (sql, filter_)
            else:
                sql = "%s WHERE %s" % (sql, filter_)

        return sql

    def fillSummary(self, model, filter_=None):
        lines = []
        locale = QLocale.system()

        sql = "SELECT count(*) FROM coins"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        if query.first():
            totalCount = query.record().value(0)
            lines.append(self.tr("Total count: %d") % totalCount)

        count_owned = 0
        quantity_owned = 0
        sql = "SELECT quantity FROM coins WHERE status IN ('owned', 'ordered', 'sale', 'duplicate')"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        while query.next():
            record = query.record()
            quantity = int(record.value('quantity') or 1)
            count_owned += 1
            quantity_owned += quantity
        if count_owned == quantity_owned:
            lines.append(self.tr("Count owned: %d") % count_owned)
        else:
            lines.append(self.tr("Count owned: %d/%d") % (quantity_owned, count_owned))

        count_gold = 0
        quantity_gold = 0
        gold_filter = self.materialFilter("Gold", self.tr("Gold"), "Au")
        sql = "SELECT quantity FROM coins WHERE status IN ('owned', 'ordered', 'sale', 'duplicate') AND " \
                "%s" % gold_filter
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        while query.next():
            record = query.record()
            quantity = int(record.value('quantity') or 1)
            count_gold += 1
            quantity_gold += quantity
        if count_gold:
            if count_gold == quantity_gold:
                lines.append(self.tr("Gold coins: %d") % count_gold)
            else:
                lines.append(self.tr("Gold coins: %d/%d") % (quantity_gold, count_gold))
        
        if count_gold:
            sql = "SELECT fineness, weight, quantity FROM coins WHERE status IN ('owned', 'ordered', 'sale', 'duplicate') AND " \
                    "%s AND " \
                    "ifnull(fineness,'')<>'' AND ifnull(weight,'')<>''" % gold_filter
            sql = self.makeSql(sql, filter_)
            query = QSqlQuery(sql, model.database())
            gold_weight = 0
            gold_count = 0
            gold_quantity = 0
            while query.next():
                record = query.record()
                fineness = record.value('fineness')
                if isinstance(fineness, str):
                    fineness = stringToMoney(fineness)
                if isinstance(fineness, float):
                    if fineness > 1:
                        fineness = str(fineness).replace('.', '')
                    else:
                        fineness = str(fineness).replace('0.', '')
                weight = record.value('weight')
                if isinstance(weight, str):
                    weight = stringToMoney(weight)
                quantity = int(record.value('quantity') or 1)
                gold_weight += weight * float("0.%s" % fineness) * quantity
                gold_count += 1
                gold_quantity += quantity
            if gold_weight:
                if gold_count == gold_quantity:
                    comment = self.tr("(calculated for %d coins)") % gold_quantity
                else:
                    comment = self.tr("(calculated for %d/%d coins)") % (gold_quantity, gold_count)
                gold_weight_str = locale.toString(float(gold_weight), format='f', precision=2)
                lines.append(' '.join((self.tr("Gold weight: %s gramm") % gold_weight_str, comment)))

        count_silver = 0
        quantity_silver = 0
        silver_filter = self.materialFilter("Silver", self.tr("Silver"), "Ag")
        sql = "SELECT quantity FROM coins WHERE status IN ('owned', 'ordered', 'sale', 'duplicate') AND " \
                "%s" % silver_filter
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        while query.next():
            record = query.record()
            quantity = int(record.value('quantity') or 1)
            count_silver += 1
            quantity_silver += quantity
        if count_silver:
            if count_silver == quantity_silver:
                lines.append(self.tr("Silver coins: %d") % count_silver)
            else:
                lines.append(self.tr("Silver coins: %d/%d") % (quantity_silver, count_silver))
        
        if count_silver:
            sql = "SELECT fineness, weight, quantity FROM coins WHERE status IN ('owned', 'ordered', 'sale', 'duplicate') AND " \
                    "%s AND " \
                    "ifnull(fineness,'')<>'' AND ifnull(weight,'')<>''" % silver_filter
            sql = self.makeSql(sql, filter_)
            query = QSqlQuery(sql, model.database())
            silver_weight = 0
            silver_count = 0
            silver_quantity = 0
            while query.next():
                record = query.record()
                fineness = record.value('fineness')
                if isinstance(fineness, str):
                    fineness = stringToMoney(fineness)
                if isinstance(fineness, float):
                    if fineness > 1:
                        fineness = str(fineness).replace('.', '')
                    else:
                        fineness = str(fineness).replace('0.', '')
                weight = record.value('weight')
                if isinstance(weight, str):
                    weight = stringToMoney(weight)
                quantity = int(record.value('quantity') or 1)
                silver_weight += weight * float("0.%s" % fineness) * quantity
                silver_count += 1
                silver_quantity += quantity
            if silver_weight:
                if silver_count == silver_quantity:
                    comment = self.tr("(calculated for %d coins)") % silver_quantity
                else:
                    comment = self.tr("(calculated for %d/%d coins)") % (silver_quantity, silver_count)
                silver_weight_str = locale.toString(float(silver_weight), format='f', precision=2)
                lines.append(' '.join((self.tr("Silver weight: %s gramm") % silver_weight_str, comment)))

        sql = "SELECT count(*) FROM coins WHERE status='wish'"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        if query.first():
            count = query.record().value(0)
            lines.append(self.tr("Count wish: %d") % count)

        count_sold = 0
        sql = "SELECT count(*) FROM coins WHERE status='sold'"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        if query.first():
            count_sold = query.record().value(0)
            if count_sold > 0:
                lines.append(self.tr("Count sales: %d") % count_sold)

        sql = "SELECT count(*) FROM coins WHERE status='bidding'"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        if query.first():
            count = query.record().value(0)
            if count > 0:
                lines.append(self.tr("Count biddings: %d") % count)

        sql = "SELECT count(*) FROM coins WHERE status='missing'"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        if query.first():
            count = query.record().value(0)
            if count > 0:
                lines.append(self.tr("Count missing: %d") % count)

        paid = 0
        commission = ""
        sql = "SELECT SUM(totalpayprice) FROM coins WHERE status IN ('owned', 'ordered', 'sale', 'sold', 'missing', 'duplicate') AND totalpayprice<>'' AND totalpayprice IS NOT NULL"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        if query.first():
            paid = query.record().value(0)
            if paid:
                sql = "SELECT SUM(payprice) FROM coins WHERE status IN ('owned', 'ordered', 'sale', 'sold', 'missing', 'duplicate') AND payprice<>'' AND payprice IS NOT NULL"
                sql = self.makeSql(sql, filter_)
                query = QSqlQuery(sql, model.database())
                if query.first():
                    paid_without_commission = query.record().value(0)
                    if paid_without_commission:
                        commission = self.tr("(commission %d%%)") % ((paid - paid_without_commission) / paid_without_commission * 100)
                paid_str = locale.toString(float(paid), format='f', precision=2)
                lines.append(' '.join((self.tr("Paid: %s") % paid_str, commission)))

                if count_owned:
                    val = paid / count_owned
                    val_str = locale.toString(float(val), format='f', precision=2)
                    lines.append(self.tr("Average paid per item: %s") % val_str)

        earned = 0
        commission = ""
        sql = "SELECT SUM(totalsaleprice) FROM coins WHERE status='sold' AND totalsaleprice<>'' AND totalsaleprice IS NOT NULL"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        if query.first():
            earned = query.record().value(0)
            if earned:
                sql = "SELECT SUM(saleprice) FROM coins WHERE status='sold' AND saleprice<>'' AND saleprice IS NOT NULL"
                sql = self.makeSql(sql, filter_)
                query = QSqlQuery(sql, model.database())
                if query.first():
                    earn_without_commission = query.record().value(0)
                    if earn_without_commission:
                        commission = self.tr("(commission %d%%)") % ((earn_without_commission - earned) / earn_without_commission * 100)
                earned_str = locale.toString(float(earned), format='f', precision=2)
                lines.append(' '.join((self.tr("Earned: %s") % earned_str, commission)))

                if count_sold:
                    val = earned / count_sold
                    val_str = locale.toString(float(val), format='f', precision=2)
                    lines.append(self.tr("Average earn per item: %s") % val_str)

        if paid and earned:
            total = paid - earned
            total_str = locale.toString(float(total), format='f', precision=2)
            lines.append(self.tr("Total (paid - earned): %s") % total_str)

        sql = "SELECT paydate FROM coins WHERE status IN ('owned', 'ordered', 'sale', 'sold', 'missing', 'duplicate') AND paydate<>'' AND paydate IS NOT NULL ORDER BY paydate LIMIT 1"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        if query.first():
            date = QDate.fromString(query.record().value(0), Qt.DateFormat.ISODate)
            paydate = date.toString(Qt.SystemLocaleShortDate)
            lines.append(self.tr("First purchase: %s") % paydate)

        sql = "SELECT UPPER(grade), price1, price2, price3, price4, quantity FROM coins WHERE status IN ('owned', 'ordered', 'sale', 'duplicate') AND (ifnull(price1,'')<>'' OR ifnull(price2,'')<>'' OR ifnull(price3,'')<>'' OR ifnull(price4,'')<>'')"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        est_owned = 0
        count = 0
        coins_quantity = 0
        comment = ""
        while query.next():
            record = query.record()
            grade = record.value(0)
            price1 = record.value(1)
            price2 = record.value(2)
            price3 = record.value(3)
            price4 = record.value(4)
            quantity = int(record.value(5) or 1)

            try:
                if grade[:2] in ('UN', 'MS'):
                    price = price4 if price4 else price3 * 1.6 if price3 else price2 * 2.2 if price2 else price1 * 5.5 if price1 else 0
                elif grade[:2] in ('XF', 'EF'):
                    price = price3 if price3 else price4 * 0.6 if price4 else price2 * 1.4 if price2 else price1 * 3.5 if price1 else 0
                elif grade[:2] in ('AU',):
                    priceU = price4 if price4 else price3 * 1.6 if price3 else price2 * 2.2 if price2 else price1 * 5.5 if price1 else 0
                    priceX = price3 if price3 else price4 * 0.6 if price4 else price2 * 1.4 if price2 else price1 * 3.5 if price1 else 0
                    price = priceX + (priceU - priceX) * 0.6
                elif grade[:2] in ('VF',):
                    price = price2 if price2 else price3 * 0.7 if price3 else price4 * 0.45 if price4 else price1 * 2.5 if price1 else 0
                elif grade[:2] in ('F', 'FI'):
                    price = price1 if price1 else price2 * 0.4 if price2 else price3 * 0.3 if price3 else price4 * 0.18 if price4 else 0
                elif grade[:2] in ('VG',):
                    price = price1 * 0.5 if price1 else price2 * 0.2 if price2 else price3 * 0.14 if price3 else price4 * 0.09 if price4 else 0
                else:
                    price = price4 if price4 else price3 if price3 else price2 if price2 else price1 if price1 else 0

                if price:
                    est_owned += price * quantity
                    count += 1
                    coins_quantity += quantity

            except TypeError:
                continue

        if count:
            if count == coins_quantity:
                comment = self.tr("(calculated for %d coins)") % count
            else:
                comment = self.tr("(calculated for %d/%d coins)") % (coins_quantity, count)

        lines.append(' '.join((self.tr("Estimation owned: %d") % est_owned, comment)))

        sql = "SELECT price1, price2, price3, price4 FROM coins WHERE status='wish' AND (ifnull(price1,'')<>'' OR ifnull(price2,'')<>'' OR ifnull(price3,'')<>'' OR ifnull(price4,'')<>'')"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        est_wish = 0
        count = 0
        comment = ""
        while query.next():
            record = query.record()
            price1 = record.value(0)
            price2 = record.value(1)
            price3 = record.value(2)
            price4 = record.value(3)

            price = price4 if price4 else price3 if price3 else price2 if price2 else price1 if price1 else 0

            try:
                if price:
                    est_wish += price
                    count += 1
            except TypeError:
                continue

        if count:
            comment = self.tr("(calculated for %d coins)") % count

        lines.append(' '.join((self.tr("Estimation wish: %d") % est_wish, comment)))

        sql = "SELECT count(*) FROM photos"
        sql = self.makeSql(sql, filter_)
        query = QSqlQuery(sql, model.database())
        if query.first():
            count = query.record().value(0)
            lines.append(self.tr("Count images: %d") % count)

        return lines

    def materialFilter(self, *materials):
        filters = []
        for material in materials:
            for material_variant in (material.lower(), material.upper(), material.capitalize()):
                filters.append("'%s'" % material_variant)

        return 'material IN (%s)' % ','.join(filters)
