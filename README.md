<p align="right">
    <img src="./smseventlog/_resources/images/sms_icon.png" width="100" height="100" title="SMS Logo"/>
</p>

The SMS Event Log is a desktop application to create a single source of truth for a variety of technical information related to equipment events/failures/work completed. It is designed to be highly available, fast, user friendly, and scalable to any number of equipment fleets/mine sites.

The log is structured around several main tables, each of which can be used to input and retrieve data, as well as perform other automated tasks such as emailing tables, importing data from other sources, and creating reports.


## Install Instructions
1. Download latest version of `SMS Event Log-win-{version}.zip` from download link. (ask Jayme for link if you don't have it).
2. Extract folder to `C:\Users\your_user_name\SMS Event Log` (eg jgordon)
3. Double click `SMS Event Log.exe` to open
    * Note: Windows may prevent the app from opening with a blue 'Protected your PC' screen. Press <u>More info</u> then select <u>Run Anyways</u>. 
4. Right click icon in taskbar and select `Pin to Taskbar` or `Pin to Start` to create a persistent shortcut
5. Set your default minesite with `Ctrl + Shift + M`. This will determine the default data refreshed in many tables, and is saved as a persistent setting between restarts/updates.

### Update
* The event log checks for updates on startup, periodically, or when a user selects Help > Check for Updates
* When an update is available, follow the prompts to download/extract update/restart. (Restart can take ~30-60s)

## Usage
### Keyboard shortcuts

| Action               | Shortcut         |
|----------------------|------------------|
| Show Refresh Menu    | Ctrl + R         |
| Refresh All Open     | Ctrl + Shift + R |
| Reload Previous Query| Ctrl + Shift + L |
| View Folder          | Ctrl + Shift + V |
| Create New Event     | Ctrl + Shift + N |
| Change MineSite      | Ctrl + Shift + M |
| Show Details View    | Ctrl + Shift + D |
| Jump start/end table | Ctrl + Shift + J |
| Jump to Previous Tab | Ctrl + Tab       |
| New line in cell     | Shift + Enter    |
| Fill cell value down | Ctrl + D         |
| Search all cells     | Ctrl + F         |

### Refreshing Tables
* Any text field can handle a \*wildcard\* search
    * Eg, search for any event with a title like \*Alternator\*
* Filter/sort the contents of the current table by right clicking on a header cell

### Menu Bar Functions
There are several extra functions in the menubar, such as:
* Email current table
* Export current table to excel file
* Delete selected row
* Create TSI
* Get WorkOrder number from email (Work order emails must be in a folder titled "WO Request")
* Reset database connection (useful if getting connection related errors)
* Reset your username/any other credentials

### Examples
* Create a new event | (Ctrl + Shift + N):
![](docs/gifs/Add-New-Event.gif)

* Refresh 'All Open', or specific events with the Refresh Menu | (Ctrl + R):
![](docs/gifs/Refresh-Events.gif)

* Filter/sort | (right click header cell)
![](docs/gifs/Filter-Menu.gif)

* View event folder and failure pictures | (Ctrl + Shift + V):
![](docs/gifs/View-Event-Folder.gif)


# Developer Guide
### Software

* [VS Code](https://code.visualstudio.com/download) 
    * Settings Sync
        * Install 'Settings Sync' extension
        * Sync settings from public gist: `87b79ab2b6d3dc30fcd703f2fe02b421`
    * jupyter
        * Add startup script from `/docs/launch.py` to jupyter startup location `/Users/{username}/.ipython/profile_default/startup`. This will import everything each time the ipython interactive window is launched.
* [Azure Data Studio](https://docs.microsoft.com/en-us/sql/azure-data-studio/download-azure-data-studio)
* [Github Desktop](https://desktop.github.com/)
    * Install and create a github account
    * Create empty top level folder 'SMS'
    * git commands
        <!-- todo: link good guide? -->
        * [Guide](https://product.hubspot.com/blog/git-and-github-tutorial-for-beginners)
        * [initialize local project](https://www.atlassian.com/git/tutorials/setting-up-a-repository/git-clone): `git clone https://github.com/jaymegordo/SMSEventLog .` (the period is important!)
        * check current staged files: `git status`
        * ignore line endings (if project is worked on between mac and windows): `git config --global core.autocrlf true`
        * exit logs/messages: `q`
        * show history: `git log --pretty=oneline`
        * [tag version](https://git-scm.com/book/en/v2/Git-Basics-Tagging): `git tag -a 3.0.0 -m "this is the fist release version"`
        * vscode github pannel > commit
        * cmd + shift + p > git push: follow tags
        * [Create release](https://help.github.com/en/github/administering-a-repository/managing-releases-in-a-repository)
* [Python 3.8](https://www.python.org/downloads/)
    * Install Python
    * open command prompt, check python installed correctly with `python --version`
    * [Pipenv](https://github.com/pypa/pipenv)
        * `pip install pipenv`
        * Init virtual environment with `pipenv lock` to create Pipfile.lock
        * Download and sync all packages from Pipfile with `pipenv sync --dev` (run this at any time if things get out of sync or broken)
        * Use pipenv as main package manager
        * When working in the cmd line, activate environment with `pipenv shell` to have access to developer packages (eg twine)
        * print list of installed packages:
            * `pipenv graph` or
            * `pipenv run pip list`
        * Create requirements.txt: `pipenv lock -r > requirements.txt`
        * Update single package: `pipenv update <packagename>`
        * Install from custom forked repo: `pipenv install git+https://github.com/jaymegordo/python-chromedriver-autoinstaller.git@master#egg=chromedriver-autoinstaller`
            * `#egg` comes from `name` defined in setup.py, will be name of install
            * `-e` flag makes the package 'editable' and puts in into `src`
    * twine
        * `pip install twine`
        * Used to push build wheel to pypi
* Install pyodbc

### GUI
* PyQt5
    * SMS Event Log's gui is built with PyQt5
    * [Docs](https://doc.qt.io/qtforpython/)
    * [Multithreading](https://www.learnpyqt.com/courses/concurrent-execution/multithreading-pyqt-applications-qthreadpool/)

## Deployment
### Build Process
1. Commit all changes to git, add comments etc (use github menu in vscode)
2. Increment version with eg `bumpversion patch --verbose` (must be run inside active pipenv)
3. Push tags to git `git push --tags` (only pushes tags, increments version on github)
4. `git push` > pushes all changes (could also use vscode menu to push)
5. 
    * Local testing - Build exe using custom build script `python -m build` (see pyinstaller below for more info)
    * Production - Build exe with pyupdater:
        * Note - dev needs to get the .env file with saved settings/passwords (ask jayme)
        * first `cd build_scripts` (location of the build scripts)
        * Mac: `zsh build.sh true` (true = upload after build is complete)
        * Win: `build.bat true`
6. Push build package to s3 bucket with `zsh upload.sh` or `upload.bat`

### Build Software
* [bump2version](https://github.com/c4urself/bump2version)
    * Use bumpversion to control version increments
    * creates a git tag before pushing
    * testing: `bumpversion patch --dry-run --verbose --allow-dirty`
    * usage: `bumpversion [major | minor | patch]`
        * `bumpversion patch` > will increment version from 3.0.1 to 3.0.2
        * `bumpversion minor` > will increment version from 3.0.1 to 3.1.0       

* [PyUpdater](https://www.pyupdater.org/installation/)
    * PyUpdater handles package build (wraps PyInstaller), signs code, uploads to amazon s3, and handles app update checks/downloads/restarts
    * [AppUpdatesDemo](https://github.com/jameswettenhall/pyupdater-wx-demo/blob/master/run.py)

* [PyInstaller](https://pyinstaller.readthedocs.io/en/stable/usage.html)
    * In project dir (SMS), `python -m build` (runs custom build python file which calls PyInstaller with args)
    * Only use PyInstaller on its own to create a test build because PyUpdater auto zips everything.
    * This will package app and output files to /dist/[mac|win]

    * Build Issues
        * Files in `frozen py files` need to be replaced after version updates to their packages. They contain small changes eg try/except for getting a version number. The originals break the exe build.
        If directly replacing these files doesn't work, may need to dig into code and redo fixes somehow.

        1. Pandas.io.formats.style
            * [not exact issue but related](https://stackoverflow.com/questions/52429350/cant-perform-this-operation-for-unregistered-loader-type-is-there-any-workaro)
            * this needs to be fixed any time pandas is udpated.
            
            1. open [*virtualenv*]/Lib/site-packages/pandas/io/formats/style.py
            2. change line 135 from:
                ```
                template = env.get_template("html.tpl")
                
                # to

                import os
                path = os.path.dirname(__file__) + "/templates/html.tpl"
                with open(path) as fin:
                    data = fin.read()
                    template = env.from_string(data)
                ```
        
        2. Weasyprint / Cairosvg
            * VERSION fails to load (fix `__init__.py` in both)
            * `weasyprint/__init__.py` - Line 24 - add:
                ```
                try:
                    VERSION = __version__ = (ROOT / 'VERSION').read_text().strip()
                except:
                    VERSION = __version__ = ''
                ```
        
        2. Matplotlib
            * [this isssue](https://stackoverflow.com/questions/63163027/how-to-use-pyinstaller-with-matplotlib-in-use)
            * change `PyInstaller\hooks\hook-matplotlib.py` to:
                ```
                datas = [(mpl_data_dir, "matplotlib/mpl-data")]
                ```

* Code Signing
    * (mac only so far)
    * Sign - `codesign --deep -s "SMS Event Log" "/Applications/SMS Event Log.app"`
    * Verify - `codesign -dv --verbose=4 "/Applications/SMS Event Log.app"`

* [pypi](https://packaging.python.org/tutorials/packaging-projects/)
    * create `.pypirc` file at 'c:\users\username' (one time, stores api key for login)
    * make sure user installed setuptools is up to date (or bdist_wheel doesn't work) `python -m pip install --user --upgrade setuptools wheel`
    * create wheel:
        * TODO: get version from github with requests?
        * `python setup.py clean --pre && python setup.py sdist bdist_wheel clean --post`
        * bdist_wheel > creates wheel (built distribution) to upload to pypi
        * sdist > creates source distribution (fallback)
        * clean --pre > runs custom command to remove previously leftover folders if they exist
        * clean --post > remove smseventlog.egg-info folder (never needed)
    * check contents of wheel package (optional) `tar -tf dist\smseventlog-3.0.0.tar.gz`
    * upload with twine
        * test `twine upload --repository testpypi dist/*`
        * live `twine upload dist/*`
    * cleanup all leftover folders: `python setup.py clean --all`

* Azure Functions
    * Parts of the smseventlog package run as smseventlog-app in azure functions
    * This runs several functions such as: daily availability imports, oil sample imports, SMR hrs imports
    * Some key azure commands are:
        * Publish to azure `func azure functionapp publish smseventlog-app --build-native-deps`
        * Test locally `func host start` (must be run in active pipenv shell)
        * Manually trigger timer function `curl --request POST -H "Content-Type:application/json" --data '{"input":""}' http://localhost:7071/admin/functions/az_TimerImportSMR`