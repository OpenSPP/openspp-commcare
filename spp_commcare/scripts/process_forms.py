#!/usr/bin/env python
from __future__ import print_function
import click

import click_odoo


@click.command()
@click_odoo.env_options(default_log_level='info')
def main(env):
    forms = env['spp.commcare.form'].search([], order='id DESC', limit=1)
    forms.create_event_data_from_form()
    # partners = env['res.partner'].search([], limit=1)
    # partners.recompute_indicators_for_all_records(fields)


if __name__ == '__main__':
    main()
