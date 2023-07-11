'''
TODO

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
import subprocess



### methods
def find_git_dir(dir):
    original_dir = dir
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
        raise Exception("Couldn't find .git folder in %s or any of its parent directories." % original_dir)
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


def get_assistant(repo_dir, use_existing=True, debug=False):
    '''
    DON'T NEED ANYMORE! ...?
    '''
    repo_dir = os.path.abspath(repo_dir)
    assistant_dir = os.path.join(repo_dir, ".assistant")
    if not os.path.isdir(assistant_dir):
        use_existing = False
    #os.makedirs(assistant_dir, exist_ok=True)

    if use_existing:
        # look for existing assistant. if not found then continue as if use_existing is False
        possible_assistant = glob.glob(os.path.join(assistant_dir, "assistant*.pkl"))
        if len(possible_assistant) > 0:
            try:
                with open(max(possible_assistant), 'rb') as f:
                    assistant = pickle.load(f)
                    assistant.testing = debug
            except Exception as err:
                response = input("Error in loading pickled assistant...would you like to start from scratch? (y/n)")
                if response.lower() == 'y':
                    use_existing = True
                else:
                    raise Exception(err)
        else:
            print("Warning: Couldn't find any existing pickled-assistant so going to start from scratch.")
            use_existing = True

    if not use_existing:
        # redundant if-not statement to allow the above if-statement to switch boolean to False and trigger this loop
        assistant = SOTFAssistant(repo_dir, debug)

    return assistant


### assistant class
class SOTFAssistant():
    '''
    Used to:
    * keep track of output directory structure
    * incroporate git commits + diffs into running
    * keep track of metadata like ask user for run description or keep track of kwargs etc

    '''
    def __init__(self, repo_dir=".", testing=False, output_dir="./output"):
        assert os.path.isdir(repo_dir), "Given `repo_dir` is not actually a directory: %s" % repo_dir
        if not os.path.isabs(repo_dir):
            repo_dir = os.path.abspath(repo_dir)

        self.git_dir = find_git_dir(repo_dir)
        self.repo_dir = os.path.dirname(self.git_dir) # overwrite whatever the user passed for 'repo_dir' with the parent dir of the .git folder because we know 100% that one is correct
        if os.path.isabs(output_dir):
            self.output_dir = output_dir
        else:
            # big assumption here that this will work!
            self.output_dir = os.path.abspath(os.path.join(repo_dir, output_dir))
        assert os.path.isdir(self.output_dir), "Given `output_dir` is not actually a directory: %s" % self.output_dir

        self.testing = testing
        self.commit_log = {}

    def save(self):
        assistant_dir = os.path.join(self.repo_dir, ".assistant")
        os.makedirs(assistant_dir, exist_ok=True)
        with open(os.path.join(assistant_dir,"assistant.pkl"), 'wb') as f:
            pickle.dump(self, f)
        print("Assistant saved.")


    def parse_output_dir(self):
        # read through the folders in the output_dir and get most recent folder
        possible_output_folders = glob.glob(os.path.join(self.output_dir, "*", ""), recursive=True) # should only get subfolders
        if len(possible_output_folders) > 0:
            latest_output_folder = os.path.basename(os.path.dirname(max(possible_output_folders))) # need the dirname() call because outputs of glob should end with "/"
            return latest_output_folder
        else:
            return None


    def get_new_run_tag(self):
        self.current_run_letter = None
        self.current_run_number = None
        self.current_test_number = None
        self.branch_name, self.full_commit_hash, self.partial_commit_hash = get_git_log(self.git_dir)
        latest_run_log = self.parse_output_dir()
        if latest_run_log is None:
            # assume that we're starting a new project so initialize everything
            self.current_run_letter = "AA"
            self.current_run_number = 1
            if self.testing:
                self.current_test_number = 1
            else:
                self.current_test_number = None
            self.commit_log[self.full_commit_hash] = self.current_run_letter
        else:
            prev_run_letter = re.findall(string=latest_run_log, pattern="^([A-Z]+)[0-9]+")[0]
            prev_run_number = int(re.findall(string=latest_run_log, pattern="^[A-Z]+([0-9]+)")[0])
            try:
                prev_test_number = int(re.findall(string=latest_run_log, pattern="_TEST([0-9]+)")[0])
            except:
                prev_test_number = None
            print(prev_run_letter, prev_run_letter, prev_test_number)

            if (self.full_commit_hash in self.commit_log) and (self.commit_log[self.full_commit_hash] == prev_run_letter):
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
                
                self.commit_log[self.full_commit_hash] = self.current_run_letter
                self.current_run_number = 1
                if self.testing:
                    self.current_test_number = 1

        # form into tag
        self.current_run_tag = "%s%03i_%s_%s" % (self.current_run_letter, self.current_run_number, self.branch_name, self.partial_commit_hash)
        
        if self.testing:
            self.current_run_tag += "_TEST%03i" % self.current_test_number

        time_tag = time.strftime("%Y%m%d%H%M%S")
        self.current_run_tag += "_%s" % time_tag


    def get_diff(self):
        cmd = "git diff"
        self.repo_diff = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE).stdout.decode('utf-8')

        # parse diff
        num_files_changed = len(re.findall(pattern="diff --git", string=self.repo_diff))
        lines_added = len(re.findall(pattern="\n\+[^\+]", string=self.repo_diff))
        lines_removed = len(re.findall(pattern="\n\-[^\-]", string=self.repo_diff))

        print("\nSince the last commit, %i files changed, %i lines added, %i lines removed." % (num_files_changed, lines_added, lines_removed))

        if (num_files_changed >= 5) or (lines_added+lines_removed >= 200):
            response = input("  Looks like you've made quite a few changes since your last commit. I recommend you exit and commit the changes; would you like to do that? (y/n)")
            if response.lower() == 'y':
                raise Exception("\nEXITING so that the user can `add` and `commit` their changes.")


    def write_diff(self):
        with open(os.path.join(self.current_run_output_folder, "diff.log"), 'w') as f:
            f.write("Branch: %s\n" % (self.branch_name))
            f.write("Last Commit Hash: %s\n\n" % (self.full_commit_hash))
            f.write(self.repo_diff)


    def start(self):
        self.get_diff()
        self.get_new_run_tag()
        self.save()
        self.current_run_output_folder = os.path.join(self.output_dir, self.current_run_tag)
        os.makedirs(self.current_run_output_folder, exist_ok=True)
        self.write_diff()
    

    def write_meta(self):
        '''
        TODO write a script that will make a meta file at the start
        and then open file with 'w+' so we can add new lines.
        Also allow ther user to add a description at the start of the run
        when assistant is started
        '''
    
    def ask_for_description(self):
        pass

    def document_kwargs(self):
        '''
        Maybe this should get moved to whatever file handles the start and writing of the meta file...
        * create the meta file
        * add to it the kwargs at the start of the run after the diff has been made
        * then go and ask for description?
        * then have the write_meta() method to append to the file?
        '''
        pass
