from odoo import fields, models


class CommCareFieldMapping(models.Model):
    """Field Mapping parent model
    Configuration of Commcare fields for mapping with OpenSPP fields
    """

    _name = "spp.commcare.field.map"
    _description = "CommCare Field Mapping"
    _order = "id desc"

    name = fields.Char("Form Name", required=True)
    field_ids = fields.One2many(
        "spp.commcare.field.map.fields", "map_id", string="Field Mappings"
    )
    model_id = fields.Many2one(
        "ir.model", "Default Model", required=True, ondelete="cascade"
    )


class CommCareFieldMappingFields(models.Model):
    """Field Mapping child model
    Details of the mapping of Commcare fields with OpenSPP fields
    """

    _name = "spp.commcare.field.map.fields"
    _description = "Commcare Field Mapping Fields"

    def _default_model(self):
        return self.map_id.model_id.id

    map_id = fields.Many2one("spp.commcare.field.map")
    model_id = fields.Many2one(
        "ir.model", "Model", required=True, default=_default_model, ondelete="cascade"
    )
    commcare_field = fields.Char(required=True)

    # TODO: Fix issue with ir.model.fields not accessible here
    # openspp_field_id = fields.Many2one(
    #    "OpenSPP Field", "ir.model.fields", required=True, ondelete="cascade"
    # )
    # openspp_field_type_id = fields.Selection(
    #    string="Field Type", related="openspp_field_id.ttype", readonly=True
    # )

    # Temporary fix
    openspp_field = fields.Char()

    # @api.onchange("model_id")
    # def _onchange_model_id(self):
    #    for rec in self:
    #        res = None
    #        if rec.model_id:
    #            res = {
    #                "domain": {"openspp_field_id": [("model_id", "=", rec.model_id.id)]}
    #            }
    #        return res
