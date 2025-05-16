# example systemd service file for the verification bot

```ini
[Unit]
Description=Verification Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/verification-discord-bot
ExecStart=/bin/bash -c "git reset --hard && git pull && source /path/to/verification-discord-bot/venv/bin/activate && python bot.py"
Restart=always
Environment="PYTHONUNBUFFERED=1"
Environment="RES_OPTIONS=attempts:3 timeout:5"
DNS=8.8.8.8 8.8.4.4

[Install]
WantedBy=multi-user.target
```

> **Notes:**
> - This service file ensures the bot runs in the background and restarts automatically if it crashes or is stopped.
> - It pulls the latest changes from the repository before starting and activates the virtual environment.
> - Replace `your_user` with your actual username.
> - Replace `/path/to/verification-discord-bot` with the actual path to your project directory.
> - The DNS settings use Google DNS servers in case the default DNS servers are unreachable, with a timeout of 5 seconds and 3 attempts.
> - Save this file as `/etc/systemd/system/verification-bot.service`.
> - make sure you have made the virtual environment and installed the requirements.

 ## Enable and Start the Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable verification-bot.service
sudo systemctl start verification-bot.service
```

## check the status of the service
```bash
sudo systemctl status verification-bot.service
```
This will show you the current status of the service, including any errors or logs.
## check the logs of the service
```bash
sudo journalctl -u verification-bot.service
```
This will show you the logs of the service, including any errors or logs.

to follow the logs in real time:
```bash
sudo journalctl -u verification-bot.service -f
```
this will tail the logs and show you the latest entries as they are written.