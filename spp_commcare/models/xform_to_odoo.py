from odoo import api, models, fields, exceptions
import xml.etree.ElementTree as ET


class XFormToOdoo(models.TransientModel):
    _name = 'xform.to.odoo'

    name = fields.Text()

    def create_odoo_model(self, xform):
        try:
            # Parse the XForm XML
            root = ET.fromstring(xform)

            for elem in root.iter():
                elem.tag = elem.tag.split('}')[-1]

            # Find the 'instance' tag
            instance = root.find(".//instance")
            # Find the 'bind' elements
            binds = root.findall(".//bind")
            data = instance.find('.//data')
            repeat_templates = self.find_repeat_templates(data)

            # Create the main model
            model_name = data.get('name').replace(" ", "_").lower()
            model_db_name = 'x_' + model_name

            # Check if a model with this name already exists
            existing_model = self.env['ir.model'].search([
                ('model', '=', model_db_name),
            ])

            if existing_model:
                counter = 1
                while existing_model:
                    new_model_name = f"{model_db_name}_{counter}"
                    existing_model = self.env['ir.model'].search([
                        ('model', '=', new_model_name),
                    ])
                    counter += 1
                model_db_name = new_model_name

            model_id = self.env['ir.model'].create({
                'name': data.get('name'),
                'model': model_db_name,
            })
            self.create_access_rights(model_id)

            # Create fields for the main model
            for elem in binds:
                self.create_field(model_id, elem)

            # # Handle one-to-many relationships
            # for repeat_elem in data.findall('.//repeat'):
            #     child_model_id = self.handle_one_to_many(model_id, repeat_elem)
            #     self.create_access_rights(child_model_id)

            # Handle one-to-many relationships (repeat templates)
            for repeat_elem in repeat_templates:
                self.handle_one_to_many(model_id, repeat_elem, binds)

        except Exception as e:
            # Catch exceptions and rollback transactions
            self.env.cr.rollback()
            raise exceptions.ValidationError(f"An error occurred: {str(e)}")

    def find_repeat_templates(self, root):
        # Find all repeat elements that have a template attribute (i.e. are one-to-many relationships)
        # TODO: not sure this is the proper way...
        return [elem for elem in root.iter() if elem.get('jr:template') is not None]

    def create_field(self, model_id, elem):
        # field_type = self.map_xform_to_odoo_type(elem.get('type'))
        # Create unique field name
        field_display_name = {elem.get("nodeset").split("/")[-1]}
        field_name = f'x_{field_display_name}'
        field_type = self.map_xform_to_odoo_type(elem.get('type'))

        if not field_type:
            print(f"Field type not found for {field_display_name}")
            return

        # Check if a field with this name already exists for the model
        existing_field = self.env['ir.model.fields'].search([
            ('name', '=', field_name),
            ('model_id', '=', model_id.id),
        ])

        # If field already exists, update or skip depending on requirement
        if existing_field:
            # Uncomment the next line to update the existing field
            # existing_field.write({'ttype': field_type, 'field_description': elem.tag})
            return

        print(f"Creating field {field_name} for model {model_id.name}")
        # Create new field
        self.env['ir.model.fields'].create({
            'name': field_name,
            'ttype': field_type,
            'model_id': model_id.id,
            'field_description': field_display_name,
        })

    def map_xform_to_odoo_type(self, xform_type):
        mapping = {
            'xsd:int': 'integer',
            'xsd:double': 'float',
            'xsd:date': 'date',
            'xsd:string': 'char',
            'binary': 'binary',
        }
        return mapping.get(xform_type)

    # TODO Fix one to many
    def handle_one_to_many(self, parent_model_id, repeat_elem):
        # Create a child model for the one-to-many relationship
        child_model_name = repeat_elem.tag.replace(" ", "_").lower()
        child_model_id = self.env['ir.model'].create({
            'name': repeat_elem.tag,
            'model': f'x_{child_model_name}',
        })

        # Create fields for the child model
        for elem in repeat_elem:
            self.create_field(child_model_id, elem)

        # Establish the one-to-many relationship
        self.env['ir.model.fields'].create({
            'name': f'x_{repeat_elem.tag}_ids',
            'ttype': 'one2many',
            'model_id': parent_model_id.id,
            'relation': child_model_id.model,
            'field_description': repeat_elem.tag,
        })
        return child_model_id

    def create_access_rights(self, model_id):
        self.env['ir.model.access'].create({
            'name': f"access_{model_id.model}",
            'model_id': model_id.id,
            'group_id': False,
            'perm_read': True,
            'perm_write': True,
            'perm_create': True,
            'perm_unlink': True,
        })

    def create_basic_views(self, model_id, model_fields):
        # Create tree view
        tree_fields = ' '.join([f'<field name="{f[0]}"/>' for f in model_fields])
        self.env['ir.ui.view'].create({
            'name': f"{model_id.name} Tree View",
            'model': model_id.model,
            'arch': f'''<tree string="{model_id.name}">
                           {tree_fields}
                        </tree>''',
            'type': 'tree',
        })

        # Create form view
        form_fields = ' '.join([f'<field name="{f[0]}"/>' for f in model_fields])
        self.env['ir.ui.view'].create({
            'name': f"{model_id.name} Form View",
            'model': model_id.model,
            'arch': f'''<form string="{model_id.name}">
                           {form_fields}
                        </form>''',
            'type': 'form',
        })
