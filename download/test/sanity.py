from pulp.download import Batch, HttpRequest

# -----------------------------------------------------------------------
#     EXAMPLES
# -----------------------------------------------------------------------

PATH = '/tmp/x'
URL = 'file://{}'.format(__file__)
ATTACHMENT = object()


def test_single():
    print('single')
    request = HttpRequest(URL, PATH)
    request.attachment = ATTACHMENT
    request.ssl_ca_certificate = '/test/ca.pem'
    request.ssl_client_certificate = '/test/client.pem'
    request.ssl_client_key = '/test/key.pem'
    request.headers = {'TEST': 1234}
    result = request()  # execute the request
    print(result)


def test_batched_iterated(n=10):
    print('batch-iterated ({})'.format(n))
    requests = (HttpRequest(URL, PATH) for _ in range(n))
    with Batch(requests) as batch:
        for request in batch.download():
            print(request)
            print('http: {}'.format(request.http_code))
            print('destination: {}'.format(request.destination))
            print('__________________________________________')


def main():
    test_single()
    test_batched_iterated()
    test_batched_iterated(n=0)


if __name__ == '__main__':
    main()
