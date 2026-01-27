#from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
import logging
from odoo import models, fields, api,SUPERUSER_ID

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    codice_sdi = fields.Char(string='Codice sdi')    
    #numero_verde = fields.Char(string='Numero verde')
    #numero_righe = fields.Integer(string='Numero Righe')

    #def create(self, values):
    #    result = super(ResPartner, self).create(values)
    #    return result

    #def write(self, values):
    #    return super(ResPartner, self).write(values)



    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        # Ottieni l'utente corrente
        user = self.env.user
        # Controlla se l'utente appartiene al gruppo 'group_venditore'
        if not user.has_group('lasercom.group_telemarketing') and not user.has_group('lasercom.group_amministratore'):
            if user.has_group('lasercom.group_venditore'):
                # Se l'utente appartiene al gruppo, esegui la ricerca includendo i criteri specificati
                user_state_ids = [state.id for state in user.state_ids]  # Prepara una lista di ID degli stati
                if not args:
                    args = []
                """
                args += [
                    '|',
                    ('venditore_ids', 'in', [user.id]),  # Contatti dove l'utente è un venditore
                    '|',
                    ('venditore_ids', '=', False),  # Contatti senza venditore specificato
                    #'&',
                    ('state_id.id', 'in', user_state_ids)  # Contatti nello stato dell'utente
                    #('venditore_ids', '=', False)  # E l'utente è il venditore
                ]
                """
                args += [
                    '|',
                    ('venditore_ids', 'in', [user.id]),
                    '|',
                    ('venditore_ids', '=', False),
                    ('state_id', 'in', user_state_ids)
                ]

        return super(ResPartner,self.sudo()).name_search(name, args=args, operator=operator, limit=limit)
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        # Ottieni l'utente corrente
        user = self.env.user
        # Controlla se l'utente appartiene al gruppo 'group_venditore'
        """
        if user.has_group('lasercom.group_venditore'):
            # Se l'utente appartiene al gruppo, esegui la ricerca includendo i criteri specificati
            user_state_ids = [state.id for state in user.state_ids]  # Prepara una lista di ID degli stati
            if not args:
                args = []
            args += [
                '|',
                ('venditore_ids', 'in', [user.id]),  # Contatti dove l'utente è un venditore
                '|',
                ('venditore_ids', '=', False),  # Contatti senza venditore specificato
                '&',
                ('state_id.id', 'in', user_state_ids),  # Contatti nello stato dell'utente
                ('venditore_ids', '=', False)  # E l'utente è il venditore
            ]
        """
        return super(ResPartner, self.sudo())._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        #return super().with_user(SUPERUSER_ID).with_context({'bypass_rule': True})._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

    @api.model
    @api.returns('self',
        upgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False: value if count else self.browse(value),
        downgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False: value if count else value.ids)
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """ search(args[, offset=0][, limit=None][, order=None][, count=False])

        Searches for records based on the ``args``
        :ref:`search domain <reference/orm/domains>`.

        :param args: :ref:`A search domain <reference/orm/domains>`. Use an empty
                     list to match all records.
        :param int offset: number of results to ignore (default: none)
        :param int limit: maximum number of records to return (default: all)
        :param str order: sort string
        :param bool count: if True, only counts and returns the number of matching records (default: False)
        :returns: at most ``limit`` records matching the search criteria

        :raise AccessError: * if user tries to bypass access rules for read on the requested object.
        """
        user = self.env.user
        # Controlla se l'utente appartiene al gruppo 'group_venditore'
        if not user.has_group('lasercom.group_telemarketing') and not user.has_group('lasercom.group_amministratore'):
           if user.has_group('lasercom.group_venditore'):
                user_state_ids = [state.id for state in user.state_ids]  # Prepara una lista di ID degli stati
                if not args:
                 args = []
                args += [
                    '|',
                    #'|',
                    #('venditore_ids', 'in', [user.id]),
                    ('venditore_ids', '=', False),
                    ('state_id', 'in', user_state_ids)
                ]

        res = super(ResPartner,self.sudo()).search(args, offset=offset, limit=limit, order=order, count=count)
        return res

    @api.depends_context('force_company')
    def _credit_debit_get(self):
        if hasattr(self.env, 'account.move.line'):
            super(ResPartner, self.sudo())._credit_debit_get()
        else:
            treated = self.browse()
            remaining = (self - treated)
            remaining.debit = False
            remaining.credit = False

class ResCompany(models.Model):
    _inherit = "res.company"

    numero_verde = fields.Char(string='Numero verde')
