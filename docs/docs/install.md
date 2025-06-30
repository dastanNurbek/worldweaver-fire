# Installation

WorldWeaver is a Blender addon written in Python. It uses a few Python libraries and other softwares.

## Dependencies

Current dependencies are as follows:

* [Blender](https://www.blender.org/download/) 4.1 (or [bpy](https://pypi.org/project/bpy/4.1.0/) for headless runs)
* [Python](https://www.python.org/downloads/) 3.11
* [7zip](https://www.7-zip.org/)
* [geopandas](https://geopandas.org/en/stable/index.html) 1.0.1
* [rasterio](https://rasterio.readthedocs.io/en/stable/) 1.3.7
* [pyogrio](https://pyogrio.readthedocs.io/en/latest/) 0.5.1
* [scipy](https://scipy.org/) 1.10.0
* [scikit-image](https://scikit-image.org/) 0.21.0
* [scikit-learn](https://scikit-learn.org/stable/) 1.6.1
* [numpy](https://numpy.org/) 1.24.2
* [tqdm](https://github.com/tqdm/tqdm)
* [OPENEXR](https://openexr.com/en/latest/)
* [PIL](https://he-arc.github.io/livre-python/pillow/index.html)
* [owslib](https://owslib.readthedocs.io/en/latest/)
* [funkybob](https://github.com/andreacorbellini/funkybob)
* [overpass](https://pypi.org/project/overpass/)
* [timezonefinder](https://timezonefinder.readthedocs.io/en/latest/)
* [ladybug-geometry](https://www.ladybug.tools/ladybug-geometry/docs/)
* [IMath](https://github.com/AcademySoftwareFoundation/Imath)
* [Sun Position](https://docs.blender.org/manual/en/3.5/addons/lighting/sun_position.html) (native Blender add-on)

## Setup instructions

The installation procedure is slightly different if you want to be able to use Blender's GUI or just use the headless version:

### Blender GUI Version

Install Blender:

```bash
snap install blender --channel=4.1/stable
```

Creating the virtual environment that will be used by the software using the python interpreter packaged by Blender:

```bash
/snap/blender/current/4.1/python/bin/python3.11 -m venv <path/to/virtual_env>
```

Entering the virtual environment.

```bash
source <path/to/virtual_env>/bin/activate
```

Cloning the repository from GitHub or extract the tarball:

```bash
git clone https://github.com/geo-mage/worldweaver
```

Installing the python dependencies:
```bash
python -m pip install -r requirements.txt
```

You can then install the WorldWeaver Python module into your Python environment using:
```bash
pip install .
```

### Headless Version

Getting the python version (this exact version is needed for compatibility with blender and use of virtual environments):

```bash
sudo apt install python3.11-venv
```

Creating the virtual environment that will be used by the software:

```bash
python3.11 -m venv <path/to/virtual_env>
```

Entering the virtual environment.

```bash
source <path/to/virtual_env>/bin/activate
```

Cloning the repository from GitHub or extract the tarball:

```bash
git clone https://github.com/geo-mage/worldweaver
```

Installing the python dependencies:
```bash
python -m pip install -r requirements_headless.txt
```

You can then install the WorldWeaver Python module into your Python environment using:
```bash
pip install .
```

### Other dependencies:

Install 7zip (or p7zip-full, both work):
```bash
sudo apt install 7zip
```
or:
```bash
sudo apt install p7zip-full
```

### Registering the addon in Blender (only for GUI)

Because Blender uses its own Python interpreter, we have to specify that we now want Blender to use the system Python (or the Python from your virtualenv).
This is achieved by setting the PYTHONPATH and passing the `--python-use-system-env` to Blender at startup:

```bash
PYTHONPATH="$(python -c "import sys; print(\":\".join(sys.path))")" blender --python-use-system-env
```

Once Blender has started, we can register the WorldWeaver plugin as an add-on in the software. To do so:

1. Open the *Edit->Preferences->Add-ons* menu.
2. Click the *Install* button.
3. Browse the file explorer to the folder where WorldWeaver has been downloaded and select the `module_worldweaver.py` file.

This registers WorldWeaver as a Blender add-on. In particular, this makes it possible to run the procedural generation using a simple keyboard shortcut.

### Using WorldWeaver

Once WorldWeaver is installed, check out the [basic workflow](basic_workflow.md) for more details on how to use the software.



