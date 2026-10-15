# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


def _sort_field_selection(self):
    return [('module', "Ordine del modulo (con sezioni)")] + \
        self.env['sale.order']._MODULO_SORT_FIELDS


class PrintModuloWizard(models.TransientModel):
    """Stampa del Modulo Installazione con scelta dell'ordinamento delle
    righe. Con un ordinamento diverso da quello del modulo le Sezioni non
    vengono stampate."""
    _name = "x.sale.order.print.modulo.wizard"
    _description = "Wizard stampa Modulo Installazione"

    order_id = fields.Many2one("sale.order", string="Ordine", required=True)
    sort_field = fields.Selection(
        _sort_field_selection,
        string="Ordina per",
        required=True,
        default='module',
    )
    sort_desc = fields.Boolean(string="Decrescente")
    print_supplier = fields.Boolean(string="Stampa colonna Fornitore")

    def action_print(self):
        self.ensure_one()
        sort_field = self.sort_field if self.sort_field != 'module' else False
        report = self.env.ref('lasercom_2_13.action_report_saleorder_laser_modulo')
        # Con data il client non passa gli id nell'URL: li legge il report
        # model qui sotto da data['ids'].
        return report.report_action(self.order_id, data={
            'ids': self.order_id.ids,
            'x_sort_field': sort_field,
            'x_sort_desc': bool(sort_field and self.sort_desc),
            'x_print_supplier': self.print_supplier,
        })


class ReportSaleOrderLaserModulo(models.AbstractModel):
    _name = "report.lasercom_2_13.report_saleorder_laser_modulo"
    _description = "Report Modulo Installazione"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        docids = docids or data.get('ids') or []
        # Colonna Fornitore solo se richiesta dal wizard (spunta "Stampa
        # colonna Fornitore") e solo per Sales Manager e Admin LAV: dal menu
        # Stampa e nel PDF allegato alla conferma del modulo non c'e' mai.
        user = self.env.user
        show_supplier = (
            data.get('x_print_supplier')
            and (user.has_group('sales_team.group_sale_manager')
                 or user.has_group('lasercom_2_13.group_admin_lav'))
        )
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': self.env['sale.order'].browse(docids),
            'x_sort_field': data.get('x_sort_field') or False,
            'x_sort_desc': data.get('x_sort_desc') or False,
            'x_show_supplier': show_supplier,
        }
