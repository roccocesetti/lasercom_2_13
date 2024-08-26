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
    sale_string_subtotal = fields.Char(compute='_compute_sale_string_price', store=True, precompute=True,string='Sub totale riga' )
    sale_string_total = fields.Char(compute='_compute_sale_string_price', store=True, precompute=True,string='Totale riga' )

    @api.depends('product_id', 'purchase_price', 'product_uom_qty', 'price_unit', 'price_subtotal')
    def _compute_sale_string_price(self):
        for line in self:
            #sale_string_price = "{:.2f}".format(line.price_unit) #if line.purchase_price>0 else 'INCLUSO'
            sale_string_price = "{:,.2f}".format(line.price_unit).replace(',', 'X').replace('.', ',').replace('X', '.')
            sale_string_price = sale_string_price.rjust(len(sale_string_price) + 12-len(sale_string_price), ' ')
            #sale_string_subtotal = "{:.2f}".format(line.price_subtotal) if line.purchase_price>0 else 'INCLUSO'
            sale_string_subtotal =  "{:,.2f}".format(line.price_subtotal).replace(',', 'X').replace('.', ',').replace('X', '.') if line.purchase_price>0 else 'INCLUSO'
            sale_string_subtotal = sale_string_subtotal.rjust(len(sale_string_subtotal) + 12-len(sale_string_subtotal), ' ')

            #sale_string_total = "{:.2f}".format(line.price_total) if line.purchase_price>0 else 'INCLUSO'
            sale_string_total = "{:,.2f}".format(line.price_total).replace(',', 'X').replace('.', ',').replace('X', '.') if line.purchase_price>0 else 'INCLUSO'
            sale_string_total = sale_string_total.rjust(len(sale_string_total) + 12-len(sale_string_total), ' ')
            #sale_string_price=decode_protocollo(sale_string_price)
            #line.price_unit = line.price_unit if line.purchase_price>0 else 0.0
            line.sale_string_price = sale_string_price
            line.sale_string_subtotal=sale_string_subtotal            
            line.sale_string_total=sale_string_total            
            

    @api.onchange('product_id', 'product_uom','price_unit','purchase_price')
    def product_id_change_sale_string_price(self):
        if not self.order_id.pricelist_id or not self.product_id or not self.product_uom or not self.price_unit:
            return
        self._compute_sale_string_price
        #self.sale_string_price = self._compute_sale_string_price
        #self.sale_string_subtotal = self._compute_sale_string_price
        #self.sale_string_total = self._compute_sale_string_price
        print(f"Codice Prodotto: {self.product_id.default_code}")
        print(f"Nome Prodotto: {self.product_id.name}")
        print(f"Quantità: {self.product_uom}")
        print(f"Prezzo Unitario: €{self.price_unit:,.2f}")

        print(f"Prezzo unitario: €{self.sale_string_price}")
        print(f"Prezzo sub Totale: €{self.sale_string_subtotal}")
        print(f"Prezzo Totale: €{self.sale_string_total}")
        self.update({
            'sale_string_price': self.sale_string_price,
            'sale_string_subtotal': self.sale_string_subtotal,
            'sale_string_total': self.sale_string_total,

        })

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
        [('vendors', 'Acquisto'),
        ('quotation', 'Valutazione usato')],
        string="Tipo valutazione",
        default="vendors")
    sale_acq_usage = fields.Monetary(string='Acquisto usato', digits='Product Price', default=0.0)
    sale_val_usage = fields.Monetary(string='valutazione usato', digits='Product Price', default=0.0)
    sale_ritiro_usato=fields.Boolean(string='Acquisto usato',default=False)
    sale_modello_usato = fields.Char(string='Modello usato', required=False, copy=False, readonly=False, default='')
    sale_promotion = fields.Monetary(string='Promozione', digits='Product Price', default=0.0)
    sale_promotion_note = fields.Char(string='Nota promozione', required=False, copy=False, readonly=False, default='')

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
    amount_untaxed_arrotondamento = fields.Monetary(string='Arrotondamento', store=True,copy=False, readonly=False, default=0.0,currency_field='currency_id',)
    amount_untaxed_arrotondato = fields.Monetary(string='Imponibile finale', store=True, readonly=True, compute='_amount_all',tracking=5)
    payment_direct=fields.Boolean(string='Pagamento Diretto',default=False)
    payment_direct_allordine = fields.Monetary(string="All'ordine", digits='Product Price', default=0.0,currency_field='currency_id',)
    payment_direct_allaconsegna = fields.Monetary(string='Alla consegna', digits='Product Price', default=0.0,currency_field='currency_id',)
    payment_direct_saldo = fields.Monetary(string='Rimanente a saldo', digits='Product Price', compute='_amount_diretto', default=0.0,currency_field='currency_id',)
    payment_direct_num_titoli = fields.Integer(string='Da pagare in Numero Titoli', default=0)
    payment_direct_importo_titoli = fields.Monetary(string='Importo titoli', compute='_amount_diretto', digits='Product Price', default=0.0,currency_field='currency_id',)
    payment_direct_nota = fields.Char(string='NOta', required=False, copy=False, readonly=False, default='A scadenza mensile a partire da 30 giorni data installazione')

    
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
    attachment_url = fields.Char(default='/web/content/%s?download=true' % 6541,)
    attachment_link = fields.Char('Retro contratto', readonly=True)

    annotazione = fields.Text(string='Annotazione', required=False, copy=False, readonly=False, default='')
    tag_iva = fields.Char(string='+iva', required=False, copy=False, readonly=True, default='+iva')

    #def _compute_attachment_url(self):
        #self._recompute_attachment_url()
        #for record in self:
        #    attachment = self.env['ir.attachment'].search([('res_model', '=', 'res.partner'), ('res_id', '=', 1)], limit=1)
        #    if attachment:
        #        if not record.numero_contratto:
        #            record.attachment_url = '/web/content/%s?download=true' % attachment.id
        #            record.attachment_link = '<a href="%s" download>Download retro Contratto</a>' % record.attachment_url
        #            record.file_name='retro_contratto.pdf'

    def _recompute_attachment_url(self,numero_contratto=None):
        for record in self:
            attachment = self.env['ir.attachment'].search([('res_model', '=', 'res.partner'), ('res_id', '=', 1)], limit=1)
            new_attach=attachment.add_text_and_save_to_partner(record.id, 'Contratto n. %s ' % numero_contratto if numero_contratto else record.numero_contratto, x=10, y=825)            # Uso del metodo
            print("Debug message: ", new_attach.name)
            if new_attach:
                record.attachment_url = '/web/content/%s?download=true' % new_attach.id
                record.attachment_link = '<a href="%s" download>Download retro Contratto</a>' % record.attachment_url
                #record.file_name = 'retro_contratto.pdf'
                record.write({'attachment_url': record.attachment_url, 'attachment_link': record.attachment_link})

    def action_quotation_send(self):
        # Eredita la chiamata al metodo originale
        res = super(SaleOrder, self).action_quotation_send()

        # Aggiungi logica per creare o ottenere l'allegato
        attachment = self._create_dynamic_attachment()

        if attachment:
            # Aggiungi l'allegato ai valori di contesto dell'email
            res['context'].update({
                'default_attachment_ids': [(4, attachment.id)],
            })

        return res

    def _create_dynamic_attachment(self):
        contratto_attachment = self.env['ir.attachment'].search(
            [('res_model', '=', 'sale.order'), ('res_id', '=', order_id)], limit=1)

        # Logica per creare o ottenere l'allegato
        attachment_values = {
            'name': 'Retro contratto',
            'type': 'binary',
            'datas':contratto_attachment.datas,
            'res_model': 'sale.order',
            'res_id': self.id,
        }
        attachment = self.env['ir.attachment'].create(attachment_values)
        return attachment

    def partner_control(self):
            errore=[]
            user = self.env.user
            if not user.has_group('lasercom.group_telemarketing') and not user.has_group(
                    'lasercom.group_amministratore'):
                if user.has_group('lasercom.group_venditore'):

                    if not self.partner_id.name:
                        errore.append('Ragione Sociale campo obbligatorio')
                    if not self.partner_id.rivendita:
                        errore.append('Rivendita campo obbligatorio')
                    if not self.partner_id.street:
                        errore.append('Via campo obbligatorio')
                    if not self.partner_id.zip:
                        errore.append('cap campo obbligatorio')
                    if not self.partner_id.city:
                        errore.append('località campo obbligatorio')
                    if not self.partner_id.state_id:
                        errore.append('provinvia campo obbligatorio')
                    if not self.partner_id.vat:
                        errore.append('P.iva campo obbligatorio')
                    if not self.partner_id.l10n_it_codice_fiscale:
                        errore.append('Codice Fiscale campo obbligatorio')
                    if not self.partner_id.phone:
                        errore.append('Telefono campo obbligatorio')
                    if not self.partner_id.mobile:
                        errore.append('Cellulare campo obbligatorio')
                    if not self.partner_id.email:
                        errore.append('Email campo obbligatorio')
                    if not self.partner_id.l10n_it_pec_email:
                        errore.append('Pec campo obbligatorio')
                    if not self.partner_id.codice_sdi:
                        errore.append('Codice SDI campo obbligatorio')
                    if not self.partner_shipping_id:
                        errore.append('Luogo di consegna campo obbligatorio')

                    if not self.partner_shipping_id.street:
                        errore.append('Via di consegna campo obbligatorio')
                    if not self.partner_shipping_id.zip:
                        errore.append('cap di consegna campo obbligatorio')
                    if not self.partner_shipping_id.city:
                        errore.append('località di consegna campo obbligatorio')
                    if not self.partner_shipping_id.state_id:
                        errore.append('provinvia di consegna campo obbligatorio')


                    if not self.payment_direct and not self.leasing_direct and  not self.finaziamento_direct :
                        errore.append('Inserire almeno un metodo di pagamento')


                    if  self.payment_direct:
                        if self.payment_direct_allordine<=0 and self.payment_direct_allaconsegna<=0:
                                errore.append('inserire importi del pagamento')
                    if  self.finaziamento_direct:
                        if self.finaziamento_direct_costodelbene<=0 and self.finaziamento_direct_finanziamento<=0:
                                errore.append('inserire importi del finaziamento')
                    if  self.leasing_direct:
                        if self.leasing_direct_importo<=0 and self.leasing_direct_macrocanone<=0:
                                errore.append('inserire importi del leasing')
            if errore:
                raise ValidationError(errore)
            return True

    @api.model
    def create(self, vals):
        if vals.get('numero_contratto', _('New')) == _('New'):
            seq_date = None
            if 'data_contratto' in vals and vals['data_contratto'] :
                if not self.partner_control():
                    raise UserError(_('DAti non validi'))

                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['data_contratto']))
                if 'company_id' in vals:
                    vals['numero_contratto'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                        'sale.order.contract', sequence_date=seq_date) or _('New')
                else:
                    vals['numero_contratto'] = self.env['ir.sequence'].next_by_code('sale.order.contract', sequence_date=seq_date) or _('New')
                self._recompute_attachment_url(vals['numero_contratto'])
        vals.update({'note':'Prezzi iva esclusa, Trasporto, installazione, collaudo a nostro carico' })

        res=super(SaleOrder, self).create(vals)
        if len(res.order_line)>16:
            raise UserError(_('Superato il limite di righe da immettere: 16 invece di %s' % str(len(res.order_line)) ))

        return res
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for order in self:

            if len(order.order_line) > 16:
                raise UserError(_('Superato il limite di righe da immettere: 16 invece di %s ' % str(len(order.order_line))))
        return res
    def _write(self, vals):
        """ Override of private write method in order to generate activities
        based in the invoice status. As the invoice status is a computed field
        triggered notably when its lines and linked invoice status changes the
        flow does not necessarily goes through write if the action was not done
        on the SO itself. We hence override the _write to catch the computation
        of invoice_status field. """
        mutable_vals = dict(vals)
        for order in self:

            if order.data_contratto:
                if not order.partner_control():
                    raise UserError(_('DAti non validi'))

            if 'data_contratto' in mutable_vals and mutable_vals['data_contratto']:
                if not order.partner_control():
                    raise UserError(_('DAti non validi'))

                if order.numero_contratto ==_('New') or not order.numero_contratto  :
                        seq_date = fields.Datetime.context_timestamp(order, fields.Datetime.to_datetime(mutable_vals['data_contratto']))
                        if 'company_id' in vals:
                            numero_contratto = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                                'sale.order.contract', sequence_date=seq_date) or _('New')
                            mutable_vals.update({'numero_contratto':numero_contratto})
                        else:
                           numero_contratto= order.env['ir.sequence'].next_by_code('sale.order.contract', sequence_date=seq_date) or  _('New')
                           mutable_vals.update({'numero_contratto':numero_contratto})
                        self._recompute_attachment_url(numero_contratto)

        res= super(SaleOrder, self)._write(mutable_vals)
        return res
    @api.depends('amount_untaxed','amount_total','payment_direct_allordine','payment_direct_allaconsegna','payment_direct_num_titoli')
    def _amount_diretto(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            payment_direct_saldo = order.amount_total - order.payment_direct_allordine-order.payment_direct_allaconsegna
            if order.payment_direct_num_titoli>0:
                payment_direct_importo_titoli=payment_direct_saldo/order.payment_direct_num_titoli
            else:
                payment_direct_importo_titoli=0
            order.update({
                'payment_direct_saldo': payment_direct_saldo,
                'payment_direct_importo_titoli':payment_direct_importo_titoli
            })

    @api.depends('leasing_direct_importo','leasing_direct_macrocanone')
    def _amount_leasing(self):
        """
        Compute the total amounts of the SO.
        """
        #for order in self:
        #    leasing_direct_totale = order.leasing_direct_importo + order.leasing_direct_macrocanone
        #    order.update({
        #        'leasing_direct_totale': leasing_direct_totale,
        #    })

    @api.depends('order_line.price_total','sale_acq_usage','sale_val_usage','sale_promotion','footer_discount','select_acq_usage','amount_untaxed_arrotondamento')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                #line.write({'discount':order.footer_discount})
                if 'incluso' not in line.sale_string_subtotal.lower():
                    amount_untaxed += line.price_subtotal
                    amount_tax += line.price_tax
            amount_untaxed_nocalc = amount_untaxed
            amount_untaxed=amount_untaxed-order.sale_promotion
            amount_untaxed=amount_untaxed-order.sale_val_usage
            importo_discount=amount_untaxed*(order.footer_discount)/100
            amount_untaxed=amount_untaxed-importo_discount
            amount_untaxed = amount_untaxed + order.sale_acq_usage
            amount_untaxed_arrotondato = amount_untaxed - order.amount_untaxed_arrotondamento
            amount_total=(amount_untaxed_arrotondato * 122)/100
            amount_tax=(amount_untaxed_arrotondato * 22)/100
            order.update({
                'amount_untaxed_nocalc': amount_untaxed_nocalc,
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_total,
                'importo_discount': importo_discount,
                'amount_untaxed_arrotondato': amount_untaxed_arrotondato,
            })

    @api.depends('order_line.purchase_price','order_line.margin','sale_acq_usage','sale_val_usage','amount_untaxed')
    def _product_purchase_price(self):
        if not all(self._ids):

            for order in self:
                order.total_purchase_price=0.00
                order.total_purchase_price = sum(order.order_line.filtered(lambda r: r.state != 'cancel').mapped(lambda r: r.purchase_price * r.product_uom_qty))
            order.total_purchase_price = order.total_purchase_price + order.sale_acq_usage
            #order.sale_string_margin = order.amount_untaxed - order.total_purchase_price
        else:
            self.env["sale.order.line"].flush(['margin', 'state','purchase_price','product_uom_qty'])
            # On batch records recomputation (e.g. at install), compute the margins
            # with a single read_group query for better performance.
            # This isn't done in an onchange environment because (part of) the data
            # may not be stored in database (new records or unsaved modifications).

            # Read the order lines for the relevant orders
            order_lines = self.env['sale.order.line'].search(
                [
                    ('order_id', 'in', self.ids),
                    ('state', '!=', 'cancel'),
                ]
            )

            # Create a dictionary to store the total purchase price for each order
            order_totals = {}
            for line in order_lines:
                if line.order_id.id not in order_totals:
                    order_totals[line.order_id.id] = 0.0
                order_totals[line.order_id.id] += line.purchase_price * line.product_uom_qty

            # Assign the computed total purchase price to each order
            for order in self:
                order.total_purchase_price = order_totals.get(order.id, 0.0)
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

    def get_formatted_sale_promotion(self):
        self.ensure_one()
        return self.env['ir.qweb.field.monetary'].value_to_html(
            -1 * self.sale_promotion, {'display_currency': self.currency_id}
        )

    def get_formatted_importo_discount(self):
        self.ensure_one()
        return self.env['ir.qweb.field.monetary'].value_to_html(
            -1 * self.importo_discount, {'display_currency': self.currency_id}
        )

    #@api.depends('partner_id','partner_shipping_id','payment_direct','leasing_direct','finanziamento_direct')


import base64
from io import BytesIO
from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import red
class DocumentPDFAnnotation(models.Model):
    _inherit = 'ir.attachment'


    def add_text_and_save_to_partner(self,order_id, text, x=200, y=800):
        # Cerca l'allegato
        attachment = self
        if attachment:
            # Decodifica il contenuto base64 del campo datas
            pdf_data = base64.b64decode(attachment.datas)

            # Leggi il PDF originale
            pdf_reader = PdfFileReader(BytesIO(pdf_data))
            pdf_writer = PdfFileWriter()

            # Crea un nuovo PDF con il testo aggiunto
            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)
            can.setFillColor(red)
            can.drawString(x, y, text)
            can.save()

            # Muovi il buffer alla posizione iniziale
            packet.seek(0)
            new_pdf = PdfFileReader(packet)

            # Unisci il nuovo PDF con il PDF esistente
            for page_num in range(pdf_reader.getNumPages()):
                page = pdf_reader.getPage(page_num)

                # Solo se il PDF contiene pagine e il nuovo PDF non è vuoto
                if new_pdf.numPages > 0:
                    page.mergePage(new_pdf.getPage(0))

                pdf_writer.addPage(page)

            # Scrivi il nuovo PDF in un buffer
            output = BytesIO()
            pdf_writer.write(output)

            # Codifica in base64
            encoded_pdf = base64.b64encode(output.getvalue())

            # Crea un nuovo allegato o aggiorna quello esistente
            contratto_attachment = self.env['ir.attachment'].search([('name', '=', attachment.name),('res_model', '=', 'sale.order'),('res_id', '=', order_id)], limit=1)
            if contratto_attachment:
                contratto_attachment.write({'datas':encoded_pdf})
            else:
                contratto_attachment = self.env['ir.attachment'].create({
                    'name': attachment.name,
                    'datas': encoded_pdf,
                    'res_model': 'sale.order',
                    'res_id': order_id,
                    'type': 'binary',
                    'mimetype': 'application/pdf'
                })
            with open('/tmp/modified_pdf.pdf', 'wb') as f:
                f.write(output.getvalue())

            return contratto_attachment
        else:
            raise ValidationError("Nessun allegato trovato.")

