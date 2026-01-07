# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo import api, fields, models, _

class ImportLoadLinesWizard(models.TransientModel):
    _name = "x.sale.order.import.load.lines.wizard"
    _description = "Wizard import righe da Caricamento Prodotti"

    order_id = fields.Many2one("sale.order", required=True)
    load_id = fields.Many2one("x.product.load", required=True)

    load_line_ids = fields.Many2many(
        "x.product.load.line",
        string="Righe selezionabili",
        domain="[('load_id', '=', load_id)]",
    )

    def action_confirm_import(self):
        self.ensure_one()
        order = self.order_id

        # opzionale: se vuoi forzare coerenza
        if order.x_load_id != self.load_id:
            order.x_load_id = self.load_id

        # copia righe selezionate nella tab dell'ordine
        for ll in self.load_line_ids:
            # logica di merge semplice (se stesso prodotto+prezzo+nota)
            existing = order.x_load_line_ids.filtered(
                lambda r: r.product_id == ll.product_id
                and (r.price_unit or 0.0) == (ll.price_unit or 0.0)
                and (r.note or "") == (ll.note or "")
            )
            if existing:
                existing[0].product_uom_qty += ll.product_uom_qty or 0.0
            else:
                self.env["sale.order.x_load_line"].create({
                    "order_id": order.id,
                    "product_id": ll.product_id.id,
                    "product_uom_qty": ll.product_uom_qty,
                    "price_unit": ll.price_unit,
                    "note": ll.note,
                })

        return {"type": "ir.actions.act_window_close"}
