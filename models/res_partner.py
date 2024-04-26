from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    codice_sdi = fields.Char(string='Codice sdi')    
#    numero_verde = fields.Char(string='Numero verde')

class ResCompany(models.Model):
    _inherit = "res.company"

    numero_verde = fields.Char(string='Numero verde')
    