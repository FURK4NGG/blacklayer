# blacklayer
A lightweight, per-monitor screen saver for Hyprland that automatically dims inactive displays and instantly restores them on focus.

# Blacklayer configration files (Setup Section) 

Required packets

Arch
```
sudo pacman -S jq
```

Debian / Ubuntu
```
sudo apt install jq
```

Fedora
```
sudo dnf install jq
```


mkdir -p ~/.config/blacklayer  
cp blacklayer event-driven.sh blacklayer.conf blacklayer-worker.sh call-blacklayer.sh ~/.config/blacklayer/  
chmod +x ~/.config/blacklayer/*.sh 2>/dev/null || true  
chmod 600 ~/.config/blacklayer/*.conf 2>/dev/null || true  
[ -f ~/.config/blacklayer/blacklayer ] && chmod +x ~/.config/blacklayer/blacklayer  
chmod 700 ~/.config/blacklayer  

sudo chown -R "$USER:$USER" ~/.config/waybar  
chmod 700 ~/.config/waybar  

./generate-waybar-configs.sh  



# For Waybar  
❌ exec-once = waybar &  
✅ exec-once = ~/.config/blacklayer/start-waybars.sh


Run/Stop
```
~/.config/blacklayer/call-blacklayer.sh
```

# Tips  
To verify whether the blacklayer process is running, use:  
ps aux | grep call-blacklayer.sh  

Note: The `grep` command itself may appear in the output.  

# Fast Installation   
sudo pacman -Syu git  
git clone https://github.com/furk4ngg/blacklayer.git  
cd blacklayer  
chmod +x install.sh  
./install.sh  
