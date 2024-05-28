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
        # Ottieni l'utente corrente
        user = self.env.user
        # Controlla se l'utente appartiene al gruppo 'group_venditore'
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

        return super(ResPartner, self.sudo())._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        #return super().with_user(SUPERUSER_ID).with_context({'bypass_rule': True})._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

class ResCompany(models.Model):
    _inherit = "res.company"

    numero_verde = fields.Char(string='Numero verde')
    