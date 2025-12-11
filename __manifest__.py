# -*- coding: utf-8 -*-
{
    'name': "LaserCom",

    'summary': """
        Personalizzazioni CRM LaserCom""",

    'description': """
        Personalizzazioni CRM LaserCom
    """,

    'author': "Rocco Cesetti",
    'website': "https://www.ideawork.it",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Technical Settings',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','crm','sale','sale_margin','sale_management','lasercom','sale_product_configurator'],

    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_data.xml',

        'wizard/crm_lead_view.xml',
        'views/res_partner.xml',
       'views/sale_string_price_view.xml',
        'report/sale_report_templates.xml',
        'report/sale_report.xml',

        
    ],
}
