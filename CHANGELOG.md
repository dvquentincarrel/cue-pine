# CHANGELOG

## 1.1.2
- Don't run pre/post when uninstalling
- Don't exit after dependency check, allows check of dependencies in sublevels

## 1.1.1
- Fixed reporting of broken symlinks (would consider the file non-existant)
- Test whether a file exists before attempting to symlink it
- Fixed implicit naming when using a URL (would attempt to use the whole URL as a name)

## 1.1
- Fixed inability to use cue-pine if there were no config file in the current directory
- Added dry run flag

## 1.0
Release
