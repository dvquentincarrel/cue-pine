# CHANGELOG
## 1.4
- Add conditional install
- Add optional dependencies check
- Better yaml template order

## 1.3
- Add installation instructions
- Change flags name

## 1.2.1
- Add -t/--template flag to output a template ready to be used

## 1.2.0
- Add support for yaml, toml and python config files
- Tolerates missing dependencies in sublevels

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
