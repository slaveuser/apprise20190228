# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 Chris Caron <lead2gold@gmail.com>
# All rights reserved.
#
# This code is licensed under the MIT License.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files(the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and / or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions :
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import requests
from json import dumps

from .NotifyBase import NotifyBase
from .NotifyBase import HTTP_ERROR_MAP
from ..common import NotifyImageSize
from ..common import NotifyType
from ..utils import compat_is_basestring


class NotifyJSON(NotifyBase):
    """
    A wrapper for JSON Notifications
    """

    # The default descriptive name associated with the Notification
    service_name = 'JSON'

    # The default protocol
    protocol = 'json'

    # The default secure protocol
    secure_protocol = 'jsons'

    # A URL that takes you to the setup/help of the specific protocol
    setup_url = 'https://github.com/caronc/apprise/wiki/Notify_Custom_JSON'

    # Allows the user to specify the NotifyImageSize object
    image_size = NotifyImageSize.XY_128

    # Disable throttle rate for JSON requests since they are normally
    # local anyway
    request_rate_per_sec = 0

    def __init__(self, headers, **kwargs):
        """
        Initialize JSON Object

        headers can be a dictionary of key/value pairs that you want to
        additionally include as part of the server headers to post with

        """
        super(NotifyJSON, self).__init__(**kwargs)

        if self.secure:
            self.schema = 'https'

        else:
            self.schema = 'http'

        self.fullpath = kwargs.get('fullpath')
        if not compat_is_basestring(self.fullpath):
            self.fullpath = '/'

        self.headers = {}
        if headers:
            # Store our extra headers
            self.headers.update(headers)

        return

    def url(self):
        """
        Returns the URL built dynamically based on specified arguments.
        """

        # Define any arguments set
        args = {
            'format': self.notify_format,
            'overflow': self.overflow_mode,
        }

        # Append our headers into our args
        args.update({'+{}'.format(k): v for k, v in self.headers.items()})

        # Determine Authentication
        auth = ''
        if self.user and self.password:
            auth = '{user}:{password}@'.format(
                user=self.quote(self.user, safe=''),
                password=self.quote(self.password, safe=''),
            )
        elif self.user:
            auth = '{user}@'.format(
                user=self.quote(self.user, safe=''),
            )

        default_port = 443 if self.secure else 80

        return '{schema}://{auth}{hostname}{port}/?{args}'.format(
            schema=self.secure_protocol if self.secure else self.protocol,
            auth=auth,
            hostname=self.host,
            port='' if self.port is None or self.port == default_port
                 else ':{}'.format(self.port),
            args=self.urlencode(args),
        )

    def send(self, body, title='', notify_type=NotifyType.INFO, **kwargs):
        """
        Perform JSON Notification
        """

        # prepare JSON Object
        payload = {
            # Version: Major.Minor,  Major is only updated if the entire
            # schema is changed. If just adding new items (or removing
            # old ones, only increment the Minor!
            'version': '1.0',
            'title': title,
            'message': body,
            'type': notify_type,
        }

        headers = {
            'User-Agent': self.app_id,
            'Content-Type': 'application/json'
        }

        # Apply any/all header over-rides defined
        headers.update(self.headers)

        auth = None
        if self.user:
            auth = (self.user, self.password)

        url = '%s://%s' % (self.schema, self.host)
        if isinstance(self.port, int):
            url += ':%d' % self.port

        url += self.fullpath

        self.logger.debug('JSON POST URL: %s (cert_verify=%r)' % (
            url, self.verify_certificate,
        ))
        self.logger.debug('JSON Payload: %s' % str(payload))

        # Always call throttle before any remote server i/o is made
        self.throttle()

        try:
            r = requests.post(
                url,
                data=dumps(payload),
                headers=headers,
                auth=auth,
                verify=self.verify_certificate,
            )
            if r.status_code != requests.codes.ok:
                try:
                    self.logger.warning(
                        'Failed to send JSON notification: '
                        '%s (error=%s).' % (
                            HTTP_ERROR_MAP[r.status_code],
                            r.status_code))

                except KeyError:
                    self.logger.warning(
                        'Failed to send JSON notification '
                        '(error=%s).' % (r.status_code))

                # Return; we're done
                return False

            else:
                self.logger.info('Sent JSON notification.')

        except requests.RequestException as e:
            self.logger.warning(
                'A Connection error occured sending JSON '
                'notification to %s.' % self.host)
            self.logger.debug('Socket Exception: %s' % str(e))

            # Return; we're done
            return False

        return True

    @staticmethod
    def parse_url(url):
        """
        Parses the URL and returns enough arguments that can allow
        us to substantiate this object.

        """
        results = NotifyBase.parse_url(url)

        if not results:
            # We're done early as we couldn't load the results
            return results

        # Add our headers that the user can potentially over-ride if they wish
        # to to our returned result set
        results['headers'] = results['qsd-']
        results['headers'].update(results['qsd+'])

        return results
