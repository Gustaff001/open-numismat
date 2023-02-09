from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtSql import QSqlQuery
from PyQt6.QtWidgets import *

from OpenNumismat.Collection.CollectionFields import FieldTypes as Type
from OpenNumismat.Collection.CollectionFields import Statuses, StatusesOrder
from OpenNumismat.Tools.Gui import statusIcon
from OpenNumismat.Tools.Converters import numberWithFraction


class CustomSortListWidgetItem(QListWidgetItem):

    def __lt__(self, other):
        left = self.data(Qt.ItemDataRole.UserRole + 1)
        right = other.data(Qt.ItemDataRole.UserRole + 1)

        if isinstance(left, str):
            right = str(right)
        elif isinstance(right, str):
            left = str(left)

        return left < right


class StatusSortListWidgetItem(QListWidgetItem):

    def __lt__(self, other):
        left = self.data(Qt.ItemDataRole.UserRole)
        right = other.data(Qt.ItemDataRole.UserRole)
        return StatusesOrder[left] < StatusesOrder[right]


class FilterMenuButton(QPushButton):
    DefaultType = QListWidgetItem.ItemType.UserType
    SelectAllType = QListWidgetItem.ItemType.UserType + 1
    BlanksType = QListWidgetItem.ItemType.UserType + 2
    DataType = QListWidgetItem.ItemType.UserType + 3

    def __init__(self, columnParam, listParam, model, parent):
        super().__init__(parent)

        self.db = model.database()
        self.model = model
        self.reference = model.reference
        self.columnName = self.model.fields.fields[columnParam.fieldid].name
        self.fieldid = columnParam.fieldid
        self.filters = listParam.filters
        self.listParam = listParam
        self.settings = model.settings

        menu = QMenu()

        self.setToolTip(self.tr("Filter items"))

        self.setFixedHeight(self.parent().height() - 2)
        self.setFixedWidth(self.height())
        self.setMenu(menu)
        if self.fieldid in self.filters.keys():
            self.setIcon(QIcon(':/filters.ico'))

        menu.aboutToShow.connect(self.prepareMenu)

    def prepareMenu(self):
        self.listWidget = QListWidget(self)

        filters = self.filters.copy()
        appliedValues = []
        columnFilters = None
        revert = False
        if self.fieldid in filters.keys():
            columnFilters = filters.pop(self.fieldid)
            for filter_ in columnFilters.filters():
                if filter_.isRevert():
                    revert = True
                appliedValues.append(filter_.value)

        hasBlanks = False
        columnType = self.model.columnType(self.fieldid)
        if self.model.columnName(self.fieldid) == 'year':
            filtersSql = self.filtersToSql(filters.values())
            if filtersSql:
                filtersSql = 'WHERE ' + filtersSql
            sql = "SELECT DISTINCT %s FROM coins %s" % (self.columnName, filtersSql)
            query = QSqlQuery(sql, self.db)

            while query.next():
                icon = None
                if query.record().isNull(0):
                    data = None
                else:
                    orig_data = query.record().value(0)
                    data = str(orig_data)
                    label = data
                    try:
                        year = int(orig_data)
                        if year < 0:
                            label = "%d BC" % -year
                    except ValueError:
                        pass

                if not data:
                    hasBlanks = True
                    continue

                item = CustomSortListWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, label)
                item.setData(Qt.ItemDataRole.UserRole, data)
                item.setData(Qt.ItemDataRole.UserRole + 1, orig_data)
                if data in appliedValues:
                    if revert:
                        item.setCheckState(Qt.CheckState.Checked)
                    else:
                        item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    if revert:
                        item.setCheckState(Qt.CheckState.Unchecked)
                    else:
                        item.setCheckState(Qt.CheckState.Checked)
                self.listWidget.addItem(item)

            self.listWidget.sortItems()
        elif columnType == Type.Text or columnType in Type.ImageTypes:
            dataFilter = BlankFilter(self.columnName).toSql()
            blanksFilter = DataFilter(self.columnName).toSql()

            filtersSql = self.filtersToSql(filters.values())
            sql = "SELECT 1 FROM coins WHERE " + filtersSql
            if filtersSql:
                sql += ' AND '

            # Get blank row count
            blank_sql = sql + blanksFilter + " LIMIT 1"
            query = QSqlQuery(blank_sql, self.db)
            if query.first():
                hasBlanks = True

            # Get not blank row count
            not_blank_sql = sql + dataFilter + " LIMIT 1"
            query = QSqlQuery(not_blank_sql, self.db)
            if query.first():
                if columnType in Type.ImageTypes:
                    label = self.tr("(Images)")
                elif columnType == Type.Text:
                    label = self.tr("(Text)")
                else:
                    label = self.tr("(Data)")
                item = QListWidgetItem(label,
                                       type=FilterMenuButton.DataType)
                item.setData(Qt.ItemDataRole.UserRole, label)
                item.setCheckState(Qt.CheckState.Checked)
                if columnFilters and columnFilters.hasData():
                    item.setCheckState(Qt.CheckState.Unchecked)
                self.listWidget.addItem(item)
        elif columnType == Type.Status:
            filtersSql = self.filtersToSql(filters.values())
            if filtersSql:
                filtersSql = 'WHERE ' + filtersSql
            sql = "SELECT DISTINCT %s FROM coins %s ORDER BY %s ASC" % (
                self.columnName, filtersSql, self.columnName)
            query = QSqlQuery(sql, self.db)

            while query.next():
                value = query.record().value(0)
                label = Statuses[value]

                item = StatusSortListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, value)

                icon = statusIcon(value)
                item.setIcon(icon)

                if value in appliedValues:
                    if revert:
                        item.setCheckState(Qt.CheckState.Checked)
                    else:
                        item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    if revert:
                        item.setCheckState(Qt.CheckState.Unchecked)
                    else:
                        item.setCheckState(Qt.CheckState.Checked)
                self.listWidget.addItem(item)

            self.listWidget.sortItems()
        elif columnType == Type.Denomination:
            filtersSql = self.filtersToSql(filters.values())
            if filtersSql:
                filtersSql = 'WHERE ' + filtersSql
            sql = "SELECT DISTINCT %s FROM coins %s" % (self.columnName, filtersSql)
            query = QSqlQuery(sql, self.db)

            while query.next():
                icon = None
                if query.record().isNull(0):
                    data = None
                else:
                    orig_data = query.record().value(0)
                    data = str(orig_data)
                    label, _ = numberWithFraction(data, self.settings['convert_fraction'])

                if not data:
                    hasBlanks = True
                    continue

                item = CustomSortListWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, label)
                item.setData(Qt.ItemDataRole.UserRole, data)
                item.setData(Qt.ItemDataRole.UserRole + 1, orig_data)
                if data in appliedValues:
                    if revert:
                        item.setCheckState(Qt.CheckState.Checked)
                    else:
                        item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    if revert:
                        item.setCheckState(Qt.CheckState.Unchecked)
                    else:
                        item.setCheckState(Qt.CheckState.Checked)
                self.listWidget.addItem(item)

            self.listWidget.sortItems()
        else:
            filtersSql = self.filtersToSql(filters.values())
            if filtersSql:
                filtersSql = 'WHERE ' + filtersSql
            sql = "SELECT DISTINCT %s FROM coins %s" % (self.columnName, filtersSql)
            query = QSqlQuery(sql, self.db)

            while query.next():
                icon = None
                if query.record().isNull(0):
                    data = None
                else:
                    orig_data = query.record().value(0)
                    data = str(orig_data)
                    icon = self.reference.getIcon(self.columnName, data)

                if not data:
                    hasBlanks = True
                    continue

                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, orig_data)
                item.setData(Qt.ItemDataRole.UserRole, data)
                if icon:
                    item.setIcon(icon)
                if data in appliedValues:
                    if revert:
                        item.setCheckState(Qt.CheckState.Checked)
                    else:
                        item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    if revert:
                        item.setCheckState(Qt.CheckState.Unchecked)
                    else:
                        item.setCheckState(Qt.CheckState.Checked)
                self.listWidget.addItem(item)

            self.listWidget.sortItems()

        item = QListWidgetItem(self.tr("(Select all)"),
                               type=FilterMenuButton.SelectAllType)
        item.setData(Qt.ItemDataRole.UserRole, self.tr("(Select all)"))
        item.setCheckState(Qt.CheckState.Checked)
        self.listWidget.insertItem(0, item)

        if hasBlanks:
            item = QListWidgetItem(self.tr("(Blanks)"),
                                   type=FilterMenuButton.BlanksType)
            item.setData(Qt.ItemDataRole.UserRole, self.tr("(Blanks)"))
            item.setCheckState(Qt.CheckState.Checked)
            if revert:
                if columnFilters and not columnFilters.hasBlank():
                    item.setCheckState(Qt.CheckState.Unchecked)
            else:
                if columnFilters and columnFilters.hasBlank():
                    item.setCheckState(Qt.CheckState.Unchecked)
            self.listWidget.addItem(item)

        self.listWidget.itemChanged.connect(self.itemChanged)

        self.searchBox = QLineEdit(self)
        self.searchBox.setPlaceholderText(self.tr("Filter"))
        self.searchBox.textChanged.connect(self.applySearch)

        self.buttonBox = QDialogButtonBox(Qt.Orientation.Horizontal)
        self.buttonBox.addButton(QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.apply)
        self.buttonBox.rejected.connect(self.menu().hide)

        layout = QVBoxLayout()
        layout.addWidget(self.searchBox)
        layout.addWidget(self.listWidget)
        layout.addWidget(self.buttonBox)

        widget = QWidget(self)
        widget.setLayout(layout)

        widgetAction = QWidgetAction(self)
        widgetAction.setDefaultWidget(widget)
        self.menu().clear()
        self.menu().addAction(widgetAction)

        # Fill items
        if self.listWidget.count() > 1:
            self.itemChanged(self.listWidget.item(1))

    def itemChanged(self, item):
        self.listWidget.itemChanged.disconnect(self.itemChanged)

        if item.type() == FilterMenuButton.SelectAllType:
            for i in range(1, self.listWidget.count()):
                self.listWidget.item(i).setCheckState(item.checkState())

            # Disable applying filter when nothing to show
            button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
            button.setDisabled(item.checkState() == Qt.CheckState.Unchecked)
        else:
            checkedCount = 0
            for i in range(1, self.listWidget.count()):
                item = self.listWidget.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    checkedCount = checkedCount + 1

            if checkedCount == 0:
                state = Qt.CheckState.Unchecked
            elif checkedCount == self.listWidget.count() - 1:
                state = Qt.CheckState.Checked
            else:
                state = Qt.PartiallyChecked
            self.listWidget.item(0).setCheckState(state)

            # Disable applying filter when nothing to show
            button = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
            button.setDisabled(checkedCount == 0)

        self.listWidget.itemChanged.connect(self.itemChanged)

    def apply(self):
        filters = ColumnFilters(self.columnName)
        unchecked = 0
        checked = 0
        for i in range(1, self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.checkState() == Qt.CheckState.Unchecked:
                unchecked = unchecked + 1
            else:
                checked = checked + 1

        for i in range(1, self.listWidget.count()):
            item = self.listWidget.item(i)
            if unchecked > checked:
                if item.checkState() == Qt.CheckState.Checked:
                    if item.type() == FilterMenuButton.BlanksType:
                        filter_ = BlankFilter(self.columnName)
                    elif item.type() == FilterMenuButton.DataType:
                        filter_ = DataFilter(self.columnName)
                    else:
                        value = item.data(Qt.ItemDataRole.UserRole)
                        filter_ = ValueFilter(self.columnName, value)

                    filter_.revert = True
                    filters.addFilter(filter_)
            else:
                if item.checkState() == Qt.CheckState.Unchecked:
                    if item.type() == FilterMenuButton.BlanksType:
                        filter_ = BlankFilter(self.columnName)
                    elif item.type() == FilterMenuButton.DataType:
                        filter_ = DataFilter(self.columnName)
                    else:
                        value = item.data(Qt.ItemDataRole.UserRole)
                        filter_ = ValueFilter(self.columnName, value)

                    filters.addFilter(filter_)

        self.applyFilters(filters)

        self.menu().hide()

    def applyFilters(self, filters):
        if filters.filters():
            self.setIcon(QIcon(':/filters.ico'))
            self.filters[self.fieldid] = filters
        else:
            self.setIcon(QIcon())
            if self.fieldid in self.filters.keys():
                self.filters.pop(self.fieldid)

        filtersSql = self.filtersToSql(self.filters.values())
        self.model.setFilter(filtersSql)

        self.listParam.save_filters()

    def clear(self):
        self.setIcon(QIcon())

    def applySearch(self, text):
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.text().find(text) >= 0:
                item.setHidden(False)
            else:
                item.setHidden(True)

    @staticmethod
    def filtersToSql(filters):
        sqlFilters = []
        for columnFilters in filters:
            sqlFilters.append(columnFilters.toSql())

        return ' AND '.join(sqlFilters)


class BaseFilter:
    def __init__(self, name):
        self.name = name
        self.value = None
        self.revert = False

    def toSql(self):
        raise NotImplementedError

    def isBlank(self):
        return False

    def isData(self):
        return False

    def isRevert(self):
        return self.revert


class ValueFilter(BaseFilter):
    def __init__(self, name, value):
        super().__init__(name)

        self.value = value

    # TODO: Deprecated method
    def toSql(self):
        if self.revert:
            return "%s='%s'" % (self.name, self.value.replace("'", "''"))
        else:
            return "%s<>'%s'" % (self.name, self.value.replace("'", "''"))


class DataFilter(BaseFilter):
    def toSql(self):
        if self.revert:
            # Filter out blank values
            return "ifnull(%s,'')<>''" % self.name
        else:
            # Filter out not null and not empty values
            return "ifnull(%s,'')=''" % self.name

    def isData(self):
        return True


class BlankFilter(BaseFilter):
    def toSql(self):
        if self.revert:
            # Filter out not null and not empty values
            return "ifnull(%s,'')=''" % self.name
        else:
            # Filter out blank values
            return "ifnull(%s,'')<>''" % self.name

    def isBlank(self):
        return True


class ColumnFilters:
    def __init__(self, name):
        self.name = name
        self._filters = []
        self._blank = None  # blank out filter
        self._data = None  # data out filter
        self._revert = False

    def addFilter(self, filter_):
        if filter_.isBlank():
            self._blank = filter_
        if filter_.isData():
            self._data = filter_
        self._revert = self._revert or filter_.isRevert()
        self._filters.append(filter_)

    def filters(self):
        return self._filters

    def hasBlank(self):
        return self._blank

    def hasData(self):
        return self._data

    def hasRevert(self):
        return self._revert

    def toSql(self):
        values = []
        for filter_ in self._valueFilters():
            sql = "'%s'" % filter_.value.replace("'", "''")
            values.append(sql)

        combinedFilters = ''
        if values:
            sqlValueFilters = ','.join(values)
            if self.hasRevert():
                combinedFilters = "%s IN (%s)" % (self.name, sqlValueFilters)
            else:
                combinedFilters = "%s NOT IN (%s)" % (self.name, sqlValueFilters)

        if self.hasBlank():
            if combinedFilters:
                if self.hasRevert():
                    combinedFilters = combinedFilters + ' OR ' + self._blank.toSql()
                else:
                    combinedFilters = combinedFilters + ' AND ' + self._blank.toSql()
            else:
                combinedFilters = self._blank.toSql()
        elif self.hasData():
            # Data filter can't contain any additional value filters
            combinedFilters = self._data.toSql()

        # Note: In SQLite SELECT * FROM coins WHERE title NOT IN ('value') also
        # filter out a NULL values. Work around this problem
        if not self.hasBlank() and not self.hasRevert():
            combinedFilters = combinedFilters + (' OR %s IS NULL' % self.name)
        return '(' + combinedFilters + ')'

    def _valueFilters(self):
        for filter_ in self._filters:
            if isinstance(filter_, ValueFilter):
                yield filter_
