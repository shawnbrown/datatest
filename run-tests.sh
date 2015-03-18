#!/usr/bin/env bash
#=======================================================================
#        FILE: run-tests.sh
# DESCRIPTION: Runs test suite under all supported versions of Python
#              and displays failures when encountered.
#=======================================================================

#-----------------------------------------------------------------------
# Define function (takes command to run as a single argument).
#-----------------------------------------------------------------------
run_command ()
{
    echo "" >&2
    echo "======================================================================" >&2
    echo "$1" >&2
    echo "======================================================================" >&2
    $1  # <- Run command.
    if [ $? -ne 0 ]  # Check exit status of completed command.
    then
        echo "" >&2
        echo "Failed Command: $1" >&2
        echo "" >&2
        exit $?  # <- EXIT!
    fi
}

#-----------------------------------------------------------------------
# Run test suite in all supported versions of Python.
#-----------------------------------------------------------------------
run_command "python3.4 -B -m unittest $*"
run_command "python3.3 -B -m unittest $*"
run_command "python3.2 -B -m unittest $*"
run_command "python3.1 -B discover.py $*"
run_command "python2.7 -B -m unittest discover $*"
run_command "python2.6 -B discover.py $*"

echo "" >&2
echo "All commands successful." >&2
