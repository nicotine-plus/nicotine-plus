*** Settings ***
Documentation     Basic integration tests for nicotine+
...               Start nicotine both as a thread and as a process and check if
...               it is still alive after a few seconds
...
...               Keywords are defined in ``nicotine_library.py``.
Library           nicotine_library.py


*** Test Cases ***

Run nicotine as shell command
    Running nicotine starts a process    nicotine    3
    Result should be    ${True}

