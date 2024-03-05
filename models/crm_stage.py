from odoo import models, fields, api

class CrmStage(models.Model):
    _inherit = 'crm.stage'

    venditore_ids = fields.Many2many('res.users', string='Venditori')