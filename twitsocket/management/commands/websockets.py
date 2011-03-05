import asyncore
import logging
import datetime
import md5
import re
import socket
import struct
import time

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import simplejson as json

import oauth2 as oauth

from twitsocket.models import Tweet

HASH_RE = re.compile(r"(?P<start>.?) #(?P<hashtag>[A-Za-z0-9_]+)(?P<end>.?)")
HASH_RE2 = re.compile(r"^#(?P<hashtag>[A-Za-z0-9_]+)(?P<end>.?)")
USERNAME_RE = re.compile(r"(?P<start>.?)@(?P<user>[A-Za-z0-9_]+)(?P<end>.?)")

logger = logging.getLogger('twitstream')
handler = logging.FileHandler(settings.LOGFILE)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

BANNED_USERS = getattr(settings, 'BANNED_USERS', ())

POLICY_FILE = """<?xml version=\"1.0\"?>
<cross-domain-policy>
    <allow-access-from domain="*" to-ports= "*" />
</cross-domain-policy>"""


def get_oauth_request(url, consumer, token, extra_params):
    oparams = {
        'oauth_version': '1.0',
        'oauth_nonce': oauth.generate_nonce(),
        'oauth_timestamp': int(time.time()),
        'oauth_token': token.key,
        'oauth_consumer_key': consumer.key,
    }
    oparams.update(extra_params)

    req = oauth.Request(method="POST", url=url, parameters=oparams)
    signature_method = oauth.SignatureMethod_HMAC_SHA1()
    req.sign_request(signature_method, consumer, token)
    return req


class StreamClient(asyncore.dispatcher):

    def __init__(self, host, headers, body, server):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, 80))
        self.buffer = '\r\n'.join(headers) + '\r\n\r\n' + body + '\r\n\r\n'
        self.data = ''
        self.server = server
        logger.info("Twitter StreamClient listening.")

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()
        raise ValueError("Connection closed by remote host")

    def handle_read(self):
        buf = self.recv(8192)
        logger.info('Twitter: %s bytes' % len(buf))
        self.data += buf
        if not self.data.endswith('\r\n\r\n'):
            return

        data = self.data.split('\r\n')

        if len(data) > 4:
            data = data[-2:]
        content = data[1]
        if not content:
            self.data = ''
            return

        payload = json.loads(content)

        if type(payload) == int:
            self.data = ''
            return

        self.handle_json(payload)
        self.data = ''

    def writable(self):
        return len(self.buffer) > 0

    def write(self, data):
        self.buffer += data

    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]

    def handle_json(self, payload):
        if payload['user']['screen_name'] in BANNED_USERS:
            return

        dt = datetime.datetime.strptime(payload['created_at'],
                                        '%a %b %d %H:%M:%S +0000 %Y')
        dt = dt + datetime.timedelta(hours=1)
        payload['created_at'] = dt.strftime('%a %b %d %H:%M:%S +0100 %Y')

        dumped = json.dumps(payload)
        tw = Tweet(status_id=payload['id'], content=dumped).save()
        self.server.send_to_clients(dumped)


class WebSocket(asyncore.dispatcher):
    handshake_75 = """HTTP/1.1 101 Web Socket Protocol Handshake\r
Upgrade: WebSocket\r
Connection: Upgrade\r
WebSocket-Origin: %(web_server)s\r
WebSocket-Location: %(websocket_server)s/\r
WebSocket-Protocol: sample""" + '\r\n\r\n'

    handshake_76 = """HTTP/1.1 101 Web Socket Protocol Handshake\r
Upgrade: WebSocket\r
Connection: Upgrade\r
Sec-WebSocket-Origin: %(web_server)s\r
Sec-WebSocket-Location: %(websocket_server)s/\r
Sec-WebSocket-Protocol: sample""" + '\r\n\r\n'

    def __init__(self, web_server, websocket_server):
        params = {'web_server': web_server,
                  'websocket_server': websocket_server}
        self.handshake_75 = self.handshake_75 % params
        self.handshake_76 = self.handshake_76 % params
        port = int(websocket_server.split(':')[-1])

        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(('0.0.0.0', port))
        self.listen(5)

        self.clients = set()
        logger.info("Websocket server ready")

    def handle_accept(self):
        sock, addr = self.accept()
        handshaken = False
        header = ''
        while handshaken == False:
            header += sock.recv(8192)

            if (not header.startswith('<policy') and
                not header.startswith('GET /')):
                sock.close()
                return

            if header.startswith('<policy-file-request/>'):
                sock.send(POLICY_FILE)
                sock.close()
                return

            if len(header) - header.find('\r\n\r\n') == 12:
                # WebSockets 76
                handshake = self.handshake_76 + self.get_challenge(header)
                handshaken = True
                sock.send(handshake)

            elif header.find('\r\n\r\n') != -1:
                # WebSockets 75
                handshaken = True
                sock.send(self.handshake_75)
        handler = WebSocketHandler(self, sock)

    def send_to_clients(self, payload):
        if not self.clients:
            logger.info("Could have send something but no client")
        else:
            logger.info("Sending payload to %s clients" % len(self.clients))
        for client in self.clients:
            client.queue.append(payload)

    def get_challenge(self, header_string):
        headers = header_string.split('\r\n')
        header_dict = {}
        for h in [head for head in headers[1:] if ': ' in head]:
            key, value = h.split(': ', 1)
            header_dict[key] = value

        key_1 = header_dict['Sec-WebSocket-Key1']
        key_2 = header_dict['Sec-WebSocket-Key2']
        key_3 = header_string[-8:]

        def key_challenge(key):
            key_number = int(''.join([i for i in key if 47 < ord(i) < 58]))
            spaces = len([i for i in key if i == ' '])
            part = key_number / spaces
            return struct.pack('!I', part)

        challenge = key_challenge(key_1) + key_challenge(key_2) + key_3
        return md5.md5(challenge).digest()


class WebSocketHandler(asyncore.dispatcher):

    def __init__(self, server, sock):
        asyncore.dispatcher.__init__(self, sock=sock)
        self.server = server
        self.server.clients.add(self)
        self.queue = []
        logger.info("New client connected, count: %s" % len(self.server.clients))

    def handle_read(self):
        data = self.recv(4096)
        logger.debug("Got some data: %s" % data)

    def handle_write(self):
        logger.debug("Handling write")
        if self.queue:
            message = self.queue.pop(0)
            self.send('\x00%s\xff' % message)
        else:
            logger.info("Nothing to write")

    def writable(self):
        return len(self.queue) > 0

    def handle_close(self):
        self.server.clients.remove(self)
        logger.info("Client quitting, count: %s" % len(self.server.clients))
        self.close()


def dict_to_postdata(data_dict):
    body = ''
    for key, value in data_dict.items():
        data = '%s=%s' % (key, value)
        if body:
            body += '&' + data
        else:
            body = data
    return body


def all_in_one_handler():
    keywords = getattr(settings, 'TRACK_KEYWORDS', ())
    user_ids = map(str, getattr(settings, 'TRACK_USERS', ()))
    if not keywords and not user_ids:
        raise ValueError("Set at least TRACK_KEYWORDS or TRACK_USERS "
                         "in your settings")
    post_params = {}
    if keywords:
        post_params['track'] = ','.join(keywords)
    if user_ids:
        post_params['follow'] = ','.join(user_ids)

    body = dict_to_postdata(post_params)

    token = oauth.Token(secret=settings.TOKEN_SECRET,
                        key=settings.TOKEN_KEY)
    consumer = oauth.Consumer(secret=settings.CONSUMER_SECRET,
                              key=settings.CONSUMER_KEY)
    host = 'stream.twitter.com'
    path = '/1/statuses/filter.json'
    url = 'http://%s%s' % (host, path)
    request = get_oauth_request(url, consumer, token, post_params)

    headers = [
        'POST %s HTTP/1.1' % path,
        'Host: %s' % host,
        'Authorization: %s' % request.to_header()['Authorization'],
        'Content-Type: application/x-www-form-urlencoded',
        'Content-Length: %s' % len(body),
    ]

    websocket_server = WebSocket(settings.WEB_SERVER,
                                 settings.WEBSOCKET_SERVER)
    twitter_client = StreamClient(host, headers, body, websocket_server)
    asyncore.loop()


class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        all_in_one_handler()
