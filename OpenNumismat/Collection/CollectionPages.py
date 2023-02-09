from PyQt6 import QtCore
from PyQt6.QtSql import QSqlQuery

from OpenNumismat.Collection.CollectionFields import CollectionFields
from OpenNumismat.Collection.ListPageParam import ListPageParam
from OpenNumismat.Collection.TreeParam import TreeParam
from OpenNumismat.Collection.StatisticsParam import StatisticsParam
from OpenNumismat.StatisticsView import statisticsAvailable, importedQtWebKit


class CollectionPageTypes:
    Default = 0
    TypeMask = 0x0F
    List = 0
    Icon = 1
    Card = 2
    InfoTypeMask = 0xF0
    Details = 0
    Statistics = 0x10
    Map = 0x20


class CollectionPageParam(QtCore.QObject):
    def __init__(self, record, parent=None):
        QtCore.QObject.__init__(self, parent)

        for name in ('id', 'title', 'isopen'):
            setattr(self, name, record.value(name))
        setattr(self, 'type',
                record.value('type') & CollectionPageTypes.TypeMask)
        info_type = record.value('type') & CollectionPageTypes.InfoTypeMask
        if info_type == CollectionPageTypes.Statistics and not statisticsAvailable:
            info_type = CollectionPageTypes.Details
        if info_type == CollectionPageTypes.Map and not importedQtWebKit:
            info_type = CollectionPageTypes.Details
        setattr(self, 'info_type', info_type)


class CollectionPages(QtCore.QObject):
    def __init__(self, db, parent=None):
        super().__init__(parent)

        self.db = db
        sql = "CREATE TABLE IF NOT EXISTS pages (\
            id INTEGER PRIMARY KEY,\
            title TEXT,\
            isopen INTEGER,\
            position INTEGER,\
            type INTEGER)"
        QSqlQuery(sql, self.db)

        self.fields = CollectionFields(self.db)
        self.params = None

    def pagesParam(self):
        if self.params is None:
            query = QSqlQuery("SELECT * FROM pages ORDER BY position")
            self.params = self.__queryToParam(query)
        return self.params

    def addPage(self, title):
        query = QSqlQuery(self.db)
        query.prepare("INSERT INTO pages (title, isopen, type, position) "
                      "VALUES (?, ?, ?, (SELECT COUNT(*) FROM pages))")
        query.addBindValue(title)
        query.addBindValue(int(True))
        query.addBindValue(CollectionPageTypes.Default)
        query.exec()

        query = QSqlQuery("SELECT * FROM pages WHERE id=last_insert_rowid()",
                          self.db)
        return self.__queryToParam(query)[0]  # get only one item

    def renamePage(self, page, title):
        query = QSqlQuery(self.db)
        query.prepare("UPDATE pages SET title=? WHERE id=?")
        query.addBindValue(title)
        query.addBindValue(page.id)
        query.exec()

    def closePage(self, page):
        query = QSqlQuery(self.db)
        query.prepare("UPDATE pages SET isopen=? WHERE id=?")
        query.addBindValue(int(False))
        query.addBindValue(page.id)
        query.exec()

    def openPage(self, page):
        query = QSqlQuery(self.db)
        query.prepare("UPDATE pages SET isopen=? WHERE id=?")
        query.addBindValue(int(True))
        query.addBindValue(page.id)
        query.exec()

    def removePage(self, page):
        page.listParam.remove()
        page.treeParam.remove()
        page.statisticsParam.remove()

        query = QSqlQuery(self.db)
        query.prepare("DELETE FROM pages WHERE id=?")
        query.addBindValue(page.id)
        query.exec()

    def savePositions(self, pages):
        for position, page in enumerate(pages):
            query = QSqlQuery(self.db)
            query.prepare("UPDATE pages SET position=? WHERE id=?")
            query.addBindValue(position)
            query.addBindValue(page.id)
            query.exec()

    def closedPages(self):
        query = QSqlQuery(self.db)
        query.prepare("SELECT * FROM pages WHERE isopen=? ORDER BY title")
        query.addBindValue(int(False))
        query.exec()
        return self.__queryToParam(query)

    def changeView(self, page, type_):
        query = QSqlQuery(self.db)
        query.prepare("UPDATE pages SET type=? WHERE id=?")
        query.addBindValue(type_ | page.info_type)
        query.addBindValue(page.id)
        query.exec()

    def changeInfoType(self, page, info_type):
        query = QSqlQuery(self.db)
        query.prepare("UPDATE pages SET type=? WHERE id=?")
        query.addBindValue(info_type | page.type)
        query.addBindValue(page.id)
        query.exec()

    def __queryToParam(self, query):
        pagesParam = []
        while query.next():
            param = CollectionPageParam(query.record())
            param.fields = self.fields
            param.db = self.db
            # TODO: Improve code
            if param.type == CollectionPageTypes.List:
                param.listParam = ListPageParam(param)
            elif param.type == CollectionPageTypes.Card:
                param.listParam = ListPageParam(param)
            elif param.type == CollectionPageTypes.Icon:
                param.listParam = ListPageParam(param)
            param.treeParam = TreeParam(param)
            param.statisticsParam = StatisticsParam(param)
            pagesParam.append(param)

        return pagesParam
