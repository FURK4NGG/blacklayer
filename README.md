## 👀 blacklayer Overview  
A lightweight, per-monitor inactivity screen saver for Hyprland that automatically dims inactive displays and instantly restores them when activity is detected. It supports both single-target and independent per-monitor activity monitoring, with optional session locking and system suspend after prolonged inactivity.  
<br><br>

[![blacklayer Demo Video](https://github.com/user-attachments/assets/c99873a1-ef0a-42a6-a6e8-66ede9074440)](https://github.com/user-attachments/assets/40fe7394-0690-441f-a1b9-12b85e41d43b)

[![blacklayer Demo Video](https://github.com/user-attachments/assets/68f1ec5e-6734-45d1-9a4e-756ea2b618a6)](https://github.com/user-attachments/assets/a8207566-6148-4196-87dd-dba462894d42)


<br><br>
# ✅ Works On
wlroots-based Wayland compositors (Hyprland, Sway, River, Wayfire, Hikari, Labwc(wlroots based) )
<br><br>

# ⚠️ PARTIALLY / LIMITED 
GNOME (Wayland), KDE Plasma (Wayland) !Not tested!
<br><br>

## 📦 Setup  

Required packets

Arch
```
sudo pacman -S \
gtk3 \
gdk-pixbuf2 \
gtk-layer-shell \
jq \
python \
python-gobject \
python-evdev \
libadwaita
```
<br><br>

Debian / Ubuntu  
```
sudo apt install \
python3 \
python3-gi \
python3-evdev \
gir1.2-gtk-3.0 \
gir1.2-adwaita-1 \
libgtk-3-0 \
libgdk-pixbuf-2.0-0 \
libgtk-layer-shell0 \
libadwaita-1-0 \
jq
```
<br><br>

Fedora
```
sudo dnf install \
python3 \
python3-gobject \
python3-evdev \
gtk3 \
gdk-pixbuf2 \
gtk-layer-shell \
libadwaita \
jq
```
<br><br>

```
git clone https://github.com/furk4ngg/blacklayer.git
cd blacklayer
mkdir -p ~/.config/blacklayer
cp blacklayer \
   blacklayer.c \
   blacklayer.conf \
   blacklayer-worker.sh \
   input-activity.py \
   start-waybars.sh \
   blacklayer-ui.py \
   generate-waybar-configs.sh \
   LICENSE \
   README.md \
   ~/.config/blacklayer/

sudo chown -R "$USER:$USER" ~/.config/blacklayer/
chmod 700 ~/.config/blacklayer
chmod +x \
    ~/.config/blacklayer/blacklayer \
    ~/.config/blacklayer/blacklayer-worker.sh \
    ~/.config/blacklayer/input-activity.py \
    ~/.config/blacklayer/blacklayer-ui.py \
    ~/.config/blacklayer/start-waybars.sh \
    ~/.config/blacklayer/generate-waybar-configs.sh

chmod 600 ~/.config/blacklayer/blacklayer.conf
mkdir -p ~/.config/blacklayer/.blacklayer_state/pids
mkdir -p ~/.config/blacklayer/.blacklayer_state/waybar
chmod 700 ~/.config/blacklayer/.blacklayer_state
chmod 700 ~/.config/blacklayer/.blacklayer_state/pids
chmod 700 ~/.config/blacklayer/.blacklayer_state/waybar
```

 
# If you want to disappear waybar(for use 100% of screen) when blacklayer is active follow these steps: 
```
sudo chown -R "$USER:$USER" ~/.config/waybar  
chmod 700 ~/.config/waybar  
cd ~/.config/blacklayer/  
./generate-waybar-configs.sh  
```
Change these codes in your hyprland.conf document  
❌ exec-once = waybar &  
✅ exec-once = ~/.config/blacklayer/start-waybars.sh


## 🎉 Run/Stop blacklayer
```
~/.config/blacklayer/blacklayer-ui.py
```

## Reset
```
cd ~/.config/blacklayer

pkill -KILL -f "$HOME/.config/blacklayer/blacklayer-worker.sh" 2>/dev/null || true
pkill -KILL -f "$HOME/.config/blacklayer/input-activity.py" 2>/dev/null || true

rm -f ~/.config/blacklayer/blacklayer_worker.pid
rm -f ~/.config/blacklayer/.input_main_monitor
rm -f ~/.config/blacklayer/.input_activity
rm -f ~/.config/blacklayer/.input_activity.*
rm -f ~/.config/blacklayer/.blacklayer_state/pids/*.pid
rm -f ~/.config/blacklayer/.blacklayer_state/waybar/*.pid
rm -f ~/.config/blacklayer/.waybar_restore.lock
rm -f ~/.config/blacklayer/event-driven.sh
rm -f ~/.config/blacklayer/.blacklayer_idle.py
rm -f ~/.config/blacklayer/hypridle.conf
rm -f ~/.config/blacklayer/hypridle.service

chmod +x blacklayer
chmod +x blacklayer-worker.sh
chmod +x input-activity.py
chmod +x blacklayer-ui.py
chmod +x start-waybars.sh
chmod +x generate-waybar-configs.sh

chmod 600 blacklayer.conf

mkdir -p .blacklayer_state/pids
mkdir -p .blacklayer_state/waybar

chmod 700 .blacklayer_state
chmod 700 .blacklayer_state/pids
chmod 700 .blacklayer_state/waybar
```

# If you want to compile your special blacklayer.c document:
Arch
```
sudo pacman -S gcc pkgconf gtk3 gdk-pixbuf2 gtk-layer-shell jq
```
<br><br>

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
<br><br>

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
<br><br>

Compile:
```
gcc -o ~/.config/blacklayer/blacklayer \
~/blacklayer/blacklayer.c \
$(pkg-config --cflags --libs gtk+-3.0 gdk-pixbuf-2.0) \
-lgtk-layer-shell
```
<br><br>

## Here are the available settings in blacklayer.conf:  
run_blacklayer=true → Enables Blacklayer after the inactivity threshold is reached  
run_lock=true → Locks the session after the configured LOCK_DELAY  
run_sleep=true → Suspends the system after the configured SLEEP_DELAY  
BLACKLAYER_DELAY=5 → Inactivity time before Blacklayer opens  
LOCK_DELAY=9 → Inactivity time before the session is locked  
SLEEP_DELAY=20 → Inactivity time before the system is suspended  
USE_INPUT_ACTIVITY=true → Monitors the focused monitor at the moment Run is clicked  
USE_INPUT_ACTIVITY=false → Uses an independent inactivity timer for each monitor  
resource= → Blacklayer background resource(png, jpg, gif)  

!If you want to change blacklayer color:  
Change the color value: blacklayer.c > static const GdkRGBA DEFAULT_COLOR = { 0.0, 0.0, 0.0, 1.0 };  
Then, compile the blacklayer.c file!  

<br><br>

## ❓ HOW IT WORKS ❓

                  Hyprland monitor count
                           │
                ┌──────────┴──────────┐
                │                     │
             1 monitor              2+ monitors
                │                     │
                ▼                     ▼
        INPUT ACTIVITY          USE_INPUT_ACTIVITY?
           REQUIRED                  │
                │              ┌─────┴─────┐
                │             true        false
                │              │             │
                ▼              ▼             ▼
       input-activity.py   TARGET MONITOR  EACH MONITOR
                │              │          INDEPENDENT TIMER
                │              │             │
                ▼              ▼             ▼
        Inactivity timer   Input activity  Input activity
                │              │             │
                ▼              ▼             ▼
           Blacklayer      Blacklayer     Blacklayer
                │              │             │
                ▼              ▼             ▼
       Input → close      Input → close   Input → close
         Blacklayer         Blacklayer      Blacklayer



                  USER INPUT
                      │
             ┌────────┴────────┐
             │                 │
          Keyboard            Mouse
             │                 │
             ▼                 ▼
       Focused monitor    Cursor monitor
             │                 │
             └────────┬────────┘
                      ▼
              input-activity.py
                      │
                      ▼
             activity timestamp
                      │
                      ▼
            blacklayer-worker.sh
                      │
          ┌───────────┴───────────┐
          │                       │
    BLACKLAYER_DELAY          LOCK / SLEEP
          │                       │
          ▼                       ▼
      Blacklayer             Lock / Suspend
      

## [blacklayer.conf]
- Stores Blacklayer configuration and resource settings  
- Blacklayer’a ait ayarların ve kaynakların tutulduğu dosyadır  

## [blacklayer-worker.sh]
- Manages inactivity timers and triggers Blacklayer, lock, and suspend actions  
- Inactivity sürelerini yönetir ve Blacklayer, kilitleme ve suspend işlemlerini tetikler  

## [input-activity.py]
- Monitors keyboard and mouse activity and resets the corresponding inactivity timer  
- Klavye ve mouse hareketlerini izler ve ilgili inactivity timer’ını sıfırlar  

## [blacklayer-ui.py]
- Provides the Blacklayer configuration interface and controls the Run / Stop state of the worker  
- Blacklayer yapılandırma arayüzünü sağlar ve worker’ın Run / Stop durumunu kontrol eder  

## [blacklayer]
- Displays a fullscreen color, image, or GIF on the monitor  
- Monitörde tam ekran renk, resim veya GIF görüntüler  

## [blacklayer.c]
- Contains the source code for the native Blacklayer application  
- Native Blacklayer uygulamasının kaynak kodunu içerir  

## [start-waybars.sh]
- Starts a separate Waybar instance for each monitor using its generated configuration  
- Oluşturulan yapılandırmaları kullanarak her monitör için ayrı bir Waybar örneği başlatır  

## [generate-waybar-configs.sh]
- Generates the required Waybar configuration for each monitor  
- Her monitör için gerekli Waybar yapılandırmasını oluşturur  
<br><br>

## Roadmap
- [x] Changeable and resizable background(color, png, jpg, gif) using by .conf
- [x] Run logout codes when detect no movement in any monitor
- [x] Closes the screen when detect no movement in any monitor
- [ ] Moving the workspaces from the screen where Blacklayer is running to another screen
- [ ] Clock widget

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

<br><br>

## 🔒 License  
<h1 align="center">📜 GPL-3.0 License</h1>
