"""Qt日志处理器 -- 将logging输出捕获到PyQt6信号，供QTextEdit显示"""
import logging
from PyQt6.QtCore import QObject, pyqtSignal


class QtLogSignal(QObject):
    """日志信号桥接：线程安全的logging->Qt信号"""
    log_message = pyqtSignal(str)


class QtLogHandler(logging.Handler):
    """自定义logging.Handler，将日志记录通过Qt信号发射

    用法:
        log_signal = QtLogSignal()
        handler = QtLogHandler(log_signal)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                                                datefmt="%H:%M:%S"))
        logging.getLogger().addHandler(handler)
        # 在MainWindow中连接: log_signal.log_message.connect(self.log_output.append)
    """

    def __init__(self, signal: QtLogSignal):
        super().__init__()
        self.signal = signal

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.signal.log_message.emit(msg)
        except Exception:
            pass  # 日志处理器自身不应抛异常
