'''
Used to:
* keep track of output directory structure
* incroporate git commits + diffs into running
* keep track of metadata like ask user for run description or keep track of kwargs etc

git info stuff inspired by 
https://github.com/spapas/python-git-info/

'''

### packages
import os, sys
import glob
import re
import pickle
import datetime
import time
import inspect
import logging
import subprocess


### methods
def find_git_dir(starting_path):
    if not os.path.isdir(starting_path):
        starting_path = os.path.dirname(starting_path)
    dir = starting_path
    git_dir = None
    while git_dir is None:
        possible_git_dir = os.path.join(dir, ".git")
        if os.path.isdir(possible_git_dir):
            git_dir = possible_git_dir
        else:
            # check parent directory
            dir = os.path.dirname(dir)
            if (dir == "/") or (dir == "/home") or (dir == "/user") or (dir == "/users"):
                # FAILED. no point in checking higher
                break
    
    if git_dir is None:
        raise Exception("Couldn't find .git folder in %s or any of its parent directories." % starting_path)
    else:
        return git_dir


def get_git_log(git_dir):
    '''
    Simple version from gitinfo repo
    https://github.com/spapas/python-git-info/blob/master/gitinfo/gitinfo.py#L31
    '''
    head_file = os.path.join(git_dir, "HEAD")
    assert os.path.isfile(head_file), "Failed to find any HEAD file in .git folder %s" % git_dir

    # get branch name
    with open(head_file, 'r') as f:
        ref_file = os.path.join(git_dir, f.read().strip().split(" ")[1])
    assert os.path.isfile(ref_file), "Repo might be broken; can't find HEAD ref file %s" % ref_file
    branch_name = os.path.basename(ref_file)

    with open(ref_file, 'r') as f:
        full_commit_hash = f.read().strip()
    partial_commit_hash = full_commit_hash[:7]

    return branch_name, full_commit_hash, partial_commit_hash



class SOTFAssistant():
    '''
    Tuck into __init__():
    1) Establish repo-directory + output-parent-directory
    2) Get code-diff
    3) Get last directory
    4) Get what would be new directory

    Tuck into start():
    5) Interact with the user
        * if code-diff 'high', ask if they want to exit and commit code
        * ask for any 'description'
    6) Make new directory and write meta file + codediff file
        * use logging or just use assistant to write to this file?...ya just go with logging...better in long run
    '''
    def __init__(self, runfile, relative_parent_output_dir="./output", using_git=True, testing=False):
        self.testing = testing

        # 1) Establish repo-directory + output-parent-directory
        if using_git:
            self.git_dir = find_git_dir(runfile) # will return /repo_dir/.git/
            self.repo_dir = os.path.dirname(self.git_dir)
        else:
            print("ASSISTANT: ...bruh, your project doesn't have a git repo? C'mon son.")
            self.git_dir = None
            # can't use git to establish the parent directory of the codebase...just going to assume:
            self.repo_dir = os.path.dirname(os.path.abspath(runfile))
            print("So I have no way to verify that this is correct...because you aren't using git...so fix this if it is wrong...")
            print("Assuming your project's parent directory is in: %s" % self.repo_dir)

        self.parent_output_dir = os.path.abspath(os.path.join(self.repo_dir, relative_parent_output_dir))
        assert os.path.isdir(self.parent_output_dir)
        
        # 2) Get code-diff
        if using_git:
            self.branch_name, self.full_commit_hash, self.partial_commit_hash = get_git_log(self.git_dir)
            self.get_diff()
        else:
            self.branch_name = "nogit"
            self.full_commit_hash = "NA"
            self.partial_commit_hash = "NA"
            self.code_diff = None
        
        # 3) Get last directory
        latest_run_dir = self.get_latest_run()

        # 4) Get what would be new directory
        self.get_new_run_tag(latest_run_dir) # creates self.current_run_tag and self.current_run_output_folder


    def start(self):
        # 5) Interact with the user
        run_description = self.checkin_with_user()

        # 6) Make new directory and write meta file + codediff file
        os.makedirs(self.current_run_output_folder, exist_ok=True)
        if self.code_diff is not None:
            self.write_diff()
        self.setup_logger()
        logging.info("Current run tag is %s" % self.current_run_tag)
        logging.info('User-given run description is "%s"' % run_description)


    def get_diff(self):
        cmd = "git diff"
        self.code_diff = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE).stdout.decode('utf-8')


    def write_diff(self):
        with open(os.path.join(self.current_run_output_folder, "diff.log"), 'w') as f:
            f.write("Branch: %s\n" % (self.branch_name))
            f.write("Last Commit Hash: %s\n\n" % (self.full_commit_hash))
            f.write(self.code_diff)


    def checkin_with_user(self):
        # parse diff
        num_files_changed = len(re.findall(pattern="diff --git", string=self.code_diff))
        lines_added = len(re.findall(pattern="\n\+[^\+]", string=self.code_diff))
        lines_removed = len(re.findall(pattern="\n\-[^\-]", string=self.code_diff))

        print("\nASSISTANT: Since the last commit, %i files changed, %i lines added, %i lines removed." % (num_files_changed, lines_added, lines_removed))

        if (num_files_changed >= 5) or (lines_added+lines_removed >= 200):
            response = input("  Looks like you've made quite a few changes since your last commit. I recommend you exit and commit the changes; would you like to do that? (y/n) ... ")
            if response.lower() == 'y':
                raise Exception("\nASSISTANT: EXITING so that the user can `add` and `commit` their changes.")
        
        run_description = input("\nASSISTANT: Help with documentation by writing a few words describing your current run:\n--> ")
        return run_description
    

    def setup_logger(self):
        logfile = os.path.join(self.current_run_output_folder, "logfile.txt")
        if self.testing:
            level = logging.DEBUG
        else:
            level = logging.INFO
        logging.basicConfig(filename=logfile,
                            filemode='a',
                            level=level,
                            format='%(asctime)s.%(msecs)03d [%(levelname)-8s] %(module)s-%(funcName)s: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')


    def get_latest_run(self):
        # read through the folders in the output_dir and get most recent folder
        possible_output_folders = glob.glob(os.path.join(self.parent_output_dir, "*", ""), recursive=True) # should only get subfolders
        if len(possible_output_folders) > 0:
            latest_output_folder = os.path.dirname(max(possible_output_folders)) # need the dirname() call because outputs of above glob should end with "/"
            return latest_output_folder
        else:
            return None


    def get_new_run_tag(self, latest_run_dir):
        self.current_run_letter = None
        self.current_run_number = None
        self.current_test_number = None

        if latest_run_dir is None:
            # assume that we're starting a new project so initialize everything
            self.current_run_letter = "AA"
            self.current_run_number = 1
            if self.testing:
                self.current_test_number = 1
            else:
                self.current_test_number = None
        
        else:
            latest_run_tag = os.path.basename(latest_run_dir)

            # parse previous run tag to see where we left off
            prev_run_letter = re.findall(string=latest_run_tag, pattern="^([A-Z]+)[0-9]+")[0]
            prev_run_number = int(re.findall(string=latest_run_tag, pattern="^[A-Z]+([0-9]+)")[0])
            prev_run_branch = latest_run_tag.split("_")[1]
            prev_run_hash = latest_run_tag.split("_")[2]
            try:
                prev_test_number = int(re.findall(string=latest_run_tag, pattern="_TEST([0-9]+)")[0])
            except:
                prev_test_number = None

            # now see how we want to name the current run
            if self.partial_commit_hash == prev_run_hash:
                # continue with current run letter
                self.current_run_letter = prev_run_letter
                if self.testing:
                    if prev_test_number is None:
                        self.current_test_number = 1
                    else:
                        self.current_test_number = prev_test_number + 1
                    self.current_run_number = prev_run_number
                else:
                    self.current_run_number = prev_run_number + 1
                    self.current_test_number = None
        
            else:
                # new commit, new run letter
                for j, letter in enumerate([let for let in reversed(prev_run_letter)]):
                    i = len(prev_run_letter) - 1 - j #undo the reversed() to get index i from j
                    if letter == "Z":
                        if i > 0:
                            # we need to iterate the next letter
                            continue
                        else:
                            # We need to add another letter.
                            # NOTE: hopefully this will never be the case if we default with start with AA instead of A
                            # because in sorting, AAA would come before ZZ which is not what we want.
                            # Could fix this by starting with AAA but that would make it harder to see the different tags
                            # and it seems unlikely we'll go over the 27*27=729 possible letter combos before having to go to 3digits
                            self.current_run_letter = "A" * (len(prev_run_letter)+1)
                    else:
                        # https://stackoverflow.com/questions/55115070/next-letter-in-alphabet
                        next_letter = chr((ord(letter.upper())+1 - 65) % 26 + 65)
                        self.current_run_letter = prev_run_letter[:i] + next_letter + "A"*(len(prev_run_letter[i+1:]))
                        break
                
                self.current_run_number = 1
                if self.testing:
                    self.current_test_number = 1

        # form into tag
        self.current_run_tag = "%s%03i_%s_%s" % (self.current_run_letter, self.current_run_number, self.branch_name, self.partial_commit_hash)
        
        if self.testing:
            self.current_run_tag += "_TEST%03i" % self.current_test_number

        time_tag = time.strftime("%Y%m%d%H%M%S")
        self.current_run_tag += "_%s" % time_tag
        self.current_run_output_folder = os.path.join(self.parent_output_dir, self.current_run_tag)
