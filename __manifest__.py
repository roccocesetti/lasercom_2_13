# -*- coding: utf-8 -*-
{
    'name': "LaserCom",

    'summary': """
        Personalizzazioni CRM LaserCom""",

    'description': """
        Personalizzazioni CRM LaserCom
    """,

    'author': "Murri Augusto",
    'website': "https://www.opent.it",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Technical Settings',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','crm'],

    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'views/calendar_event.xml',
        'views/res_partner.xml',
        'views/crm_lead.xml',
        'views/crm_stage.xml',
        'views/res_country_state.xml',
        'views/res_users.xml',
        'views/security.xml',
        'views/rules.xml',
    ],
}
