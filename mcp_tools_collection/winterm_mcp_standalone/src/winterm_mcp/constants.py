"""
常量定义 - winterm-mcp
"""

NAME = "winterm-mcp"
VERSION = "0.1.7"

ENV_POWERSHELL_PATH = "WINTERM_POWERSHELL_PATH"
ENV_CMD_PATH = "WINTERM_CMD_PATH"
ENV_PYTHON_PATH = "WINTERM_PYTHON_PATH"
ENV_LOG_LEVEL = "WINTERM_LOG_LEVEL"

POWERSHELL_PATHS = [
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
]

PWSH_PATHS = [
    r"C:\Program Files\PowerShell\7\pwsh.exe",
    r"C:\Program Files (x86)\PowerShell\7\pwsh.exe",
]

CMD_PATHS = [
    r"C:\Windows\System32\cmd.exe",
]

PTY_COLS = 80
PTY_ROWS = 30

MIN_TIMEOUT = 1
MAX_TIMEOUT = 3600
DEFAULT_TIMEOUT = 30
