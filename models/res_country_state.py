from odoo import models, fields, api

class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    venditore_ids = fields.Many2many('res.users', string='Venditori')