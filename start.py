import sys
import os

# PyQt5中使用的基本控件都在PyQt5.QtWidgets模块中
from PyQt5.QtWidgets import QApplication, QMainWindow
# 导入designer工具生成的login模块
from ui import Ui_MainWindow


class MyMainForm(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MyMainForm, self).__init__(parent)
        self.setupUi(self)

        self.pushButton.clicked.connect(self.display)

    def display(self):
        FileName = self.FilePath.text()
        StartAddress = self.StartAddress.text()
        EndAddress = self.EndAddress.text()
        Cpu = self.CPU_MODEL.text()
        model = self.Model.text()
        FileFullName = FileName + ".so"
        newfile = FileName + "_recovered.so"
        trace = self.TraceText.text()
        if (Cpu == "arm"):
            flag = "0"
        else:
            flag = "1"
        cmd = 'python deobf.py ' + FileFullName + " " + newfile + " " + trace + ' ' + StartAddress + ' ' + EndAddress + ' ' + flag + " " + model
        self.textBrowser.setText(cmd)
        os.system(cmd)
        self.textBrowser.setText("success!")



if __name__ == "__main__":
    # 固定的，PyQt5程序都需要QApplication对象。sys.argv是命令行参数列表，确保程序可以双击运行
    app = QApplication(sys.argv)
    # 初始化
    myWin = MyMainForm()
    # 将窗口控件显示在屏幕上
    myWin.show()
    # 程序运行，sys.exit方法确保程序完整退出。
    sys.exit(app.exec_())