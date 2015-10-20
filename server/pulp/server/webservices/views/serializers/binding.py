"""
Module for binding serialization.
"""

import link

from pulp.server.exceptions import MissingResource
from pulp.server.controllers import distributor as dist_controller
from pulp.server.db import model
from pulp.server.webservices import http


def serialize(bind, include_details=True):
    """
    Construct a REST object to be returned.
    Add _href and augments information used by the caller
    to consume published content.
    @param bind: A bind model/SON object.
    @type bind: dict/SON
    @return: A bind REST object.
        {consumer_id:<str>,
         repo_id:<str>,
         distributor_id:<str>,
         href:<str>,
         type_id:<str>,
         details:<dict>}
    @rtype: dict
    """
    # bind
    serialized = dict(bind)

    consumer_id = bind['consumer_id']
    repo_id = bind['repo_id']
    distributor_id = bind['distributor_id']

    # href
    # 1019155 - Make sure the binding URL points to:
    # /pulp/api/v2/consumers/<consumer_id>/bindings/<repo_id>/<distributor_id/
    href_url = '%s/consumers/%s/bindings/%s/%s/' % (
        http.API_V2_HREF, consumer_id, repo_id, distributor_id)
    href = link.link_obj(href_url)
    serialized.update(href)

    try:
        dist = model.Distributor.objects.get_or_404(repo_id=repo_id, distributor_id=distributor_id)
    except MissingResource:
        if include_details:
            raise

    else:
        serialized['type_id'] = dist.distributor_type_id

    if include_details:
        details = dist_controller.create_bind_payload(repo_id, distributor_id,
                                                      bind['binding_config'])
        serialized['details'] = details

    return serialized
