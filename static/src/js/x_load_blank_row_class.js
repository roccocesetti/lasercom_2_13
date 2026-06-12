odoo.define('lasercom_2_13.x_load_blank_row_class', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        _renderRow: function (record) {
            var $tr = this._super.apply(this, arguments);

            if (!record || !record.data || record.data.tipo_vetrina !== 'blank') {
                return $tr;
            }

            $tr.addClass('x_row_text_white');

            /*
             * Campi da sbiancare.
             * Li marchiamo per nome campo, non in base alla posizione della colonna T.vetr.
             * Così funziona anche se tipo_vetrina è nascosto.
             */
            var blankRightFields = {
                product_uom_qty: true,
                price_unit: true,
                price_extra: true,
                price_subtotal: true,
                product_uom_height: true,
                product_uom_length: true,
                product_uom_width: true,
                supplier_id: true,
                note: true,
                uom_id: true
            };

            /*
             * Metodo principale: Odoo 13 normalmente mette data-name sul td.
             */
            $tr.find('td[data-name]').each(function () {
                var $td = $(this);
                var fieldName = $td.attr('data-name');

                if (fieldName && blankRightFields[fieldName]) {
                    $td.addClass('x_blank_right_cell');
                }
            });

            /*
             * Fallback: se per qualche motivo data-name non è presente,
             * uso la mappatura colonne visibili.
             */
            if (!$tr.find('td.x_blank_right_cell').length && this.columns) {
                var $cells = $tr.children('td');
                _.each(this.columns, function (column, index) {
                    var fieldName = false;

                    if (column.attrs && column.attrs.name) {
                        fieldName = column.attrs.name;
                    } else if (column.name) {
                        fieldName = column.name;
                    }

                    if (fieldName && blankRightFields[fieldName]) {
                        $cells.eq(index).addClass('x_blank_right_cell');
                    }
                });
            }

            return $tr;
        },
    });
});