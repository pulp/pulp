from logging import getLogger

from pulp.agent.lib.handler import ContentHandler
from pulp.agent.lib.report import ContentReport

from pulp_node import constants
from pulp_node import resources
from pulp_node.error import GetBindingsError
from pulp_node.handlers.model import RepositoryBinding
from pulp_node.handlers.reports import HandlerProgress, SummaryReport
from pulp_node.handlers.strategies import find_strategy, Request


log = getLogger(__name__)


def parent_bindings(options):
    """
    Get the parent API bindings based on handler options.
    :param options: Update options.
    :type options: dict
    :return: A configured parent API bindings.
    :rtype: pulp.bindings.bindings.Bindings
    """
    settings = options[constants.PARENT_SETTINGS]
    host = settings[constants.HOST]
    port = settings[constants.PORT]
    return resources.parent_bindings(host, port)


class NodeHandler(ContentHandler):

    def update(self, conduit, units, options):
        """
        Update the specified content units.  Each unit must be of
        type 'node'.  Updates the entire child node.

        Report format:
          succeeded: <bool>
          details: {
            errors: [
              { error_id: <str>,
                details: {}
              },
            ]
            repositories: [
              { repo_id: <str>,
                action: <str>,
                units: {
                  added: <int>,
                  updated: <int>,
                  removed: <int>
                }
              },
            ]
          }

        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param units: A list of content unit_keys.
        :type units: list
        :param options: Unit update options.
        :type options: dict
        :return: An update report.
        :rtype: ContentReport
        """
        handler_report = ContentReport()
        summary_report = SummaryReport()
        progress_report = HandlerProgress(conduit)
        pulp_bindings = parent_bindings(options)

        try:
            bindings = RepositoryBinding.fetch_all(pulp_bindings, conduit.consumer_id)
        except GetBindingsError, ne:
            log.error(ne)
            summary_report.errors.append(ne)
            handler_report.set_failed(summary_report.dict())
            return handler_report

        strategy_name = options.setdefault(constants.STRATEGY_KEYWORD, constants.MIRROR_STRATEGY)
        request = Request(
            conduit=conduit,
            progress=progress_report,
            summary=summary_report,
            bindings=bindings,
            scope=constants.NODE_SCOPE,
            options=options)
        strategy = find_strategy(strategy_name)()
        strategy.synchronize(request)

        for ne in summary_report.errors:
            log.error(ne)

        if summary_report.succeeded():
            handler_report.set_succeeded(summary_report.dict())
        else:
            handler_report.set_failed(summary_report.dict())
        return handler_report


class RepositoryHandler(ContentHandler):

    def update(self, conduit, units, options):
        """
        Update the specified content units.  Each unit must be
        of type 'repository'.  Updates only the repositories specified in
        the unit_key by repo_id.

        Report format:
          succeeded: <bool>
          details: {
            errors: [
              { error_id: <str>,
                details: {}
              },
            ]
            repositories: [
              { repo_id: <str>,
                action: <str>,
                units: {
                  added: <int>,
                  updated: <int>,
                  removed: <int>
                }
              },
            ]
          }

        :param conduit: A handler conduit.
        :type conduit: pulp.agent.lib.conduit.Conduit
        :param units: A list of content unit_keys.
        :type units: list
        :param options: Unit update options.
        :type options: dict
        :return: An update report.
        :rtype: ContentReport
        """
        summary_report = SummaryReport()
        progress_report = HandlerProgress(conduit)
        repo_ids = [key['repo_id'] for key in units if key]
        pulp_bindings = parent_bindings(options)
        bindings = RepositoryBinding.fetch(pulp_bindings, conduit.consumer_id, repo_ids)

        strategy_name = options.setdefault(constants.STRATEGY_KEYWORD, constants.MIRROR_STRATEGY)
        request = Request(
            conduit=conduit,
            progress=progress_report,
            summary=summary_report,
            bindings=bindings,
            scope=constants.REPOSITORY_SCOPE,
            options=options)
        strategy = find_strategy(strategy_name)()
        strategy.synchronize(request)

        for ne in summary_report.errors:
            log.error(ne)

        handler_report = ContentReport()
        if summary_report.succeeded():
            handler_report.set_succeeded(summary_report.dict())
        else:
            handler_report.set_failed(summary_report.dict())
        return handler_report
