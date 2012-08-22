from github3 import login, GitHub
import twitter
import time
import os
import pickle
from getpass import getpass, getuser
from config import secret, LOGIN, PASSWORD


FILENAME = 'repos.dat'


'''
TODO:
** logging instead of print
** regexp for matching commands
'''


api = twitter.Api(secret.keys['consumer_key'], secret.keys['consumer_secret'],
    secret.keys['auth_key'], secret.keys['auth_secret'])
dict_of_repos = {}
SPECIAL_COMMANDS = []


def get_data(filename='id.dat'):
    with open(filename, 'rb') as file:
        return pickle.load(file)


def save(data):
    path = os.path.dirname(__file__)
    filename = FILENAME
    path = os.path.join(path, filename)
    log_file = open(path, 'wb')
    pickle.dump(data, log_file)
    log_file.close()


def check(problem):
    if problem['command'] not in SPECIAL_COMMANDS:
        return True
    else:
        return problem['user'].lower() == problem['params'][0].lower()


def solve(problem, gh):
    functions = {0: get_last_commit,
                 1: get_list_of_contributors,
                 2: get_count_of_open_issues,
                 3: get_count_of_commits,
                 4: get_count_of_repos,
                 5: subscribe_on_commits,
                 6: help,
                 7: unsubscribe_on_commits}
    return functions[problem['command']](gh, problem['params'], problem['user'])


def get_last_commit(gh, params, user):
    pattern = 'Latest commit in "%s" is "%s" by %s'
    repository = gh.repository(params[0], params[1])
    last_commit = repository.list_commits()[0]
    return pattern % (repository.name, last_commit.commit.message,
                    last_commit.commit.author.name)


def get_count_of_commits(gh, params, user):
    pattern = 'There %s %s commit%s in "%s"'
    repository = gh.repository(params[0], params[1])
    count = len(repository.list_commits())
    if count == 0:
        return pattern % ('is', 'NO', 's', repository.name)
    elif count == 1:
        return pattern % ('is', 'ONE', '', repository.name)
    else:
        return pattern % ('are', str(count), 's', repository.name)


def get_count_of_repos(gh, params, user):
    pattern = 'There %s %s repo%s by %s'
    owner = gh.user(params[0])
    count = owner.public_repos
    if count == 0:
        return pattern % ('is', 'NO', 's', owner.login)
    elif count == 1:
        return pattern % ('is', 'ONE', '', owner.login)
    else:
        return pattern % ('are', str(count), 's', owner.login)


def get_list_of_contributors(gh, params, user):
    pattern = 'List of contributors of %s: %s'
    list_of_contributors = []
    for user in gh.repository(params[0], params[1]).list_contributors():
        list_of_contributors.append(user.login)
    return pattern % (params[1], str(list_of_contributors))


def get_count_of_open_issues(gh, params, user):
    pattern = 'There %s %s open issues in %s%s'
    latest = '. The latest is "%s".'
    list_of_issues = gh.list_repo_issues(params[0], params[1])
    count = len(list_of_issues)
    if count == 0:
        return pattern % ('is', 'NO', params[1], '')
    elif count == 1:
        return patter % ('is', 'ONE', params[1], latest % list_of_issues[0].title)
    else:
        return patter % ('are', str(count), params[1], latest % list_of_issues[0].title)


def subscribe_on_commits(gh, params, user):
    global dict_of_repos
    name = params[0] + '/' + params[1]
    if not (name in dict_of_repos.keys()):
        dict_of_repos[name] = {}
        dict_of_repos[name]['users'] = [user]
        dict_of_repos[name]['commit'] = ''
    else:
        dict_of_repos[name]['users'].append(user)
    save(dict_of_repos)
    return 'You was successful subscribed on this repository'


def unsubscribe_on_commits(gh, params, user):
    global dict_of_repos
    name = params[0] + '/' + params[1]
    if not (name in dict_of_repos.keys()):
        return 'You wasn\'t subscribed on this repo'
    else:
        if not (user in dict_of_repos[name]['users']):
            return 'You wasn\'t subscribed on this repo'
        else:
            while dict_of_repos[name]['users'].index(user):
                num = dict_of_repos[name]['users'].index(user)
                del dict_of_repos[name]['users'][num]
            return 'You was successful unsubscribed'
            save(dict_of_repos)


def check_new_commits(gh):
    global dict_of_repos
    pattern = '@%s %s'
    for repo, users in dict_of_repos.items():
        commit = get_last_commit(gh, repo.split('/'), '')
        if commit != users['commit']:
            for user in users['users']:
                print('NEW commit!')
                send_to_twitter(pattern % (user, commit))
            dict_of_repos[repo]['commit'] = commit


def help(gh, params):
    return "Usage: @GitToTweet [command], [params, params, ..., params]"


def auth_user():
    gh = login(LOGIN, PASSWORD)
    return gh


def form_problem(problem):
    commands = ['get last commit',
                'get list of contributors',
                'get count of open issues',
                'get count of commits',
                'get count of repos',
                'subscribe me',
                'help',
                'unsubscribe me']
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
    global dict_of_repos
    gh = auth_user()
    try:
        dict_of_repos = get_data('repos.dat')
    except:
        save(dict_of_repos)
    while True:
        print('Get new list of problems')
        problems = get_problems()
        for problem in problems:
            result = solve(problem, gh)
            try:
                result = solve(problem, gh)
            except:
                result = 'Repository not found'
            send_to_twitter('@%s %s.' % (problem['user'], result))
        check_new_commits(gh)
        time.sleep(10)


if __name__ == '__main__':
    main()
