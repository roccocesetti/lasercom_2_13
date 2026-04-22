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




class ProductCategory(models.Model):
    _inherit = "product.category"

    x_lavorazione = fields.Boolean(string="Lavorazione")

class Tag(models.Model):

    _name = "x.product.load.tag"
    _description = "product Tag"

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]



class ProductLoad(models.Model):
    _name = "x.product.load"
    _description = "Caricamento Prodotti"
    _order = "id desc"

    name = fields.Char(string="Riferimento", required=True, default=lambda self: self._default_name(), copy=True)
    note = fields.Text(string="Nota", copy=True)
    line_ids = fields.One2many("x.product.load.line", "load_id", string="Righe prodotti", copy=True)

    @api.model
    def _default_name(self):
        # semplice progressivo basato su sequenza; se non vuoi la sequenza, puoi mettere un default diverso
        return self.env["ir.sequence"].next_by_code("x.product.load") or "Nuovo"

    def action_add_section_line(self):
        self.ensure_one()
        max_seq = max(self.line_ids.mapped('sequence') or [0])
        self.write({
            'line_ids': [(0, 0, {
                'display_type': 'line_section',
                'name': '__________________________________________________',
                'sequence': max_seq + 10,
            })]
        })
        return True
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})

        # nome duplicato
        if not default.get("name"):
            default["name"] = _("%s (Copia)") % (self.name or "")

        return super(ProductLoad, self).copy(default)

    def action_duplicate(self):
        self.ensure_one()
        new_record = self.copy()
        return {
            "type": "ir.actions.act_window",
            "name": _("Duplicato"),
            "res_model": "x.product.load",
            "view_mode": "form",
            "res_id": new_record.id,
            "target": "current",
        }
class ProductLoadLine(models.Model):
    _name = "x.product.load.line"
    _description = "Riga Caricamento Prodotto"
    _order = "sequence,id asc"
    sequence = fields.Integer(string="Sequenza", default=10, index=True)
    load_id = fields.Many2one("x.product.load", string="Caricamento", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Prodotto", required=False)
    product_uom_height = fields.Float(string="Altezza", default=0.0)
    product_uom_length = fields.Float(string="Lunghezza", default=0.0)
    product_uom_width = fields.Float(string="Larghezza", default=0.0)
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
    display_type = fields.Selection([
        ('line_section', "Sezione"),

    ], default=False)
    name = fields.Char(string='Sezione')
    x_lavorazione = fields.Boolean(
        string="Lavorazione",
        related="product_id.categ_id.x_lavorazione",
        store=True,
        readonly=True,
    )
    tag_true = fields.Boolean(string="Etc", default=False,help="Etichetta obbligatoria")
    tag_ids = fields.Many2many('x.product.load.tag', 'x_product_load_line_rel', 'product_line_id', 'tag_id', string='Tags', help="Etichette")

    @api.onchange('uom_id', 'product_uom_height', 'product_uom_length')
    def product_uom_change(self):
        if not self.uom_id or not self.product_id:
            self.product_uom_qty = 0.0
            return
        self.product_uom_qty=self.product_uom_height*self.product_uom_length
        self.price_unit=self.product_id.standard_price

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("display_type") == "line_section":
                vals.update({
                    "product_id": False,
                    "product_uom_qty": 0.0,
                    "price_unit": 0.0,
                    "price_extra": 0.0,
                    "supplier_id": False,

                })
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("display_type") == "line_section":
            vals.update({
                "product_id": False,
                "product_uom_qty": 0.0,
                "price_unit": 0.0,
                "price_extra": 0.0,
                "supplier_id": False,

            })
        return super().write(vals)


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

    def _default_validity_date_2(self):
        if self.env['ir.config_parameter'].sudo().get_param('sale.use_quotation_validity_days'):
            days = self.env.company.quotation_validity_days
            if days > 0:
                return fields.Date.to_string(datetime.now() + timedelta(days))
        return False


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
    date_module = fields.Date(string='Data Modulo',  copy=False,
                                default=_default_validity_date_2)
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
            testata=True
            for ll in order.x_load_id.line_ids:
                # usa new() + onchange per avere descrizione, tasse, uom coerenti con Odoo
                if self.order_line and testata:
                    line = self.env["sale.order.x_load_line"].new({
                        "order_id": order.id,
                        "product_id": self.order_line[0].product_id.id,
                        "product_uom_qty": 1.0,
                        "price_unit": self.order_line[0].purchase_price,

                    })
                    line._onchange_product_id()
                    vals = line._convert_to_write(line._cache)
                    testata=False
                    self.env["sale.order.x_load_line"].create(vals)
                line = self.env["sale.order.x_load_line"].new({
                    "order_id": order.id,
                    "product_id": ll.product_id.id,
                    "product_uom_qty": ll.product_uom_qty or 1.0,
                    "product_uom_height": ll.product_uom_height,
                    "product_uom_length": ll.product_uom_length,
                    "product_uom_width": ll.product_uom_width,
                    "price_unit": ll.price_unit,
                    "price_extra": ll.price_extra,
                    "supplier_id": ll.supplier_id,
                    "editable": ll.editable,
                    "note": ll.note,
                    "display_type":ll.display_type,
                    "name": ll.name,
                    "x_lavorazione":ll.x_lavorazione,
                    "tag_true": ll.tag_true,
                    "tag_ids": [(6, 0, ll.tag_ids.ids)],
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
                vals['display_type']: ll.display_type
                self.env["sale.order.x_load_line"].create(vals)

        return True



    x_filter_tag_id = fields.Many2one(
        'x.product.load.tag',
        string='Filtra per etichetta'
    )
    x_load_line_filtered_ids = fields.Many2many(
        'sale.order.x_load_line',
        compute='_compute_x_load_line_filtered_ids',
        string='Righe filtrate'
    )
    @api.depends('x_load_line_ids', 'x_load_line_ids.tag_ids', 'x_filter_tag_id')
    def _compute_x_load_line_filtered_ids(self):
        for order in self:
            if order.x_filter_tag_id:
                order.x_load_line_filtered_ids = order.x_load_line_ids.filtered(
                    lambda l: order.x_filter_tag_id in l.tag_ids
                )
            else:
                order.x_load_line_filtered_ids = order.x_load_line_ids
    def action_refresh_tag_filter(self):
        self._compute_x_load_line_filtered_ids()
        return True
    x_tag_warning_visible = fields.Boolean(
        string='Mostra warning etichette',
        compute='_compute_x_tag_warning',
        store=False
    )

    x_tag_warning_message = fields.Html(
        string='Messaggio warning etichette',
        compute='_compute_x_tag_warning',
        sanitize=False,
        store=False
    )


    @api.depends(
        'x_load_line_ids',
        'x_load_line_ids.tag_ids',
        'x_load_line_ids.etichetta_si',
        'x_load_line_ids.display_type',
    )
    def _compute_x_tag_warning(self):
        for order in self:
            order.x_tag_warning_visible = False
            order.x_tag_warning_message = False

            conflicts = []
            lines = order.x_load_line_ids.filtered(lambda l: not l.display_type and l.tag_ids)

            yes_lines = lines.filtered(lambda l: l.etichetta_si == 'yes')

            for line in yes_lines:
                same_group_yes = yes_lines.filtered(
                    lambda l: l.id != line.id and bool(l.tag_ids & line.tag_ids)
                )
                if same_group_yes:
                    tags = ', '.join(line.tag_ids.mapped('name'))
                    conflicts.append(tags)

            if conflicts:
                unique_conflicts = sorted(set(conflicts))
                order.x_tag_warning_visible = True
                order.x_tag_warning_message = _(
                    "<div class='alert alert-danger' role='alert'>"
                    "<strong>Attenzione:</strong> esistono più righe con valore SI per lo stesso gruppo etichetta: %s"
                    "</div>"
                ) % ', '.join(unique_conflicts)

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
    product_id = fields.Many2one("product.product", string="Prodotto", required=False)
    product_uom_height = fields.Float(string="Alt", default=0.0)
    product_uom_length = fields.Float(string="Lung", default=0.0)
    product_uom_width = fields.Float(string="Prof", default=0.0)
    product_uom_qty = fields.Float(string="Qta", default=1.0)
    price_unit = fields.Float(string="PU")
    price_extra = fields.Float(string="PE")
    note = fields.Char(string="Nota")
    supplier_id = fields.Many2one("res.partner", string="For", required=False)
    default_code = fields.Char(related="product_id.default_code", string="Codice", readonly=True, store=False)
    uom_id = fields.Many2one(related="product_id.uom_id", string="U.M.", readonly=True, store=False)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='T.riga', readonly=True, store=True)

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
        string='T.vetr.',
    )
    x_lavorazione = fields.Boolean(
        string="Lav",
        related="product_id.categ_id.x_lavorazione",
        store=True,
        readonly=True,
    )
    tag_true = fields.Boolean(string="Etc", default=False,help="Etichetta obbligatoria")
    tag_ids = fields.Many2many('x.product.load.tag', 'sale_order_x_load_line_rel', 'product_line_id', 'tag_id', string='Tags', help="Etichette")


    x_tag_visible = fields.Boolean(
        string='Visibile filtro tag',
        compute='_compute_x_tag_visible',
        store=False
    )
    etichetta_si = fields.Selection(
        [
            ('yes', 'SI'),
            ('no', 'NO'),

        ],
        string='SI/NO',default='no'
    )

    @api.depends('tag_ids', 'order_id.x_filter_tag_id')
    def _compute_x_tag_visible(self):
        for line in self:
            if not line.order_id.x_filter_tag_id:
                line.x_tag_visible = True
            else:
                line.x_tag_visible = line.order_id.x_filter_tag_id in line.tag_ids

    @api.constrains('tag_true', 'tag_ids')
    def _check_tag_ids_required(self):
        for rec in self:
            if rec.tag_true and not rec.tag_ids:
                raise ValidationError(_("Il campo Tags è obbligatorio quando Edit è attivo."))
    @api.onchange('uom_id', 'product_uom_height', 'product_uom_length')
    def product_uom_change(self):
        if not self.uom_id or not self.product_id:
            self.product_uom_qty = 0.0
            return
        self.product_uom_qty=self.product_uom_height*self.product_uom_length
        self.price_unit=self.product_id.standard_price
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
                    price = product.standard_price

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

                    line.price_unit = product.standard_price

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




    display_type = fields.Selection([
        ('line_section', "Sezione"),

    ], default=False)
    name = fields.Char(string='S.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("display_type") == "line_section":
                vals.update({
                    "product_id": False,
                    "product_uom_qty": 0.0,
                    "price_unit": 0.0,
                    "price_extra": 0.0,
                    "supplier_id": False,
                    "editable": False,
                })
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("display_type") == "line_section":
            vals.update({
                "product_id": False,
                "product_uom_qty": 0.0,
                "price_unit": 0.0,
                "price_extra": 0.0,
                "supplier_id": False,
                "editable": False,
            })
        else:
            protected_fields = {
                'tag_ids',
                'etichetta_si',
                'product_id',
                'product_uom_qty',
                'price_unit',
                'discount',
                'price_extra'
            }
            if protected_fields.intersection(vals.keys()):
                for rec in self:
                    rec._compute_x_locked_by_tag()
                    if rec.x_locked_by_tag:
                        raise ValidationError(
                            _("Non puoi modificare una riga NO se nel gruppo esiste già una riga SI.")
                        )


        return super(SaleOrderXLoadLine,self).write(vals)





    def _tag_signature(self):
        self.ensure_one()
        return tuple(sorted(self.tag_ids.ids))


    x_locked_by_tag = fields.Boolean(
        string='Bloccata da etichetta',
        compute='_compute_x_locked_by_tag',
        store=False
    )

    @api.depends(
        'etichetta_si',
        'tag_ids',
        'display_type',
        'order_id.x_load_line_ids.etichetta_si',
        'order_id.x_load_line_ids.tag_ids',
        'order_id.x_load_line_ids.display_type',
    )
    def _compute_x_locked_by_tag(self):
        for rec in self:
            rec.x_locked_by_tag = False

            if rec.display_type or not rec.order_id or not rec.tag_ids:
                continue

            gruppo = rec.order_id.x_load_line_ids.filtered(
                lambda l: l.id != rec.id
                and not l.display_type
                and l.tag_ids
                and bool(l.tag_ids & rec.tag_ids)
            )

            has_si = any(l.etichetta_si == 'yes' for l in gruppo)

            rec.x_locked_by_tag = (
                rec.etichetta_si != 'yes'
                and has_si
            )

    @api.constrains('etichetta_si', 'tag_ids', 'order_id', 'display_type')
    def _check_unique_si_per_tag_group(self):
        for rec in self:
            if rec.display_type or not rec.order_id or not rec.tag_ids:
                continue

            if rec.etichetta_si != 'yes':
                continue

            righe_conflitto = rec.order_id.x_load_line_ids.filtered(
                lambda l: l.id != rec.id
                and not l.display_type
                and l.etichetta_si == 'yes'
                and l.tag_ids
                and bool(l.tag_ids & rec.tag_ids)
            )

            if righe_conflitto:
                raise ValidationError(
                    _("Può esistere una sola riga SI per gruppo con la stessa etichetta.")  )



