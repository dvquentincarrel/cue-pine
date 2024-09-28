#!/bin/env python
import json
import argparse
import os
import sys
import shutil
import subprocess
from urllib import request

# Directories to prune if subdirectories are crawled for config files
EXCLUDED_DIRS=['.git', 'node_modules', 'venv']
FORCE_COLOR = False

# Colored output
color_names = ["BK", "RD", "GR", "YL", "BL", "PR", "CY", "WH"]
modifiers_map = {'': 0, 'B': 10, 'S': 60, 'SB': 70}
if FORCE_COLOR or sys.stderr.isatty():
    ST, BD, FT, IT, UL = [lambda msg, cd=code: f"\x1b[{cd}m{msg}\x1b[m" for code in range(5)]
    for prefix, modifier in modifiers_map.items():
        for code, color in enumerate(color_names):
            color_code = code+modifier+30
            globals()[f"{prefix}{color}"] = lambda msg, cc=color_code: f"\x1b[{cc}m{msg}\x1b[m"
else:
    ST, BD, FT, IT, UL = (lambda x:x,) * 5
    for prefix in modifiers_map:
        for color in color_names:
            globals()[f"{prefix}{color}"] = ST

# Args parsing
parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description="(un)install the files",
    epilog="Just run the script to install the files.\nAdd the '-u' flag to uninstall the files instead.",
)
parser.add_argument("-u", "--uninstall", action="store_true", help="Uninstalls the files instead")
parser.add_argument("--explain-config", action="store_true", help="Details the capabilities and uses of a config file")
parser.add_argument("--config-name", default="install.json", help="Name of the config files. ('install.json' by default)")
parser.add_argument("--strict-pre", action="store_true", help="Abort installation if any of the pre scripts produce an error")
parser.add_argument("--no-sublevel", action="store_true", help="Don't attempt to process config files found in sub-directories")
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
            UL("Example:"),
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

def process_config_file(file_path: str, cwd='.') -> None:
    """Extracts and use informations from a config file to do the installation
    Changes cwd during its execution, reverts changes at the end"""
    original_pos = os.getcwd()
    os.chdir(cwd)

    # formatted like "===== cwd/file_path ====="
    side_size = os.get_terminal_size().columns - len(file_path) - 1 - len(cwd) - 2
    lhs = "="  * (side_size // 2)
    rhs = "=" * (side_size - len(lhs)) # Resolves issues if number if odd

    print("{0} {2} {1}".format(lhs, rhs, SCY(f"{cwd}/{file_path}")))
    with open(file_path, "r") as cfg_file:
        config = json.load(cfg_file)

    # Check dependencies
    dependencies = config.get("dependencies", [])
    if dependencies and not args.uninstall:
        all_deps_found = True
        print(UL("Dependencies check:"))
        for dependency in dependencies:
            print(f"    {dependency} ", end="")
            if shutil.which(dependency):
                print(GR("OK"))
            else:
                print(RD("not found"))
                all_deps_found = False

        print() # Newline
        if args.check_dependencies:
            exit(0)
        elif not all_deps_found:
            print("Not all dependencies met. Aborting.")
            exit(1)

    action = "Uninstallation:" if args.uninstall else "Installation:"

    def process(src, dest) -> bool:
        """Based on the mode, install/uninstall file if it does/does not exist.
        Supports files, urls, and git repos

        :return: True if something was done, False otherwise
        """
        exists = os.path.exists(dest)
        done_something = False
        if exists and args.uninstall:
            print(f"        {dest}")
            os.remove(dest)
            done_something = True
        elif not (exists or args.uninstall):
            done_something = True
            if src.endswith('.git'):
                callback = lambda src, dest: subprocess.run(["git", "clone", src, dest])
            elif src.startswith('http'):
                callback = request.urlretrieve
            else:
                callback = os.symlink
                src = f"{os.getcwd()}/{src}"
            print(f"        {src} => {dest}")
            callback(f"{src}", dest)
        return done_something

    # Pre-processing
    if 'pre' in config:
        print(UL('Pre-scripts:'))
        for i, command in enumerate(config['pre']):
            print(f'    running pre script #{i}')
            e_code = subprocess.call(command, shell=True)
            if args.strict_pre and e_code:
                print(f"\n{RD('Error')}: exit code '{YL(e_code)}' was produced by the command '{SCY(command)}'", file=sys.stderr)
                exit(1)
        print()

    # Either create or delete symlinks for the files given in the config
    print(UL(action))
    for name, content in config['installation'].items():
        dir = (content['dir'].replace('$HOME', os.getenv('HOME')))
        done_something = False
        print(f"    {BD(name)}:")

        if not (os.path.exists(dir) or args.uninstall):
            os.makedirs(dir)

        for file in content.get('files', []):
            if content.get('strip_ext'):
                final_file = file.rsplit('.', 1)[0]
            else:
                final_file = file

            done_something = process(f"{file}", f"{dir}/{final_file}") or done_something

        for mapping in content.get('renamed_files', []):
            done_something = process(f"{mapping['src']}", f"{dir}/{mapping['dest']}") or done_something

        if not done_something:
            print(YL("        Nothing done"))

    print()

    # Post-processing
    if 'post' in config:
        print(UL('Post-scripts:'))
        for i, command in enumerate(config['post']):
            print(f'    running post script #{i}')
            e_code = subprocess.call(command, shell=True)
        print()

    os.chdir(original_pos)

process_config_file(args.config_name, '.')

# Process config files found in sub-directories
if not args.no_sublevel:
    for cwd, subdirs, files in os.walk('.'):
        # Prune unwanted dirs
        if subdirs:
            for undesirable in EXCLUDED_DIRS:
                if undesirable in subdirs:
                    subdirs.remove(undesirable)
        if cwd == '.': # Already processed
            continue

        if args.config_name in files:
            process_config_file(args.config_name, cwd)
