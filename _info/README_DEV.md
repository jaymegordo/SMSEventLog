
## Developer Guide

### Software

* [VS Code](https://code.visualstudio.com/download) 
    * Settings Sync
        * Install 'Settings Sync' extension
        * Sync settings from public gist: `87b79ab2b6d3dc30fcd703f2fe02b421`
* [Azure Data Studio](https://docs.microsoft.com/en-us/sql/azure-data-studio/download-azure-data-studio)
* [Github Desktop](https://desktop.github.com/)
    * Install and create a github account
    * Create empty top level folder 'SMS'
    * git commands
        <!-- todo: link good guide? -->
        * [Guide](https://product.hubspot.com/blog/git-and-github-tutorial-for-beginners)
        * [initialize local project](https://www.atlassian.com/git/tutorials/setting-up-a-repository/git-clone): `git clone https://github.com/jaymegordo/SMSEventLog .`
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
    * twine
        * `pip install twine`
        * Used to push build wheel to pypi
* Install pyodbc

## Deployment

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
    * This runs several functions such as: daily availability imports, oil sample imports etc
    * publish to azure with `func azure functionapp publish smseventlog-app --build-native-deps`

* Pyinstaller
    * in project dir (SMS), `python -m build` (runs custom build python file which calls PyInstaller with args)
    * (old) To build, activate pipenv with `pipenv shell` then run `pyinstaller smseventlog.spec --noconfirm`
    * This will package app and output files to /dist/[mac|win]

    * Build Issues
        * Files in `frozen py files` need to be replaced after version updates to their packages. They contain small changes eg try/except for getting a version number. The originals break the exe build.
        If directly replacing these files doesn't work, may need to dig into code and redo fixes somehow.

        1. Pandas.io.formats.style
            * [not exact issue but related](https://stackoverflow.com/questions/52429350/cant-perform-this-operation-for-unregistered-loader-type-is-there-any-workaro)
            1. open [*virtualenv*]/Lib/site-packages/pandas/io/formats/style.py
            2. change line 120 from:
                ```
                template = env.get_template("html.tpl")
                
                # to

                path = os.path.dirname(__file__) + "/templates/html.tpl"
                    with open(path) as fin:
                        data = fin.read()
                        template = env.from_string(data)```
        
        2. Weasyprint / Cairosvg
            * VERSION fails to load (fix `__init__.py` in both)
            * `weasyprint/__init__.py` - Line 24 - add:
                ```
                try:
                    VERSION = __version__ = (ROOT / 'VERSION').read_text().strip()
                except:
                    VERSION = __version__ = ''
                ```

* PyUpdater
