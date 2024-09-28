# Why
Because at some point, after a certain number of repos, having a standardized installation script gets really handy.

Because doing it in bash was hell. Json is notoriously awful to write by hand, this is most likely gonna
end up as something else, most likely as actual python code or yaml. Or even all of the above at once.

# How
Run the script with the `--explain-config` flag to get an explanation of what each
key of the config file does.

Also, take a look at `sample_install.json`

## Considerations
By default, the installer crawls the subdirectories, looking for 'install.json' files
to run. '.git' and 'node_modules' directories are pruned when looking for such files.

The files can contain literal strings of text to be executed (`pre` and `post` keys),
so be careful and think about whether or not such files could be present in your projects
beforehand
