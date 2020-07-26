import sys

from system_hotkey import SystemHotkey

from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer,QAbstractAnimation,pyqtSignal
from PyQt5.QtGui import QBrush, QPainter,QPixmap,QFontMetrics,QFont
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from .play_button import PlayButton

sys.path.append('..')
from Groove.my_functions.is_not_leave import isNotLeave
from Groove.my_functions.get_album_cover_path import getAlbumCoverPath
from Groove.my_widget.my_button import ThreeStateButton
from Groove.my_widget.my_slider import Slider


class SubPlayWindow(QWidget):
    """ 桌面左上角子播放窗口 """

    def __init__(self, parent=None, songInfo: dict = None):
        super().__init__(parent)
        self.songInfo = {}
        if songInfo:
            self.songInfo = songInfo.copy()
        self.__lastSongIconPath = {'normal': r'resource\images\sub_play_window\lastSong_50_50_normal.png',
                                   'hover': r'resource\images\sub_play_window\lastSong_50_50_hover.png',
                                   'pressed': r'resource\images\sub_play_window\lastSong_50_50_pressed.png'}
        self.__nextSongIconPath = {'normal': r'resource\images\sub_play_window\nextSong_50_50_normal.png',
                                   'hover': r'resource\images\sub_play_window\nextSong_50_50_hover.png',
                                   'pressed': r'resource\images\sub_play_window\nextSong_50_50_pressed.png'}
        # 创建小部件
        self.volumeSlider = Slider(Qt.Vertical, self)
        self.volumeLabel = QLabel(self)
        self.lastSongButton = ThreeStateButton(
            self.__lastSongIconPath, self, (50, 50))
        self.playButton = PlayButton(self)
        self.nextSongButton = ThreeStateButton(
            self.__nextSongIconPath, self, (50, 50))
        self.albumPic = QLabel(self)
        self.songNameLabel = QLabel(self)
        self.songerNameLabel = QLabel(self)
        self.ani = QPropertyAnimation(self, b'windowOpacity')
        self.timer = QTimer(self)
        # 初始化
        self.__initWidget()

    def __initWidget(self):
        """ 初始化小部件 """
        self.move(62, 75)
        self.resize(635, 175)
        self.albumPic.move(478, 25)
        self.playButton.move(222, 26)
        self.volumeLabel.move(32, 140)
        self.volumeSlider.move(34, 25)
        self.songNameLabel.move(122, 93)
        self.lastSongButton.move(122, 26)
        self.nextSongButton.move(322, 26)
        self.songerNameLabel.move(122, 138)
        self.albumPic.setFixedSize(125, 125)
        self.songNameLabel.setFixedWidth(285)
        self.songerNameLabel.setFixedWidth(290)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        # 初始化动画和定时器
        self.timer.setInterval(3000)
        self.ani.setEasingCurve(QEasingCurve.Linear)
        self.ani.setDuration(700)
        self.ani.setStartValue(1)
        self.ani.setEndValue(0)
        # 分配ID
        self.volumeLabel.setObjectName('volumeLabel')
        self.songNameLabel.setObjectName('songNameLabel')
        self.songerNameLabel.setObjectName('songerNameLabel')
        # 设置层叠样式
        self.__setQss()
        # 将信号连接到槽
        self.connectSignalToSlot()
        self.volumeSlider.setValue(30)
        # 设置封面和标签
        self.updateWindow(self.songInfo)
        # 引用方法
        self.setPlay=self.playButton.setPlay

    def updateWindow(self, songInfo: dict):
        """ 设置窗口内容 """
        self.songInfo = songInfo.copy()
        self.songName = self.songInfo.get('songName', '未知歌名')
        self.songerName = self.songInfo.get('songer', '未知歌手')
        # 调整长度
        self.adjustText()
        # 更新标签和专辑封面
        self.songNameLabel.setText(self.songName)
        self.songerNameLabel.setText(self.songerName)
        self.setAlbumCover()

    def setAlbumCover(self):
        """ 设置封面 """
        # 如果专辑信息为空就直接隐藏
        self.coverPath = getAlbumCoverPath(self.songInfo.get('album',' ')[-1])
        self.albumPic.setPixmap(
            QPixmap(self.coverPath).scaled(
                125, 125, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def adjustText(self):
        """ 根据文本长度决定是否显示省略号 """
        fontMetrics_1 = QFontMetrics(QFont('Microsoft YaHei',17))
        self.songName = fontMetrics_1.elidedText(
            self.songName, Qt.ElideRight, 270)
        fontMetrics_2 = QFontMetrics(QFont('Microsoft YaHei', 9))
        self.songerName = fontMetrics_2.elidedText(
            self.songerName, Qt.ElideRight, 290)

    def timeOutEvent(self):
        """ 定时器溢出时间 """
        self.timer.stop()
        self.ani.start()

    def connectSignalToSlot(self):
        """ 将信号连接到槽 """
        self.ani.finished.connect(self.hide)
        self.timer.timeout.connect(self.timeOutEvent)
        self.volumeSlider.valueChanged.connect(
            lambda value:self.volumeLabel.setText(str(value)))

    def enterEvent(self, e):
        """ 鼠标进入时停止动画并重置定时器 """
        self.timer.stop()
        if self.ani.state() == QAbstractAnimation.Running:
            self.ani.stop()
            self.setWindowOpacity(1)

    def leaveEvent(self, e):
        """ 鼠标离开窗口时打开计时器 """
        # 判断事件发生的位置发生在自己所占的rect内
        notLeave = isNotLeave(self)
        if not notLeave:
            self.timer.start()

    def show(self):
        """ show()时重置透明度并根据鼠标位置决定是否打开计时器 """
        self.setWindowOpacity(1)
        super().show()
        notLeave = isNotLeave(self)
        if not notLeave:
            self.timer.start()
        
    def paintEvent(self, e):
        """ 绘制背景色 """
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        brush = QBrush(Qt.black)
        painter.setBrush(brush)
        # 绘制音量滑动条的背景
        painter.drawRect(0, 0, 81, 175)
        # 绘制控制面板的背景
        painter.drawRect(86, 0, 549, 175)
        
    def __setQss(self):
        """ 设置层叠样式 """
        with open(r'resource\css\subPlayWindow.qss',encoding='utf-8') as f:
            self.setStyleSheet(f.read())


class Demo(QWidget):
    printSig = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        songInfo = {'songName': 'ひねくれ (乖僻)',
                    'songer': '鎖那',
                    'album': ['Hush a by little girl']}
        self.subWindow = SubPlayWindow(self, songInfo)
        self.widget = QWidget(self)
        self.label = QLabel('测试', self.widget)
        self.resize(500, 500)
        self.printSig.connect(lambda:print('哈哈哈'))
        
    def enterEvent(self, QEvent):
        self.subWindow.show()
        self.printSig.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo = Demo()
    demo.show()
    demo.subWindow.show()
    sys.exit(app.exec_())
