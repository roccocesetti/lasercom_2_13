# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from babel.dates import format_datetime, format_date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF,DEFAULT_SERVER_DATETIME_FORMAT as DTF, safe_eval

class crmleadwizard(models.TransientModel):
    _name = "crm.lead.wizard"
    _description = "crm.lead.wizard"

    """
    def _get_default_country(self):
        if self.env.user.company_id.country_id:
            return self.env.user.company_id.country_id.id
        else:
            return False
    """
    def _get_date_deadline(self):
        date_deadline = fields.Date.today()
        
        
        return date_deadline
    """
    def _get_default_end_week(self):
        init_week_date = fields.Date.today()
        day_of_week = int(format_datetime(init_week_date, 'e', locale=self._context.get('lang') or 'en_US'))-1
        while day_of_week!=1:
            init_week_date=init_week_date- timedelta(days=1)
            day_of_week = int(format_datetime(init_week_date, 'e', locale=self._context.get('lang') or 'en_US'))-1
        
        
        return init_week_date+ timedelta(days=+7)

    """
    date_deadline = fields.Date(string='',default=_get_date_deadline)
    #date_to = fields.Date(string='Fine Settimana',default=_get_default_end_week)


    def set_deadline(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        for my_lead in self.env['crm.lead'].browse(data['ids']):
            my_lead.write({'date_deadline':self.date_deadline})
        action = {
            'name': _('lead'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'context': self.env.context.copy(),
            }
        if len(data['ids']) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': data['ids'][0],
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', data['ids'])],
            })
        return action

