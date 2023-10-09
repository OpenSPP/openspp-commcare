# from odoo import http
# import json
from odoo.addons.base_rest.controllers import main

print('Hello world! CommCareController')

# class CommCareController(http.Controller):
#
#     @http.route('/commcare/form/', auth='public', methods=['POST'], csrf=False)
#     def create_form(self, **kwargs):
#         print('Hello world! CommCareController create_form')
#         CommCareForm = http.request.env['spp.commcare.form']
#         form_data = json.loads(http.request.jsonrequest)
#
#         if not form_data:
#             return {'error': 'No valid data received'}
#
#         new_form = CommCareForm.create_form_from_json(form_data)
#
#         if new_form:
#             return {'success': True, 'form_id': new_form.id}
#         else:
#             return {'error': 'Form could not be created'}


class CommcareFormController(main.RestController):
    _root_path = '/commcare/'
    _collection_name = 'base.rest.commcare.services'
    _default_auth = 'public'

    def _process_method(
        self, service_name, method_name, *args, collection=None, params=None
    ):
        print('Hello world! CommCareController _process_method')
        super(CommcareFormController, self)._process_method(
            service_name, method_name, *args, collection=None, params=None
        )

