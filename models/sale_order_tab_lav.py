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
    _order = "sequence,id asc"
    sequence = fields.Integer(string="Sequenza", default=10, index=True)
    load_id = fields.Many2one("x.product.load", string="Caricamento", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Prodotto", required=True)
    product_uom_height = fields.Float(string="Altezza", default=0.0)
    product_uom_length = fields.Float(string="Lunghezza", default=0.0)
    product_uom_qty = fields.Float(string="Quantità", default=1.0)
    price_unit = fields.Float(string="Prezzo Unitario")
    price_extra = fields.Float(string="Prezzo Extra")
    supplier_id = fields.Many2one("res.partner", string="Fornitore", required=False)
    editable = fields.Boolean(string="Edit", default=False)
    # Nota riga (se serve anche per ogni prodotto)
    note = fields.Char(string="Nota riga")

    # Campi utili “related” per vedere info del prodotto senza duplicarle
    default_code = fields.Char(related="product_id.default_code", string="Rif. Interno", readonly=True, store=False)
    uom_id = fields.Many2one(related="product_id.uom_id", string="U.M.", readonly=True, store=False)
    tipo_vetrina = fields.Selection(
        [
            ('inside', 'Interna'),
            ('outside', 'Esterna'),

        ],
        string='Tipo vetrina',
    )

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



    def action_apply_product_load(self, replace=True):
        """
        Carica tutte le righe x.product.load.line in sale.order.line.
        replace=True  -> rimpiazza le righe ordine
        replace=False -> aggiunge alle righe esistenti
        """
        for order in self:
            if not order.x_load_id:
                raise UserError(_("Seleziona un Caricamento Prodotti."))

            if replace:
                order.x_load_line_ids.unlink()

            # Creazione righe ordine
            for ll in order.x_load_id.line_ids:
                # usa new() + onchange per avere descrizione, tasse, uom coerenti con Odoo
                line = self.env["sale.order.x_load_line"].new({
                    "order_id": order.id,
                    "product_id": ll.product_id.id,
                    "product_uom_qty": ll.product_uom_qty or 1.0,
                })
                line._onchange_product_id()

                vals = line._convert_to_write(line._cache)

                # Override prezzo e nota da caricamento
                if ll.price_unit:
                    vals["price_unit"] = ll.price_unit
                vals["note"] = ll.note or False

                # opzionale: se vuoi la nota anche nel testo riga:
                # if ll.note:
                #     vals["name"] = (vals.get("name") or "") + "\n" + ll.note

                vals["order_id"] = order.id
                self.env["sale.order.x_load_line"].create(vals)

        return True



class SaleOrderXLoadLine(models.Model):
    _name = "sale.order.x_load_line"
    _description = "Righe Caricamento su Ordine di Vendita"
    _order = "sequence,id asc"

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

    sequence = fields.Integer(string="Sequenza", default=10, index=True)
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

    sale_line_id = fields.Many2one(
        "sale.order.line",
        compute="_compute_sale_line_id",
        store=False,
        string="Riga Ordine (mappata)",
    )
    editable = fields.Boolean(string="Edit", default=False)
    tipo_vetrina = fields.Selection(
        [
            ('inside', 'Interna'),
            ('outside', 'Esterna'),

        ],
        string='Tipo vetrina',
    )

    @api.onchange('uom_id', 'product_uom_height', 'product_uom_length')
    def product_uom_change(self):
        if not self.uom_id or not self.product_id:
            self.product_uom_qty = 0.0
            return
        self.product_uom_qty=self.product_uom_height*self.product_uom_length
    @api.onchange("product_id")
    def _onchange_product_id(self):
            for line in self:
                if not line.product_id:
                    # reset “soft”
                    line.supplier_id = False
                    if not line.product_uom_qty:
                        line.product_uom_qty = 1.0
                    return

                # qty default
                if not line.product_uom_qty:
                    line.product_uom_qty = 1.0

                # fornitore suggerito (primo vendor)
                # (Odoo 13: seller_ids è su product.template, ma su product.product esiste via related)
                seller = False
                # prova su product_id.seller_ids (di solito ok) altrimenti su template
                sellers = getattr(line.product_id, "seller_ids", False) or line.product_id.product_tmpl_id.seller_ids
                if sellers:
                    # prendi il primo vendor “utile” (puoi migliorare filtrando per company, qty, ecc.)
                    seller = sellers[0]
                line.supplier_id = seller.name if seller else False

                # prezzo: se l'utente lo ha già messo, non lo sovrascrivo
                if not line.price_unit:
                    order = line.order_id
                    qty = line.product_uom_qty or 1.0
                    product = line.product_id

                    # fallback: list_price
                    price = product.lst_price

                    # se ho un ordine con listino, provo a prendere il prezzo dal listino
                    if order and getattr(order, "pricelist_id", False):
                        pricelist = order.pricelist_id
                        partner = order.partner_id

                        # Tentativo 1: API moderna (get_product_price_rule)
                        if hasattr(pricelist, "get_product_price_rule"):
                            # ritorna (price, rule_id) o (rule_id, price) a seconda di implementazioni
                            res = pricelist.get_product_price_rule(product, qty, partner)
                            # gestisco entrambe le forme in modo safe
                            if isinstance(res, (list, tuple)) and len(res) >= 1:
                                # alcuni moduli: (price, rule_id)
                                if isinstance(res[0], (int, float)):
                                    price = res[0]
                                # altri: (rule_id, price)
                                elif len(res) > 1 and isinstance(res[1], (int, float)):
                                    price = res[1]

                        # Tentativo 2: API vecchia (price_get)
                        elif hasattr(pricelist, "price_get"):
                            # price_get ritorna dict {pricelist_id: price}
                            d = pricelist.price_get(product.id, qty, partner=partner.id if partner else False)
                            if isinstance(d, dict) and d.get(pricelist.id) is not None:
                                price = d[pricelist.id]

                    line.price_unit = price

                # prezzo extra: se vuoi che si azzeri al cambio prodotto (opzionale)
                if line.price_extra is False:
                    line.price_extra = 0.0
            # line.note = line.note  # non tocco la nota

    @api.depends("order_id", "order_id.order_line.product_id", "product_id")
    def _compute_sale_line_id(self):
        for line in self:
            if not line.order_id or not line.product_id:
                line.sale_line_id = False
                continue
            so_line = line.order_id.order_line.filtered(lambda l: l.product_id == line.product_id)[:1]
            line.sale_line_id = so_line

    def write(self, vals):
        #only_toggle = set(vals.keys()) <= {"editable"}

        #if 'editable' in vals.keys() and vals['editable']==True:
        #    locked = self.filtered(lambda r: not r.editable)
        #    if locked:
        #        raise UserError(_("Riga bloccata: abilita 'Edit' sulla singola riga per modificarla."))

        return super().write(vals)
    def unlink(self):
        #locked = self.filtered(lambda r: not r.editable)
        #if locked:
        #    raise UserError(_("Riga bloccata: abilita 'Edit' sulla singola riga per eliminarla."))
        return super().unlink()