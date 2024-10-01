{ path=$(which cue-pine | xargs readlink -f | xargs dirname || pwd); } 2>/dev/null

# Cue-pine's own installation should only be run from the repo's root
if ! [[ -d $path/venv ]]; then
    echo 'Setting up cue-pine venv...'
    $(which python3 python | head -n1) -m venv venv
    source "$path/"venv"/bin/activate"
    pip install -r requirements.txt
else
    source "$path/"venv"/bin/activate"
fi

env python "$path/cue-pine.py" "$@"
