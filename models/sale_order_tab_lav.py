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
from collections import defaultdict
_logger = logging.getLogger(__name__)




class ProductCategory(models.Model):
    _inherit = "product.category"

    x_lavorazione = fields.Boolean(string="Lavorazione")

class Producttemplate(models.Model):
    _inherit = "product.template"

    x_load_id = fields.Many2one(
        "x.product.load",
        string="Modulo Caricamento Prodotti",
    )


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
    price_unit = fields.Float(string="Prezzo Unitario",digits='Product Price')
    price_extra = fields.Float(string="Prezzo Extra",digits='Product Price')
    supplier_id = fields.Many2one("res.partner", string="Fornitore", required=False)
    editable = fields.Boolean(string="Edit", default=True)
    # Nota riga (se serve anche per ogni prodotto)
    note = fields.Char(string="Nota riga")

    # Campi utili “related” per vedere info del prodotto senza duplicarle
    default_code = fields.Char(related="product_id.default_code", string="Rif. Interno", readonly=True, store=False)
    uom_id = fields.Many2one(related="product_id.uom_id", string="U.M.", readonly=True, store=False)
    tipo_vetrina = fields.Selection(
        [
            ('blank', 'Riga in bianco'),
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


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    x_load_id = fields.Many2one(
        comodel_name="x.product.load",
        string="Caricamento Prodotti",
    )

    @api.onchange("product_id", "product_uom_qty")
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()

        for line in self:
            product_tmpl = line.product_id.product_tmpl_id if line.product_id else False
            if not product_tmpl:
                line.x_load_id = False
                continue

            optional_products = getattr(product_tmpl, "optional_product_ids", False)

            if optional_products and product_tmpl.x_load_id:
                line.x_load_id = product_tmpl.x_load_id
            else:
                line.x_load_id = False

        return res
class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _default_validity_date_2(self):
        if self.env['ir.config_parameter'].sudo().get_param('sale.use_quotation_validity_days'):
            days = self.env.company.quotation_validity_days
            if days > 0:
                return fields.Date.to_string(datetime.now() + timedelta(days))
        return False

    @api.depends(
        'x_load_line_ids',
        'x_load_line_ids.etichetta_si',
        'x_load_line_ids.price_subtotal',
        'x_load_line_ids.product_uom_qty',
        'x_load_line_ids.price_unit',
        'x_load_line_ids.price_extra',
        'sale_acq_usage'
    )
    def _compute_amount_lav(self):
        """
        Compute the amounts of the SO line.
        """
        for order in self:
            price_subtotal_lav=0.00
            for line in order.x_load_line_ids:
                if line.etichetta_si=="yes":
                        price_subtotal_lav+=line.price_subtotal


            order.price_subtotal_lav = price_subtotal_lav+order.sale_acq_usage

    x_load_ids = fields.Many2many(
        comodel_name="x.product.load",
        relation="sale_order_x_product_load_rel",
        column1="sale_order_id",
        column2="product_load_id",
        string="Caricamenti Prodotti",

    )
    note_modulo_agente = fields.Char(string='Note agente ', required=False, copy=False, readonly=False, default='', )
    note_modulo_installazione = fields.Char(string='Note installazione ', required=False, copy=False, readonly=False, default='', )

    x_show_manager_fields = fields.Boolean(
        string="Mostra campi riservati al manager",
        compute="_compute_x_show_manager_fields",
    )

    def _compute_x_show_manager_fields(self):
        is_manager = (
            self.env.user.has_group('sales_team.group_sale_manager')
            or self.env.user.has_group('lasercom_2_13.group_admin_lav')
        )
        for order in self:
            order.x_show_manager_fields = is_manager

    def _sync_x_load_ids_from_order_lines(self):
        for order in self:
            load_ids = []

            for line in order.order_line:
                if line.display_type:
                    continue

                load = line.x_load_id

                if not load and line.product_id:
                    load = line.product_id.product_tmpl_id.x_load_id
                    line.x_load_id = load

                if load:
                    load_ids.append(load.id)

            load_ids = list(dict.fromkeys(load_ids))

            if load_ids:
                order.x_load_ids = [(6, 0, load_ids)]
            else:
                order.x_load_ids = [(5, 0, 0)]

    @api.onchange("order_line")
    def _onchange_order_line_sync_x_load_ids(self):
        self._sync_x_load_ids_from_order_lines()
        #self.action_apply_product_load()

    def _rebuild_x_load_lines_from_loads(self):
        for order in self:
            commands = [(5, 0, 0)]
            sequence = 10

            lines = order.order_line.filtered(
                lambda l: not l.display_type and l.x_load_id
            )

            # Raggruppo per modulo x_load_id, sommando le quantità
            qty_by_load = {}

            for so_line in lines:
                load = so_line.x_load_id
                if not load:
                    continue

                if load.id not in qty_by_load:
                    qty_by_load[load.id] = {
                        "load": load,
                        "qty": 0.0,
                        "first_sale_line": so_line,
                    }

                qty_by_load[load.id]["qty"] += so_line.product_uom_qty or 0.0

            for data in qty_by_load.values():
                load = data["load"]
                qta_multi = data["qty"]
                first_sale_line = data["first_sale_line"]

                # Riga di testata derivata dalla riga ordine
                commands.append((0, 0, {
                    "x_load_id": load.id,
                    "sequence": sequence,
                    "product_id": first_sale_line.product_id.id if first_sale_line.product_id else False,
                    "product_uom_qty": qta_multi,
                    "price_unit": first_sale_line.purchase_price or 0.0,
                    "name": first_sale_line.name,
                }))
                sequence += 10

                # Righe del modulo caricamento prodotti
                for ll in load.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
                    commands.append((0, 0, {
                        "x_load_id": load.id,
                        "sequence": sequence,
                        "display_type": ll.display_type,
                        "name": ll.name or (ll.product_id.display_name if ll.product_id else False),
                        "name": ll.name or (ll.product_id.display_name if ll.product_id else False),
                        "tag_true": ll.tag_true,
                        "tag_ids": [(6, 0, ll.tag_ids.ids)],
                        "editable": ll.editable,
                        "tipo_vetrina": ll.tipo_vetrina,
                        "product_id": ll.product_id.id if ll.product_id else False,
                        "x_lavorazione": ll.x_lavorazione,
                        "product_uom_height": ll.product_uom_height,
                        "product_uom_length": ll.product_uom_length,
                        "product_uom_width": ll.product_uom_width,
                        "product_uom_qty": 0.0 if ll.display_type else (ll.product_uom_qty or 0.0) * qta_multi,
                        "price_unit": 0.0 if ll.display_type else ll.price_unit,
                        "price_extra": 0.0 if ll.display_type else ll.price_extra,
                        "supplier_id": ll.supplier_id.id if ll.supplier_id and not ll.display_type else False,
                        "note": ll.note,
                    }))
                    sequence += 10

            order.x_load_line_ids = commands

    def action_apply_product_load(self, replace=True):
        SaleOrderXLoadLine = self.env["sale.order.x_load_line"].sudo()

        for order in self:
            if not order.id or not isinstance(order.id, int):
                raise UserError(_("Salva prima il preventivo prima di applicare il caricamento prodotti."))

            order_lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id
            ).sorted(key=lambda l: (l.sequence, l.id))

            if not order_lines:
                raise UserError(_("Non sono presenti righe prodotto nell'ordine."))

            def _get_optional_products(line):
                template = line.product_id.product_tmpl_id if line.product_id else False
                if not template:
                    return self.env["product.product"]
                return getattr(template, "optional_product_ids", self.env["product.product"])

            def _get_line_load(line):
                if line.x_load_id:
                    return line.x_load_id

                template = line.product_id.product_tmpl_id if line.product_id else False
                if template and template.x_load_id:
                    return template.x_load_id

                return self.env["x.product.load"]

            def _is_main_line(line):
                return bool(_get_optional_products(line) and _get_line_load(line))

            main_lines = order_lines.filtered(lambda l: _is_main_line(l))
            if not main_lines:
                raise UserError(_("Nessuna riga ordine contiene un prodotto principale con modulo di caricamento."))

            if replace and order.x_load_line_ids:
                order.x_load_line_ids.unlink()

            sequence = 10
            current_main_line = False
            current_generated_by_product = {}
            current_optional_counter = defaultdict(int)

            for so_line in order_lines:
                product = so_line.product_id
                qty = so_line.product_uom_qty or 0.0

                if qty <= 0.0:
                    raise UserError(
                        _("La quantità del prodotto '%s' deve essere maggiore di zero.") % product.display_name)

                if _is_main_line(so_line):
                    current_main_line = so_line
                    current_generated_by_product = {}
                    current_optional_counter = defaultdict(int)

                    load = _get_line_load(so_line)

                    if not load.line_ids:
                        raise UserError(_(
                            "Il modulo di caricamento '%s' collegato al prodotto '%s' non contiene righe."
                        ) % (
                                            load.display_name,
                                            product.display_name,
                                        ))

                    # Riga testata prodotto principale
                    SaleOrderXLoadLine.create({
                        "order_id": order.id,
                        "x_load_id": load.id,
                        "sequence": sequence,
                        "product_id": product.id,
                        "product_uom_qty": qty,
                        "price_unit": so_line.purchase_price or 0.0,
                        "price_extra": 0.0,
                        "name": so_line.name,
                        "editable": False,
                        "etichetta_si": "yes",
                        "product_cassetti_slave": False
                    })
                    sequence += 10

                    # Righe modulo caricamento
                    for ll in load.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
                        vals = {
                            "order_id": order.id,
                            "x_load_id": load.id,
                            "sequence": sequence,
                            "display_type": ll.display_type,
                            "name": ll.name or (ll.product_id.display_name if ll.product_id else False),
                            "product_id": ll.product_id.id if ll.product_id and not ll.display_type else False,
                            "product_uom_height": ll.product_uom_height,
                            "product_uom_length": ll.product_uom_length,
                            "product_uom_width": ll.product_uom_width,
                            "product_uom_qty": 0.0 if ll.display_type else (ll.product_uom_qty or 0.0) * qty,
                            "price_unit": 0.0 if ll.display_type else (ll.product_id.standard_price or 0.0),
                            "price_extra": 0.0 if ll.display_type else (ll.price_extra or 0.0),
                            "supplier_id": ll.supplier_id.id if ll.supplier_id and not ll.display_type else False,
                            "editable": ll.editable,
                            "tipo_vetrina": ll.tipo_vetrina,
                            "note": ll.note,
                            "x_lavorazione": ll.x_lavorazione,
                            "tag_true": ll.tag_true,
                            "tag_ids": [(6, 0, ll.tag_ids.ids)],
                            "product_cassetti_slave": False
                        }

                        created_line = SaleOrderXLoadLine.create(vals)

                        if created_line.product_id and not created_line.display_type:
                            current_generated_by_product.setdefault(
                                created_line.product_id.product_tmpl_id.id,
                                created_line
                            )

                        sequence += 10

                    continue

                # Riga accessoria/successiva
                if not current_main_line:
                    continue

                product_key = product.product_tmpl_id.id

                current_optional_counter[product_key] += 1
                if current_optional_counter[product_key] > 1:
                    raise UserError(_(
                        "Nel blocco del prodotto principale '%s' il prodotto '%s' "
                        "è stato inserito più di una volta."
                    ) % (
                                        current_main_line.product_id.display_name,
                                        product.display_name,
                                    ))

                target_line = current_generated_by_product.get(product_key)

                if target_line:
                    target_line.write({
                        "product_uom_qty": (target_line.product_uom_qty or 0.0) * qty,
                        "etichetta_si": "yes",
                        "tipo_vetrina": False,
                        "editable": True,
                    })

            order._compute_amount_lav()
        return True

    def action_apply_product_load_old4(self, replace=True):
        """
        Genera le righe sale.order.x_load_line partendo dalle righe ordine.

        Regole:
        - solo i prodotti principali generano il modulo;
        - un prodotto principale è una riga con x_load_id e optional_product_ids;
        - le righe successive non principali sommano quantità alle righe generate;
        - se nello stesso blocco un prodotto successivo è ripetuto, viene bloccato.
        """
        SaleOrderXLoadLine = self.env["sale.order.x_load_line"]

        for order in self:
            if not order.id or not isinstance(order.id, int):
                raise UserError(_("Salva prima il preventivo prima di applicare il caricamento prodotti."))

            order_lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id
            ).sorted(key=lambda l: (l.sequence, l.id))

            if not order_lines:
                raise UserError(_("Non sono presenti righe prodotto nell'ordine."))

            def _get_optional_products(line):
                template = line.product_id.product_tmpl_id if line.product_id else False
                if not template:
                    return self.env["product.product"]
                return getattr(template, "optional_product_ids", self.env["product.product"])

            def _get_line_load(line):
                """
                Recupera il modulo caricamento:
                - prima dalla riga ordine;
                - se vuoto, dal template prodotto.
                Non scrive nulla sulla riga ordine.
                """
                if line.x_load_id:
                    return line.x_load_id

                template = line.product_id.product_tmpl_id if line.product_id else False
                if template and template.x_load_id:
                    return template.x_load_id

                return self.env["x.product.load"]

            def _is_main_line(line):
                """
                Riga principale = prodotto che contiene optional_product_ids
                e che ha un modulo x_load_id, anche recuperato dal template.
                """
                return bool(_get_optional_products(line) and _get_line_load(line))






            if replace and order.x_load_line_ids:
                order.x_load_line_ids.unlink()

            sequence = 10
            current_main_line = False
            current_generated_by_product = {}
            current_optional_counter = defaultdict(int)

            for so_line in order_lines:
                product = so_line.product_id
                qty = so_line.product_uom_qty or 0.0

                if qty <= 0.0:
                    raise UserError(
                        _("La quantità del prodotto '%s' deve essere maggiore di zero.") % product.display_name)

                if _is_main_line(so_line):
                    current_main_line = so_line
                    current_generated_by_product = {}
                    current_optional_counter = defaultdict(int)

                    load = so_line.x_load_id

                    SaleOrderXLoadLine.create({
                        "order_id": order.id,
                        "x_load_id": load.id,
                        "sequence": sequence,
                        "product_id": product.id,
                        "product_uom_qty": qty,
                        "price_unit": so_line.purchase_price or 0.0,
                        "price_extra": 0.0,
                        "name": so_line.name,
                        "editable": False,
                    })
                    sequence += 10

                    for ll in load.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
                        vals = {
                            "order_id": order.id,
                            "x_load_id": load.id,
                            "sequence": sequence,
                            "display_type": ll.display_type,
                            "name": ll.name or (ll.product_id.display_name if ll.product_id else False),
                            "product_id": ll.product_id.id if ll.product_id and not ll.display_type else False,
                            "product_uom_height": ll.product_uom_height,
                            "product_uom_length": ll.product_uom_length,
                            "product_uom_width": ll.product_uom_width,
                            "product_uom_qty": 0.0 if ll.display_type else (ll.product_uom_qty or 0.0) * qty,
                            "price_unit": 0.0 if ll.display_type else (ll.price_unit or 0.0),
                            "price_extra": 0.0 if ll.display_type else (ll.price_extra or 0.0),
                            "supplier_id": ll.supplier_id.id if ll.supplier_id and not ll.display_type else False,
                            "editable": ll.editable,
                            "tipo_vetrina": ll.tipo_vetrina,
                            "note": ll.note,
                            "x_lavorazione": ll.x_lavorazione,
                            "tag_true": ll.tag_true,
                            "tag_ids": [(6, 0, ll.tag_ids.ids)],
                        }

                        created_line = SaleOrderXLoadLine.create(vals)

                        if created_line.product_id and not created_line.display_type:
                            current_generated_by_product.setdefault(
                                created_line.product_id.product_tmpl_id.id,
                                created_line
                            )

                        sequence += 10

                    continue

                # Riga successiva/non principale.
                if not current_main_line:
                    continue

                product_key = product.product_tmpl_id.id

                current_optional_counter[product_key] += 1
                if current_optional_counter[product_key] > 1:
                    raise UserError(_(
                        "Nel blocco del prodotto principale '%s' il prodotto '%s' "
                        "è stato inserito più di una volta."
                    ) % (
                                        current_main_line.product_id.display_name,
                                        product.display_name,
                                    ))

                target_line = current_generated_by_product.get(product_key)

                if target_line:
                    target_line.write({
                        "product_uom_qty": (target_line.product_uom_qty or 0.0) + qty,
                    })

        return True
    def action_apply_product_load_old3(self, replace=True):
        """
        Carica le righe di lavorazione su sale.order.x_load_line.

        Regole:
        - solo le righe ordine che hanno x_load_id generano il modulo;
        - le righe ordine senza x_load_id non vengono aggiunte come righe nuove;
        - le righe senza x_load_id incrementano la quantità della riga generata
          con lo stesso product_id;
        - il controllo duplicati viene fatto per blocco, cioè tra un prodotto
          con x_load_id e il successivo prodotto con x_load_id.
        """
        SaleOrderXLoadLine = self.env["sale.order.x_load_line"]

        for order in self:
            if not order.id or not isinstance(order.id, int):
                raise UserError(_("Salva prima il preventivo prima di applicare il caricamento prodotti."))

            order_lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id
            ).sorted(key=lambda l: (l.sequence, l.id))

            if not order_lines:
                raise UserError(_("Non sono presenti righe prodotto nell'ordine."))

            # Recupero x_load_id dal prodotto, se non già valorizzato sulla riga ordine
            for so_line in order_lines:
                if not so_line.x_load_id and so_line.product_id.product_tmpl_id.x_load_id:
                    so_line.x_load_id = so_line.product_id.product_tmpl_id.x_load_id

            main_lines = order_lines.filtered(lambda l: l.x_load_id)
            if not main_lines:
                raise UserError(_(
                    "Nessuna riga ordine contiene un modulo di caricamento prodotti."
                ))

            if replace and order.x_load_line_ids:
                order.x_load_line_ids.unlink()

            sequence = 10

            current_main_line = False
            current_generated_by_product = {}
            current_optional_counter = defaultdict(int)

            for so_line in order_lines:
                product = so_line.product_id
                qty = so_line.product_uom_qty or 0.0

                if qty <= 0.0:
                    raise UserError(_(
                        "La quantità del prodotto '%s' deve essere maggiore di zero."
                    ) % product.display_name)

                # CASO 1: riga ordine principale, cioè con modulo x_load_id
                if so_line.x_load_id:
                    current_main_line = so_line
                    current_generated_by_product = {}
                    current_optional_counter = defaultdict(int)

                    load = so_line.x_load_id

                    # Riga testata del prodotto principale
                    SaleOrderXLoadLine.create({
                        "order_id": order.id,
                        "x_load_id": load.id,
                        "sequence": sequence,
                        "product_id": product.id,
                        "product_uom_qty": qty,
                        "price_unit": so_line.purchase_price or 0.0,
                        "price_extra": 0.0,
                        "name": so_line.name,
                        "editable": False,
                    })
                    sequence += 10

                    # Righe del modulo caricamento
                    for ll in load.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
                        vals = {
                            "order_id": order.id,
                            "x_load_id": load.id,
                            "sequence": sequence,
                            "display_type": ll.display_type,
                            "name": ll.name or (ll.product_id.display_name if ll.product_id else False),
                            "product_id": ll.product_id.id if ll.product_id and not ll.display_type else False,
                            "product_uom_height": ll.product_uom_height,
                            "product_uom_length": ll.product_uom_length,
                            "product_uom_width": ll.product_uom_width,

                            # Quantità base del modulo moltiplicata per la quantità della riga principale
                            "product_uom_qty": 0.0 if ll.display_type else (ll.product_uom_qty or 0.0) * qty,

                            "price_unit": 0.0 if ll.display_type else (ll.price_unit or 0.0),
                            "price_extra": 0.0 if ll.display_type else (ll.price_extra or 0.0),
                            "supplier_id": ll.supplier_id.id if ll.supplier_id and not ll.display_type else False,
                            "editable": ll.editable,
                            "tipo_vetrina": ll.tipo_vetrina,
                            "note": ll.note,
                            "x_lavorazione": ll.x_lavorazione,
                            "tag_true": ll.tag_true,
                            "tag_ids": [(6, 0, ll.tag_ids.ids)],
                        }

                        created_line = SaleOrderXLoadLine.create(vals)

                        # Mappa prodotto -> riga generata.
                        # Serve per sommare le quantità delle righe ordine senza x_load_id.
                        if created_line.product_id and not created_line.display_type:
                            current_generated_by_product.setdefault(
                                created_line.product_id.id,
                                created_line
                            )

                        sequence += 10

                    continue

                # CASO 2: riga ordine senza x_load_id.
                # Non viene aggiunta come nuova riga: aggiorna solo quantità.
                if not current_main_line:
                    # Riga senza modulo prima di qualsiasi prodotto principale: la ignoro.
                    # Se preferisci bloccarla, sostituisci con UserError.
                    continue

                current_optional_counter[product.id] += 1
                if current_optional_counter[product.id] > 1:
                    raise UserError(_(
                        "Nel blocco del prodotto principale '%s' il prodotto '%s' "
                        "è stato inserito più di una volta."
                    ) % (
                                        current_main_line.product_id.display_name,
                                        product.display_name,
                                    ))

                target_line = current_generated_by_product.get(product.id)

                if not target_line:
                    raise UserError(_(
                        "Il prodotto '%s' è presente nelle righe ordine senza modulo di caricamento, "
                        "ma non esiste una riga corrispondente nel modulo '%s' del prodotto principale '%s'.\n"
                        "Non è quindi possibile sommare la quantità."
                    ) % (
                                        product.display_name,
                                        current_main_line.x_load_id.display_name,
                                        current_main_line.product_id.display_name,
                                    ))

                target_line.write({
                    "product_uom_qty": (target_line.product_uom_qty or 0.0) + qty,
                })

        return True

    def action_apply_product_load_old2(self, replace=True):
        SaleOrderXLoadLine = self.env["sale.order.x_load_line"]

        for order in self:
            if not order.id or not isinstance(order.id, int):
                raise UserError(_("Salva prima il preventivo prima di applicare il caricamento prodotti."))

            order_lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id
            )

            if not order_lines:
                raise UserError(_("Non sono presenti righe prodotto nell'ordine."))

            for so_line in order_lines:
                if not so_line.x_load_id and so_line.product_id.product_tmpl_id.x_load_id:
                    so_line.x_load_id = so_line.product_id.product_tmpl_id.x_load_id

            missing_load_lines = order_lines.filtered(lambda l: not l.x_load_id)
            if missing_load_lines:
                products = "\n".join(
                    "- %s" % (line.product_id.display_name or line.name)
                    for line in missing_load_lines
                )
                raise UserError(_(
                    "I seguenti prodotti dell'ordine non hanno un modulo di caricamento prodotti collegato:\n%s"
                ) % products)

            # NUOVO CONTROLLO PER BLOCCHI DI OPZIONALI
            order._check_optional_product_blocks()

            if replace and order.x_load_line_ids:
                order.x_load_line_ids.unlink()

            sequence = 10

            for so_line in order_lines.sorted(key=lambda l: (l.sequence, l.id)):
                load = so_line.x_load_id
                multiplier_qty = so_line.product_uom_qty or 0.0

                if multiplier_qty <= 0.0:
                    raise UserError(_(
                        "La quantità del prodotto '%s' deve essere maggiore di zero."
                    ) % so_line.product_id.display_name)

                SaleOrderXLoadLine.create({
                    "order_id": order.id,
                    "x_load_id": load.id,
                    "sequence": sequence,
                    "product_id": so_line.product_id.id,
                    "product_uom_qty": multiplier_qty,
                    "price_unit": so_line.purchase_price or 0.0,
                    "price_extra": 0.0,
                    "name": so_line.name,
                    "editable": False,
                })
                sequence += 10

                for ll in load.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
                    SaleOrderXLoadLine.create({
                        "order_id": order.id,
                        "x_load_id": load.id,
                        "sequence": sequence,
                        "display_type": ll.display_type,
                        "name": ll.name or (ll.product_id.display_name if ll.product_id else False),
                        "product_id": ll.product_id.id if ll.product_id and not ll.display_type else False,
                        "product_uom_height": ll.product_uom_height,
                        "product_uom_length": ll.product_uom_length,
                        "product_uom_width": ll.product_uom_width,

                        # quantità riga modulo moltiplicata per quantità riga ordine
                        "product_uom_qty": 0.0 if ll.display_type else (ll.product_uom_qty or 0.0) * multiplier_qty,

                        "price_unit": 0.0 if ll.display_type else (ll.price_unit or 0.0),
                        "price_extra": 0.0 if ll.display_type else (ll.price_extra or 0.0),
                        "supplier_id": ll.supplier_id.id if ll.supplier_id and not ll.display_type else False,
                        "editable": ll.editable,
                        "tipo_vetrina": ll.tipo_vetrina,
                        "note": ll.note,
                        "tag_true": ll.tag_true,
                        "tag_ids": [(6, 0, ll.tag_ids.ids)],
                    })
                    sequence += 10

        return True
    def action_apply_product_load_old(self, replace=True):
        """
        Carica tutte le righe x.product.load.line in sale.order.line.
        replace=True  -> rimpiazza le righe ordine
        replace=False -> aggiunge alle righe esistenti
        """

        for order in self:
            #if not order.x_load_ids:
            #   raise UserError(_("Seleziona un Caricamento Prodotti."))
            if not order.id or not isinstance(order.id, int):
                raise UserError(_("Salva prima il preventivo prima di applicare il caricamento prodotti."))
            if replace:
                if  order.x_load_line_ids:
                    order.x_load_line_ids.unlink()

            # Creazione righe ordine
            testata = True
            for x_load_id in order.x_load_ids:
                for ll in x_load_id.line_ids:
                    # usa new() + onchange per avere descrizione, tasse, uom coerenti con Odoo
                    if self.order_line and testata:
                        line = self.env["sale.order.x_load_line"].new({
                            "order_id": order.id,
                            "product_id": self.order_line[0].product_id.id,
                            "product_uom_qty": 1.0,
                            "price_unit": self.order_line[0].purchase_price,
                            "x_load_id": x_load_id.id

                        })
                        line._onchange_product_id()
                        vals = line._convert_to_write(line._cache)
                        testata = False
                        self.env["sale.order.x_load_line"].create(vals)
                    line = self.env["sale.order.x_load_line"].new({
                        "order_id": order.id,
                        "x_load_id": x_load_id.id,
                        "product_id": ll.product_id.id,
                        "product_uom_qty": ll.product_uom_qty or 1.0,
                        "product_uom_height": ll.product_uom_height,
                        "product_uom_length": ll.product_uom_length,
                        "product_uom_width": ll.product_uom_width,
                        "price_unit": ll.price_unit,
                        "price_extra": ll.price_extra,
                        "supplier_id": ll.supplier_id,
                        "editable": ll.editable,
                        "tipo_vetrina": ll.tipo_vetrina,
                        "note": ll.note,
                        "display_type": ll.display_type,
                        "name": ll.name,
                        "x_lavorazione": ll.x_lavorazione,
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



    def _check_optional_product_blocks(self):
        """
        Controlla le righe ordine per blocchi.

        Un blocco inizia quando viene incontrato un prodotto che ha optional_product_ids.
        Le righe successive, fino al prossimo prodotto con optional_product_ids,
        sono considerate prodotti opzionali del prodotto principale precedente.

        Regole:
        - il prodotto opzionale deve appartenere agli optional_product_ids del prodotto principale;
        - lo stesso prodotto opzionale non può comparire più di una volta nello stesso blocco.
        """
        for order in self:
            current_main_line = False
            current_allowed_optional_ids = set()
            current_optional_counter = defaultdict(int)

            def flush_current_block():
                """
                Valida il blocco corrente prima di aprirne uno nuovo.
                """
                if not current_main_line:
                    return

                duplicated_ids = [
                    product_id
                    for product_id, count in current_optional_counter.items()
                    if count > 1
                ]

                if duplicated_ids:
                    duplicated_products = self.env["product.product"].browse(duplicated_ids)
                    duplicated_names = "\n".join(
                        "- %s" % product.display_name
                        for product in duplicated_products
                    )
                    raise UserError(_(
                        "Nel blocco del prodotto principale '%s' ci sono prodotti opzionali ripetuti:\n%s"
                    ) % (current_main_line.product_id.display_name, duplicated_names))

            order_lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id
            ).sorted(key=lambda l: (l.sequence, l.id))

            for so_line in order_lines:
                product = so_line.product_id
                template = product.product_tmpl_id

                optional_products = getattr(template, "optional_product_ids", False)

                # Nuovo prodotto principale: chiudo il blocco precedente e apro il nuovo.
                if optional_products:
                    flush_current_block()

                    current_main_line = so_line
                    current_allowed_optional_ids = set(optional_products.ids)
                    current_optional_counter = defaultdict(int)
                    continue

                # Se non c'è ancora un prodotto principale, ignoro il prodotto.
                # In alternativa si può bloccare, ma per ora lo lasciamo passare.
                if not current_main_line:
                    continue


                current_optional_counter[product.id] += 1

            # Valido anche l'ultimo blocco
            flush_current_block()
    x_load_line_ids = fields.One2many(
        "sale.order.x_load_line",
        "order_id",
        string="Righe Caricamento (in ordine)",
        copy=False,
    )


    price_subtotal_lav = fields.Monetary(compute='_compute_amount_lav', string='Totale costi installazione', readonly=True, store=True)
    date_module = fields.Date(string='Consegna Richiesta dal Cliente',  copy=False,
                                default=_default_validity_date_2)
    date_installation = fields.Date(string='Installazione prevista il',  copy=False,
                                default=_default_validity_date_2)



    date_installation_display = fields.Char(
        string="Mese previsto per l'installazione",
        compute="_compute_date_installation_display",
    )

    @api.depends("date_installation_display","date_installation")
    def _compute_date_installation_display(self):
        for record in self:
            record.date_installation_display = (
                record.date_installation.strftime("%m/%Y")
                if record.date_installation
                else False
            )

    date_module_display = fields.Char(
        string="Mese previsto per la consegna",
        compute="_compute_date_module_display",
    )

    @api.onchange("date_module")
    def _onchange_period_date(self):
        if self.date_module:
            self.date_module = self.date_module.replace(day=1)


    @api.depends("date_module_display","date_module")
    def _compute_date_module_display(self):
        for record in self:
            record.date_module_display = (
                record.date_module.strftime("%m/%Y")
                if record.date_module
                else False
            )

    #@api.onchange("company_id")
    #def _onchange_company_id_set_default_load(self):
    #    for order in self:
    #        if not order.x_load_ids and order.company_id.x_default_product_load_id:
    #            order.x_load_ids = [(6, 0, [order.company_id.x_default_product_load_id.id])]
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

    def _check_unique_si_per_tag_group_on_order(self):
        """
        Controlla che, per ogni gruppo tag, esista una sola riga con etichetta_si = 'yes'.
        Controllo da eseguire sul salvataggio dell'ordine, non come constraint globale.
        """
        for order in self:
            checked_tags = set()

            lines = order.x_load_line_ids.filtered(
                lambda l: not l.display_type
                          and l.etichetta_si == 'yes'
                          and l.tag_ids
            )

            for line in lines:
                for tag in line.tag_ids:
                    if tag.id in checked_tags:
                        continue

                    same_tag_yes_lines = lines.filtered(
                        lambda l: tag in l.tag_ids
                    )

                    if len(same_tag_yes_lines) > 1:
                        product_names = "\n".join(
                            "- %s" % (l.product_id.display_name or l.name or _("Riga senza prodotto"))
                            for l in same_tag_yes_lines
                        )

                        raise ValidationError(_(
                            "Può esistere una sola riga con valore SI per lo stesso gruppo etichetta.\n\n"
                            "Etichetta: %s\n"
                            "Righe in conflitto:\n%s"
                        ) % (
                                                  tag.name,
                                                  product_names,
                                              ))

                    checked_tags.add(tag.id)








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

    def action_open_product_load_fullscreen(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Caricamento Prodotti',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'lasercom_2_13.view_sale_order_product_load_fullscreen_form'
            ).id,
            'target': 'current',
            'context': dict(
                self.env.context,
                form_view_initial_mode='edit',
            ),
        }

    def action_open_sale_order_standard_form(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Ordine di vendita',
            'res_model': 'sale.order',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('sale.view_order_form').id,
            'target': 'current',
            'context': dict(
                self.env.context,
                form_view_initial_mode='edit',
            ),
        }

    def action_open_sale_order_standard_form_note_modello(self):
        self.ensure_one()

        action = self.action_open_sale_order_standard_form()
        action['context'] = dict(action['context'], open_notebook_tab='Note modello')
        return action

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)

        if 'x_load_line_ids' in vals and not self.env.context.get('skip_unique_si_tag_check'):
            self._check_unique_si_per_tag_group_on_order()

        return res
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
                line.price_subtotal = (
                        (line.price_unit or 0.0) * (line.product_uom_qty or 0.0)
                        + (line.price_extra or 0.0)
                )

    @api.depends('product_id', 'order_id.state', 'qty_invoiced', 'qty_delivered')
    def _compute_product_updatable(self):
        for line in self:
            if line.state in ['done', 'cancel'] or (line.state == 'sale' and (line.qty_invoiced > 0 or line.qty_delivered > 0)):
                line.product_updatable = False
            else:
                line.product_updatable = True

    x_load_id = fields.Many2one("x.product.load", required=False, ondelete="cascade")
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
    price_unit = fields.Float(string="P.Unitario",digits='Product Price')
    price_extra = fields.Float(string="P.Extra",digits='Product Price')
    note = fields.Char(string="Nota")
    supplier_id = fields.Many2one("res.partner", string="For", required=False)
    default_code = fields.Char(related="product_id.default_code", string="Codice", readonly=True, store=False)
    uom_id = fields.Many2one(related="product_id.uom_id", string="U.M.", readonly=True, store=False)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Tot.riga', readonly=True, store=True)
    product_cassetti_slave = fields.Char(string="Config.")
    sale_line_id = fields.Many2one(
        "sale.order.line",
        compute="_compute_sale_line_id",
        store=False,
        string="Riga Ordine (mappata)",
    )
    editable = fields.Boolean(string="Edit", default=True)
    tipo_vetrina = fields.Selection(
        [
            ('blank', 'Riga in bianco'),
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
        string='SI/NO',default=''
    )
    attachment_product = fields.Binary("Allegato", Copy=False)
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

    @api.onchange('etichetta_si', 'tag_ids')
    def _onchange_etichetta_si_force_same_tag_no(self):
        """
        Aggiorna subito le altre righe con la stessa etichetta a NO,
        senza attendere il salvataggio: così l'utente vede l'effetto
        in tabella restando sulla riga che sta modificando.
        """
        for line in self:
            if line.display_type or line.etichetta_si != 'yes' or not line.tag_ids or not line.order_id:
                continue

            siblings = (line.order_id.x_load_line_ids - line).filtered(
                lambda other: not other.display_type
                              and other.tag_ids
                              and (other.tag_ids & line.tag_ids)
            )

            for sibling in siblings:
                if sibling.etichetta_si != 'no':
                    sibling.etichetta_si = 'no'

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
            #if so_line:
            #    line.etichetta_si="yes"
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
            # Fallback: se x_load_id non arriva ma c'è il prodotto,
            # lo recupero dal template prodotto.
            if not vals.get("x_load_id") and vals.get("product_id"):
                product = self.env["product.product"].browse(vals["product_id"])
                if product and product.product_tmpl_id.x_load_id:
                    vals["x_load_id"] = product.product_tmpl_id.x_load_id.id

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

        res = super(SaleOrderXLoadLine, self).write(vals)

        if self.env.context.get("skip_force_same_tag_no"):
            return res

        if vals.get("etichetta_si") != "yes":
            return res

        selected_lines = self.filtered(
            lambda l: l.etichetta_si == "yes"
                      and l.order_id
                      and not l.display_type
                      and l.tag_ids
        )

        if not selected_lines:
            return res

        for order in selected_lines.mapped("order_id"):
            order_selected_lines = selected_lines.filtered(lambda l: l.order_id == order)

            selected_line_ids = set(order_selected_lines.ids)

            selected_tag_ids = set()
            for selected_line in order_selected_lines:
                selected_tag_ids.update(selected_line.tag_ids.ids)

            if not selected_tag_ids:
                continue

            lines_to_set_no = order.x_load_line_ids.filtered(
                lambda other:
                other.id not in selected_line_ids
                and not other.display_type
                and other.tag_ids
                and bool(set(other.tag_ids.ids) & selected_tag_ids)
            )

            if lines_to_set_no:
                lines_to_set_no.with_context(
                    skip_force_same_tag_no=True,
                    skip_unique_si_tag_check=True,
                ).write({
                    "etichetta_si": "no"
                })

        return res



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

        return True
        if not self.env.context.get('check_unique_si_tag_group'):
            return

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



