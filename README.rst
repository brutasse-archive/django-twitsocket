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

Installation
------------

::

    pip install https://github.com/brutasse/django-twitsocket/tarball/master

**Requirements**:

* Python >=2.4
* Django >= 1.0
* python-oauth2
* Jquery >= 1.4 enabled in your templates.

Configuration
-------------

You need to register an OAuth consumer on twitter.com (read AND write if you
want to maintain the Twitter list) and get a token for it (using ``tweepy``
and `this script`_ for instance).

.. _this script: https://gist.github.com/545143

Add ``twitsocket`` to your ``INSTALLED_APPS``, run ``syncdb`` and add a few
settings::

    CONSUMER_SECRET = 'your consumer secret'
    CONSUMER_KEY = 'your consumer key'

    TOKEN_SECRET = 'your token secret'
    TOKEN_KEY = 'your token key'

    # Optional, in case of spam
    BANNED_USERS = ('list', 'of', 'banned', 'users')

    TRACK_KEYWORDS = ('europython', 'python', 'java')
    TRACK_USERS = (15324940, 15389140) # Only IDs here

    # The WebSocket port is mandatory, no trailing slash.
    WEBSOCKET_SERVER = 'ws://ws.example.com:8888'
    WEB_SERVER = 'http://example.com'

    # The log file tells you when new clients and new tweets arrive.
    LOGFILE = '/path/to/logfile.log'

Create a view somewhere that renders a template and add this to the content::

    {% load twitsocket_tags %}

    {% render_tweets 30 %}

    {% websocket_client %}

Extra template tags
-------------------

The following template tags are available. They are not required but may be
used to display extra information about the stream.

* **count**: ``{% count %}`` will output the number of tweets saved in the
  database. The counter is automatically incremented when new tweets are
  received.

* **top_users**: ``{% top_users <num> %}`` will display the top ``<num>``
  users, people who are tweeting the most about the topic.

* **top_tweets**: ``{% top_tweets <num> %}`` will display the top ``<num>``
  tweets, ordered by number of retweets.

* **retweet_switch**: ``{% retweet_switch %}`` will display a "show retweets" /
  "hide retweets" button if users want to see only original tweets. The user's
  preference is stored in the browser's localStorage and restored when the
  page is reloaded.

.. note::

    For the ``top_users`` and ``top_tweets`` tags, you need to run the
    ``top_tweets`` management command every once a while to refreshed the
    cached values. It's up to you to decide on the frequency since the
    operation can be rather intensive with a large number of tweets.

Running the websocket server
----------------------------

::

    ./manage.py websockets

Ideally, you should put this line in a bash script and run it with supervisord
to restart it automatically when Twitter cuts the connection.

Bonus
-----

There is a ``lister`` management command which you can use to maintain a
Twitter list of people tweeting about the subject you're tracking.

If you want to use the command, create the list on twitter and add it to your
settings (prepend you twitter username)::

    TWITTER_LIST = 'brutasse/europython2010'

Running ``manage.py lister`` will add everyone to the list. Run it every once
a while, Twitter has a rate-limit (and a max. of 500 ppl on a list). Note that
only people who send an 'original' tweet (not a retweet) will appear on the
list.

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
    #tweets .tweet p { margin: 0; padding: 0; float: left; width: 500px; }
    #tweets .clear {
      clear: both;             border-bottom: 1px solid #ccc;
      margin-bottom: 10px;     padding-bottom: 10px;
      font-size: 0.8em;        color: #aaa;
      text-align: right;       text-shadow: 0 1px 0 #fff;
    }
    #tweets .rt { color: #d01f3c; font-weight: bold; padding-right: 15px; }
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
implements WebSockets for older browsers. To enable it, simply use
contrib.staticfiles (or django-staticfiles with django 1.2). Add it to your
``INSTALLED_APPS``, configure ``STATIC_ROOT`` and ``STATIC_URL`` and run
``manage.py collectstatic``.

Then add to your ``<head>`` block (assuming you've loaded
``twitsocket_tags``)::

    <head>
        <title> ... whatever you have </title>
        ...
        {% flash_hack %}
    </head>

Note that because of some cross-domain security concerns, the flash hack will
only if the media files are served on the same domain name as the website
itself. No media.example.com for serving static files.

TODO
----

* i18n for websocket error messages.

* Try to decouple the Twitter consumer and the WebSocket server. Maybe with
  Redis and its Pub/Sub mechanism.
