<img src="./coa_tools_logo.png" width="250" alt="COA Tools logo">

# Cutout Animation Tools – documentation

This is the documentation for the Cutout Animation Tools Blender/Godot add-on.

If you like this add-on and want to thank me with a small donation,
feel free to do this here:

[![](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=8TB6CNT9G8LEN)

## Description

The Cutout Animation Tools (COA Tools) add-on for Blender is a 2D rigging
and animation suite. It offers you tools similar to programs like
Spine or Spriter. COA Tools offer you a rapid workflow to create 2D cut-out
characters and animations using Blender. Thanks to Blender's great animation
system and to this addon, you get a powerful solution to create 2D animations.
It is split into 3 different components: the Photoshop sprite exporter,
the Blender add-on and the Godot importer.

[Take a look at the add-on in action.](https://www.youtube.com/playlist?list=PLPI26-KXCXpA-VMlDIWpmdq6M1m4LEjf_)

### Photoshop sprite exporter

Quickly export Photoshop layers into separate files with
JSON coordinate information. This can be used in Blender to import sprites
very quickly.

Features:

- Export layers as sprites.
- Export folder with multiple layers as spritesheets.
- Generate JSON data with all layer positions and spritesheet information.

### GIMP sprite exporter

Export GIMP layers and layer groups into separate files with
JSON coordinate information. For additional usage information,
see [README.md](GIMP/README.md) in the `GIMP/` folder.

### Cutout Animation Tools Blender

This is the biggest component, as most of the work will be done here.

The add-on offers the following features:

- Sprite importer (import single sprites or multiple, or use JSON data as import information)
- Animated spritesheet support for meshes.
- Armature editing – super fast bone creation tool.
  Just draw bones and click to append sprites to bones.
- Mesh editing – draw vertex countours and fill them quickly with tesselated mesh.
  Filling also unwraps and maps texture data.
- Weight editing – fast weight editing for tesselated meshes
- Fast IK and stretch to constraint generation
- Enhanced animation handling for sprite_objects
- Sprite object outliner → displays all containing sprites, armatures with bones
  for better and quick access to single sprites
- Orthographic camera operator → generates an orthographic camera which can
  be used to render animations. Camera resolution fits perfectly the pixel
  space of sprites
- JSON export → Exports all sprite_object data to a JSON file.
  Supported features are: Bone and Sprite hierarchy export, baked animation export.

### Godot Cutout Animation Importer

This is an advanced importer that helps you get all your
exported Blender data into Godot.

Features:

- JSON importer.
- Sprites, bones and animations get imported.
- Clever reimport functionality. Offers the possibility to merge local changes
  that were made in Godot to the newly imported scene. This enables a
  very flexible workflow: work in Blender, then export, then import in Godot.
  Make additions such as adding new nodes or adding custom animations.
  After reimporting, all local changes will be preserved if merging is enabled.

## Download and Installation

Download or clone the GitHub repository to your local drive.
If you downloaded the ZIP file from GitHub, make sure to extract it.
Don't try to install the downloaded ZIP file directly in Blender;
this won't work. Once you have extracted the ZIP file, follow
the installation instructions below.

### Photoshop exporter

The `.jsx` file has to be copied into the Photoshop scripts folder which is located in:

```
C:\Program Files\Adobe\Adobe Photoshop CC 2015\Presets\Scripts
```

Don’t forget to restart Photoshop and then go to
**File** → **Scripts** → **BlenderExporter.jsx**.

### GIMP exporter

The `coatools_exporter.py` file should be copied to your GIMP plug-ins folder
which is located in:

- Linux: `$HOME/.gimp-2.8/plug-ins/`
- Windows: `%USERPROFILE%\.gimp-2.8\plug-ins\`

After restarting GIMP, it should show up under **Files** → **Export to CoaTools…**.

### Blender add-on

Create a ZIP archive of `coa_folder/` which is located inside the `Blender/` folder.
Go to **File** → **User Preferences** → **Add-ons** and click the
**Install from file…** button.
This will install and enable the add-on for Blender. Don’t forget to
save the user preferences, otherwise the add-on will not be activated
after restarting.

<a href="http://misc.artbyndee.de/coa_tools_installation.gif">
  <img src="http://misc.artbyndee.de/coa_tools_installation.gif" width="250">
</a>

### Godot importer

Note that this importer will only run with current Godot 2.1 development builds.
Create an `addons/` folder in your game project's folder and copy the `coa_importer/`
folder into that addons folder. Once the files are loaded, go to
**Project Settings** → **Plugins** → **Cutout Animation Importer**
then activate the plugin.
