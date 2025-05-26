from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
import pandas as pd

class VCFTableModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._data = pd.DataFrame()
        self._columns = ['Name', 'Phone', 'E-mail', 'Type']
    
    def rowCount(self, parent=QModelIndex()):
        return len(self._data)
    
    def columnCount(self, parent=QModelIndex()):
        return len(self._columns)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        
        if role == Qt.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            return str(value)
        
        return None
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._columns[section]
            if orientation == Qt.Vertical:
                return str(section + 1)
        return None
    
    def set_data(self, df):
        """DataFrame'i modele yükler"""
        self.beginResetModel()
        self._data = df
        self.endResetModel()
    
    def get_data(self):
        """Mevcut DataFrame'i döndürür"""
        return self._data
    
    def flags(self, index):
        """Hücrelerin düzenlenebilir olmasını sağlar"""
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
    
    def setData(self, index, value, role=Qt.EditRole):
        """Hücre değerini günceller"""
        if role == Qt.EditRole:
            self._data.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        return False

class VCFProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._filters = {}
        self._except_filters = {}  # Store except filters
    
    def set_filter(self, column, text):
        """Belirli bir sütun için filtre ayarlar"""
        if text.startswith('!'):  # Except filter
            self._except_filters[column] = text[1:].lower().split(',')
            self._filters[column] = ''  # Clear normal filter
        else:
            self._filters[column] = text.lower()
            self._except_filters[column] = []  # Clear except filter
        self.invalidateFilter()
    
    def clear_filters(self):
        """Tüm filtreleri temizler"""
        self._filters.clear()
        self._except_filters.clear()
        self.invalidateFilter()
    
    def filterAcceptsRow(self, source_row, source_parent):
        """Satırın filtrelere uyup uymadığını kontrol eder"""
        # Check normal filters
        for column, filter_text in self._filters.items():
            if not filter_text:
                continue
                
            index = self.sourceModel().index(source_row, column, source_parent)
            value = str(self.sourceModel().data(index, Qt.DisplayRole)).lower()
            
            if filter_text not in value:
                return False
        
        # Check except filters
        for column, except_words in self._except_filters.items():
            if not except_words:
                continue
                
            index = self.sourceModel().index(source_row, column, source_parent)
            value = str(self.sourceModel().data(index, Qt.DisplayRole)).lower()
            
            # If any of the except words are in the value, reject the row
            if any(word.strip() in value for word in except_words):
                return False
        
        return True 