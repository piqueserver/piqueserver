# Config directory

Structure as follows:

```
.
├── config.json                 # default config file if no file specified
├── config.json.default         # backup config file (same as config.json as supplied)
├── logs                        # logs directory 
│   └── log.txt                 #  default server logfile
├── maps                        # maps in .txt generate script form or .vxl data
│   ├── classicgen.txt          #  includes a couple of simple maps - add any maps you want to use here
│   └── ...
└── scripts                     # contains all scripts and extensions - load by adding name to script list in config
    ├── __init__.py             #  don't delete this - needed so python can import scripts for this directory
    ├── afk.py                  #  huge number of scripts included - see each file for more information, instructions, and attributions
    ├── aimblock.py             #  place any other scripts you want to use in this directory
    ├── aimbot2.py
    ├── airstrike.py
    ├── antijerk.py
    ├── arena.py
    ├── autohelp.py
    └── ...
```

