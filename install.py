#!/bin/env python
import json
import argparse
import os
import sys
import shutil
import subprocess
from urllib import request

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description="(un)install the files",
    epilog="Just run the script to install the files.\nAdd the '-u' flag to uninstall the files instead.",
)
parser.add_argument("-u", "--uninstall", action="store_true", help="Uninstalls the files instead")
parser.add_argument("--explain-config", action="store_true", help="Details the capabilities and uses of a config file")
parser.add_argument("--strict-pre", action="store_true", help="WIP: Abort installation if any of the pre scripts produce an error")
parser.add_argument("-c", "--check-dependencies", action="store_true", help="Only check for dependencies and exit")
args = parser.parse_args()

if args.explain_config:
    print('\n'.join(
        [
            "This program requires a config file named 'install.json' inside the current working directory.",
            "This config file describes the actions to do.",
            "",
            "The config file has 4 main keys:",
            "1) 'pre', a list of strings executed in a shell, before starting the installation",
            "2) 'post', a list of strings executed in a shell, after the installation is done",
            "3) 'dependencies', the names of the executables your software relies on (list of strings)",
            "4) 'installation', What to install and how.",
            "",
            "The value of installation is a dict. Its keys can be any string, usually used to separate",
            "different kind of files ('config' and 'scripts', for example.)",
            "Installation's entries are themselves dicts, with the following keys:",
            "1) 'files', the path to the files to install (list of str)",
            "2) 'dir', the path to the directory where the files are to be put.",
            "   The path to the directory is fully created if it doesn't exist.",
            "   Any occurence of '$HOME' in the paths is replaced by the path to the",
            "   user's home directory.",
            "3) 'renamed_files', (instead of files), which is a list of dicts with a 'src' and 'dest' key.",
            "  The 'src' key is the path to the file to install, and 'dest' is its new name inside of the",
            "  directory given in 'dir'.",
            "",
            "\x1b[21mExample:\x1b[m",
            '{',
            '  "dependencies": ["python", "foo", "foobar"],',
            '  "pre": ["foo --bar", "foo --baz"],',
            '  "post": ["foobar", "foobar --baz", "notify-send done", "cd subdir; python install.py"],',
            '  "installation": {',
            '    "config": {',
            '      "dir": "$HOME/.config/app_conf",',
            '      "files": ["cfg_file_1", "cfg_file_2"]',
            '    },',
            '    "script": {',
            '      "dir": "$HOME/.local/bin",',
            '      "renamed_files": [{',
            '        "src": "install.py",',
            '        "dest": "pyinstaller"',
            '      }]',
            '    }',
            '  }',
            '}',
    ]), file=sys.stderr)
    exit(0)

with open("install.json", "r") as cfg_file:
    config = json.load(cfg_file)

# Check dependencies
dependencies = config.get("dependencies", [])
if dependencies and not args.uninstall:
    all_deps_found = True
    print("\x1b[1mDependencies check:\x1b[0m") # ]]
    for dependency in dependencies:
        print(f"    {dependency} ", end="")
        if shutil.which(dependency):
            print("\x1b[32mOK\x1b[0m") # ]]
        else:
            print("\x1b[31mnot found\x1b[0m") # ]]
            all_deps_found = False

    print()
    if args.check_dependencies:
        exit(0)
    elif not all_deps_found:
        print("Not all dependencies met. Aborting.")
        exit(1)


action = "uninstalling" if args.uninstall else "installing"

def process(src, dest):
    """Based on the mode, install/uninstall file if it does/does not exist.
    Supports files, urls, and git repos"""
    exists = os.path.exists(dest)
    if exists and args.uninstall:
        print(f"    {dest}")
        os.remove(dest)
    elif not (exists or args.uninstall):
        if src.endswith('.git'):
            callback = lambda src, dest: subprocess.run(["git", "clone", src, dest])
        elif src.startswith('http'):
            callback = request.urlretrieve
        else:
            callback = os.symlink
            src = f"{os.getcwd()}/{src}"
        print(f"    {src} => {dest}")
        callback(f"{src}", dest)

# Pre-processing
for command in config.get('pre', []):
    e_code = subprocess.call(command, shell=True)
    if args.strict_pre and e_code:
        print(f"\x1b[31Error\x1b[m: exit code '{e_code}' was produced by the command'{command}'", file=sys.stderr)
        exit(1)

# Either create or delete symlinks for the files given in the config
for name, content in config['installation'].items():
    dir = (content['dir'].replace('$HOME', os.getenv('HOME')))
    print(f"\x1b[1m{action} {name}:\x1b[0m") # ]]

    if not (os.path.exists(dir) or args.uninstall):
        os.mkdir(dir)

    for file in content.get('files', []):
        if content.get('strip_ext'):
            final_file = file.rsplit('.', 1)[0]
        else:
            final_file = file

        process(f"{file}", f"{dir}/{final_file}")

    for mapping in content.get('renamed_files', []):
        process(f"{mapping['src']}", f"{dir}/{mapping['dest']}")

    print()

# Post-processing
for command in config.get('post', []):
    subprocess.run(command, shell=True)
