# Ground station
---

This directory contains all of the useful ground station deployment scripts and tools for interfacing with IMPISH.
**Nothing** in this directory needs to be deployed to or accessed by IMPISH.


## Deployment

Most of the ground station computer deployment is automated.
There are currently three things that must manually be performed when deploying the ground station on a **fresh** OS installation:
1. (*before executing `oneshot_deploy`*) copy or create the `grafana.env` file in `/usr/local/bin`. This file is used by `install_mysql` (which will halt the deployment process if the file is not found) and contains the password that will be used for interfacing with the MariaDB database and Grafana app. 
    - `grafana.env` file structure:
        ```
        PASS="SUPER_SECRET_PASSWORD!"
        export PASS
        ```
    - Ask either Reed or William where you can find the file.
2. (*after executing `oneshot_deploy`*) upload the three dashboard JSON files to Grafana (health, quicklook, and commander).
    - *This is something can likely be done automatically, but it is unclear at the moment if it's bad to keep our JSON files on Github (probably not?)*
3. (*after executing `oneshot_deploy`; optional*) change the Grafana username to whatever (the default is admin). Currently, I don't think can be done automatically with `gcx` (the Grafana CLI).
