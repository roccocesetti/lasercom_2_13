from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'
    _order = 'date_deadline'

    data_installazione = fields.Date(related='partner_id.data_installazione', string="Data Installazione")

    @api.model
    def create(self, values):
        values['user_id'] = None
        values['color'] = None

        partner = self.env['res.partner'].browse(values['partner_id'])
        if (len(partner['category_id']) > 0) :
            categorie_ids = [category.id for category in partner['category_id']]
            if (1 in categorie_ids) :
                values['color'] = 10
            elif (6 in categorie_ids) :
                values['color'] = 1

        result = super(CrmLead, self).create(values)
        return result

    def fields_get(self, fields=None):
        res = super(CrmLead, self).fields_get()

        fields_to_show = ['city','state_id','prodotto','company_name','date_deadline','write_date','street']
        for field in res:
            if (field not in fields_to_show):
                res.get(field)['searchable'] = False
                res.get(field)['sortable'] = False

        return res