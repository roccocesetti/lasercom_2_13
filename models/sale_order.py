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
                   ',':'V',
                   '.':'P'
    }
    myvalore="A"
    valchar2=""
    id3=3
    for valchar in valore:
        id3= id3+1 if id3<3 else 0
        if id3==0 :
            valchar2= valchar
        else:
            valchar2= valchar2+valchar
        if id3==3:    
            myvalore= myvalore+nprot[valchar]+valchar2
    if id3<3:
            myvalore= myvalore+nprot[valchar]+valchar2
    myvalore=myvalore.replace('.','VI').replace('.','PU')
        
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
    sale_string_subtotal = fields.Char(compute='_compute_sale_string_price', store=True, precompute=True,string='Prezzo' )
    sale_string_total = fields.Char(compute='_compute_sale_string_price', store=True, precompute=True,string='Prezzo' )

    @api.depends('product_id', 'purchase_price', 'product_uom_qty', 'price_unit', 'price_subtotal')
    def _compute_sale_string_price(self):
        for line in self:
            sale_string_price = "{:.2f}".format(line.price_unit) if line.purchase_price>0 else 'INCLUSO'
            sale_string_subtotal = "{:.2f}".format(line.price_subtotal) if line.purchase_price>0 else 'INCLUSO'
            sale_string_total = "{:.2f}".format(line.price_total) if line.purchase_price>0 else 'INCLUSO'
            #sale_string_price=decode_protocollo(sale_string_price)
            line.sale_string_price = sale_string_price
            line.sale_string_subtotal=sale_string_subtotal            
            line.sale_string_total=sale_string_total            
            

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

    total_purchase_price = fields.Monetary(compute='_product_purchase_price', help="protocollo", currency_field='currency_id', store=True)
    sale_string_price = fields.Char(compute='_product_purchase_price', store=True, precompute=True,string='Numero protocollo vendita' )
    footer_discount = fields.Float(string='Sconto piede (%)', digits='Discount', default=0.0)
    sale_string_margin = fields.Char(compute='_product_purchase_price', store=True, precompute=True,string='Numero protocollo contabile ' )
    select_acq_usage = fields.Selection(
        [('vendors', 'Riacquisto'),
        ('quotation', 'Valutazione usato')],
        string="Acquisto",
        default="vendors")
    sale_acq_usage = fields.Float(string='Valutazione usato', digits='Product Price', default=0.0)
    sale_promotion = fields.Float(string='Promozione', digits='Product Price', default=0.0)

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=5)
    amount_by_group = fields.Binary(string="Tax amount by group", compute='_amount_by_group', help="type: [(name, amount, base, formated amount, formated base)]")
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', tracking=4)
    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', compute_sudo=True, store=True, digits=(12, 6), readonly=True, help='The rate of the currency to the currency of rate 1 applicable at the date of the order')
    
    @api.model
    def create(self, vals):
        vals.update({'note':'Prezzi iva esclusa, Trasporto, installazione, collaudo a nostro carico, Garanzia 24 mesi' })
        res=super(SaleOrder, self).create(vals)
        return res
         

    @api.depends('order_line.price_total','sale_acq_usage','sale_promotion','footer_discount','select_acq_usage')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                #line.write({'discount':order.footer_discount})
                
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            amount_untaxed=amount_untaxed*(100-order.footer_discount)/100
            amount_total=amount_untaxed + amount_tax    
            amount_total=amount_total-order.sale_promotion
            if order.select_acq_usage=='vendors':
                amount_total=amount_total+order.sale_acq_usage
            elif order.select_acq_usage=='quotation':   
                amount_total=amount_total-order.sale_acq_usage
            else:
                amount_total=amount_total+order.sale_acq_usage
                
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_total,
            })

    @api.depends('order_line.purchase_price','order_line.margin','select_acq_usage')
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
        if order.select_acq_usage=='vendors':
                order.total_purchase_price=order.total_purchase_price+order.sale_acq_usage

        sale_string_price=   "{:.2f}".format(order.total_purchase_price) if order.total_purchase_price>0 else '999999999'  
        sale_string_margin=   "{:.2f}".format(order.margin) if order.margin>0 else '999999999'  
        order.sale_string_price=decode_protocollo(sale_string_price)
        order.sale_string_margin=decode_protocollo(sale_string_margin)                
        order.update({
                'sale_string_price': order.sale_string_price,
                'sale_string_margin': order.sale_string_margin,
            })
        
