from pulp.bindings.base import PulpAPI


class UploadAPI(PulpAPI):
    """
    Facade into calls related to content upload and importing into repositories.
    """

    def __init__(self, pulp_connection):
        super(UploadAPI, self).__init__(pulp_connection)

    def initialize_upload(self):
        url = '/v2/content/uploads/'
        return self.server.POST(url)

    def upload_segment(self, upload_id, offset, data):
        url = '/v2/content/uploads/%s/%s/' % (upload_id, offset)
        return self.server.PUT(url, data, ensure_encoding=False)

    def list_all_uploads(self):
        url = '/v2/content/uploads/'
        return self.server.GET(url)

    def delete_upload(self, upload_id):
        url = '/v2/content/uploads/%s/' % upload_id
        return self.server.DELETE(url)

    def import_upload(self, upload_id, repo_id, unit_type_id, unit_key, unit_metadata,
                      override_config=None):
        url = '/v2/repositories/%s/actions/import_upload/' % repo_id
        body = {
            'upload_id': upload_id,
            'unit_type_id': unit_type_id,
            'unit_key': unit_key,
            'unit_metadata': unit_metadata,
            'override_config': override_config,
        }
        return self.server.POST(url, body)
