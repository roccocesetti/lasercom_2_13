from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    state_ids = fields.Many2many('res.country.state', string='Province assegnate')
    stage_ids = fields.Many2many('crm.stage', string='Fasi CRM visibili')