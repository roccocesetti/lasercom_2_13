#from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
import logging
from odoo import models, fields, api,SUPERUSER_ID

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    codice_sdi = fields.Char(string='Codice sdi')    
#    numero_verde = fields.Char(string='Numero verde')

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator == 'ilike':
            if SUPERUSER_ID !=self.env.uid and self.env.uid != 2 and self.env.uid != 10:
                args =["|",('venditore_ids','in',[self.env.uid]),('venditore_ids','=',False)]

        return super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

class ResCompany(models.Model):
    _inherit = "res.company"

    numero_verde = fields.Char(string='Numero verde')
    