# coding:utf-8
import os
from math import ceil

from common.crawler import KuWoMusicCrawler
from common.database.entity import SongInfo
from common.library import Library
from common.signal_bus import signalBus
from common.thread.download_song_thread import DownloadSongThread
from components.widgets.label import PixmapLabel
from components.widgets.scroll_area import ScrollArea
from components.widgets.state_tooltip import DownloadStateTooltip
from PyQt5.QtCore import QFile, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from .album_group_box import AlbumGroupBox
from .playlist_group_box import PlaylistGroupBox
from .song_group_box import SongGroupBox


class SearchResultInterface(ScrollArea):
    """ Search result interface """

    downloadFinished = pyqtSignal(str)    # 下载歌曲完成
    playLocalSongSig = pyqtSignal(int)    # 播放本地歌曲
    playOnlineSongSig = pyqtSignal(int)   # 播放在线音乐

    def __init__(self, library: Library, onlineMusicPageSize=10, onlinePlayQuality='Standard quality',
                 downloadFolder='app/download', parent=None):
        """
        Parameters
        ----------
        onlineMusicPageSize: int
            number of online songs displayed per page

        onlinePlayQuality: str
            online play quality, including  `Standard quality`, `High quality` and `Super quality`

        downloadFolder: str
            the folder to save downloaded music

        parent:
            parent window
        """
        super().__init__(parent=parent)
        self.library = library
        self.keyWord = ''            # searched key word
        self.playlists = {}          # matched local playlists
        self.albumInfos = []         # matched album information
        self.localSongInfos = []     # matched song information
        self.onlineSongInfos = []    # matched online information

        self.titleLabel = QLabel(self)
        self.searchLabel = PixmapLabel(self)
        self.scrollWidget = QWidget(self)
        self.vBox = QVBoxLayout(self.scrollWidget)
        self.albumGroupBox = AlbumGroupBox(library, self.scrollWidget)
        self.playlistGroupBox = PlaylistGroupBox(library, self.scrollWidget)
        self.localSongGroupBox = SongGroupBox('Local songs', self.scrollWidget)
        self.onlineSongGroupBox = SongGroupBox(
            'Online songs', self.scrollWidget)
        self.searchOthersLabel = QLabel(
            self.tr("Try searching for something else."), self)
        self.checkSpellLabel = QLabel(
            self.tr('Check your spelling, or search for something else'), self)

        self.localSongListWidget = self.localSongGroupBox.songListWidget
        self.onlineSongListWidget = self.onlineSongGroupBox.songListWidget

        self.crawler = KuWoMusicCrawler()
        self.totalPages = 1                             # 在线音乐总分页数
        self.currentPage = 1                            # 当前在线音乐页码
        self.totalOnlineMusic = 0                       # 数据库中所有符合条件的在线音乐数
        self.downloadFolder = downloadFolder            # 在线音乐的下载目录
        self.onlinePlayQuality = onlinePlayQuality      # 在线音乐播放音质
        self.onlineMusicPageSize = onlineMusicPageSize  # 每页最多显示的在线音乐数量

        self.downloadSongThread = DownloadSongThread(self.downloadFolder, self)
        self.downloadStateTooltip = None
        self.__initWidget()

    def __initWidget(self):
        """ initialize widgets """
        self.vBox.setSpacing(20)
        self.vBox.setContentsMargins(0, 10, 0, 116)
        self.vBox.addWidget(self.albumGroupBox)
        self.vBox.addWidget(self.playlistGroupBox)
        self.vBox.addWidget(self.localSongGroupBox)
        self.vBox.addWidget(self.onlineSongGroupBox)
        self.setWidget(self.scrollWidget)
        self.setViewportMargins(0, 115, 0, 0)
        self.__setQss()
        self.searchLabel.setPixmap(
            QPixmap(":/images/search_result_interface/Search.png"))
        self.__setHintsLabelVisible(False)
        self.titleLabel.move(30, 55)
        self.titleLabel.raise_()
        self.resize(1200, 500)
        self.__connectSignalToSlot()

    def resizeEvent(self, e):
        self.scrollWidget.resize(self.width(), self.scrollWidget.height())
        self.albumGroupBox.resize(self.width(), self.albumGroupBox.height())
        self.localSongGroupBox.resize(
            self.width(), self.localSongGroupBox.height())
        self.onlineSongGroupBox.resize(
            self.width(), self.onlineSongGroupBox.height())
        self.searchLabel.move(self.width()//2-self.searchLabel.width()//2, 138)
        self.checkSpellLabel.move(
            self.width()//2-self.checkSpellLabel.width()//2, 225)
        self.searchOthersLabel.move(
            self.width()//2-self.searchOthersLabel.width()//2, 300)
        self.playlistGroupBox.resize(
            self.width(), self.playlistGroupBox.height())

    def __setQss(self):
        """ set style sheet """
        self.titleLabel.setObjectName('titleLabel')
        self.checkSpellLabel.setObjectName('checkSpellLabel')
        self.searchOthersLabel.setObjectName('searchOthersLabel')

        f = QFile(":/qss/search_result_interface.qss")
        f.open(QFile.ReadOnly)
        self.setStyleSheet(str(f.readAll(), encoding='utf-8'))
        f.close()

        self.checkSpellLabel.adjustSize()
        self.searchOthersLabel.adjustSize()

    def __setHintsLabelVisible(self, isVisible: bool):
        """ set the visibility of hints label """
        self.searchLabel.setVisible(isVisible)
        self.checkSpellLabel.setVisible(isVisible)
        self.searchOthersLabel.setVisible(isVisible)

    def __downloadSong(self, songInfo: SongInfo, quality: str):
        """ download online music """
        self.downloadSongThread.appendDownloadTask(songInfo, quality)
        if self.downloadSongThread.isRunning():
            self.downloadStateTooltip.appendOneDownloadTask()
            return

        title = self.tr('Downloading songs')
        content = self.tr('There are') + f' {1} ' + \
            self.tr('left. Please wait patiently')
        self.downloadStateTooltip = DownloadStateTooltip(
            title, content, 1, self.window())
        self.downloadSongThread.downloadOneSongFinished.connect(
            self.downloadStateTooltip.completeOneDownloadTask)

        pos = self.downloadStateTooltip.getSuitablePos()
        self.downloadStateTooltip.move(pos)
        self.downloadStateTooltip.show()
        self.downloadSongThread.start()

    def __onDownloadAllComplete(self):
        """ download finished slot """
        self.downloadStateTooltip = None
        self.downloadFinished.emit(self.downloadFolder)

    def search(self, keyWord: str):
        """ search local songs, albums, playlist and online songs """
        self.keyWord = keyWord

        # match album information
        self.albumInfos = self.library.albumInfoController.getAlbumInfosLike(
            singer=keyWord,
            album=keyWord
        )

        # match local song information
        self.localSongInfos = self.library.songInfoController.getSongInfosLike(
            file=keyWord,
            title=keyWord,
            singer=keyWord,
            album=keyWord
        )

        # match local playlist
        self.playlists = self.library.playlistController.getPlaylistsLike(
            name=keyWord,
            singer=keyWord,
            album=keyWord
        )

        # search online songs
        self.currentPage = 1
        self.onlineSongInfos, self.totalOnlineMusic = self.crawler.getSongInfos(
            keyWord, 1, self.onlineMusicPageSize)
        self.totalPages = 1 if not self.totalOnlineMusic else ceil(
            self.totalOnlineMusic/self.onlineMusicPageSize)

        self.__updateLoadMoreLabel()

        # update window
        self.titleLabel.setText(f'"{keyWord}"'+self.tr('Search Result'))
        self.titleLabel.adjustSize()
        self.albumGroupBox.updateWindow(self.albumInfos)
        self.playlistGroupBox.updateWindow(self.playlists)
        self.localSongGroupBox.updateWindow(self.localSongInfos[:5])
        self.onlineSongGroupBox.updateWindow(self.onlineSongInfos)

        self.__adjustHeight()
        self.__updateWidgetsVisible()
        self.verticalScrollBar().setValue(0)

    def __adjustHeight(self):
        """ adjust window height """
        isAlbumVisible = len(self.albumInfos) > 0
        isPlaylistVisible = len(self.playlists) > 0
        isLocalSongVisible = len(self.localSongInfos) > 0
        isOnlineSongVisible = len(self.onlineSongInfos) > 0

        visibleNum = isAlbumVisible+isLocalSongVisible + \
            isPlaylistVisible+isOnlineSongVisible
        spacing = 0 if not visibleNum else (visibleNum-1)*20

        self.scrollWidget.resize(
            self.width(),
            241 + isAlbumVisible*self.albumGroupBox.height() +
            isLocalSongVisible*self.localSongGroupBox.height() +
            isOnlineSongVisible*self.onlineSongGroupBox.height() +
            isPlaylistVisible*self.playlistGroupBox.height() + spacing
        )
        self.__setHintsLabelVisible(visibleNum == 0)

    def __updateWidgetsVisible(self):
        """ update the visibility of widgets """
        self.albumGroupBox.setVisible(bool(self.albumInfos))
        self.playlistGroupBox.setVisible(bool(self.playlists))
        self.localSongGroupBox.setVisible(bool(self.localSongInfos))
        self.onlineSongGroupBox.setVisible(bool(self.onlineSongInfos))
        if self.albumGroupBox.isHidden() and self.localSongGroupBox.isHidden() and \
                self.playlistGroupBox.isHidden() and self.onlineSongGroupBox.isHidden():
            self.__setHintsLabelVisible(True)

    def setDownloadFolder(self, folder: str):
        """ set the folder to download online music """
        if not os.path.exists(folder):
            raise ValueError(f"The folder `{folder}` doesn't exists")

        self.downloadSongThread.downloadFolder = folder
        self.downloadFolder = folder

    def setOnlinePlayQuality(self, quality: str):
        """ set online music quality """
        if quality not in ['Standard quality', 'High quality', 'Super quality']:
            raise ValueError(f'The quality `{quality}` is illegal')

        self.onlinePlayQuality = quality

    def setOnlineMusicPageSize(self, pageSize: int):
        """ set online music page size """
        self.onlineMusicPageSize = pageSize if pageSize > 0 else 20

    def __updateLoadMoreLabel(self):
        """ update load more label """
        label = self.onlineSongGroupBox.loadMoreLabel

        if self.currentPage < self.totalPages:
            label.setText(self.tr('Load more'))
            label.setProperty('loadFinished', 'false')
            label.setCursor(Qt.PointingHandCursor)
        else:
            label.setText(self.tr('No more results'))
            label.setProperty('loadFinished', 'true')
            label.setCursor(Qt.ArrowCursor)

        label.adjustSize()
        label.setStyle(QApplication.style())

    def __loadMoreOnlineMusic(self):
        """ load more online music """
        if self.currentPage == self.totalPages:
            return

        # send request for online music
        self.currentPage += 1
        songInfos, _ = self.crawler.getSongInfos(
            self.keyWord, self.currentPage, self.onlineMusicPageSize)

        # update online music group box
        offset = len(self.onlineSongListWidget.songInfos)
        self.onlineSongGroupBox.loadMoreOnlineMusic(songInfos)
        self.onlineSongInfos = self.onlineSongListWidget.songInfos

        self.__updateLoadMoreLabel()
        self.__adjustHeight()

    def deletePlaylistCard(self, name: str):
        """ delete a playlist card """
        self.playlistGroupBox.playlistCardView.deletePlaylistCard(name)
        if len(self.playlistGroupBox.playlistCards) == 0:
            self.playlistGroupBox.hide()
            self.__adjustHeight()

    def __connectSignalToSlot(self):
        """ connect signal to slot """
        # local song group box signal
        self.localSongGroupBox.switchToMoreSearchResultInterfaceSig.connect(
            lambda: signalBus.switchToMoreSearchResultInterfaceSig.emit(self.keyWord, 'local song', self.localSongInfos))
        self.localSongListWidget.playSignal.connect(self.playLocalSongSig)

        # online song group box signal
        self.onlineSongListWidget.playSignal.connect(self.playOnlineSongSig)
        self.onlineSongListWidget.downloadSig.connect(self.__downloadSong)
        self.onlineSongGroupBox.loadMoreSignal.connect(
            self.__loadMoreOnlineMusic)

        # album group box signal
        self.albumGroupBox.switchToMoreSearchResultInterfaceSig.connect(
            lambda: signalBus.switchToMoreSearchResultInterfaceSig.emit(self.keyWord, 'album', self.albumInfos))

        # playlist group box signal
        self.playlistGroupBox.switchToMoreSearchResultInterfaceSig.connect(
            lambda: signalBus.switchToMoreSearchResultInterfaceSig.emit(self.keyWord, 'playlist', self.playlists))

        # down thread signal
        self.downloadSongThread.finished.connect(self.__onDownloadAllComplete)
