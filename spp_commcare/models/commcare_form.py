import json
from odoo import models, fields, api


class CommCareForm(models.Model):
    _name = 'spp.commcare.form'
    _description = 'CommCare Forms'

    # Basic Info
    app_id = fields.Char(string='App ID', required=True, index=True)
    build_id = fields.Char(string='Build ID')
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

        # Loop over the recordset
        for form in self:
            partner_data = {}

            # Determine if we're dealing with a group or individual
            is_group = False
            if form.form_name == 'Register New Group':
                is_group = True
            elif form.form_name != 'Register New Member':
                continue  # Skip to the next iteration if form_name doesn't match

            # Set the is_group flag
            partner_data['is_group'] = is_group

            # Extract properties from stored JSON
            properties_json = form.properties
            properties = json.loads(properties_json)

            # Compare JSON keys with res.partner fields and map
            for key, value in properties.items():
                if key in partner_fields:
                    partner_data[key] = value

            # Create new res.partner record with mapped fields
            if partner_data:  # Only create if there's data to insert
                self.env['res.partner'].create(partner_data)

    @api.model
    def create_form_from_json(self, form_json):
        primary_case = form_json.get('form', {}).get('case', {})
        primary_case_id = primary_case.get('@case_id', None)
        if primary_case_id:
            case = self.env['spp.commcare.case'].search([('case_id', '=', primary_case_id)],
                                                    order='create_date desc',
                                                    limit=1)
        else:
            case = None

        form_data = {
            'app_id': form_json.get('app_id'),
            'build_id': form_json.get('build_id'),
            'domain': form_json.get('domain'),
            'archived': form_json.get('archived', False),
            'form_name': form_json['form'].get('@name'),
            'form_type': form_json['form'].get('#type'),
            'edited_on': form_json.get('edited_on'),
            'received_on': form_json.get('received_on'),
            'server_modified_on': form_json.get('server_modified_on'),
            'properties': json.dumps(form_json.get('form', {})),
            'case_id': case
        }

        # Create metadata
        metadata_data = form_json.get('metadata', {})
        metadata = self.env['spp.commcare.form.metadata'].create(metadata_data)

        # Associate metadata with form
        form_data['metadata_id'] = metadata.id

        # Create the form and return
        new_form = self.env['spp.commcare.form'].create(form_data)
        return new_form


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
