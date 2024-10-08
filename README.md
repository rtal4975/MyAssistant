# Project Assistant
It becomes difficult to consistently document and keep track with code changes and versions as we try to develop code quickly and as we move from one project to another.
This code base is supposed to help automate the documentation process, but then to also build into a GitHub template that we can use that includes this code and also the sql-helper code.
At a high level, I hope that this repo will:
* make a new output folder everytime a run is done
* capture a `git diff` into a text file to log any changes made since the last commit
* improve logging by syncing repo-commits with how we name our output folders


## How to Use
In your 'main' file where the process starts, import with:
```
import sys
sys.path.append(os.path.expanduser("~/MyAssistant")) # <- adapt filepath as needed
import assistant_starter
```

...and then, in your `__main__` section, implement `MyAssistant` with:
```
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-z", "--debug",
                        action = 'store_true',
                        default = False,
                        help = "Flag to remove drop size of the data.")
    args = parser.parse_args()
    assistant = assistant_starter.SOTFAssistant(runfile=__file__, testing=args.debug)
    assistant.start()

    output_dir = assistant.current_run_output_folder
```

## Start()

The `start()` method does the following:
* check how much un-committed code is in the repo
* if 5 or more files have changed, or 200 or more lines of code have changed, then ask the user to exit and make a commit
* asks user to quickly document any meta information specific to this run for documentation purposes
* stores `git diff` output into a text file for documentation purposes
* setup `logging` module so that the user can log statements throughout the code


## Output Directory

**AA000_[BRANCHNAME]_[COMMITHASH]**

A lot of work was done to come up with a clever way to capture code iterations in the output directories. Here is the overview of the logic:
* for every new commit (monitored by commit hash), increment up the 2 letter prefix of the previous output directory
* for every run within the same commit, increment up the numerical prefix of the previous output directory


### Logging

Checkout [documentation for `logging` module](https://docs.python.org/3/library/logging.html).

There are 5 main logging levels:
* `logging.debug('[TEXT]')`
* `logging.info('[TEXT]')`
* `logging.warning('[TEXT]')`
* `logging.error('[TEXT]')`
* `logging.critical('[TEXT]')`