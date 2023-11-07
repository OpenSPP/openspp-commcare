import json
from datetime import datetime

from odoo import models, fields, api

"""
"#type": "data",
      "@name": "Add Member",
      "@uiVersion": "1",
      "@version": "44",
      "@xmlns": "http://openrosa.org/formdesigner/323346D9-79F7-4BFC-8CF3-E21309E64404",
"""

RESERVED_PROPERTY_NAME = [
    "subcase_0",
    "meta",
    "case",
    "@xmlns",
    "@version",
    "@uiVersion",
    "@name",
    "#type",
    "spp_form_type",
]

class CommCareForm(models.Model):
    _name = 'spp.commcare.form'
    _description = 'CommCare Forms'

    # Basic Info
    app_id = fields.Char(string='App ID', required=True, index=True)
    build_id = fields.Char(string='Build ID')
    form_id = fields.Char(string='Form ID')
    domain = fields.Char(string='Domain', required=True)
    archived = fields.Boolean(string='Archived', default=False)
    form_name = fields.Char(string='Form Name')
    form_type = fields.Char(string='Form Type')

    # Date Fields
    edited_on = fields.Datetime(string='Edited On')
    received_on = fields.Datetime(string='Received On')
    server_modified_on = fields.Datetime(string='Server Modified On')

    # Relationships
    case_id = fields.Many2one('spp.commcare.case', string='Case')

    # Store dynamic properties
    properties = fields.Text(string='Properties')
    metadata_id = fields.Many2one('spp.commcare.form.metadata', string='Metadata')

    @api.model
    def create_partner_from_form(self):
        # Fetch all field names from the res.partner model
        partner_fields = self.env['res.partner']._fields.keys()
        print("create_partner_from_form")
        # Loop over the recordset
        for form in self:
            partner_data = {}

            # Determine if we're dealing with a group or individual
            is_group = False
            print(form.form_name)
            if form.form_name == 'Register New Group':
                is_group = True
            elif form.form_name != 'Register New Member':
                continue  # Skip to the next iteration if form_name doesn't match

            # Set the is_group flag
            partner_data['is_group'] = is_group
            partner_data['is_registrant'] = True

            # Extract properties from stored JSON
            properties_json = form.properties
            properties = json.loads(properties_json)

            # Compare JSON keys with res.partner fields and map
            for key, value in properties.items():
                if key in RESERVED_PROPERTY_NAME:
                    continue
                #TODO: Fix dirty hardcod fix
                if key == 'first_name':
                    key = "given_name"
                elif key == 'last_name':
                    key = "family_name"
                elif key == 'gender' and value is not None:
                    value = value[0].upper() + value[1:].lower()

                if key in partner_fields:
                    partner_data[key] = value

            print(partner_data)
            # TODO: FIX! find why it is not recomputed
            if not is_group:
                partner_data['name'] = "plop"
            # Create new res.partner record with mapped fields
            if partner_data:  # Only create if there's data to insert
                partner = self.env['res.partner'].create(partner_data)
                self._associate_case_with_partner(form, partner)
                if not is_group:
                    self._associate_individual_with_group(form, partner)
            else:
                print('No partner data found')

    @api.model
    def create_event_data_from_form(self):
        print("create_event_data_from_form")
        # Loop over the recordset
        for form in self:
            # Extract properties from stored JSON
            properties_json = form.properties
            properties = json.loads(properties_json)
            if not 'spp_form_type' in properties or not properties['spp_form_type'].startswith("spp.event."):
                # Not an event_data form type
                continue
            form_type = properties['spp_form_type']
            form_fields = self.env[form_type]._fields.keys()

            related_case = self._get_related_case(properties)
            if not (related_case.id and related_case.partner_id):
                print("no related case or partner for form: %s" % form.id)
                continue

            form_data = {}

            for key, value in properties.items():
                if key in RESERVED_PROPERTY_NAME:
                    continue
                if key in form_fields:
                    form_data[key] = value
                else:
                    print("Missing field: %s" % key)

            form_id = self.env[form_type].create(form_data)
            vals_event_data = {
                "partner_id": related_case.partner_id.id,
                "model": form_type,
                "res_id": form_id.id,
            }
            event_data = self.env["spp.event.data"].create(vals_event_data)

    def _get_related_case(self, properties, parent_case=False):
        if 'subcase_0' in properties.keys() and not parent_case:
            # This is used for individuals
            case_data = properties['subcase_0']["case"]
        else:
            # This is for groups
            case_data = properties["case"]
        case_id = case_data['@case_id']
        existing_case = self.env['spp.commcare.case'].search([('case_id', '=', case_id)],
                                                             order='create_date desc', limit=1)
        return existing_case

    def _associate_individual_with_group(self, form, individual):
        # TODO: Check of the group membership app is installed
        print("_associate_individual_with_group")
        properties = json.loads(form.properties)
        print(properties)

        group_case = self._get_related_case(properties, parent_case=True)
        print(f"group_case: {group_case} ({group_case and group_case.partner_id})")
        if group_case and group_case.partner_id:
            print("create g2p.group.membership")
            self.env["g2p.group.membership"].create({
                'group': group_case.partner_id.id,
                'individual': individual.id
            })

    def _associate_case_with_partner(self, form, partner):
        domain = form.domain
        properties = json.loads(form.properties)

        if 'subcase_0' in properties.keys():
            # This is used for individuals
            case_data = properties['subcase_0']["case"]
        else:
            # This is for groups
            case_data = properties["case"]
        case_id = case_data['@case_id']
        existing_case = self.env['spp.commcare.case'].search([('case_id', '=', case_id)],
                                                             order='create_date desc', limit=1)
        print(existing_case)
        if not existing_case:
            case_data = {
                'case_id': case_id,
                'domain': domain,
                'user_id': case_data["@user_id"],
                'is_partial': True,
                'partner_id': partner.id
                # Add any other default or inferred fields for parent case here
            }
            case = self.env['spp.commcare.case'].create(case_data)
        else:
            # TODO fix this: we should not have new partner created for the same case, we just do it for testing
            # print("PartnerId %s" % existing_case.partner_id)
            # if not existing_case.partner_id.id:
            #     existing_case.write({
            #         "partner_id": partner.id
            #     })
            # elif existing_case.partner_id.id != partner.id:
            #     raise Exception(f"Unexpected existing_case.partner_id({existing_case.partner_id.id}) != partner.id ({partner.id})")
            existing_case.write({
                "partner_id": partner.id
            })

    def _convert_commcare_date(self, date_str):
        if not date_str:
            return None
        # Convert to datetime object
        dt_object = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')

        # Convert back to string with the desired format
        formatted_str = dt_object.strftime('%Y-%m-%d %H:%M:%S')
        return formatted_str

    @api.model
    def create_form_from_json(self, form_json):
        primary_case = form_json.get('form', {}).get('case', {})
        primary_case_id = primary_case.get('@case_id', None)
        if primary_case_id:
            case = self.env['spp.commcare.case'].search([('case_id', '=', primary_case_id)],
                                                    order='create_date desc',
                                                    limit=1)
            if case:
                case = case.id
            else:
                case = None
        else:
            case = None

        # TODO: Decide if we store multiple instance of the same form ID. It might be a good idea for audit purpose.
        form = []
        # form = self.env['spp.commcare.form'].search([('form_id', '=', form_json.get('id'))])

        form_data = {}
        if len(form) == 0:
            form = None
            form_data = {
                'app_id': form_json.get('app_id'),
                'build_id': form_json.get('build_id'),
                'form_id': form_json.get('id'),
                'domain': form_json.get('domain'),
                'form_name': form_json['form'].get('@name'),
                'form_type': form_json['form'].get('#type'),
            }

        form_data.update({
            'archived': form_json.get('archived', False),
            'edited_on': self._convert_commcare_date(form_json.get('edited_on')),
            'received_on': self._convert_commcare_date(form_json.get('received_on')),
            'server_modified_on': self._convert_commcare_date(form_json.get('server_modified_on')),
            'properties': json.dumps(form_json.get('form', {})),
            'case_id': case
        })
        print(form_data)

        # TODO: Check if metadata already exists and update if so
        if form is None:
            # Create metadata
            metadata_data = form_json.get('metadata', {})
            # temp
            del metadata_data['location']
            print(metadata_data)
            metadata_data['timeEnd'] = self._convert_commcare_date(metadata_data['timeEnd'])
            metadata_data['timeStart'] = self._convert_commcare_date(metadata_data['timeStart'])
            metadata = self.env['spp.commcare.form.metadata'].create(metadata_data)

            # Associate metadata with form
            form_data['metadata_id'] = metadata.id

        if form:
            form.write(form_data)
            return form
        else:
            form = self.env['spp.commcare.form'].create(form_data)
        # form.create_partner_from_form()

        spp_form_type = form_json.get('form', {}).get('spp_form_type', None)
        if spp_form_type:
            form.create_event_data_from_form()
        else:
            form.create_partner_from_form()
        return form


class CommCareFormMetadata(models.Model):
    _name = 'spp.commcare.form.metadata'
    _description = 'CommCare Form Metadata'

    # Metadata Fields
    appVersion = fields.Char(string='App Version')
    app_build_version = fields.Char(string='App Build Version')
    commcare_version = fields.Char(string='CommCare Version')
    deviceID = fields.Char(string='Device ID')
    drift = fields.Integer(string='Drift')
    geo_point = fields.Char(string='Geo Point')
    instanceID = fields.Char(string='Instance ID')
    timeEnd = fields.Datetime(string='Time End')
    timeStart = fields.Datetime(string='Time Start')
    userID = fields.Char(string='User ID')
    username = fields.Char(string='Username')
