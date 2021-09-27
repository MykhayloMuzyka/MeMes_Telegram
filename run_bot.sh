#!/bin/bash

screen -S bot
screen -r bot
source wd/AT_main/venv/bin/activate
cd MeMes_Telegram
python main.py