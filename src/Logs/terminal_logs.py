
def sucesfull_log(log)->None:
    sucesfull_bg = "\033[1;32m(SUCESSO):"
    sucesfull_end = "\033[m"
    if isinstance(log, str):
        log = log.upper()
    print(sucesfull_bg, log, sucesfull_end)
    
def check_api(log)->None:
    check_bg = "\033[1;36m(CHECK):"
    check_end = "\033[m"
    if isinstance(log, str):
        log = log.upper()
    print(check_bg, log, check_end)
    
def check_task(log)->None:
    check_bg = "\033[1m(CHECK):"
    check_end = "\033[m"
    if isinstance(log, str):
        log = log.upper()
    print(check_bg, log, check_end)
    
def warning_log(log)->None:
    warning_bg = "\033[1;33m(ATENÇÃO):"
    warning_end = "\033[m"
    if isinstance(log, str):
        log = log.upper()
    print(warning_bg, log, warning_end)    
        
def error_log(log)->None:
    error_bg = "\033[4;1;31m(ERRO):"
    error_end = "\033[m"
    if isinstance(log, str):
        log = log.upper()
    print(error_bg, log, error_end)