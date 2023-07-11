# Project Assistant
It becomes difficult to consistently document and keep track with code changes and versions as we try to develop code quickly and as we move from one project to another.
This code base is supposed to help automate the documentation process, but then to also build into a GitHub template that we can use that includes this code and also the sql-helper code.
At a high level, I hope that this repo will:
* make a new output folder everytime a run is done
* capture a `git diff` into a text file to log any changes made since the last commit
* improve logging by syncing repo-commits with how we name our output folders
