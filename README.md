# OctoPuppet

OctoPuppet is an OctoPrint-based web interface for controlling 3D printers. OctoPuppet relies heavily on the original OctoPrint, incorporating changes and features to better meet the institutional needs of libraries, makerspaces, and FabLabs with large user bases, multiple printers, and where prints need to be tracked on per-user basis. 
OctoPuppet uses FabApp (a separate project developed in the UTA FabLab; the source will be released publicly soon) as the backend to track users’ prints while keeping the many cool features of OctoPrint intact.

# Installation
We recommend installing OctoPuppet on a Raspberry Pi, but it should work on any computer (Windows/Linux/Mac OS). The steps to install OctoPuppet are exactly the same as OctoPrint, but additional steps will be needed to connect the interface to the backend.

UTA-FabLab has prepared configuration scripts to help configure the system and make the installation a breeze (sources will be released soon)

## Manual Install Instructions:

The generic steps that should basically be done regardless of operating system and runtime environment are the following (as regular user, please keep your hands off of the sudo command here!) - this assumes you already have Python 2.7, pip and virtualenv set up on your system:

1. Checkout OctoPuppet: git clone https://github.com/UTA-FabLab/OctoPuppet.git
2. Change into the OctoPuppet folder: cd OctoPuppet
3. Edit the file `src/octoprint/static/js/viewmodels/app/printerstate.js` as follows:
    1. Replace all `DEV_ID` with device id of the 3D printer. The device id is defined in the FabApp backend.
    2. Replace `FLUD_BASE` with path to the root of flud.php
4. Create a user-owned virtual environment therein: virtualenv venv
5. Install OctoPuppet into that virtual environment: 

		Linux: 		./venv/bin/python setup.py install
		Windows:	venv\bin\python setup.py install

You may then start the OctoPuppet server via 
        
        /path/to/OctoPuppet/venv/bin/octoprint --serve.
        
The OctoPuppet instance can be now accessed at:

        http://127.0.0.1:5000 or http://IP-ADDRESS:5000

# Configuration

The config file config.yaml for OctoPuppet is expected in the settings folder, which is located at `~/.octoprint` on Linux, at `%APPDATA%/OctoPrint` on Windows and at `~/Library/Application Support/OctoPrint` on MacOS.

### Sample config.yaml

        accessControl:
          enabled: false
        api:
          allowCrossOrigin: true
          key: OctoAPI
        appearance:
          color: black
          name: 'DEV_NAME'
        feature:
          sdSupport: false
        plugins:
          softwareupdate:
         _config_version: 5
        printerProfiles:
          default: _default
        serial:
          autoconnect: true
          baudrate: 250000
          disconnectOnErrors: false
          port: /dev/ttyACM0
          timeout:
            communication: 86400.0
        server:
          commands:
            serverRestartCommand: sudo service octoprint restart
            systemRestartCommand: sudo reboot
        firstRun: false
        secretKey: 397gef997rh9834r92hr8389hr92h
        seenWizards:
          corewizard: null
          softwareupdate: null
        temperature:
      profiles:
        - bed: '110'
          extruder: '240'
          name: ABS
