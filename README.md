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

Run
```
~/.config/blacklayer/call-blacklayer.sh
```  


#Tips
To verify whether the blacklayer process is running, use:
ps aux | grep call-blacklayer.sh  

Note: The `grep` command itself may appear in the output.  

# Fast Installation   
sudo pacman -Syu git  
git clone https://github.com/furk4ngg/blacklayer.git  
cd blacklayer  
chmod +x install.sh  
./install.sh  
