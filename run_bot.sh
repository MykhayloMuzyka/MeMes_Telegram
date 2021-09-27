#!/bin/bash

screen -S bot
source wd/AT_main/venv/bin/activate
screen -S bot cd /MeMes_Telegram
screen -S python main.py