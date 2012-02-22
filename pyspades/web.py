from twisted.internet import reactor
from twisted.web.client import HTTPClientFactory, _parse

def getPage(url, bindAddress = None, *arg, **kw):
    # reimplemented here to insert bindAddress
    scheme, host, port, path = _parse(url)
    factory = HTTPClientFactory(url, *arg, **kw)
    if scheme == 'https':
        from twisted.internet import ssl
        context = ssl.ClientContextFactory()
        reactor.connectSSL(host, port, factory, context, 
            bindAddress = bindAddress)
    else:
        reactor.connectTCP(host, port, factory, bindAddress = bindAddress)
    return factory.deferred