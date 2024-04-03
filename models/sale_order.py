# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import column_exists, create_column

def decode_protocollo(valore="0"):
    nprot = {'1':'AAA',
                   '2':'BCD',
                   '3':'EFG',
                   '4':'HIL',
                   '5':'MNO',
                   '6':'PQR',
                   '7':'STU',
                   '8':'VWZ',
                   '9':'YJY',
                   '0':'TTT',
                   ',':':::',
                   '.':';;;'
    }
    myvalore=str(valore).replace('0',nprot['0'])
    myvalore=myvalore.replace('1',nprot['1'])
    myvalore=myvalore.replace('2',nprot['2'])
    myvalore=myvalore.replace('3',nprot['3'])
    myvalore=myvalore.replace('4',nprot['4'])
    myvalore=myvalore.replace('5',nprot['5'])
    myvalore=myvalore.replace('6',nprot['6'])
    myvalore=myvalore.replace('7',nprot['7'])
    myvalore=myvalore.replace('8',nprot['8'])
    myvalore=myvalore.replace('9',nprot['9'])
    myvalore=myvalore.replace(',',nprot[','])
    myvalore=myvalore.replace('.',nprot['.'])
    return myvalore
    

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _auto_init(self):
        if not column_exists(self.env.cr, "sale_order_line", "sale_string_price"):
            # By creating the column 'margin' manually we steer clear of hefty data computation.
            create_column(self.env.cr, "sale_order_line", "sale_string_price", "varchar")
        return super()._auto_init()
    #purchase_price = fields.Float(string='Cost', digits='Product Price')
    sale_string_price = fields.Char(compute='_compute_sale_string_price', store=True, precompute=True,string='Prezzo' )

    @api.depends('product_id', 'purchase_price', 'product_uom_qty', 'price_unit', 'price_subtotal')
    def _compute_sale_string_price(self):
        for line in self:
            sale_string_price = "{:.2f}".format(line.price_unit) if line.purchase_price>0 else 'INCLUSO'
            #sale_string_price=decode_protocollo(sale_string_price)
            line.sale_string_price = sale_string_price            
            

    @api.onchange('product_id', 'product_uom','price_unit','purchase_price')
    def product_id_change_sale_string_price(self):
        if not self.order_id.pricelist_id or not self.product_id or not self.product_uom or not self.price_unit:
            return
        self.sale_string_price = self._compute_sale_string_price

    @api.onchange('product_id')
    def product_id_change(self):
        # VFE FIXME : bugfix for matrix, the purchase_price will be changed to a computed field in master.
        res = super(SaleOrderLine, self).product_id_change()
        self.product_id_change_sale_string_price()
        return res

    @api.model
    def create(self, vals):
        vals.update(self._prepare_add_missing_fields(vals))
        return super(SaleOrderLine, self).create(vals)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_purchase_price = fields.Monetary(compute='_product_purchase_price', help="It gives profitability by calculating the difference between the Unit Price and the cost.", currency_field='currency_id', store=True)
    sale_string_price = fields.Char(compute='_product_purchase_price', store=True, precompute=True,string='Numero protocollo' )


    @api.depends('order_line.purchase_price')
    def _product_purchase_price(self):
        if not all(self._ids):
            for order in self:
                order.total_purchase_price = sum(order.order_line.filtered(lambda r: r.state != 'cancel').mapped('purchase_price'))
        else:
            self.env["sale.order.line"].flush(['margin', 'state'])
            # On batch records recomputation (e.g. at install), compute the margins
            # with a single read_group query for better performance.
            # This isn't done in an onchange environment because (part of) the data
            # may not be stored in database (new records or unsaved modifications).
            grouped_order_lines_data = self.env['sale.order.line'].read_group(
                [
                    ('order_id', 'in', self.ids),
                    ('state', '!=', 'cancel'),
                ], ['purchase_price', 'order_id'], ['order_id'])
            mapped_data = {m['order_id'][0]: m['purchase_price'] for m in grouped_order_lines_data}
            for order in self:
                order.total_purchase_price = mapped_data.get(order.id, 0.0)
        sale_string_price=   "{:.2f}".format(order.total_purchase_price) if order.total_purchase_price>0 else '999999999'  
        order.sale_string_price=decode_protocollo(sale_string_price)
