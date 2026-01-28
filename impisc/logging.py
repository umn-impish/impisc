"""
Standard functions for logging to the system journal with syslog.
"""

import syslog


def log_debug(s: str):
    syslog.syslog(syslog.LOG_DEBUG, s)

def log_info(s: str):
    syslog.syslog(syslog.LOG_INFO, s)

def log_warning(s: str):
    syslog.syslog(syslog.LOG_WARNING, s)

def log_error(s: str):
    syslog.syslog(syslog.LOG_ERR, s)