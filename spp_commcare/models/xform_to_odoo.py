from odoo import api, models, fields, exceptions
import xml.etree.ElementTree as ET
from lxml import etree


class XFormToOdoo(models.TransientModel):
    _name = 'xform.to.odoo'
    _xform_namespaces = {
        'xf': 'http://www.w3.org/2002/xforms',
        'h': 'http://www.w3.org/1999/xhtml',
        'orx': 'http://openrosa.org/jr/xforms',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
        'jr': 'http://openrosa.org/javarosa',
        'vellum': 'http://commcarehq.org/xforms/vellum'
    }

    name = fields.Text()

    def create_odoo_model(self, xform):
        try:
            xform_dict = self.xform_to_dict(xform)

            # Create the main model
            model_name = xform_dict.get('_model_name').replace(" ", "_").lower()
            model_db_name = 'x_' + model_name
            existing_model = self.env['ir.model'].search([('model', '=', model_db_name)])

            if existing_model:
                counter = 1
                while existing_model:
                    new_model_name = f"{model_db_name}_{counter}"
                    existing_model = self.env['ir.model'].search([('model', '=', new_model_name)])
                    counter += 1
                model_db_name = new_model_name

            model_id = self.env['ir.model'].create({
                'name': xform_dict.get('_model_name'),
                'model': model_db_name,
            })
            self.create_access_rights(model_id)

            # Create fields for the main model
            for field_name, field_attrs in xform_dict.items():
                if field_name != '_model_name':
                    self.create_field(model_id, field_name, field_attrs)

        except Exception as e:
            self.env.cr.rollback()
            raise exceptions.ValidationError(f"An error occurred: {str(e)}")

    def create_field(self, model_id, field_name, field_attrs):
        # Use the label in 'en' language if available, else default to the field name.
        field_display_name = field_attrs.get('label', {}).get('en', field_name)
        field_db_name = f'x_{field_name}'
        field_type = self.xsd_to_odoo_type(field_attrs.get('type'))

        if not field_type:
            print(f"Field type not found for {field_display_name}")
            return

        existing_field = self.env['ir.model.fields'].search([
            ('name', '=', field_db_name),
            ('model_id', '=', model_id.id),
        ])

        if existing_field:
            return

        created_field = self.env['ir.model.fields'].create({
            'name': field_db_name,
            'ttype': field_type,
            'model_id': model_id.id,
            'field_description': field_display_name,
        })

        # If the field has select options, populate them
        select_options = field_attrs.get('select_options')
        if select_options:
            for option in select_options:
                value = option['value']
                display_name = option['label'].get('en', value)  # Default to the value if 'en' label is not available
                self.env['ir.model.fields.selection'].create({
                    'field_id': created_field.id,
                    'value': value,
                    'name': display_name,
                })


    def xsd_to_odoo_type(self, xsd_type):
        """
        Convert an XSD type to an Odoo field type
        """
        mapping = {
            'xsd:string': 'char',
            'xsd:double': 'float',
            'xsd:int': 'integer',
            'xsd:date': 'date',
            'binary': 'binary',
        }
        return mapping.get(xsd_type, 'char')

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

    def _parse_xml(self, xform):
        root = etree.fromstring(xform)
        model_element = root.xpath('.//xf:model', namespaces=self._xform_namespaces)[0]
        instance_element = model_element.xpath('.//xf:instance', namespaces=self._xform_namespaces)[0]
        data_element = instance_element[0]
        body_element = root.xpath('.//h:body', namespaces=self._xform_namespaces)[0]
        return model_element, data_element, body_element

    def _traverse_element(self, element, json_dict):
        for child in element:
            tag = child.tag.split('}')[-1]
            if child.attrib.get('jr:template') is not None:
                json_dict[tag] = [self._traverse_element(child, {})]
            else:
                json_dict[tag] = self._traverse_element(child, {})
        return json_dict

    def _update_json_structure(self, element, json_dict, field_types):
        for child in element:
            tag = child.tag.split('}')[-1]
            field_info = {
                "type": field_types.get(tag, "unknown"),
                "relationship": None,
                "select_options": None
            }
            if child.attrib.get('jr:template') is not None:
                json_dict[tag] = {
                    "type": "list",
                    "items": [self._update_json_structure(child, {}, field_types)]
                }
            else:
                json_dict[tag] = self._update_json_structure(child, field_info, field_types)
        return json_dict

    def _update_select_options_in_json(self, json_dict, ref_path, select_options):
        keys = ref_path.split('/')[2:]
        temp_dict = json_dict
        for key in keys:
            temp_dict = temp_dict.get(key, {})
        if temp_dict is not None:
            temp_dict["select_options"] = select_options

    def _extract_select_options_manual(self, select_element):
        options = []
        for item in select_element.findall('.//item', namespaces=select_element.nsmap):
            value_element = item.find('./value', namespaces=select_element.nsmap)
            if value_element is not None and value_element.text is not None:
                options.append({"value": value_element.text})
        return options

    def _extract_translations(self, model_element):
        translations = {}
        for itext in model_element.xpath('.//xf:itext/xf:translation', namespaces=self._xform_namespaces):
            lang = itext.get('lang')
            for text in itext.xpath('.//xf:text', namespaces=self._xform_namespaces):
                field_id = text.get('id')
                label = text.xpath('./xf:value/text()', namespaces=self._xform_namespaces)
                label = label[0] if label else None
                if label:
                    translations.setdefault(field_id, {})[lang] = label
        return translations

    def _update_json_with_translations(self, json_dict, translations, current_path=[]):
        for key, value in json_dict.items():
            new_path = current_path + [key]
            field_id = "/".join(new_path) + "-label"  # Use forward slash (/) instead of hyphen (-)
            label_translations = translations.get(field_id)
            if label_translations:
                value["label"] = label_translations
            if isinstance(value, dict):
                if "select_options" in value and value["select_options"] is not None:
                    for option in value["select_options"]:
                        option_value = option.get("value")
                        if option_value:
                            option_id = "/".join(
                                new_path) + "-" + option_value + "-label"  # Use forward slash (/) instead of hyphen (-)
                            option_label_translations = translations.get(option_id)
                            if option_label_translations:
                                option["label"] = option_label_translations
                self._update_json_with_translations(value, translations, new_path)
            elif isinstance(value, list):
                for item in value:
                    self._update_json_with_translations(item, translations, new_path)

    def xform_to_dict(self, xform):
        json_structure = {}
        field_types = {}

        model_element, data_element, body_element = self._parse_xml(xform)

        json_structure = self._traverse_element(data_element, {})

        for bind in model_element.xpath('.//xf:bind', namespaces=self._xform_namespaces):
            nodeset = bind.get('nodeset')
            field_name = nodeset.split('/')[-1]
            field_type = bind.get('type')
            field_types[field_name] = field_type

        json_structure = self._update_json_structure(data_element, json_structure, field_types)

        for select_element in body_element.xpath('.//xf:select1', namespaces=self._xform_namespaces):
            ref = select_element.get('ref')
            select_options = self._extract_select_options_manual(select_element)
            self._update_select_options_in_json(json_structure, ref, select_options)

        translations = self._extract_translations(model_element)
        self._update_json_with_translations(json_structure, translations)

        model_name = data_element.get('name')
        json_structure["_model_name"] = model_name

        return json_structure
