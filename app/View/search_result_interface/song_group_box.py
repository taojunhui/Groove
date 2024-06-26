# coding:utf-8
from typing import List

from common.icon import getIconColor
from common.crawler import QueryServerType
from common.database.entity import SongInfo
from common.signal_bus import signalBus
from common.style_sheet import setStyleSheet
from components.buttons.three_state_button import ThreeStatePushButton
from components.song_list_widget import NoScrollSongListWidget, SongCardType
from components.song_list_widget.song_card import (NoCheckBoxSongCard,
                                                   NoCheckBoxOnlineSongCard)
from components.widgets.menu import AddToMenu, DownloadMenu, RoundMenu
from PyQt5.QtCore import QMargins, Qt, pyqtSignal
from PyQt5.QtWidgets import QAction, QPushButton, QWidget


class SongGroupBox(QWidget):
    """ Song group box """

    switchToMoreSearchResultInterfaceSig = pyqtSignal()

    def __init__(self, song_type: str, parent=None):
        """
        Parameters
        ----------
        song_type: str
            song type, could be `'Online songs'` or `'Local songs'`

        parent:
            parent window
        """
        super().__init__(parent=parent)
        if song_type not in ['Online', 'Local']:
            raise ValueError(
                "Song type must be 'Online songs' or 'Local songs'")

        self.songType = song_type
        self.isOnline = song_type == 'Online'
        self.songInfos = []
        if not self.isOnline:
            self.songListWidget = LocalSongListWidget(self)
            self.titleButton = QPushButton(self.tr('Local songs'), self)
        else:
            self.songListWidget = OnlineSongListWidget(self)
            self.titleButton = QPushButton(self.tr('Online songs'), self)

        c = getIconColor()
        self.showAllButton = ThreeStatePushButton(
            {
                "normal": f":/images/search_result_interface/ShowAll_normal_{c}.svg",
                "hover": f":/images/search_result_interface/ShowAll_hover_{c}.svg",
                "pressed": f":/images/search_result_interface/ShowAll_pressed_{c}.svg",
            },
            self.tr(' Show All'),
            (14, 14),
            self,
        )
        self.__initWidget()

    def __initWidget(self):
        """ initialize widgets """
        self.resize(1200, 500)
        self.setMinimumHeight(47)
        self.titleButton.move(35, 0)
        self.songListWidget.move(0, 57)
        self.titleButton.clicked.connect(self.switchToMoreSearchResultInterfaceSig)
        self.showAllButton.clicked.connect(self.switchToMoreSearchResultInterfaceSig)
        self.__setQss()

    def __setQss(self):
        """ set style sheet """
        self.titleButton.setObjectName('titleButton')
        self.showAllButton.setObjectName('showAllButton')
        setStyleSheet(self, 'song_group_box')
        self.titleButton.adjustSize()
        self.showAllButton.adjustSize()

    def resizeEvent(self, e):
        self.songListWidget.resize(self.width(), self.songListWidget.height())
        self.showAllButton.move(self.width()-self.showAllButton.width()-30, 5)

    def __adjustHeight(self):
        self.setFixedHeight(57+self.songListWidget.height())

    def updateWindow(self, songInfos: List[SongInfo]):
        """ update window """
        if songInfos == self.songInfos:
            return

        self.songInfos = songInfos
        self.songListWidget.updateAllSongCards(self.songInfos)
        self.__adjustHeight()


class LocalSongListWidget(NoScrollSongListWidget):
    """ Local song list widget """

    def __init__(self, parent=None):
        super().__init__(None, SongCardType.NO_CHECKBOX_SONG_CARD,
                         parent, QMargins(30, 0, 30, 0), 0)
        setStyleSheet(self, 'song_list_widget')

    def contextMenuEvent(self, e):
        hitIndex = self.indexAt(e.pos()).column()
        if hitIndex > -1:
            contextMenu = LocalSongListContextMenu(self)
            self.__connectContextMenuSignalToSlot(contextMenu)
            contextMenu.exec(self.cursor().pos())

    def __connectContextMenuSignalToSlot(self, menu):
        menu.playAct.triggered.connect(
            lambda: signalBus.playOneSongCardSig.emit(self.currentSongInfo))
        menu.nextSongAct.triggered.connect(
            lambda: signalBus.nextToPlaySig.emit([self.currentSongInfo]))
        menu.viewOnlineAct.triggered.connect(
            lambda: signalBus.getSongDetailsUrlSig.emit(self.currentSongInfo, QueryServerType.WANYI))
        menu.showPropertyAct.triggered.connect(self.showSongPropertyDialog)
        menu.showAlbumAct.triggered.connect(
            lambda: signalBus.switchToAlbumInterfaceSig.emit(
                self.currentSongCard.singer,
                self.currentSongCard.album
            )
        )

        menu.addToMenu.playingAct.triggered.connect(
            lambda: signalBus.addSongsToPlayingPlaylistSig.emit([self.currentSongInfo]))
        menu.addToMenu.addSongsToPlaylistSig.connect(
            lambda name: signalBus.addSongsToCustomPlaylistSig.emit(name, [self.currentSongInfo]))
        menu.addToMenu.newPlaylistAct.triggered.connect(
            lambda: signalBus.addSongsToNewCustomPlaylistSig.emit([self.currentSongInfo]))

    def _connectSongCardSignalToSlot(self, songCard: NoCheckBoxSongCard):
        songCard.doubleClicked.connect(lambda i: self._playSongs(i))
        songCard.playButtonClicked.connect(lambda i: self._playSongs(i))
        songCard.clicked.connect(self.setCurrentIndex)


class OnlineSongListWidget(NoScrollSongListWidget):
    """ Online song list widget """

    def __init__(self, parent=None):
        super().__init__(None, SongCardType.NO_CHECKBOX_ONLINE_SONG_CARD,
                         parent, QMargins(30, 0, 30, 0), 0)
        setStyleSheet(self, 'song_list_widget')

    def contextMenuEvent(self, e):
        hitIndex = self.indexAt(e.pos()).column()
        if hitIndex > -1:
            menu = OnlineSongListContextMenu(self)
            self.__connectContextMenuSignalToSlot(menu)
            menu.exec(self.cursor().pos())

    def _connectSongCardSignalToSlot(self, songCard: NoCheckBoxOnlineSongCard):
        songCard.doubleClicked.connect(lambda i: self._playSongs(i))
        songCard.playButtonClicked.connect(lambda i: self._playSongs(i))
        songCard.clicked.connect(self.setCurrentIndex)

    def __connectContextMenuSignalToSlot(self, menu):
        menu.showPropertyAct.triggered.connect(
            self.showSongPropertyDialog)
        menu.playAct.triggered.connect(
            lambda: signalBus.playOneSongCardSig.emit(self.currentSongInfo))
        menu.nextSongAct.triggered.connect(
            lambda: signalBus.nextToPlaySig.emit([self.currentSongInfo]))
        menu.downloadMenu.downloadSig.connect(
            lambda quality: signalBus.downloadSongSig.emit(self.currentSongInfo, quality))
        menu.viewOnlineAct.triggered.connect(
            lambda: signalBus.getSongDetailsUrlSig.emit(self.currentSongInfo, QueryServerType.KUWO))
        menu.addToMenu.playingAct.triggered.connect(
            lambda: signalBus.addSongsToPlayingPlaylistSig.emit([self.currentSongInfo]))
        menu.addToMenu.addSongsToPlaylistSig.connect(
            lambda name: signalBus.addSongsToCustomPlaylistSig.emit(name, [self.currentSongInfo]))
        menu.addToMenu.newPlaylistAct.triggered.connect(
            lambda: signalBus.addSongsToNewCustomPlaylistSig.emit([self.currentSongInfo]))


class LocalSongListContextMenu(RoundMenu):
    """ Local song list widget context menu """

    def __init__(self, parent):
        super().__init__("", parent)
        self.playAct = QAction(self.tr("Play"), self)
        self.nextSongAct = QAction(self.tr("Play next"), self)
        self.showAlbumAct = QAction(self.tr("Show album"), self)
        self.viewOnlineAct = QAction(self.tr('View online'), self)
        self.showPropertyAct = QAction(self.tr("Properties"), self)
        self.addToMenu = AddToMenu(self.tr("Add to"), self)
        self.addActions([self.playAct, self.nextSongAct])
        self.addMenu(self.addToMenu)
        self.addActions(
            [self.showAlbumAct, self.viewOnlineAct, self.showPropertyAct])


class OnlineSongListContextMenu(RoundMenu):
    """ Online song list widget context menu """

    def __init__(self, parent):
        super().__init__("", parent)
        self.setObjectName('onlineSongListContextMenu')
        self.playAct = QAction(self.tr("Play"), self)
        self.nextSongAct = QAction(self.tr("Play next"), self)
        self.viewOnlineAct = QAction(self.tr('View online'), self)
        self.showPropertyAct = QAction(self.tr("Properties"), self)
        self.downloadMenu = DownloadMenu(self.tr('Download'), self)
        self.addToMenu = AddToMenu(self.tr("Add to"), self)
        self.addActions([self.playAct, self.nextSongAct])
        self.addMenu(self.addToMenu)
        self.addAction(self.viewOnlineAct)
        self.addMenu(self.downloadMenu)
        self.addAction(self.showPropertyAct)
