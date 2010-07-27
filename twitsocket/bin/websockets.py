import asyncore
import base64
import logging
import re
import socket
import struct
import md5

from django.conf import settings
from django.utils import simplejson as json
from django.utils.html import urlize

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


def twitterfy(tweet):
    # FIXME highlights every other word when there are many...
    link = r'\g<start> <a target="_blank" href="http://search.twitter.com/search?q=\g<hashtag>"  title="#\g<hashtag> on Twitter">#\g<hashtag></a>\g<end>'
    tweet = HASH_RE.sub(link, tweet)
    link = r'<a target="_blank" href="http://search.twitter.com/search?q=\g<hashtag>" title="#\g<hashtag> on Twitter">#\g<hashtag></a>\g<end>'
    tweet = HASH_RE2.sub(link, tweet)

    link = r'\g<start><a target="_blank" href="https://twitter.com/\g<user>" title="@\g<user> on Twitter">@\g<user></a>\g<end>'
    return USERNAME_RE.sub(link, tweet)


def process(tweet):
    return urlize(twitterfy(tweet))


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
        raise ValueError("Connection closed by foreign host")

    def handle_read(self):
        self.data += self.recv(8192)
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
        if 'text' in payload:
            if payload['user']['screen_name'] in BANNED_USERS:
                return

            payload['text'] = process(payload['text'])
            if 'retweeted_status' in payload:
                payload['retweeted_status']['text'] = process(payload['retweeted_status']['text'])
            dumped = json.dumps(payload)
            tw = Tweet(status_id=payload['id'], content=dumped).save()
            self.server.send_to_clients(dumped)
        else:
            logger.info("Skipping a status that was not a tweet")


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

            if len(header) - header.find('\r\n\r\n') == 12:
                # WebSockets 76
                handshake = self.handshake_76 + self.get_challenge(header)
                handshaken = True
                sock.send(handshake)

            elif header.find('\r\n\r\n') != -1:
                # WebSocket 75
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
        key_number_1 = int(''.join([i for i in key_1 if 47 < ord(i) < 58]))
        key_number_2 = int(''.join([i for i in key_2 if 47 < ord(i) < 58]))
        spaces_1 = len([i for i in key_1 if i == ' '])
        spaces_2 = len([i for i in key_2 if i == ' '])

        part_1 = key_number_1 / spaces_1
        part_2 = key_number_2 / spaces_2

        challenge = struct.pack('!I', part_1)
        challenge += struct.pack('!I', part_2)
        challenge += key_3
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


def main():
    # FIXME switch to OAuth
    token = base64.encodestring('%s:%s' % (settings.TWITTER_USERNAME,
                                           settings.TWITTER_PASSWORD)).strip()
    host = 'stream.twitter.com'
    track = 'track=' + '%2C'.join(settings.TRACK_KEYWORDS)
    users = 'follow=' + '%2C'.join(map(str, settings.TRACK_USERS))
    if not track and not users:
        raise ValueError("Set at least TRACK_KEYWORDS or TRACK_USERS "
                         "in your settings")
    body = track
    if body:
        body += '&' + users
    else:
        body = users
    headers = [
        'POST /1/statuses/filter.json HTTP/1.1',
        'Host: %s' % host,
        'Content-Type: application/x-www-form-urlencoded',
        'Content-Length: %s' % len(body),
        'Authorization: Basic %s' % token,
    ]

    websocket_server = WebSocket(settings.WEB_SERVER,
                                 settings.WEBSOCKET_SERVER)
    twitter_client = StreamClient(host, headers, body, websocket_server)
    asyncore.loop()


if __name__ == '__main__':
    main()
