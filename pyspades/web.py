from twisted.internet import reactor
from twisted.web import client
from twisted.web.client import HTTPClientFactory, URI


def getPage(url, bindAddress=None, *arg, **kw):
    # reimplemented here to insert bindAddress

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
        reactor.connectSSL(host, port, factory, context,
                           bindAddress=bindAddress)
    else:
        reactor.connectTCP(host, port, factory, bindAddress=bindAddress)
    return factory.deferred
