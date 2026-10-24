"""Attempt-scoped HTTPS deadlines for credential-bearing DeepSeek requests.

DNS may block past the deadline; the caller's external hard timeout still applies.
No socket is created after DNS returns with an exhausted budget.
"""
import functools
import http.client
import io
import socket
import time
import urllib.error
import urllib.parse
import urllib.request


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('deepseek_attempt_deadline_exceeded')
    return remaining


class _DeadlineRaw(io.RawIOBase):
    """Keep SocketIO's makefile reference and refresh every native read."""

    def __init__(self, raw, sock, deadline):
        super().__init__()
        self._raw = raw
        self._sock = sock
        self._deadline = deadline

    def readable(self):
        return True

    def readinto(self, buffer):
        self._sock.settimeout(_remaining(self._deadline))
        count = self._raw.readinto(buffer)
        _remaining(self._deadline)
        return count

    def close(self):
        try:
            self._raw.close()
        finally:
            super().close()


class _DeadlineSocket:
    def __init__(self, sock, deadline):
        self._sock = sock
        self._deadline = deadline

    def __getattr__(self, name):
        return getattr(self._sock, name)

    def sendall(self, data, flags=0):
        _remaining(self._deadline)
        # SSLSocket.sendall can perform several writes. Refresh each one.
        with memoryview(data).cast('B') as view:
            sent = 0
            while sent < len(view):
                self._sock.settimeout(_remaining(self._deadline))
                count = self._sock.send(view[sent:], flags)
                _remaining(self._deadline)
                if not count:
                    raise ConnectionError('deepseek_socket_closed_during_write')
                sent += count

    def makefile(self, mode='rb', buffering=None):
        raw = self._sock.makefile(mode, buffering=0)
        guarded = _DeadlineRaw(raw, self._sock, self._deadline)
        if buffering == 0:
            return guarded
        return io.BufferedReader(guarded, buffering or io.DEFAULT_BUFFER_SIZE)


class DeadlineResponse(http.client.HTTPResponse):
    """Use the stock header/chunk parser with deadline-aware SocketIO reads."""

    def __init__(self, sock, *args, deadline, **kwargs):
        self._deadline = deadline
        if isinstance(sock, _DeadlineSocket):
            sock = sock._sock
        super().__init__(_DeadlineSocket(sock, deadline), *args, **kwargs)

    def begin(self):
        _remaining(self._deadline)
        super().begin()
        _remaining(self._deadline)

    def read(self, *args, **kwargs):
        _remaining(self._deadline)
        data = super().read(*args, **kwargs)
        _remaining(self._deadline)
        return data

    def read1(self, *args, **kwargs):
        _remaining(self._deadline)
        data = super().read1(*args, **kwargs)
        _remaining(self._deadline)
        return data

    def readinto(self, buffer):
        _remaining(self._deadline)
        count = super().readinto(buffer)
        _remaining(self._deadline)
        return count

    def readline(self, *args, **kwargs):
        _remaining(self._deadline)
        data = super().readline(*args, **kwargs)
        _remaining(self._deadline)
        return data


def _connect(address, timeout, source_address, *, deadline):
    host, port = address
    # Unlike socket.create_connection, each address gets the remaining budget.
    _remaining(deadline)
    addresses = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    _remaining(deadline)
    last_error = None
    for family, socktype, proto, _, sockaddr in addresses:
        _remaining(deadline)
        sock = None
        try:
            sock = socket.socket(family, socktype, proto)
            sock.settimeout(_remaining(deadline))
            if source_address:
                sock.bind(source_address)
            sock.settimeout(_remaining(deadline))
            sock.connect(sockaddr)
            _remaining(deadline)
            return _DeadlineSocket(sock, deadline)
        except OSError as error:
            last_error = error
            if sock is not None:
                sock.close()
        except BaseException:
            if sock is not None:
                sock.close()
            raise
    if last_error is not None:
        raise last_error
    raise OSError('getaddrinfo returns an empty list')


class _DeadlineHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, *, deadline, **kwargs):
        super().__init__(host, **kwargs)
        self._deadline = deadline
        self._create_connection = functools.partial(_connect, deadline=deadline)
        self.response_class = functools.partial(DeadlineResponse, deadline=deadline)

    def connect(self):
        # The socket facade also guards stock CONNECT header parsing and writes.
        http.client.HTTPConnection.connect(self)
        server_hostname = self._tunnel_host or self.host
        raw = self.sock._sock
        raw.settimeout(_remaining(self._deadline))
        self.sock = _DeadlineSocket(
            self._context.wrap_socket(raw, server_hostname=server_hostname),
            self._deadline)
        _remaining(self._deadline)


class _DeadlineHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, deadline):
        super().__init__()
        self._deadline = deadline

    def https_open(self, request):
        connection = functools.partial(_DeadlineHTTPSConnection, deadline=self._deadline)
        return self.do_open(connection, request, context=self._context)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def http_error_302(self, request, fp, code, message, headers):
        fp.close()
        raise urllib.error.HTTPError(request.full_url, code, message, headers, fp)

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


def _validate_destination(request):
    url = request.full_url if isinstance(request, urllib.request.Request) else request
    if not isinstance(url, str) or any(ord(c) <= 32 or ord(c) == 127 for c in url):
        raise ValueError('deepseek_invalid_destination')
    parts = urllib.parse.urlsplit(url)
    if (parts.scheme != 'https'
            or parts.netloc.lower() not in ('api.deepseek.com', 'api.deepseek.com:443')
            or parts.path not in ('/chat/completions', '/v1/chat/completions',
                                  '/anthropic/v1/messages')
            or '?' in url or '#' in url):
        raise ValueError('deepseek_invalid_destination')


class _DeepseekOpener:
    def __init__(self, timeout):
        self._deadline = time.monotonic() + timeout
        self._opener = urllib.request.build_opener(
            _DeadlineHTTPSHandler(self._deadline), _NoRedirect())

    def open(self, request, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        # Validate before dispatch, including before proxy or protocol handlers.
        _validate_destination(request)
        remaining = _remaining(self._deadline)
        return self._opener.open(request, data=data, timeout=remaining)


def deepseek_opener(timeout):
    return _DeepseekOpener(timeout)
