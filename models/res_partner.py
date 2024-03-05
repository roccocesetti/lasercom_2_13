from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    venditore_ids = fields.Many2many('res.users', string='Venditore')
    rivendita = fields.Char(string='Rivendita')
    prodotto = fields.Selection([
        ('ALTRO', 'Altro'),
        ('AM_TOUCH', 'AM Touch'),
        ('AM_PULSANTI', 'AM Pulsanti'),
        ('AUTOMATICA_TOUCH', 'Automatica Touch'),
        ('ARUBA', 'Aruba'),
        ('BAHAMAS', 'Bahamas'),
        ('BIG_ONE', 'Big One'),
        ('CAYENNE', 'Cayenne'),
        ('EFFE.TI_MYA', 'Effe.Ti MYA'),
        ('EVX_TOUCH', 'Evx Touch'),
        ('HARVIN_PULSANTI', 'Harvin Pulsanti'),
        ('HARVIN_TOUCH', 'Harvin Touch'),
        ('HAVANA', 'Havana'),
        ('JAMAICA', 'Jamaica'),
        ('JAGUAR', 'Jaguar'),
        ('LASERVIDEO_PULSANTI', 'Laservideo Pulsanti'),
        ('LASERVIDEO TOUCH', 'Lservideo Touch'),
        ('LEOPARD', 'Leopard'),
        ('LION', 'Lion'),
        ('LEGEND', 'Legend'),
        ('MECSYSTEM', 'Mecsystem'),
        ('MIAMI', 'Miami'),
        ('NOVAMATIC_TOUCH', 'Novamatic Touch'),
        ('NOVAMATIC_PULSANTI', 'Novamatic Pulsanti'),
        ('ONE_TOUCH', 'One Touch'),
        ('PANAMA', 'Panama'),
        ('TECNOC_TOUCH', 'Tecnoc Touch'),
        ('TECNO_PULSANTI', 'Tecno Pulsanti'),
        ('SNACK24', 'Snack 24'),
        ('SIDE_PULSANTI', 'Side Pulsanti'),
        ('TIGER', 'Tiger'),
        ('NONPRESENTE', 'DISTRIBUTORE NON PRESENTE')
    ], string='Prodotto');
    data_installazione = fields.Date(string='Data installazione')

    @api.model
    def create(self, values):

        if (values['is_company']):

            if not values['state_id']:
                raise ValidationError('Il campo provincia è obbligatorio')

            provincia = self.env['res.country.state'].browse(values['state_id'])
            if not values['venditore_ids'][0][2]:
                if len(provincia['venditore_ids']):
                    venditore_ids = [user.id for user in provincia['venditore_ids']]
                    values['venditore_ids'][0][2] = venditore_ids

        result = super(ResPartner, self).create(values)

        if (values['is_company']):

            lead = {
                'user_id' : None,
                'name' : 'visita',
                'date_deadline' : date.today() + timedelta(days=30),
                'partner_id': result.id,
            }

            if (len(values['category_id'][0][2]) > 0):
                if (1 in values['category_id'][0][2]):
                    lead['color'] = 10
                elif (6 in values['category_id'][0][2]):
                    lead['color'] = 1

            # Crea opportunita stage venditori
            lead['stage_id'] = 1;
            self.env['crm.lead'].sudo().create(lead)

            lead['stage_id'] = 5;
            self.env['crm.lead'].sudo().create(lead)


        return result

    def write(self, values):
        if self:
            for value in self:
                leads = self.env['crm.lead'].sudo().search(['&', ('partner_id', '=', value.id), '|', ('active','=',True), ('active','=',False)])
                update_values = {}
                for lead in leads:
                    #_logger.debug('-------------------- %s', lead)
                    if 'active' in values:
                        update_values['active'] = values['active']
                    if 'mobile' in values:
                        update_values['mobile'] = values['mobile']
                    if 'street' in values:
                        update_values['street'] = values['street']

                    lead.sudo().write(update_values)

        return super(ResPartner, self).write(values)

    def unlink(self):
        for partner in self:
            leads = self.env['crm.lead'].search(['&', ('partner_id', '=', partner.id), '|', ('active','=',True), ('active','=',False)])
            for lead in leads:
                lead.unlink()

        return super(ResPartner, self).unlink()


    def fields_get(self, fields=None):
        res = super(ResPartner, self).fields_get()

        fields_to_show = ['city','state_id','prodotto','company_name','data_installazione','write_date']
        for field in res:
            if (field not in fields_to_show):
                res.get(field)['searchable'] = False  # hide from filter
                res.get(field)['sortable'] = False  # hide from group by

        return res