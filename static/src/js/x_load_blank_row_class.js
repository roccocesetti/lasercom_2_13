odoo.define('lasercom_2_13.x_load_blank_row_class', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');

    var BLANK_RIGHT_FIELDS = {
        product_uom_qty: true,
        price_unit: true,
        price_extra: true,
        price_subtotal: true,
        product_uom_height: true,
        product_uom_length: true,
        product_uom_width: true,
        supplier_id: true,
        note: true,
        uom_id: true,
        product_cassetti_slave: true
    };

    ListRenderer.include({

        _renderRow: function (record) {
            var $tr = this._super.apply(this, arguments);

            if (record && record.data && record.data.tipo_vetrina === 'blank') {
                $tr.addClass('x_row_text_white');
            }

            return $tr;
        },

        _renderBodyCell: function (record, node, colIndex, options) {
            var $td = this._super.apply(this, arguments);

            if (
                record &&
                record.data &&
                record.data.tipo_vetrina === 'blank' &&
                node &&
                node.attrs &&
                node.attrs.name &&
                BLANK_RIGHT_FIELDS[node.attrs.name]
            ) {
                $td.addClass('x_blank_right_cell');
            }

            return $td;
        },
    });
});