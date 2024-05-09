from odoo import models, fields, api,SUPERUSER_ID

class ResCountryState(models.Model):
    _inherit = 'res.country.state'


    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator == 'ilike':
            if SUPERUSER_ID !=self.env.uid and self.env.uid != 2:
                args =["|",('venditore_ids','in',[self.env.uid]),('venditore_ids','=',False)]

        return super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

#    @api.model
#    @api.returns('self',
#        upgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False: value if count else self.browse(value),
#        downgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False: value if count else value.ids)
#    def search(self, args, offset=0, limit=None, order=None, count=False):
#        """ search(args[, offset=0][, limit=None][, order=None][, count=False])
#
#        Searches for records based on the ``args``
#        :ref:`search domain <reference/orm/domains>`.
#
#        :param args: :ref:`A search domain <reference/orm/domains>`. Use an empty
#                     list to match all records.
#        :param int offset: number of results to ignore (default: none)
#        :param int limit: maximum number of records to return (default: all)
#        :param str order: sort string
#        :param bool count: if True, only counts and returns the number of matching records (default: False)
#        :returns: at most ``limit`` records matching the search criteria
#
#        :raise AccessError: * if user tries to bypass access rules for read on the requested object.
#        """
#        if SUPERUSER_ID !=self.env.uid and self.env.uid != 2:
#                args =["|",('venditore_ids','in',[self.env.uid]),('venditore_ids','=',False)]
#
#        res = self._search(args, offset=offset, limit=limit, order=order, count=count)
#        return res if count else self.browse(res)
#
#    #
#    # display_name, name_get, name_create, name_search
#    #
     