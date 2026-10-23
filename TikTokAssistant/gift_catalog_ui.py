"""Searchable offline gift catalogue; values are live metadata, never fabricated."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,
    QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QSpinBox,QMessageBox,
    QAbstractItemView)
from gift_catalog import presentation_items,set_override

class GiftCatalogDialog(QDialog):
    def __init__(self, language='ar', parent=None):
        super().__init__(parent);self.lang=language;self.selection='';self.items=[]
        self.setWindowTitle('مكتبة الهدايا — Gift Catalog' if language=='ar' else 'Gift Catalog')
        self.resize(790,620)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('تُملأ البيانات عند الاتصال بالبث، وقد تختلف الأسعار حسب المنطقة وتحديثات TikTok.'
            if language=='ar' else 'Metadata arrives while connected; prices vary by region and TikTok updates.'))
        controls=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('بحث عن هدية...' if language=='ar' else 'Search gifts...')
        self.search.textChanged.connect(self.refresh_rows);controls.addWidget(self.search,1)
        reload=QPushButton('تحديث العرض' if language=='ar' else 'Refresh');reload.clicked.connect(self.load);controls.addWidget(reload)
        layout.addLayout(controls)
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(['🖼','Gift ID','Name','Coins 🪙'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0,64);self.table.setColumnWidth(1,100);self.table.setColumnWidth(3,90)
        self.table.itemSelectionChanged.connect(self.select_row)
        layout.addWidget(self.table,1)
        bottom=QHBoxLayout();self.current=QLabel('—');bottom.addWidget(self.current,1)
        self.coins=QSpinBox();self.coins.setRange(0,1000000)
        bottom.addWidget(self.coins)
        set_button=QPushButton('تعديل قيمة الهدية' if language=='ar' else 'Set coin override')
        set_button.clicked.connect(self.override);bottom.addWidget(set_button)
        layout.addLayout(bottom)
        select=QPushButton('اختيار الهدية' if language=='ar' else 'Select gift');select.clicked.connect(self.accept_selection)
        close=QPushButton('إغلاق' if language=='ar' else 'Close');close.clicked.connect(self.reject)
        row=QHBoxLayout();row.addStretch();row.addWidget(select);row.addWidget(close);layout.addLayout(row)
        self.net=QNetworkAccessManager(self);self.images={};self.image_requests=set()
        self.load()

    def load(self):self.items=presentation_items();self.refresh_rows()

    def refresh_rows(self):
        q=self.search.text().strip().casefold();filtered=[g for g in self.items if q in g['name'].casefold() or q in g.get('id','')][:500]
        self.visible=filtered
        self.table.setRowCount(len(filtered));self.table.setUpdatesEnabled(False)
        for i,g in enumerate(filtered):
            for column,value in ((1,g.get('id','')),(2,g['name']),(3,str(g.get('coins',0)) if g.get('coins',0) else '—')):
                item=QTableWidgetItem(value);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i,column,item)
            image=QTableWidgetItem('🎁');self.table.setItem(i,0,image)
            local=g.get('image_file','')
            if local:
                if local not in self.images:
                    px=QPixmap(local)
                    if not px.isNull():self.images[local]=px
                if local in self.images:self._set_icon(i,self.images[local]);continue
            url=g.get('image_url','')
            if url and url in self.images:self._set_icon(i,self.images[url])
            elif url and url not in self.image_requests and len(self.image_requests)<60:
                self.image_requests.add(url)
                req=QNetworkRequest(QUrl(url));reply=self.net.get(req)
                reply.finished.connect(lambda r=reply,u=url:self._image_ready(r,u))
        self.table.setUpdatesEnabled(True)
    def _image_ready(self,reply,url):
        try:
            img=QPixmap();img.loadFromData(bytes(reply.readAll()))
            if not img.isNull():
                self.images[url]=img
                for i,g in enumerate(self.visible):
                    if g.get('image_url')==url:self._set_icon(i,img)
        finally:reply.deleteLater()
    def _set_icon(self,i,img):
        cell=self.table.item(i,0)
        if cell:cell.setText('');cell.setIcon(QIcon(img.scaled(38,38,Qt.AspectRatioMode.KeepAspectRatio)))
    def select_row(self):
        row=self.table.currentRow()
        if 0<=row<len(self.visible):
            g=self.visible[row];self.current.setText(g['name']);self.coins.setValue(int(g.get('coins') or 0))
    def override(self):
        row=self.table.currentRow()
        if not 0<=row<len(self.visible):return
        name=self.visible[row]['name'];set_override(name,self.coins.value());self.load()
    def accept_selection(self):
        row=self.table.currentRow()
        if not 0<=row<len(self.visible):return
        self.selection=self.visible[row]['name'];self.accept()
