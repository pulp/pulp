"""
This module contains set of download APIs.
"""
import os
import hashlib

import requests
from requests_futures.sessions import FuturesSession
from requests.packages.urllib3.util import retry

# TODO make config settings
DEFAULT_CONNECT_TIMEOUT = 6.1
DEFAULT_READ_TIMEOUT = 30
DEFAULT_TRIES = 5
DEFAULT_CONCURRENCY = 5
# TODO Picked a bit out of a hat - I expect it should try to line up with the FS.
DEFAULT_CHUNKSIZE = 1024 * 1024


def default_callback_generator(filename=None, size=None, checksums=None):
    """
    Creates a closure to write a response to disk, checksum it, and verify
    its size.

    :param filename: The absolute path the response should be saved to.
    :param size: The size, in bytes, that the file is expected to be; check is
                 skipped if this value is not provided.
    :param checksums: A dictionary of checksums to validate the file with; the
                      key should be the hash algorithm and the value the
                      expected hex digest.
    """
    # TODO potentially add a way to have this generate the entire checksum set.
    # Maybe if there's {'algorithm': None}?
    checksums = checksums or {}

    def callback(self, response):
        """
        A callback for the requests_futures library.

        :param resp: The requests response object
        """
        hashes = {algorithm: hashlib.new(algorithm) for algorithm in checksums}
        with open(filename, mode='wb') as fp:
            chunks = response.iter_content(chunk_size=DEFAULT_CHUNKSIZE)
            for chunk in chunks:
                for hash in hashes.values():
                    hash.update(chunk)
                fp.write(chunk)

        # Validate that what we downloaded is what the user expects
        # TODO add more reasonable exceptions
        if size and size != os.stat(filename).st_size:
            raise ValueError()

        if checksums != {algorithm: hash.hexdigest() for algorithm, hash in hashes.items()}:
            raise ValueError()

    return callback


class FileFuturesSession(FuturesSession):
    """
    This class implements the requests-futures API, with one  small adjustment. It provides
    a default callback that writes a file to disk and validates its content. Once it
    successfully returns, the file is ready to be imported into Pulp.

    requests-futures allows you to queue up a large number of requests which are run
    asynchonously on a pool of worker threads or processes. For examle:

        >>> session = FileFuturesSession(max_workers=10)  # Create a pool of 10 threads
        >>> requests = [
        ...     {url='http://example.com/file1'},
        ...     {url='http://example.com/file2'},
        ... ]
        >>> responses = []
        >>> for request in requests:
        ...     responses.append(session.get(**request))  # session.get does not block
        >>> for reponse in responses:
        ...     request_response, filename = response.result()
        ...     with open(filename) as fd:
        ...         django_file = django.core.files.File(fd)
        ...     artifact = pulp.apps.models.Artifact(file=django_file)
        ...     artifact.save()
        >>>

    Here are a list of things I think would be good to consider including in
    this module and possibly this class:

        * A synchronous API that allows callbacks that work the same way as the asynchronous
          API. This could be a different class, or the same class (with a better name) that
          has `get` and `async_get` or similar.

        * A way to have Artifact and Content models created automatically and returned. In
          most cases the users will want those rather than the files.

        * Make it easy to get the responses without writing it to a file. This class is
          currently called `FileFuturesSessions`, but it doesn't need to be. On the other
          hand, the API might be more pleasant if those features were split across Session
          classes.

        * Integration with the progress reporting API. This could probably be done in the
          callback.

        * Integrate with storage backends (long in the future, I expect).

    Here are things this API should probably _not_ attempt to do:

        * Recreate `tc` (poorly) - That means no attempting to set bandwidth limits. It's
          a feature of the Linux kernel, we will not do it better here.

        * Create its own set of exceptions: the requests API is fantastic, and its exceptions
          are helpful and clear. Don't hide them.


    Some things to simply consider:

        * This API could be run as a download service for Pulp. This would allow global
          concurrency settings, but the downside is increased complexity using the API
          and another service to deal with.
    """

    def __init__(self, executor=None, max_workers=5, session=None, *args,
                 **kwargs):
        super(FileFuturesSession, self).__init__(*args, **kwargs)

    def request(self, method, url, callback_generator=default_callback_generator,
                callback_variables=None, callback=None, **request_kwargs):
        """
        This provides the requests API as well as the requests-futures API.

        The only difference is a few additional keyword arguments are accepted. If `callback`
        is provided, it is used rather than anything created by the `callback_generator` and
        `callback_variables` arguments.
        """

        # filename should default to something useful
        callback_variables = callback_variables or {'filename': None, 'size': None, 'checksums': {}}
        callback = callback or callback_generator(**callback_variables)

        request_kwargs.setdefault('timeout', (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT))
        request_kwargs.setdefault('stream', True)
        request_kwargs.setdefault('verify', True)

        response = super(FileFuturesSession, self).request(
                method, url, background_callback=callback, **request_kwargs)
        return response, callback_variables


def configure_session():
    """
    Helpful function to configure a default requests Session object.
    """
    session = requests.Session()
    retry_conf = retry.Retry(total=DEFAULT_TRIES, connect=DEFAULT_TRIES,
                             read=DEFAULT_TRIES, backoff_factor=1)
    retry_conf.BACKOFF_MAX = 8
    adapter = requests.adapters.HTTPAdapter(
        max_retries=retry_conf,
        pool_connections=DEFAULT_CONCURRENCY,
        pool_maxsize=DEFAULT_CONCURRENCY
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.verify = True

    return session
