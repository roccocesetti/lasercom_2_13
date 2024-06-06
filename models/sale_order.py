# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools.sql import column_exists, create_column
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from datetime import datetime, timedelta

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


class productProduct(models.Model):
    _inherit = "product.product"
    def get_product_multiline_description_sale(self):
        """ Compute a multiline description of this product, in the context of sales
                (do not use for purchases or other display reasons that don't intend to use "description_sale").
            It will often be used as the default description of a sale order line referencing this product.
        """
        name = super(productProduct, self).get_product_multiline_description_sale()
        name = self.name
        if self.description_sale:
            name = self.description_sale

        return name



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

    total_purchase_price = fields.Monetary(string='Importo di riferimento',compute='_product_purchase_price', help="protocollo", currency_field='currency_id', store=True)
    sale_string_price = fields.Char(compute='_product_purchase_price', store=True, precompute=True,string='Numero protocollo vendita' )
    footer_discount = fields.Float(string='Sconto(%)', digits='Discount', default=0.0)
    importo_discount = fields.Monetary(string='Sconto', digits='Product Price', compute='_amount_all', tracking=4,default=0.0)
    sale_string_margin = fields.Char(compute='_product_purchase_price', store=True, precompute=True,string='Numero protocollo contabile ' )
    select_acq_usage = fields.Selection(
        [('vendors', 'Riacquisto'),
        ('quotation', 'Valutazione usato')],
        string="Tipo valutazione",
        default="vendors")
    sale_acq_usage = fields.Monetary(string='Riacquisto usato', digits='Product Price', default=0.0)
    sale_val_usage = fields.Monetary(string='valutazione usato', digits='Product Price', default=0.0)
    sale_ritiro_usato=fields.Boolean(string='Ritiro usato',default=False)
    sale_modello_usato = fields.Char(string='Modello usato', required=False, copy=False, readonly=False, default='')
    sale_promotion = fields.Monetary(string='Promozione', digits='Product Price', default=0.0)
    sale_modello_valutazione = fields.Char(string='Modello valutato', required=False, copy=False, readonly=False, states={'draft': [('readonly', False)]}, )

    amount_untaxed_nocalc = fields.Monetary(string='Imponibile lordo', store=True, readonly=True, compute='_amount_all', tracking=5)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=5)
    amount_by_group = fields.Binary(string="Tax amount by group", compute='_amount_by_group', help="type: [(name, amount, base, formated amount, formated base)]")
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', tracking=4)
    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', compute_sudo=True, store=True, digits=(12, 6), readonly=True, help='The rate of the currency to the currency of rate 1 applicable at the date of the order')
    codice_sdi = fields.Char('res.partner', related='partner_id.codice_sdi',readonly=False)
    numero_contratto = fields.Char(string='Numero Contratto', required=False, copy=False, readonly=False, states={'draft': [('readonly', False)]},  default=lambda self: _('New'))
    sale_caparra = fields.Monetary(string='Caparra', digits='Product Price', default=0.0,currency_field='currency_id',)

    payment_direct=fields.Boolean(string='Pagamento Diretto',default=False)
    payment_direct_allordine = fields.Monetary(string="All'ordine", digits='Product Price', default=0.0,currency_field='currency_id',)
    payment_direct_allaconsegna = fields.Monetary(string='Alla consegna', digits='Product Price', default=0.0,currency_field='currency_id',)
    payment_direct_saldo = fields.Monetary(string='Saldo', digits='Product Price', default=0.0,currency_field='currency_id',)
    payment_direct_num_titoli = fields.Integer(string='Numero Titoli', default=0)
    payment_direct_importo_titoli = fields.Monetary(string='Importo titoli', digits='Product Price', default=0.0,currency_field='currency_id',)
    payment_direct_nota = fields.Char(string='NOta', required=False, copy=False, readonly=False, default='a scadenza mensile a partire da 30 giorni data installazione')

    
    leasing_direct=fields.Boolean(string='Leasing',default=False)    
    leasing_direct_importo = fields.Monetary(string="Importo", digits='Product Price', default=0.0,currency_field='currency_id',)
    leasing_direct_macrocanone = fields.Monetary(string='Macrocanone', digits='Product Price', default=0.0,currency_field='currency_id',)
    leasing_direct_totale = fields.Monetary(string='Totale', store=True, readonly=False, compute='_amount_leasing', tracking=5,currency_field='currency_id',)
    leasing_direct_numero_rate = fields.Integer(string='Numero Rate', default=0)
    leasing_direct_importo_rate = fields.Monetary(string='Importo rate', digits='Product Price', default=0.0,currency_field='currency_id',)
    leasing_direct_numero_mesi = fields.Integer(string='Numero mesi', default=0)
    leasing_direct_nota = fields.Char(string='Nota', required=False, copy=False, readonly=False, default='Salvo approvazione Istituto erogante')
    
    finaziamento_direct=fields.Boolean(string='Finaziamento',default=False)    
    finaziamento_direct_costodelbene = fields.Monetary(string="Costo del bene", digits='Product Price', default=0.0,currency_field='currency_id',)
    finaziamento_direct_finanziamento = fields.Monetary(string='Finanziamento', digits='Product Price', default=0.0,currency_field='currency_id',)
    finaziamento_direct_numero_rate = fields.Integer(string='Numero Rate', default=0)
    finaziamento_direct_importo_rate = fields.Monetary(string='Importo rate', digits='Product Price', default=0.0,currency_field='currency_id',)
    finaziamento_direct_numero_mesi = fields.Integer(string='Numero mesi', default=0)
    finaziamento_direct_saldo_titolo = fields.Monetary(string='Saldo titoli', store=True, readonly=False, tracking=5,currency_field='currency_id',)
    finaziamento_direct_nota = fields.Char(string='Nota', required=False, copy=False, readonly=False, default='Salvo approvazione Istituto erogante')
    finaziamento_direct_nota_piede = fields.Text(string='Nota_piede', required=False, copy=False, readonly=False, default="LASER.COM snc SEDE OPERATIVA CENTRO ITALIA VIA PERU', 61 63066 GROTTAMMARE AP P.IVA 02177190440 " \
"INFORMATIVA AI SENSI DELL'ART13 D.LGS.196 DEL 30/06/03 E SUCCESSIVE MODIFICHE ED INTEGRAZIONI" \
"Laser.com snc è titolare del trattamento dei dati personali dell'acquirente, I dati necessari per la conclusione del contratto sono: la ragione sociale, la sede" \
"legale,il numero di partita iva, il codice fiscale, il codice univoco o indirizzo Pec, la banca di appogigio. In mancanza di tali dati non sarà possibile" \
"concludere il contratto. I dati verranno trattati esclusivamente da Laser.comsnc e comunicati ai soggetti terzi nei limiti degli adempimenti di natura fiscale." \
"L'interessato,ai sensi e per gli effetti dell'art.7 può chiedere che i propri dati vengano corretti, cancellati, modificati nei limiti consentiti dalla normativa" \
"vigente in materia fiscale. Il consenso scritto per il trattamento dei dati necessari alla conclusione del presente contratto non è richiesto dalla legge.")
    data_contratto = fields.Date(string='Data contratto', readonly=True, copy=False, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                )
   
    finaziamento_direct_retro = fields.Text(string='Retro', required=False, copy=False, readonly=False, default="" \
"")
    attachment_url = fields.Char(compute='_compute_attachment_url')
    annotazione = fields.Char(string='Annotazione', required=False, copy=False, readonly=False, default='')

    def _compute_attachment_url(self):
        for record in self:
            attachment = self.env['ir.attachment'].search([('res_model', '=', 'res.partner'), ('res_id', '=', 1)], limit=1)
            if attachment:
                record.attachment_url = '/web/content/%s?download=true' % attachment.id    
    @api.model
    def create(self, vals):
        if vals.get('numero_contratto', _('New')) == _('New'):
            seq_date = None
            if 'data_contratto' in vals and vals['data_contratto'] :
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['data_contratto']))
                if 'company_id' in vals:
                    vals['numero_contratto'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                        'sale.order.contract', sequence_date=seq_date) or _('New')
                else:
                    vals['numero_contratto'] = self.env['ir.sequence'].next_by_code('sale.order.contract', sequence_date=seq_date) or _('New')
    
        vals.update({'note':'Prezzi iva esclusa, Trasporto, installazione, collaudo a nostro carico' })

        res=super(SaleOrder, self).create(vals)
        if len(res.order_line)>16:
            raise UserError(_('Superato il limite di righe da immettere: 18 invece di %s' % str(len(res.order_line)) ))

        return res
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for order in self:
            if len(order.order_line) > 16:
                raise UserError(_('Superato il limite di righe da immettere: 18 invece di %s ' % str(len(order.order_line))))
        return res
    def _write(self, vals):
        """ Override of private write method in order to generate activities
        based in the invoice status. As the invoice status is a computed field
        triggered notably when its lines and linked invoice status changes the
        flow does not necessarily goes through write if the action was not done
        on the SO itself. We hence override the _write to catch the computation
        of invoice_status field. """
        mutable_vals = dict(vals)
        if 'data_contratto' in mutable_vals and mutable_vals['data_contratto']:
            if self.numero_contratto ==_('New'):
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(mutable_vals['data_contratto']))
                    if 'company_id' in vals:
                        numero_contratto = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                            'sale.order.contract', sequence_date=seq_date) or _('New')  
                        mutable_vals.update({'numero_contratto':numero_contratto})
                    else:
                       numero_contratto= self.env['ir.sequence'].next_by_code('sale.order.contract', sequence_date=seq_date) or  _('New')
                       mutable_vals.update({'numero_contratto':numero_contratto})
        res= super(SaleOrder, self)._write(mutable_vals)
        return res
         
    @api.depends('leasing_direct_importo','leasing_direct_macrocanone')
    def _amount_leasing(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            leasing_direct_totale = order.leasing_direct_importo + order.leasing_direct_macrocanone
            order.update({
                'leasing_direct_totale': leasing_direct_totale,
            })

    @api.depends('order_line.price_total','sale_acq_usage','sale_val_usage','sale_promotion','footer_discount','select_acq_usage')
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
            amount_untaxed_nocalc = amount_untaxed
            amount_untaxed=amount_untaxed-order.sale_promotion
            amount_untaxed=amount_untaxed-order.sale_val_usage
            importo_discount=amount_untaxed*(order.footer_discount)/100
            amount_untaxed=amount_untaxed-importo_discount
            amount_untaxed = amount_untaxed + order.sale_acq_usage
            amount_total=(amount_untaxed * 122)/100
            amount_tax=(amount_untaxed * 22)/100
               
            order.update({
                'amount_untaxed_nocalc': amount_untaxed_nocalc,
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_total,
                'importo_discount': importo_discount,
            })

    @api.depends('order_line.purchase_price','order_line.margin','sale_acq_usage','sale_val_usage','amount_untaxed')
    def _product_purchase_price(self):
        if not all(self._ids):
            for order in self:
                order.total_purchase_price = sum(order.order_line.filtered(lambda r: r.state != 'cancel').mapped('purchase_price'))
            order.total_purchase_price = order.total_purchase_price + order.sale_acq_usage
            #order.sale_string_margin = order.amount_untaxed - order.total_purchase_price
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
            order.total_purchase_price=order.total_purchase_price+order.sale_acq_usage
            #order.sale_string_margin=order.amount_untaxed-order.total_purchase_price

        sale_string_price=   "{:.2f}".format(order.total_purchase_price) if order.total_purchase_price>0 else '999999999'  
        sale_string_margin=   "{:.2f}".format(order.amount_untaxed-order.total_purchase_price) if order.amount_untaxed-order.total_purchase_price>0 else '999999999'
        order.sale_string_price=decode_protocollo(sale_string_price)
        order.sale_string_margin=decode_protocollo(sale_string_margin)                
        order.update({
            'total_purchase_price': order.total_purchase_price,
            'sale_string_margin': order.sale_string_margin,
            'sale_string_price': order.sale_string_price,
            'sale_string_margin': order.sale_string_margin,
            })


    def get_formatted_sale_val_usage(self):
        self.ensure_one()
        return self.env['ir.qweb.field.monetary'].value_to_html(
            -1 * self.sale_val_usage, {'display_currency': self.currency_id}
        )