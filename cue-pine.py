#!/bin/env python
import argparse
import os
import sys
import shutil
import subprocess
from urllib import request
import json
FILE_EXT='json'
try:
    import tomllib
    FILE_EXT='toml'
except ImportError:
    pass
try:
    import yaml
    FILE_EXT='yaml'
except ImportError:
    pass


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
    prog="cue-pine",
    description="(un)install the files",
    epilog="Just run the script to install the files.\nAdd the '-u' flag to uninstall the files instead.",
)
parser.add_argument("-V", "--version", action="version", version="%(prog)s 1.2.1")
parser.add_argument("-u", "--uninstall", action="store_true", help="Uninstalls the files instead")
parser.add_argument("-t", "--template", action="store_true", help="Prints a template and exits")
parser.add_argument("-d", "--dry-run", action="store_true", help="Shows what would be done, without actually doing it")
parser.add_argument("--explain-config", action="store_true", help="Details the capabilities and uses of a config file")
parser.add_argument("--config-name", default=f"install.{FILE_EXT}", help=f"Name of the config files. ('install.{FILE_EXT}' by default)")
parser.add_argument("--strict-pre", action="store_true", help="Abort installation if any of the pre scripts produce an error")
parser.add_argument("--no-sublevel", action="store_true", help="Don't attempt to process config files found in sub-directories")
parser.add_argument("-c", "--check-dependencies", action="store_true", help="Only check for dependencies and exit")
args = parser.parse_args()

FILE_EXT = args.config_name.rpartition('.')[-1]

# Prepare and print template, ± the explanation
if args.template or args.explain_config:
    TEMPLATE={
        'dependencies': ['ssh', 'ed', 'vim'],
        'installation': {
            'config': {
                'dir': '$HOME/.config/mydir',
                'files': ['file_1.py', 'file_2.py'],
            },
            'scripts': {
                'dir': '$HOME/.local/bin',
                'strip_ext': True,
                'files': ['script.sh'],
            },
            'setup': {
                'dir': '$HOME/.config/bash/setup',
                'renamed_files': [
                    {'src': 'my_aliases.sh', 'dest': '999_cue-pine_aliases.sh'},
                    {'src': 'autocompletion.bash', 'dest': '999_cue-pine_autocomp.bash'},
                ],
            }
        }
    }
    # We want empty values for the template
    if args.template:
        TEMPLATE['dependencies'] = ['']
        for key in ['config', 'scripts', 'setup']: 
            entry = TEMPLATE['installation'][key]
            if 'files' in entry:
                entry['files'] = ['']
            elif 'renamed_files' in entry:
                entry['renamed_files'] = [{'src': '', 'dest': ''}]

    # Find proper representation
    if FILE_EXT == 'json':
        template = json.dumps(TEMPLATE, indent=4)
    elif FILE_EXT == 'yaml':
        template = yaml.dump(TEMPLATE)
    elif FILE_EXT == 'toml':
        raise ValueError("tomllib can't write toml files")
    elif FILE_EXT == 'py':
        import pprint
        template = pprint.pformat(TEMPLATE)
    else:
        raise ValueError(f'Filetype not supported: "{FILE_EXT}"')

    if args.template:
        print(template)
    elif args.explain_config:
        print('\n'.join(
            [
                f"This program requires a config file named 'install.{FILE_EXT}' inside the current working directory.",
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
                "4) 'strip_ext', a boolean that if true, causes file extensions to be stripped from 'files' entry.",
                "",
                UL("Example:"),
                template,
        ]), file=sys.stderr)
    exit(0)


def check_dependencies(config: object) -> bool:
    """If trying to install, ensures all dependencies are found on the system,
    abort the execution otherwise
    If only checking dependencies, don't abort the execution if some are missing

    :param config: data of the config file
    """
    dependencies = config.get("dependencies")
    if not dependencies:
        return True

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
    if not (all_deps_found or args.check_dependencies):
        print("Not all dependencies met. Aborting.")

    return all_deps_found


def process(src, dest) -> bool:
    """Based on the mode, install/uninstall file if it does/does not exist.
    Supports files, urls, and git repos

    :return: True if something was done, False otherwise
    """
    exists = os.path.exists(dest)
    if not exists:
        try:
            # Broken symlinks are flagged as non-existant, but still cause issues
            os.remove(dest) 
        except FileNotFoundError:
            pass

    done_something = False
    if exists and args.uninstall:
        print(f"        {dest}")
        if not args.dry_run:
            os.remove(dest)
        done_something = True
    elif not (exists or args.uninstall):
        done_something = True
        if src.endswith('.git'):
            callback = lambda src, dest: subprocess.run(["git", "clone", src, dest])
        elif src.startswith('http'):
            callback = request.urlretrieve
        else:
            if not os.path.exists(src):
                print(f'        {RD("Error")}: file "{src}" does not exist')
                return False
            callback = os.symlink
            src = f"{os.getcwd()}/{src}"
        print(f"        {src} => {dest}")
        if not args.dry_run:
            callback(f"{src}", dest)
    return done_something


def alt_process(type_: str, config: object) -> None:
    """Pre or post process. Not run when uninstalling

    :param type: Either "pre" or "post"
    :param config: data of the config file
    """
    if type_ not in config or args.uninstall:
        return

    print(UL(f'{type_.capitalize()}-scripts:'))
    for i, command in enumerate(config[type_]):
        print(f'    running {type_} script #{i}')
        if args.dry_run:
            continue

        e_code = subprocess.call(command, shell=True)
        if args.strict_pre and e_code and type_ == 'pre':
            print(f"\n{RD('Error')}: exit code '{YL(e_code)}' was produced by the command '{SCY(command)}'", file=sys.stderr)
            exit(1)
    print() # Newline


def process_installation(config: object):
    """Processes the items in the installation dict.
    Either create or delete symlinks for the files given in the config
    """
    action = "Uninstallation:" if args.uninstall else "Installation:"
    print(UL(action))
    for name, content in config['installation'].items():
        dir = (content['dir'].replace('$HOME', os.getenv('HOME')))
        done_something = False
        print(f"    {BD(name)}:")

        if not (os.path.exists(dir) or args.uninstall or args.dry_run):
            os.makedirs(dir)

        file: str
        for file in content.get('files', []):
            if content.get('strip_ext'):
                final_file = file.rsplit('.', 1)[0]
            elif '/' in file: # Most likely an URL, we only want the last part
                final_file = file.rpartition('/')[-1]
            else:
                final_file = file

            done_something = process(f"{file}", f"{dir}/{final_file}") or done_something

        for mapping in content.get('renamed_files', []):
            done_something = process(f"{mapping['src']}", f"{dir}/{mapping['dest']}") or done_something

        if not done_something:
            print(YL("        Nothing done"))

    print() # Newline


def process_config_file(file_path: str, cwd='.') -> None:
    """Extracts and use informations from a config file to do the installation
    Changes cwd during its execution, reverts changes at the end
    """
    original_pos = os.getcwd()
    os.chdir(cwd)

    # Print header for config file, formatted like "===== cwd/file_path ====="
    side_size = os.get_terminal_size().columns - len(file_path) - 1 - len(cwd) - 2
    lhs = "="  * (side_size // 2)
    rhs = "=" * (side_size - len(lhs)) # Resolves issues if number if odd
    print("{0} {2} {1}".format(lhs, rhs, SCY(f"{cwd}/{file_path}")))

    with open(file_path, "r") as cfg_file:
        if file_path.endswith('.json'):
            config = json.load(cfg_file)
        elif file_path.endswith('.yaml'):
            config = yaml.full_load(cfg_file)
        elif file_path.endswith('.toml'):
            config = tomllib.loads(cfg_file)
        elif file_path.endswith('.py'):
            config = eval(cfg_file.read())

    all_deps = True
    if not args.uninstall:
        all_deps = check_dependencies(config)

    if all_deps and not args.check_dependencies:
        # Pre-processing, processing, post-processing
        alt_process('pre', config)
        process_installation(config)
        alt_process('post', config)

    os.chdir(original_pos)


# Process config files found at cwd and in sub-directories
for cwd, subdirs, files in os.walk('.'):
    # Prune unwanted dirs
    if subdirs:
        for undesirable in EXCLUDED_DIRS:
            if undesirable in subdirs:
                subdirs.remove(undesirable)

    if args.config_name in files:
        process_config_file(args.config_name, cwd)

    if args.no_sublevel:
        break
