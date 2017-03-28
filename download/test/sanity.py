
from io import BytesIO
from time import sleep
from logging import basicConfig, INFO, DEBUG
from pulp.download import Batch, Download, HttpDownload, FtpDownload, \
    SizeValidation, DigestValidation, \
    DownloadFailed, Writer

# -----------------------------------------------------------------------
#     EXAMPLES
# -----------------------------------------------------------------------

PATH = '/tmp/x'
URL = 'file://{}'.format(__file__)
ATTACHMENT = object()
DELAY = 0.5


class TestDelegate:

    def on_reply(self, download):
        print('TestDelegate.on_reply()')
        download.on_reply()

    def on_error(self, download):
        print('TestDelegate.on_error()')
        # example repair removes BAD from the end of the url.
        if download.status == 404 and download.url.endswith('BAD'):
            download.url = download.url[:-3]
            return True
        else:
            return False


class MirrorList:

    REPLY = [
        'file:///tmp/mirror0\n',
        'file:///tmp/mirror1\n',
        'file://{}\n'.format(__file__)
    ]

    def __init__(self, url):
        self.url = url

    def fetch(self):
        download = HttpDownload(self.url)
        # download()
        with download.writer:
            for url in MirrorList.REPLY:
                download.writer.append(bytes(url, encoding='utf8'))
        _list = str(download.writer)
        return [url for url in _list.split('\n') if url]


class MirrorDownload(HttpDownload):

    def prepare(self):
        m_list = MirrorList(self.list_url)
        mirrors = m_list.fetch()
        self.retries = len(mirrors)
        self.mirrors = iter(mirrors)
        self._next_mirror()

    def __init__(self, url, path=None):
        super(MirrorDownload, self).__init__(url, path)
        self.mirrors = iter([])
        self.list_url = url

    def _next_mirror(self):
        try:
            self.url = next(self.mirrors)
            print('Try mirror: {}'.format(self.url))
        except StopIteration:
            raise DownloadFailed(self, reason='No more mirrors')

    def on_error(self):
        self._next_mirror()
        return True


class SlowDownload(HttpDownload):

    def __call__(self):
        super(SlowDownload, self).__call__()
        sleep(DELAY)


class BadDownload(HttpDownload):

    def __call__(self):
        sleep(DELAY)
        raise ValueError('Something bad happened')


def test_single():
    print('single')
    download = HttpDownload(URL, PATH)
    download.attachment = ATTACHMENT
    download.ssl_ca_certificate = '/test/ca.pem'
    download.ssl_client_certificate = '/test/client.pem'
    download.ssl_client_key = '/test/key.pem'
    download.headers = {'TEST': 1234}
    try:
        download()  # execute the download
        print(download)
    except DownloadFailed as error:
        print(error)


def test_single_mirror():
    print('single-mirror')
    download = MirrorDownload(URL, PATH)
    download.attachment = ATTACHMENT
    download.ssl_ca_certificate = '/test/ca.pem'
    download.ssl_client_certificate = '/test/client.pem'
    download.ssl_client_key = '/test/key.pem'
    download.headers = {'TEST': 1234}
    try:
        download()  # execute the download
        print(download)
    except DownloadFailed as error:
        print(error)


def test_single_text():
    print('single-text')
    download = HttpDownload(URL)
    download.attachment = ATTACHMENT
    download.ssl_ca_certificate = '/test/ca.pem'
    download.ssl_client_certificate = '/test/client.pem'
    download.ssl_client_key = '/test/key.pem'
    download.headers = {'TEST': 1234}
    try:
        download()  # execute the download
        print(download)
        print(download.writer)
    except DownloadFailed as error:
        print(error)


def test_single_ftp():
    print('single-ftp')
    download = FtpDownload('ftp://speedtest.tele2.net/512KB.zip')
    download.user = 'anonymous'
    download.password = 'anonymous'
    try:
        download()  # execute the download
        print(download)
        print(download.writer)
    except DownloadFailed as error:
        print(error)


def test_single_with_delegate():
    print('single-with-delegate')
    download = HttpDownload(URL + 'BAD', PATH)
    download.attachment = ATTACHMENT
    download.delegate = TestDelegate()
    try:
        download()  # execute the download
        print(download)
    except DownloadFailed as error:
        print(error)


def test_single_exception():
    print('single-with-exception')
    url = 'https://httpbin.org/get?show_env=1'
    download = HttpDownload(url, PATH)
    download.ssl_ca_certificate = '/tmp/xxx'
    download.attachment = ATTACHMENT
    try:
        download()  # execute the download
        print(download)
    except DownloadFailed as error:
        print(error)


def test_single_streamed():
    print('single-streamed')
    download = HttpDownload(URL, '')
    download.writer = Writer(fp=BytesIO())
    download.attachment = ATTACHMENT
    download.ssl_ca_certificate = '/test/ca.pem'
    download.ssl_client_certificate = '/test/client.pem'
    download.ssl_client_key = '/test/key.pem'
    download.headers = {'TEST': 1234}
    try:
        download()  # execute the download
        print(download)
        print(download.writer)
    except DownloadFailed as error:
        print(error)


def test_single_binary():
    print('single-binary')
    download = HttpDownload('file:///usr/bin/ls', PATH)
    validation = [
        SizeValidation(0, enforced=False),
        DigestValidation('sha256', '', enforced=False),
    ]
    download.validation = validation
    try:
        download()  # execute the download
        print(download)
        for v in validation:
            print(v.__dict__)
    except DownloadFailed as error:
        print(error)


def test_batched_iterated(n=100):
    print('batch-iterated ({})'.format(n))
    downloads = (HttpDownload(URL, PATH) for _ in range(n))
    with Batch(downloads) as batch:
        for plan in batch():
            print(plan)
            print('http: {}'.format(plan.download.status))
            print('path: {}'.format(plan.download.path))
            print('__________________________________________')


def test_batched_with_error(n=100):
    print('batch-iterated-with-error ({})'.format(n))
    downloads = [HttpDownload(URL, PATH) for _ in range(n)]
    downloads[0].url = 'file:///BAD'
    with Batch(downloads) as batch:
        for plan in batch():
            if plan.failed:
                print('FAILED')
            print(plan)
            print('http: {}'.format(plan.download.status))
            print('path: {}'.format(plan.download.path))
            print('__________________________________________')


def test_batched_abort(n=100):
    print('batch-iterated-abort ({})'.format(n))
    downloads = (SlowDownload(URL, PATH) for _ in range(n))
    with Batch(downloads) as batch:
        total = 0
        iterator = batch()
        for plan in iterator:
            print(plan)
            print('http: {}'.format(plan.download.status))
            print('path: {}'.format(plan.download.path))
            total += 1
            print('{} __________________________________________'.format(total))
            if total % 5 == 0:
                batch.shutdown()
                print('aborting ...')
    print('Test End')


def test_batched_exception(n=10):
    try:
        print('batch-iterated-exception ({})'.format(n))
        downloads = (HttpDownload(URL, PATH) for _ in range(n))
        with Batch(downloads) as batch:
            total = 0
            for plan in batch():
                print(plan)
                print('http: {}'.format(plan.download.status))
                print('path: {}'.format(plan.download.path))
                total += 1
                print('{} __________________________________________'.format(total))
                raise ValueError('something bad happened')
        print('Test End')
    except ValueError as e:
        print('Caught: {}'.format(e))
        import gc
        gc.collect()


def main():
    basicConfig(level=INFO)
    test_single()
    test_single_mirror()
    test_single_text()
    test_single_exception()
    test_single_with_delegate()
    test_single_streamed()
    test_single_binary()
    test_single_ftp()
    test_batched_iterated()
    test_batched_iterated(n=0)
    test_batched_with_error(n=10)
    test_batched_abort()
    test_batched_exception()
    print('Done')


if __name__ == '__main__':
    main()
