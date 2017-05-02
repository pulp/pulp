class Cataloger(object):
    """
    The base cataloger to index content sources.

    This is meant to be subclassed by plugin authors to given the plugin control where content is
    fetched from. For a given url the plugin should return a
    :class: `~nectar.downloaders.base.Downloader` object. Using this interface, content that is
    stored locally or in multiple locations can be fetched more efficiently.

    The platform will use one :class: `~pulp.plugin.Cataloger` instance per content source so this
    object only needs to be concerned with indexing a single source provided in the config.

    :ivar config: The content source configuration
    :type config: dict
    """

    def __init__(self, config):
        """
        Initialize the Cataloger with a config.

        :param config: The content source configuration.
        :type config: dict
        """
        self.config = config

    def get_downloader(self, url):
        """
        Get a :class: `~nectar.downloaders.base.Downloader` suitable for downloading content at url

        This allows the plugin author to control where content is fetched from.

        :param url: The URL for the content source.
        :type url: str

        :return: A configured downloader.
        :rtype: :class: `nectar.downloaders.base.Downloader`
        """
        raise NotImplementedError()

    def refresh(self):
        """
        Refresh the content catalog.

        This should cause the plugin to refresh the content catalog to look for new content and/or
        verify the existence of known content. The extent of the feature set provided with refresh
        by the plugin is up to the plugin author.
        """
        raise NotImplementedError()
