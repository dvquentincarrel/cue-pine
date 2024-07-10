#!/bin/python

import json
import argparse
import os
import shutil
from urllib import request

parser = argparse.ArgumentParser(description="(un)install the files", epilog="Just run the script to install the files. Add the '-u' flag to uninstall the files instead")
parser.add_argument("-u", "--uninstall", action="store_true", help="Uninstalls the files instead")
parser.add_argument("-c", "--check-dependencies", action="store_true", help="Only check for dependencies and exit")
args = parser.parse_args()

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
    """Based on the mode, install/uninstall file if it does/does not exist"""
    exists = os.path.exists(dest)
    if exists and args.uninstall:
        print(f"    {dest}")
        os.remove(dest)
    elif not (exists or args.uninstall):
        if src.startswith('http'):
            callback = request.urlretrieve
        else:
            callback = os.symlink
            src = f"{os.getcwd()}/{src}"
        print(f"    {src} => {dest}")
        callback(f"{src}", dest)

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
