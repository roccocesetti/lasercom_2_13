odoo.define('lasercom_2_13.x_load_blank_row_class', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        _renderRow: function (record) {
            var $tr = this._super.apply(this, arguments);

            if (
                record &&
                record.data &&
                record.data.tipo_vetrina === 'blank'
            ) {
                $tr.addClass('x_row_text_white');
            }

            return $tr;
        },
    });
});
