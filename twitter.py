import oauth.oauth as oauth
import http
import urllib.parse
import json
import pickle
import os


HOME_TIMELINE_URL = 'http://api.twitter.com/1/statuses/home_timeline.json'
UPDATE_URL = 'http://api.twitter.com/1/statuses/update.json'
MENTIONS_URL = 'http://api.twitter.com/1/statuses/mentions.json'
FILENAME = 'id.dat'


class SecretKeys:
    keys = {}

    def __init__(self, consumer_key, consumer_secret, auth_key, auth_secret):
        self.keys = {'consumer_key': consumer_key,
                     'consumer_secret': consumer_secret,
                     'auth_key': auth_key,
                     'auth_secret': auth_secret}


class Api(object):
    def _to_query_string(self, params):
        return '&'.join(['%s=%s' % (urllib.parse.quote(k, ''),
                urllib.parse.quote(str(v), '')) for k, v in params.items()])

    def __init__(self, consumer_key, consumer_secret, user_key, user_secret):
        self.signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self.access_token = oauth.OAuthToken(user_key, user_secret)

    def _get_connection(self):
        self.connection = http.client.HTTPConnection('twitter.com')

    def _save(self, data):
        path = os.path.dirname(__file__)
        filename = FILENAME
        path = os.path.join(path, filename)
        log_file = open(path, 'wb')
        pickle.dump(data, log_file)
        log_file.close()

    def post_update(self, text):
        status = text
        params = {'status': status}
        self._get_connection()
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer, token=self.access_token, http_method='POST',
            http_url=UPDATE_URL, parameters=params)
        oauth_request.sign_request(self.signature_method, self.consumer,
            self.access_token)
        self.connection.request(oauth_request.http_method, UPDATE_URL,
            headers=oauth_request.to_header(),
            body=self._to_query_string(params))
        response = str(self.connection.getresponse().read(), encoding='utf-8')
        return self

    def get_new_mentions(self, idx):
        params = {'since_id': idx}
        self._get_connection()
        oauth_request =\
            oauth.OAuthRequest.from_consumer_and_token(self.consumer,
                            token=self.access_token, http_method='GET',
                            http_url=MENTIONS_URL, parameters=params)
        oauth_request.sign_request(self.signature_method,
                                        self.consumer, self.access_token)
        self.connection.request(oauth_request.http_method,
                    MENTIONS_URL + '?' + self._to_query_string(params),
                    headers=oauth_request.to_header())
        response = str(self.connection.getresponse().read(), encoding='utf-8')
        list_of_problems = []
        for status in json.loads(response):
            list_of_problems.append(status)
            print(status['text'])
            idx = status['id']
        self._save(idx)
        return list_of_problems
