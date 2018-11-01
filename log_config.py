import logging

def set_log(name):
    logging.getLogger().setLevel(logging.INFO)
    format_str = '[%(asctime)s]['+name +'][%(filename)s][%(lineno)d][%(funcName)s][%(levelname)s]:%(message)s'
    formatter = logging.Formatter(format_str,'%Y-%m-%d %H:%M:%S')
    logging.getLogger().handlers.clear()
    c_handle = logging.StreamHandler()
    c_handle.setLevel(logging.INFO)
    c_handle.setFormatter(formatter)
    logging.getLogger().addHandler(c_handle)
