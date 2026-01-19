# blacklayer
A lightweight, per-monitor screen saver for Hyprland that automatically dims inactive displays and instantly restores them on focus.

# Blacklayer configration files (Setup Section) 

Required packets

Arch
```
sudo pacman -S gtk3 gdk-pixbuf2 gtk-layer-shell jq
```

Debian / Ubuntu
```
sudo apt install \
libgtk-3-0 \
libgdk-pixbuf-2.0-0 \
libgtk-layer-shell0 \
jq

```

Fedora
```
sudo dnf install \
gtk3 \
gdk-pixbuf2 \
gtk-layer-shell \
jq
```

```
mkdir -p ~/.config/blacklayer  
cp blacklayer event-driven.sh blacklayer.conf blacklayer-worker.sh call-blacklayer.sh start-waybars.sh generate-waybar-configs.sh ~/.config/blacklayer/  
sudo chown -R bob:bob ~/.config/blacklayer/  
chmod 700 ~/.config/blacklayer  
chmod +x ~/.config/blacklayer/*.sh 2>/dev/null || true  
chmod 600 ~/.config/blacklayer/*.conf 2>/dev/null || true  
[ -f ~/.config/blacklayer/blacklayer ] && chmod +x ~/.config/blacklayer/blacklayer  
```

 
# If you want to disappear waybar when blacklayer is active follow these steps: 
cd ~/.config/blacklayer/  
sudo chown -R "$USER:$USER" ~/.config/waybar  
chmod 700 ~/.config/waybar 
```
./generate-waybar-configs.sh  
```
Then delete your default "config" file from '~/.config/waybar/' directory  


# For Disappear Waybar  
❌ exec-once = waybar &  
✅ exec-once = ~/.config/blacklayer/start-waybars.sh


Run/Stop
```
~/.config/blacklayer/call-blacklayer.sh
```

# If you want to compile your special blacklayer.c document:
Arch
```
sudo pacman -S gcc pkgconf gtk3 gdk-pixbuf2 gtk-layer-shell jq
```

Debian / Ubuntu
```
sudo apt install \
build-essential \
pkg-config \
libgtk-3-dev \
libgdk-pixbuf-2.0-dev \
libgtk-layer-shell-dev \
jq
```

Fedora
```
sudo dnf install \
gcc \
pkg-config \
gtk3-devel \
gdk-pixbuf2-devel \
gtk-layer-shell-devel \
jq
```

Compile:
```
gcc -o ~/.config/blacklayer/blacklayer \
~/blacklayer/blacklayer.c \
$(pkg-config --cflags --libs gtk+-3.0 gdk-pixbuf-2.0) \
-lgtk-layer-shell
```

## Roadmap
- [x] Changeable background(png,jpg,gif) using by .conf
- [ ] Run logout codes when detect no movement

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
