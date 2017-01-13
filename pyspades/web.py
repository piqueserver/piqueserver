from __future__ import absolute_import, division, print_function

import six

from twisted.internet import reactor
from twisted.web import client
from twisted.web.client import HTTPClientFactory

def getPage(url, bindAddress = None, *arg, **kw):
    # with python3, we need to convert the url to bytes
    if six.PY3 and isinstance(url, str):
        url = url.encode()

    # reimplemented here to insert bindAddress


    # _parse() deprecated in twisted 13.1.0 in favor of the _URI class
    if hasattr(client, '_parse'):
        scheme, host, port, path = client._parse(url)
    else:
        # _URI class renamed to URI in 15.0.0
        try:
            from twisted.web.client import _URI as URI
        except ImportError:
            from twisted.web.client import URI

        uri = URI.fromBytes(url)
        scheme = uri.scheme
        host = uri.host
        port = uri.port
        path = uri.path

    factory = HTTPClientFactory(url, *arg, **kw)
    factory.noisy = False

    if scheme == 'https':
        from twisted.internet import ssl
        context = ssl.ClientContextFactory()
        reactor.connectSSL(host.decode(), port, factory, context,
            bindAddress = bindAddress)
    else:
        reactor.connectTCP(host.decode(), port, factory, bindAddress = bindAddress)
    return factory.deferred
