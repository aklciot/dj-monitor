# Define constants
DEBUG = 10
INFO = 20
WARNING = 30
ERROR = 40
CRITICAL = 50

# ********************************************************************
def testPr(tStr, base=WARNING, level=INFO):
    if level >= base:       # only print if level is high enough
        if level <= 10:     # DEBUG
            print(tStr)
        elif level <= 20:   # INFO
            print(tStr)
        elif level <= 30:   # WARNING
            print(f"WARNING {tStr}") 
        elif level <= 40:   # WARNING
            print(f"ERROR {tStr}") 
        elif level <= 50:   # WARNING
            print(f"CRITICAL {tStr}") 
    return
