from odoo.addons.base_rest.components.service import to_int
from odoo.addons.component.core import Component

from odoo.addons.base_rest import restapi

class CommCareService(Component):
    _inherit = "base.rest.service"
    _name = "spp.commcare.form.service"
    _usage = "form"
    _collection = "base.rest.commcare.services"
    _description = """
    CommCare Services
    Access to the commcare services is restricted to authenticated partners.
    """

    # # Validator for POST request, you can define the required and optional fields
    # def _validator_create(self):
    #     return {
    #         "app_id": {"type": "string", "required": True, "nullable": False},
    #         # ... (other fields)
    #     }

    @restapi.method(
        [(["/"], "POST")],
        auth="public",
    )
    def create(self, **params):
        CommCareForm = self.env['spp.commcare.form']
        try:
            new_form = CommCareForm.create_form_from_json(params)
        except Exception as e:
            return {'error': str(e)}
        if new_form:
            return {'success': True, 'form_id': new_form.id}
        else:
            return {'error': 'Form could not be created'}

#
#
# class PingService(Component):
#     _inherit = "base.rest.service"
#     _name = "commcare.form.service"
#     _usage = "ping"
#     _collection = "commcare.services"
#     _description = """
#         Commcare Services
#         Access to the ping form services is allowed to everyone
#     """
#
#     # The following method are 'public' and can be called from the controller.
#     def get(self, _id, message):
#         """
#         This method is used to get the information of the object specified
#         by Id.
#         """
#         return {"message": message, "id": _id}
#
#     def search(self, **params):
#         """
#         A search method to illustrate how you can define a complex request.
#         In the case of the methods 'get' and 'search' the parameters are
#         passed to the server as the query part of the service URL.
#         """
#         return {"response": "Search called search with params %s" % params}
#
#     def update(self, _id, message):
#         """
#         Update method description ...
#         """
#         return {"response": "PUT called with message " + message}
#
#     # pylint:disable=method-required-super
#     def create(self, **params):
#         """
#         Create method description ...
#         """
#         return {"response": "POST called with message " + params["message"]}
#
#     def delete(self, _id):
#         """
#         Delete method description ...
#         """
#         return {"response": "DELETE called with id %s " % _id}
#
#     # Validator
#     def _validator_search(self):
#         return {
#             "param_string": {"type": "string"},
#             "param_required": {"type": "string", "required": True},
#             "limit": {"type": "integer", "default": 50, "coerce": to_int},
#             "offset": {"type": "integer", "default": 0, "coerce": to_int},
#             "params": {"type": "list", "schema": {"type": "string"}},
#         }
#
#     def _validator_return_search(self):
#         return {"response": {"type": "string"}}
#
#     # Validator
#     def _validator_get(self):
#         return {"message": {"type": "string"}}
#
#     def _validator_return_get(self):
#         return {"message": {"type": "string"}, "id": {"type": "integer"}}
#
#     def _validator_update(self):
#         return {"message": {"type": "string"}}
#
#     def _validator_return_update(self):
#         return {"response": {"type": "string"}}
#
#     def _validator_create(self):
#         return {"message": {"type": "string"}}
#
#     def _validator_return_create(self):
#         return {"response": {"type": "string"}}
#
#     def _validator_return_delete(self):
#         return {"response": {"type": "string"}}
