# blacklayer
A lightweight, per-monitor screen saver for Hyprland that automatically dims inactive displays and instantly restores them on focus.

Fast Installation
sudo pacman -Syu git
git clone https://github.com/furk4ngg/blacklayer.git
cd blacklayer
chmod +x install.sh
./install.sh

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

Run
```
~/.config/blacklayer/call-blacklayer.sh
```
