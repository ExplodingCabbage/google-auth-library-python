# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os

import mock
import pytest

from google.auth import _helpers
from google.auth import exceptions
from google.auth import transport
from google.oauth2 import credentials


DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

AUTH_USER_JSON_FILE = os.path.join(DATA_DIR, 'authorized_user.json')

with open(AUTH_USER_JSON_FILE, 'r') as fh:
    AUTH_USER_INFO = json.load(fh)


class TestCredentials(object):
    TOKEN_URI = 'https://example.com/oauth2/token'
    REFRESH_TOKEN = 'refresh_token'
    CLIENT_ID = 'client_id'
    CLIENT_SECRET = 'client_secret'

    @classmethod
    def make_credentials(cls):
        return credentials.Credentials(
            token=None, refresh_token=cls.REFRESH_TOKEN,
            token_uri=cls.TOKEN_URI, client_id=cls.CLIENT_ID,
            client_secret=cls.CLIENT_SECRET)

    def test_default_state(self):
        credentials = self.make_credentials()
        assert not credentials.valid
        # Expiration hasn't been set yet
        assert not credentials.expired
        # Scopes aren't required for these credentials
        assert not credentials.requires_scopes
        # Test properties
        assert credentials.refresh_token == self.REFRESH_TOKEN
        assert credentials.token_uri == self.TOKEN_URI
        assert credentials.client_id == self.CLIENT_ID
        assert credentials.client_secret == self.CLIENT_SECRET

    @mock.patch('google.oauth2._client.refresh_grant', autospec=True)
    @mock.patch(
        'google.auth._helpers.utcnow',
        return_value=datetime.datetime.min + _helpers.CLOCK_SKEW)
    def test_refresh_success(self, unused_utcnow, refresh_grant):
        token = 'token'
        expiry = _helpers.utcnow() + datetime.timedelta(seconds=500)
        grant_response = {'id_token': mock.sentinel.id_token}
        refresh_grant.return_value = (
            # Access token
            token,
            # New refresh token
            None,
            # Expiry,
            expiry,
            # Extra data
            grant_response)

        request = mock.create_autospec(transport.Request)
        credentials = self.make_credentials()

        # Refresh credentials
        credentials.refresh(request)

        # Check jwt grant call.
        refresh_grant.assert_called_with(
            request, self.TOKEN_URI, self.REFRESH_TOKEN, self.CLIENT_ID,
            self.CLIENT_SECRET)

        # Check that the credentials have the token and expiry
        assert credentials.token == token
        assert credentials.expiry == expiry
        assert credentials.id_token == mock.sentinel.id_token

        # Check that the credentials are valid (have a token and are not
        # expired)
        assert credentials.valid

    def test_refresh_no_refresh_token(self):
        request = mock.create_autospec(transport.Request)
        credentials_ = credentials.Credentials(
            token=None, refresh_token=None)

        with pytest.raises(exceptions.RefreshError, match='necessary fields'):
            credentials_.refresh(request)

        request.assert_not_called()

    def test_from_authorized_user_info(self):
        info = AUTH_USER_INFO.copy()

        creds = credentials.Credentials.from_authorized_user_info(info)
        assert creds.client_secret == info['client_secret']
        assert creds.client_id == info['client_id']
        assert creds.refresh_token == info['refresh_token']
        assert creds.token_uri == credentials._GOOGLE_OAUTH2_TOKEN_ENDPOINT
        assert creds.scopes is None

        scopes = ['email', 'profile']
        creds = credentials.Credentials.from_authorized_user_info(
            info, scopes)
        assert creds.client_secret == info['client_secret']
        assert creds.client_id == info['client_id']
        assert creds.refresh_token == info['refresh_token']
        assert creds.token_uri == credentials._GOOGLE_OAUTH2_TOKEN_ENDPOINT
        assert creds.scopes == scopes

    def test_from_authorized_user_file(self):
        info = AUTH_USER_INFO.copy()

        creds = credentials.Credentials.from_authorized_user_file(
            AUTH_USER_JSON_FILE)
        assert creds.client_secret == info['client_secret']
        assert creds.client_id == info['client_id']
        assert creds.refresh_token == info['refresh_token']
        assert creds.token_uri == credentials._GOOGLE_OAUTH2_TOKEN_ENDPOINT
        assert creds.scopes is None

        scopes = ['email', 'profile']
        creds = credentials.Credentials.from_authorized_user_file(
            AUTH_USER_JSON_FILE, scopes)
        assert creds.client_secret == info['client_secret']
        assert creds.client_id == info['client_id']
        assert creds.refresh_token == info['refresh_token']
        assert creds.token_uri == credentials._GOOGLE_OAUTH2_TOKEN_ENDPOINT
        assert creds.scopes == scopes
