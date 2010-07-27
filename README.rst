Twitsocket, twitter + WebSockets = ♥
====================================

A twitter wall / live stream for your conference / event / topic of interest,
integrated in your Django website.

How it works
------------

Twitsocket has 3 components:

* A client for twitter's streaming API which you can use to track keywords and
  specific accounts.

* A websocket server to broadcast new tweets to every connected client.

* A tiny Django app to store the tweets in a DB and render them.

Bonus
-----

There is a ``lister`` management command which you can use to maintain a
Twitter list of people tweeting about the subject you're tracking.

Installation
------------

::

    pip install -e git+git://github.com/brutasse/django-twitsocket

Configuration
-------------

Add ``twitsocket`` to your ``INSTALLED_APPS``, run ``syncdb`` and add a few
settings::

    TWITTER_USERNAME = 'yourtwitterusername'
    TWITTER_PASSWORD = 'yourtwitterpassword'

    # Optional, in case of spam
    BANNED_USERS = ('list', 'of', 'banned', 'users')

    TRACK_KEYWORDS = ('europython', 'python', 'java')
    TRACK_USERS = (15324940, 15389140) # Only IDs here

    # The WebSocket port is mandatory, no trailing slash.
    WEBSOCKET_SERVER = 'ws://ws.example.com:8888'
    WEB_SERVER = 'http://example.com'

    # The log file tells you when new clients and new tweets arrive.
    LOGFILE = '/path/to/logfile.log'

If you want to use the ``lister`` command, create the list on twitter and add
it to your settings::

    TWITTER_LIST = 'europython2010'

Running ``manage.py lister`` will add everyone to the list. Run it every once
a while, Twitter has a rate-limit (and apparently a max. of 500 ppl on a
list).

Create a view somewhere that renders a template and add this to the content::

    {% load twitsocket_tags %}

    {% render_tweets 30 %}

    {% websocket_client %}

You need jquery>=1.4 for the ``websocket_client`` part.

Running the websocket server
----------------------------

::

    DJANGO_SETTINGS_MODULE=settings python /path/to/twitsocket/bin/websockets.py

Ideally, you should put this line in a bash script and run it with supervisord
to restart it automatically when Twitter cuts the connection.

Styling
-------

This example CSS code will add a nice look to your tweets (WTFPL, modify it to
fit your needs)::

    #tweets {
      font: normal 18px Georgia, Times, serif; width: 600px;
      margin: 10px auto;                       padding: 10px;
      border: 1px solid #ccc;                  background-color: #eee;
    }
    #tweets a { text-decoration: none;     color: #4096ee; }
    #tweets a.username { color: #73880a;   font-weight: bold; }
    #tweets a:hover { text-decoration: underline; }
    #tweets .tweet { color: #444; }
    #tweets .tweet img {
      display: block;          float: left;
      background-color: #fff;  border: 1px solid #bbb;
      padding: 3px;            margin-right: 10px;
    }
    #tweets .tweet p {
      margin: 0;               padding: 0;
      float: left;             width: 500px;
    }
    #tweets .clear {
      clear: both;             border-bottom: 1px solid #ccc;
      margin-bottom: 10px;     padding-bottom: 10px;
      font-size: 0.8em;        color: #aaa;
      text-align: right;       text-shadow: 0 1px 0 #fff;
    }
    #tweets .rt {
      color: #d01f3c;   font-weight: bold;     padding-right: 15px;
    }
    .notice {
      width: 610px;            text-shadow: 0 1px 0 #fff;
      margin: 10px auto;       background-color: #FFFFaa;
      padding: 5px;            border: 1px solid #eecc55;
      color: #555;             font-size: 0.8em;
    }

The flash hack
--------------

As you may know, not all browsers support WebSockets. They are implemented in
Safari, Chrome and Firefox 4. There is a clever hack involving Flash that
implements WebSockets for older browsers. To enable it, copy or symlink the
media files shipped with ``twitsocket`` under the ``flash`` namespace of your
``MEDIA_URL``::

    cp -a /path/to/twitsocket/media media/flash

Then add to your ``<head>`` block (assuming you've loaded
``twitsocket_tags``)::

    <head>
        <title> ... whatever you have </title>
        ...
        {% flash_hack %}
    </head>

And `follow the instructions here`_ to add a Flash Socket Policy File on port
843.

.. _follow the instructions here: http://www.lightsphere.com/dev/articles/flash_socket_policy.html

TODO
----

* Switch to OAuth for the streaming consumer and the ``lister`` management
  command.

* Try to decouple the Twitter consumer and the WebSocket server. Maybe with
  Redis and its Pub/Sub mechanism.
