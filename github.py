from github3 import login, GitHub
import twitter
import time
import os
import pickle
from getpass import getpass, getuser
from config import secret, LOGIN, PASSWORD


'''
TODO:
** save list of subscribers on repos
'''


api = twitter.Api(secret.keys['consumer_key'], secret.keys['consumer_secret'],
    secret.keys['auth_key'], secret.keys['auth_secret'])
list_of_repos = []
SPECIAL_COMMANDS = [3, 4]


def get_data(filename='id.dat'):
    with open(filename, 'rb') as file:
        return pickle.load(file)


def check(problem):
    if problem['command'] not in SPECIAL_COMMANDS:
        return True
    else:
        return problem['user'].lower() == problem['params'][0].lower()


def solve(problem, gh):
    functions = {0: get_last_commit,
                 1: get_list_of_participants,
                 2: get_count_of_open_issues,
                 3: add_new_user_to_repository,
                 4: make_new_issue,
                 5: notice_about_commits,
                 6: help}
    return functions[problem['command']](gh, problem['params'])


def get_last_commit(gh, params):
    pattern = 'Latest commit in "%s" is "%s" by %s'
    print(params)
    owner = params[0]
    repository = params[1].split('/')[1]
    last_commit = gh.repository(owner, repository).list_commits()[0]
    return pattern % (repository, last_commit.commit.message,
                    last_commit.commit.author.name)


def get_list_of_participants(gh, params):
    pattern = 'List of contributors of %s: %s'
    owner = params[0]
    repository = params[1].split('/')[1]
    list_of_participants = []
    for user in gh.repository(owner, repository).list_contributors():
        list_of_participants.append(user.login)
    return pattern % (params[1], str(list_of_participants))


def get_count_of_open_issues(gh, params):
    pattern = 'There are %d open issues in %s. The latest is "%s".'
    owner = params[0]
    repository = params[1].split('/')[1]
    list_of_issues = gh.list_repo_issues(owner, repository)
    if len(list_of_issues) > 0:
        return pattern % (len(list_of_issues),
                        params[1], str(list_of_issues[0].title))
    else:
        return 'There are no open issues in %s' % params[1]


def make_new_issue(gh, params):
    repository = params['repository']
    owner = params['owner']
    title = params['title']
    return gh.create_issue(repository, owner, title)


def add_new_user_to_repository(gh, params):
    repo = params['repository']
    login = params['owner']
    return gh.watch(login, repo)


def notice_about_commits(gh, params):
    global list_of_repos
    user = params[0]
    repo = params[1]
    if repo in list_of_repos:
        list_of_repos[list_of_repos.index(repo)]['users'].append(user)
    else:
        commit = ''
        users = [user]
        params = repo
        new_repo = {'commit': commit, 'users': users, 'params': params}
        list_of_repos.append(new_repo)
    return 'OK, you have subscribed on %s' % repo


def check_new_commits(gh):
    pattern = '%s In repository %s found new commit(-s).'
    for repo in list_of_repos:
        commit = get_last_commit(gh, repo['params'])
        if commit != repo['commit']:
            repo['commit'] = commit
            send_to_twitter(pattern % ('@'.join(repo['users']),
                            repo['params'][1]))


def help(gh, params):
    return "Usage: @GitToTweet [command], [params, params, ..., params]"


def auth_user():
    gh = login(LOGIN, PASSWORD)
    return gh


def form_problem(problem):
    commands = ['get last commit',
                'get list of participants',
                'get count of open issues',
                'add new user to repository',
                'make new issue',
                'notice me about commits',
                'help']
    text = problem['text'].lower()
    text = text.split(', ')
    print(text)
    command = ' '.join(text[0].split()[1:])
    params = text[1:]
    if command in commands:
        command = commands.index(command)
        user = problem['user']['screen_name']
        return {'command': command, 'user': user, 'params': params}
    else:
        return None


def get_problems():
    global api
    idx = get_data()
    print(idx)
    list_of_problems = api.get_new_mentions(idx)
    problems = []
    for problem in list_of_problems:
        problem = form_problem(problem)
        if problem == None:
            pass
        elif problem['command'] == None:
            send_to_twitter('@%s %s' % (problem['user'], 'Command not found'))
        elif check(problem):
            problems.append(problem)
        else:
            send_to_twitter('@%s %s' % (problem['user'], 'Access denied!'))
    return problems


def send_to_twitter(text):
    global api
    api.post_update(text)


def main():
    gh = auth_user()

    while True:
        print('Get new list of problems')
        problems = get_problems()
        for problem in problems:
            result = solve(problem, gh)
            print('Send results to twitter')
            send_to_twitter('@%s %s.' % (problem['user'], result))
        check_new_commits(gh)
        time.sleep(10)


if __name__ == '__main__':
    main()
