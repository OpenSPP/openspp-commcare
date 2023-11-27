import json
import logging
from datetime import datetime

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class CommCareCase(models.Model):
    _name = "spp.commcare.case"
    _description = "CommCare Cases"
    _rec_name = "case_id"
    _order = "id desc"

    # Fixed fields
    domain = fields.Char(required=True)
    case_id = fields.Char(string="Case ID", required=True, index=True)
    case_type = fields.Char()
    user_id = fields.Char(string="User ID", required=True)
    closed = fields.Boolean(default=False)
    xform_ids = fields.Char(
        string="XForm IDs"
    )  # Assuming IDs can be stored as comma-separated values
    date_closed = fields.Datetime()
    date_modified = fields.Datetime()
    server_date_modified = fields.Datetime()

    # Flexible field for form-specific properties
    properties = fields.Text()

    # Parent-Child Relationship
    parent_id = fields.Many2one("spp.commcare.case", string="Parent Case")

    # Link to the res.partner model
    partner_id = fields.Many2one("res.partner", string="Associated Partner")

    is_partial = fields.Boolean(string="Is Partially filled", default=False)

    @api.model
    def link_case_to_partner(self, partner=None):
        # Step 1: Deserialize properties to Python dictionary
        properties_dict = json.loads(self.properties)

        # Step 2: Extract group_id
        group_id = properties_dict.get("group_id")
        if not group_id:
            logging.warning(f"No group_id found for case_id {self.case_id}")
            return  # or log a warning

        # Step 2: Extract group_id
        case_type = properties_dict.get("case_type")
        if not case_type:
            return  # or log a warning
        # Step 3: Search for the matching partner
        criteria = [("name", "=", group_id)]
        if case_type == "group":
            criteria.append(("is_group", "=", True))
        else:
            criteria.append(("is_group", "=", False))

        matching_partner = self.env["res.partner"].search(criteria, limit=1)

        # Step 4: Link the case to the partner if found
        if matching_partner:
            self.partner_id = matching_partner.id
        else:
            logging.warning(f"No matching partner found for group_id {group_id}")

    @api.model
    def create_case_from_json(self, case_json):
        # Serialize the properties dictionary to a JSON-formatted string
        properties_str = json.dumps(case_json.get("properties", {}))

        # Prepare a data dictionary to hold the new case's data
        case_data = {
            "domain": case_json.get("domain"),
            "case_id": case_json.get("case_id"),
            "user_id": case_json.get("user_id"),
            "closed": case_json.get("closed", False),
            "xform_ids": ",".join(case_json.get("xform_ids", [])),
            "date_closed": case_json.get("date_closed"),
            "date_modified": case_json.get("date_modified"),
            "server_date_modified": case_json.get("server_date_modified"),
            "properties": properties_str,
            "case_type": case_json.get("properties", {}).get("case_type"),
        }

        # Search for an existing case with the same case_id
        existing_case = self.env["spp.commcare.case"].search(
            [("case_id", "=", case_data["case_id"])], order="create_date desc", limit=1
        )

        # If a case exists, decide whether to update it
        if existing_case and not existing_case.is_partial:
            existing_date_str = existing_case.date_modified
            new_date_str = case_data["date_modified"]

            # Convert both dates to datetime objects for comparison
            existing_date = (
                datetime.strptime(existing_date_str, DEFAULT_SERVER_DATETIME_FORMAT)
                if existing_date_str
                else datetime.min
            )
            new_date = datetime.strptime(new_date_str, DEFAULT_SERVER_DATETIME_FORMAT)

            # Update only if the new record is more recent
            if new_date > existing_date:
                existing_case.write(case_data)
                return existing_case

        else:
            # Create a new case if none exists with the same case_id
            # Handle parent-child relationships, if applicable
            indices = case_json.get("indices", {})
            parent_info = indices.get("parent")
            if parent_info:
                parent_case_id = parent_info.get("case_id")
                parent_case = self.env["spp.commcare.case"].search(
                    [("case_id", "=", parent_case_id)],
                    order="create_date desc",
                    limit=1,
                )

                # Create parent case if not found
                if not parent_case:
                    parent_case_data = {
                        "case_id": parent_case_id,
                        # Add any other default or inferred fields for parent case here
                    }
                    parent_case = self.env["spp.commcare.case"].create(parent_case_data)

                case_data["parent_id"] = parent_case.id

            if existing_case:
                existing_case.write(case_data)
                return existing_case
            else:
                # Create the new case record in Odoo and return it
                new_case = self.env["spp.commcare.case"].create(case_data)

                # Link case to partner after creation
                new_case.link_case_to_partner()
                return new_case
