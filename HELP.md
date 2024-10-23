# How to use it
cue-pine requires a config file named "install.yaml/json/..." in the current or sub directories.
Unless explicitely asked not to, cue-pine will crawl sub-directories to look for config files.
The config file describes to actions to do, through 5 main keys.

# Keys
## pre
A list of strings, executed one by one in a shell before starting the installation.

## post
A list of strings, executed one by one in a shell after the installation.

## dependencies
A list strings, the name of the dependencies used by your scripts.
If the user misses any of these, the installation aborts.

## opt_dependencies
A list strings, the name of optional dependencies used by your scripts.
Non-blocking, unlike the main dependencies.

## installation
What to install and how. It is a dictionary of dictionaries for categories subdivided by names.
The sub dictionaries can have the following keys:

### dir
The path to the directory where the files are to be put.
The path is fully created if it doesn't exist (including intermediate directories).
Any occurence of '$HOME' in the paths is replaced by the path to the user's home directory.

### files
The name/path to the files to install, relative to the install file (list of strings).

### renamed_files
A list of dictionary, for files that should be renamed. It has two keys:
- src, the name of the file relative to the install file
- dst, the name it should have in the destination directory

### strip_ext
If present and truthy, strips the file extension from copied files when they are
put in the destination directory

### condition
A string to execute in a shell to test whether to install this entry or not.
Any non-zero return code skips the entry

# Template
To see a template config file, run `cue-pine -t`
