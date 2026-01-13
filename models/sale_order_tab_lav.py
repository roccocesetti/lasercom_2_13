# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools.sql import column_exists, create_column
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)






class ProductLoad(models.Model):
    _name = "x.product.load"
    _description = "Caricamento Prodotti"
    _order = "id desc"

    name = fields.Char(string="Riferimento", required=True, default=lambda self: self._default_name())
    note = fields.Text(string="Nota")
    line_ids = fields.One2many("x.product.load.line", "load_id", string="Righe prodotti")

    @api.model
    def _default_name(self):
        # semplice progressivo basato su sequenza; se non vuoi la sequenza, puoi mettere un default diverso
        return self.env["ir.sequence"].next_by_code("x.product.load") or "Nuovo"


class ProductLoadLine(models.Model):
    _name = "x.product.load.line"
    _description = "Riga Caricamento Prodotto"
    _order = "id asc"

    load_id = fields.Many2one("x.product.load", string="Caricamento", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Prodotto", required=True)
    product_uom_height = fields.Float(string="Altezza", default=0.0)
    product_uom_length = fields.Float(string="Lunghezza", default=0.0)
    product_uom_qty = fields.Float(string="Quantità", default=1.0)
    price_unit = fields.Float(string="Prezzo Unitario")
    price_extra = fields.Float(string="Prezzo Extra")
    supplier_id = fields.Many2one("res.partner", string="Fornitore", required=False)

    # Nota riga (se serve anche per ogni prodotto)
    note = fields.Char(string="Nota riga")

    # Campi utili “related” per vedere info del prodotto senza duplicarle
    default_code = fields.Char(related="product_id.default_code", string="Rif. Interno", readonly=True, store=False)
    uom_id = fields.Many2one(related="product_id.uom_id", string="U.M.", readonly=True, store=False)

    @api.onchange('uom_id', 'product_uom_height', 'product_uom_length')
    def product_uom_change(self):
        if not self.uom_id or not self.product_id:
            self.product_uom_qty = 0.0
            return
        self.product_uom_qty=self.product_uom_height*self.product_uom_length

class ResCompany(models.Model):
    _inherit = "res.company"

    x_default_product_load_id = fields.Many2one(
        "x.product.load",
        string="Caricamento Prodotti predefinito (Vendite)"
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    x_default_product_load_id = fields.Many2one(
        related="company_id.x_default_product_load_id",
        readonly=False,
        string="Caricamento Prodotti predefinito (Vendite)",
    )




class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends('x_load_line_ids')
    def _compute_amount_lav(self):
        """
        Compute the amounts of the SO line.
        """
        for order in self:
            price_subtotal_lav=0.00
            for line in order.x_load_line_ids:
                        price_subtotal_lav+=line.price_subtotal
            order.update({
                            'price_subtotal_lav': price_subtotal_lav ,
                        })

    x_load_id = fields.Many2one(
        "x.product.load",
        string="Caricamento Prodotti",
        default=lambda self: self.env.company.x_default_product_load_id,
    )

    x_load_line_ids = fields.One2many(
        "sale.order.x_load_line",
        "order_id",
        string="Righe Caricamento (in ordine)",
        copy=True,
    )

    price_subtotal_lav = fields.Monetary(compute='_compute_amount_lav', string='Subtotal', readonly=True, store=True)
    @api.onchange("company_id")
    def _onchange_company_id_set_default_load(self):
        for order in self:
            # se non valorizzato, applica la property della company
            if not order.x_load_id and order.company_id:
                order.x_load_id = order.company_id.x_default_product_load_id

    def action_open_import_load_lines_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Seleziona righe da Caricamento"),
            "res_model": "x.sale.order.import.load.lines.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_order_id": self.id,
                "default_load_id": self.x_load_id.id,
            },
        }


class SaleOrderXLoadLine(models.Model):
    _name = "sale.order.x_load_line"
    _description = "Righe Caricamento su Ordine di Vendita"
    _order = "id asc"

    @api.depends('product_uom_qty', 'price_unit', 'price_extra')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            if 'price_subtotal' in line._fields:
                 line.update({
                    'price_subtotal': line.price_unit * line.product_uom_qty + line.price_extra,
                })

    @api.depends('product_id', 'order_id.state', 'qty_invoiced', 'qty_delivered')
    def _compute_product_updatable(self):
        for line in self:
            if line.state in ['done', 'cancel'] or (line.state == 'sale' and (line.qty_invoiced > 0 or line.qty_delivered > 0)):
                line.product_updatable = False
            else:
                line.product_updatable = True


    order_id = fields.Many2one("sale.order", required=True, ondelete="cascade")
    currency_id = fields.Many2one(
        'res.currency',
        related='order_id.currency_id',
        store=True,
        readonly=True
    )
    product_id = fields.Many2one("product.product", string="Prodotto", required=True)
    product_uom_height = fields.Float(string="Altezza", default=0.0)
    product_uom_length = fields.Float(string="lunghezza", default=0.0)
    product_uom_qty = fields.Float(string="Quantità", default=1.0)
    price_unit = fields.Float(string="Prezzo Unitario")
    price_extra = fields.Float(string="Prezzo Extra")
    note = fields.Char(string="Nota")
    supplier_id = fields.Many2one("res.partner", string="Fornitore", required=False)
    default_code = fields.Char(related="product_id.default_code", string="Rif. Interno", readonly=True, store=False)
    uom_id = fields.Many2one(related="product_id.uom_id", string="U.M.", readonly=True, store=False)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    @api.onchange('uom_id', 'product_uom_height', 'product_uom_length')
    def product_uom_change(self):
        if not self.uom_id or not self.product_id:
            self.product_uom_qty = 0.0
            return
        self.product_uom_qty=self.product_uom_height*self.product_uom_length
