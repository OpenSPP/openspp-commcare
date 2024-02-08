import json
import logging

from odoo import http

_logger = logging.getLogger(__name__)

_logger.info("Hello world! CommCareController")


class CommCareController(http.Controller):

    # @http.route('/commcare/form/', methods=['GET'], type='http', auth='api_key')
    @http.route("/commcare/form/", methods=["GET"], type="http", auth="api_key")
    def get_sample(self, **kwargs):
        return json.dumps({"success": True})

    @http.route(
        "/commcare/form/", auth="api_key", methods=["POST"], csrf=False, type="json"
    )
    def create_form(self, **kwargs):
        _logger.info("Hello world! CommCareController create_form")
        CommCareForm = http.request.env["spp.commcare.form"]
        form_data = http.request.jsonrequest

        if not form_data:
            return {"error": "No valid data received"}

        new_form = CommCareForm.create_form_from_json(form_data)

        if new_form:
            return {"success": True, "form_id": new_form.id}
        else:
            return {"error": "Form could not be created"}
