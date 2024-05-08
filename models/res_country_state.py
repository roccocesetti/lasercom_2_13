from odoo import models, fields, api,SUPERUSER_ID

class ResCountryState(models.Model):
    _inherit = 'res.country.state'


    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator == 'ilike':
            if SUPERUSER_ID !=self.env.uid and self.env.uid != 2:
                args =["|",('venditore_ids','in',[self.env.uid]),('venditore_ids','=',False)]

        return super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
     