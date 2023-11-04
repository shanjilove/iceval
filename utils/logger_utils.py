import logging
import os
import time
from logging import handlers
from rest_framework.response import Response

from iceval.settings import PROJECT_RUNDIR
from utils.custom_exception import  SxopeException


class SafeTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False,
                 atTime=None, maxBytes=50 * 1024 * 1024):
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
        self.maxBytes = maxBytes

    def shouldRollover(self, record):
        """
        Determine if rollover should occur.

        record is not used, as we are just comparing times, but it is needed so
        the method signatures are the same
        """
        t = int(time.time())
        if t >= self.rolloverAt:
            return 1
        if self.stream is None:  # delay was set...
            self.stream = self._open()
        if self.maxBytes > 0:  # are we rolling over?
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, 2)  # due to non-posix-compliant Windows feature
            if self.stream.tell() + len(msg) >= self.maxBytes:
                return 1
        return 0

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        # get the time that this sequence started at and make it a time_tuple
        current_time = int(time.time())
        dst_now = time.localtime(current_time)[-1]
        t = self.rolloverAt - self.interval
        if self.utc:
            time_tuple = time.gmtime(t)
        else:
            time_tuple = time.localtime(t)
            dst_then = time_tuple[-1]
            if dst_now != dst_then:
                addend = 3600 if dst_now else -3600
                time_tuple = time.localtime(t + addend)
        dfn = self.rotation_filename(
            f"{self.baseFilename}.{time.strftime(self.suffix, time_tuple)}"
        )

        # 存在删除逻辑去掉
        self.rotate(self.baseFilename, dfn)
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)
        if not self.delay:
            self.stream = self._open()
        new_rollover_at = self.computeRollover(current_time)
        while new_rollover_at <= current_time:
            new_rollover_at = new_rollover_at + self.interval
        # If DST changes and midnight or weekly rollover, adjust for this.
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dst_at_rollover = time.localtime(new_rollover_at)[-1]
            if dst_now != dst_at_rollover:
                addend = 3600 if dst_now else -3600
                new_rollover_at += addend
        self.rolloverAt = new_rollover_at

    def rotate(self, source, dest):

        if callable(self.rotator):
            self.rotator(source, dest)

        elif os.path.exists(source):
            if os.path.exists(dest):
                os.remove(dest)
            os.rename(source, dest)


def setup_log(name=None):
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s[%(lineno)d] - %(funcName)s - %(message)s ')

    # file handler
    directory = f'{PROJECT_RUNDIR}/logs'
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_name = os.path.abspath(os.path.join(directory, f"daily_log_{name}.log"))
    file_handler = SafeTimedRotatingFileHandler(
        file_name, when='MIDNIGHT', backupCount=0, encoding='utf8', maxBytes=1024 * 1024 * 1024)
    file_handler.setFormatter(log_formatter)

    # stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)

    g_logger = logging.getLogger()
    g_logger.setLevel(logging.INFO)
    if g_logger.handlers:
        g_logger.handlers = []
    g_logger.addHandler(file_handler)
    g_logger.addHandler(stream_handler)
    return g_logger


logger = setup_log('iceval')


def handler_exception():
    def decorated(func):
        def inner(*args, **kwargs):
            try:
                logger.info(f"{func.__module__}.input:  Request---{args[0].get_view_name()}: {args[1].get_full_path()}")
                result = func(*args, **kwargs)
                logger.info(f"{func.__module__}.output:  Request---{args[0].get_view_name()}: {args[1].get_full_path()} Response---result: {result.status_code}")
                return result
            except SxopeException as e:
                logger.exception(e)
                logger.error(f"{func.__module__}.input: {args[0].get_view_name()}---{args[1].get_full_path()}  {e}")
                logger.debug(f"{func.__name__}.output: {args[0].get_view_name()}---{args[1].get_full_path()}  {e}")
                return Response({'message': e.error_message}, status=e.error_code)
        return inner

    return decorated

if __name__ == '__main__':
    setup_log()
