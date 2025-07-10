minimal (and poorly written) bm869s mqtt line protocol (influx) logger
based of https://github.com/TheHWcave/BM869S-remote-access/blob/main/BM869S.py

## usage
1) install uv or manualy create enviroment with  
2) create .env file based on provided sample
3) `uv run main.py`  

### linux
on linux make sure that your user has permission to access hidraw device

### WSL2
debian based wsl images have systemd disabled by default, becouse of that hid devices are not mounted properly
