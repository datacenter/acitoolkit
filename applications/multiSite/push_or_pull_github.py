from github3 import login
import sys

DEFAULT_ACCT = ''
DEFAULT_PASSWORD = ''
DEFAULT_REPO_OWNER = ''
DEFAULT_REPO = ''
DEFAULT_FILE = ''
DEFAULT_MESSAGE = ''
DEFAULT_CONTENT = ''
DEFAULT_BRANCH = 'master'


# login to github
def github_login(acct, pw):
    """
    :param acct: user name
    :param pw: password
    :return: an object of github account
    """
    return login(acct, pw)


def get_repo(github, owner, repo_name):
    """
    :param github: github account
    :param owner: owner of the repo
    :param repo_name: name of the repo
    :return: an object of the repo
    """
    return github.repository(owner, repo_name)


def create_repo(github, repo_name):
    """
    :param github: github account
    :param repo_name: name repo
    :return: an object of the repo
    """
    github.create_repo(repo_name)


def get_file(repo, file_name, branch=DEFAULT_BRANCH):
    """
    :param repo: an object of repo
    :param file_name: file_name
    :param branch: branch name, default='master'
    :return: content of file
    """
    return repo.contents(file_name, ref='refs/heads/' + branch)


def create_file(repo, file_name, commit_msg, content, branch=DEFAULT_BRANCH):
    """
    :param repo: an object of repo
    :param file_name: file_name
    :param commit_msg: commit message
    :param content: content that to be written to the file
    :param branch: branch name, default='master'
    :return: None
    """
    repo.create_file(file_name, commit_msg, content, branch=branch)


def push_to_github(user_acct=DEFAULT_ACCT,
                   user_password=DEFAULT_PASSWORD,
                   repo_owner=DEFAULT_REPO_OWNER,
                   repo_name=DEFAULT_REPO,
                   file_name=DEFAULT_FILE,
                   commit_msg=DEFAULT_MESSAGE,
                   content=DEFAULT_CONTENT,
                   branch=DEFAULT_BRANCH):
    """
    :param user_acct: github account name
    :param user_password: password
    :param repo_owner: own of the repo. Usually it is your github account
    :param repo_name: name of repo
    :param file_name: name of file
    :param commit_msg: commit message
    :param content: content that to be written to the file
    :param branch: branch name, default='master'
    :return: None
    """

    g = github_login(user_acct, user_password)
    r = get_repo(g, repo_owner, repo_name)
    if not r:
        create_repo(g, repo_name)
        r = get_repo(g, user_acct, repo_name)
    f = get_file(r, file_name, branch=branch)

    # if file already exist, delete it.
    if f:
        f.delete('delete')

    create_file(r, file_name, commit_msg, content, branch=branch)
    print "Successfully push to github."


def get_file_content(file):
    """
    :param file: file
    :return: content in the file
    """
    return file.decoded


def pull_from_github(user_acct=DEFAULT_ACCT,
                     user_passwood=DEFAULT_PASSWORD,
                     repo_owner=DEFAULT_REPO_OWNER,
                     repo_name=DEFAULT_REPO,
                     file_name=DEFAULT_FILE,
                     branch=DEFAULT_BRANCH):
    """
    :param user_acct: github account name
    :param user_password: password
    :param repo_owner: own of the repo. Usually it is your github account
    :param repo_name: name of repo
    :param file_name: name of file
    :param branch: branch name, default='master'
    :return: content of the file.
    """
    g = github_login(user_acct, user_passwood)
    r = get_repo(g, repo_owner, repo_name)
    if not r:
        print('Requested repo does not exist.')
        sys.exit()

    f = get_file(r, file_name, branch=branch)
    if not f:
        print('Requested file does not exist.')
        sys.exit()

    return get_file_content(f)


if __name__ == '__main__':
    pull_from_github()
