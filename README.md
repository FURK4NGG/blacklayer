## 👀 blacklayer Overview  
A lightweight, per-monitor screen saver for Hyprland that automatically dims inactive displays and instantly restores them on focus. It also supports optional global lock and display sleep actions after prolonged inactivity.  
<br><br>

https://github.com/user-attachments/assets/40fe7394-0690-441f-a1b9-12b85e41d43b

https://github.com/user-attachments/assets/a8207566-6148-4196-87dd-dba462894d42

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
sudo pacman -S gtk3 gdk-pixbuf2 gtk-layer-shell jq hypridle
```
<br><br>

Debian / Ubuntu  
!please install 'hypridle' manually!
```
sudo apt install \
libgtk-3-0 \
libgdk-pixbuf-2.0-0 \
libgtk-layer-shell0 \
jq

```
<br><br>

Fedora
```
sudo dnf install \
gtk3 \
gdk-pixbuf2 \
gtk-layer-shell \
jq \
hypridle
```
<br><br>

```
git clone https://github.com/furk4ngg/blacklayer.git  
cd blacklayer  
mkdir -p ~/.config/blacklayer  
cp blacklayer event-driven.sh blacklayer.conf blacklayer-worker.sh call-blacklayer.sh start-waybars.sh generate-waybar-configs.sh idle-lock.sh idle-sleep.sh idle-resume.sh "$BASE_DIR/" 2>/dev/null  
cp "/pending-relocation/hypridle.conf" "~/.config/hypr/" 2>/dev/null  
cp "/pending-relocation/hypridle.service" "~/.config/systemd/user/" 2>/dev/null  
sudo chown -R bob:bob ~/.config/blacklayer/  
chmod 700 ~/.config/blacklayer  
chmod +x ~/.config/blacklayer/*.sh 2>/dev/null || true  
chmod 600 ~/.config/blacklayer/*.conf 2>/dev/null || true  
[ -f ~/.config/blacklayer/blacklayer ] && chmod +x ~/.config/blacklayer/blacklayer
systemctl --user daemon-reload  
systemctl --user enable hypridle.service  
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
~/.config/blacklayer/call-blacklayer.sh
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
run_blacklayer=true → Enable per-monitor blacklayer  
run_lock=true  → Lock the session after inactivity  
run_sleep=true → Turn off all displays after longer inactivity  
LOOP_INTERVAL=60 → Main worker loop interval (in seconds)  
COUNT_THRESHOLD=5 → Inactivity trigger threshold  
EVENT_POLL_INTERVAL=3 → Event-driven polling interval (in seconds)  
resource= → Blacklayer background resource(png, jpg, gif)  

!If you want to change blacklayer color:  
Change the color value: blacklayer.c > static const GdkRGBA DEFAULT_COLOR = { 0.0, 0.0, 0.0, 1.0 };  
Then, compile the blacklayer.c file!  

## Here are the available settings in hypridle.conf:  
In hypridle.conf, the 'timeout:' values define how long the system must remain completely idle (no keyboard or mouse input) before the corresponding lock or sleep scripts are executed.  
<br><br>

## ❓ HOW IT WORKS ❓

## [blacklayer.conf]
- Stores Blacklayer configuration and resource settings  
- Blacklayer’a ait ayarların ve kaynakların tutulduğu dosyadır  

## [call-blacklayer.sh]
- Toggles Blacklayer by starting or stopping blacklayer-worker  
- Çağrıldığında blacklayer-worker’ı başlatır veya tüm işlemleri sonlandırır (toggle)  

## [blacklayer-worker.sh]
- Counts idle time and activates the screensaver while hiding other UI elements  
- Zamanı sayarak ekran koruyucuyu açar ve Waybar gibi diğer arayüzleri gizler  

## [blacklayer]
- Displays a fullscreen color, image, or animated GIF on the screen  
- Ekranda tercihe göre sadece renk, resim ya da GIF oynatır  

## [event-driven.sh]
- Listens for input events and stops Blacklayer when user activity is detected  
- Blacklayer aktifken çalışır ve mouse/etkileşim algılandığında ekran koruyucuyu kapatır  
<br><br>

## [generate-waybar-configs.sh]
- Generates one Waybar config per monitor from a single base config  
- Tek bir config dosyasından her monitör için ayrı Waybar config’i üretir  

## [start-waybars.sh]
- Starts all Waybar instances simultaneously  
- Tüm Waybar’ları aynı anda çalıştırmak için kullanılır  
<br><br>

## [HYPRIDLE]
user-run(call-blacklayer.sh)  -->  Run Hypridle  -->  Detect no movement for X time  -->  idle-lock.sh or idle-sleep.sh(controls the blacklayer.conf>run-lock,run-sleep values for the run)  -->  If value is true(Lock Screen or Sleep Screen process)  -->  When movement detected run(idle-resume.sh)  
<br><br>

## Roadmap
- [x] Changeable and resizable background(color, png, jpg, gif) using by .conf
- [x] Run logout codes when detect no movement in any monitor
- [x] Closes the screen when detect no movement in any monitor
- [ ] Moving the workspaces from the screen where Blacklayer is running to another screen

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
