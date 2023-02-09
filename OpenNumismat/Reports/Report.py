import codecs
import os

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print('jinja2 module missed. Report engine not available')

from PyQt6 import QtCore
from PyQt6.QtCore import Qt, QCryptographicHash
from PyQt6.QtGui import QImage

from OpenNumismat.Tools import Gui
import OpenNumismat


def copyFolder(sourceFolder, destFolder):
    sourceDir = QtCore.QDir(sourceFolder)
    if not sourceDir.exists():
        return

    destDir = QtCore.QDir(destFolder)
    if not destDir.exists():
        destDir.mkpath(destFolder)

    files = sourceDir.entryList(QtCore.QDir.Filter.Files)
    for file in files:
        srcName = os.path.join(sourceFolder, file)
        destName = os.path.join(destFolder, file)
        QtCore.QFile.remove(destName)  # remove if existing
        QtCore.QFile.copy(srcName, destName)

    files = sourceDir.entryList(QtCore.QDir.Filter.AllDirs | QtCore.QDir.Filter.NoDotAndDotDot)
    for file in files:
        srcName = os.path.join(sourceFolder, file)
        destName = os.path.join(destFolder, file)
        copyFolder(srcName, destName)


def scanTemplates():
    templates = []

    path = os.path.join(OpenNumismat.HOME_PATH, 'templates')
    sourceDir = QtCore.QDir(path)
    if sourceDir.exists():
        files = sourceDir.entryList(QtCore.QDir.Filter.AllDirs | QtCore.QDir.Filter.NoDotAndDotDot)
        for file in files:
            templates.append((file, os.path.join(path, file)))

    path = os.path.join(OpenNumismat.PRJ_PATH, 'templates')
    sourceDir = QtCore.QDir(path)
    if sourceDir.exists():
        files = sourceDir.entryList(QtCore.QDir.Filter.AllDirs | QtCore.QDir.Filter.NoDotAndDotDot)
        for file in files:
            templates.append((file, os.path.join(path, file)))

    return templates


class Report(QtCore.QObject):
    def __init__(self, model, template, dstPath, parent=None):
        super().__init__(parent)

        self.model = model
        self.srcFolder = template
        self.img_file_dict = {}

        fileInfo = QtCore.QFileInfo(dstPath)
        if fileInfo.exists() and fileInfo.isDir():
            self.dstFolder = dstPath
            self.fileName = None
        else:
            self.dstFolder = fileInfo.dir().path()
            self.fileName = fileInfo.fileName()

    def generate(self, indexes, single_file=False):
        if os.path.exists(os.path.join(self.srcFolder, 'coin.htm')):
            has_item_template = True
        else:
            has_item_template = False
            single_file = True

        self.mapping = {'single_file': single_file,
                        'date': QtCore.QDate.currentDate().toString(QtCore.Qt.DefaultLocaleLongDate)}

        self.mapping['collection'] = {'title': self.model.description.title,
                            'description': self.model.description.description,
                            'author': self.model.description.author}

        if not self.fileName:
            if len(indexes) == 1 and has_item_template:
                self.fileName = "coin_%d.htm" % self.__getId(indexes[0])
            else:
                self.fileName = "coins.htm"
        static_files = QtCore.QFileInfo(self.fileName).baseName() + '_files'
        self.contentDir = os.path.join(self.dstFolder, static_files)

        self.mapping['static_files'] = static_files

        copyFolder(os.path.join(self.srcFolder, 'files'), self.contentDir)

        loader = FileSystemLoader(self.srcFolder)
        self.env = Environment(loader=loader, autoescape=True)

        titles_mapping = {}
        for field in self.model.fields:
            titles_mapping[field.name] = field.title
        self.mapping['titles'] = titles_mapping

        if len(indexes) == 1 and has_item_template:
            self.mapping['record'] = self.__recordMapping(indexes[0])
            dstFile = self.__render('coin.htm', self.fileName)
        else:
            progressDlg = Gui.ProgressDialog(self.tr("Generating report"),
                            self.tr("Cancel"), len(indexes), self.parent())

            record_data = []
            for index in indexes:
                progressDlg.step()
                if progressDlg.wasCanceled():
                    return None

                recordMapping = self.__recordMapping(index)
                record_data.append(recordMapping)
                if not single_file:
                    self.mapping['record'] = recordMapping
                    self.__render('coin.htm', "coin_%d.htm" % self.__getId(index))

            self.mapping['records'] = record_data

            dstFile = self.__render('coins.htm', self.fileName)

            progressDlg.reset()

        return dstFile

    def __render(self, template, fileName):
        template = self.env.get_template(template)
        res = template.render(self.mapping)

        dstFile = os.path.join(self.dstFolder, fileName)
        f = codecs.open(dstFile, 'w', 'utf-8')
        f.write(res)
        f.close()

        return dstFile

    def __getId(self, index):
        field_index = self.model.index(index.row(), self.model.fieldIndex('id'))
        return self.model.data(field_index, Qt.ItemDataRole.UserRole)

    def __recordMapping(self, index):
        imgFields = ('image', 'obverseimg', 'reverseimg', 'edgeimg',
                     'varietyimg', 'photo1', 'photo2', 'photo3', 'photo4',
                     'photo5', 'photo6', 'signatureimg')

        record_mapping = {}
        record_mapping['status_raw'] = ''
        record_mapping['issuedate_raw'] = ''
        record_mapping['diameter_raw'] = ''
        row = index.row()
        for field in self.model.fields:
            field_index = self.model.index(row, self.model.fieldIndex(field.name))
            value = self.model.data(field_index, Qt.ItemDataRole.DisplayRole)

            if value is None or value == '':
                record_mapping[field.name] = ''
            else:
                if field.name in imgFields:
                    if field.name == 'image':
                        ext = 'png'
                    else:
                        ext = 'jpg'
                    
                    hash_ = QCryptographicHash.hash(value, QCryptographicHash.Sha1)
                    if hash_ in self.img_file_dict:
                        img_file_title = self.img_file_dict[hash_]
                    else:
                        img_file_title = "%s_%d.%s" % (field.name, self.__getId(index), ext)
                        self.img_file_dict[hash_] = img_file_title

                        imgFile = os.path.join(self.contentDir, img_file_title)
                        image = QImage()
                        image.loadFromData(value)
                        image.save(imgFile)

                    record_mapping[field.name] = img_file_title
                else:
                    record_mapping[field.name] = value
                    if field.name == 'status':
                        record_mapping['status_raw'] = self.model.data(field_index, Qt.ItemDataRole.UserRole)
                    elif field.name == 'issuedate':
                        record_mapping['issuedate_raw'] = self.model.data(field_index, Qt.ItemDataRole.UserRole)
                    elif field.name == 'diameter':
                        record_mapping['diameter_raw'] = self.model.data(field_index, Qt.ItemDataRole.UserRole)

        return record_mapping
