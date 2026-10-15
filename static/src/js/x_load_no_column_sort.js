odoo.define('lasercom_2_13.x_load_no_column_sort', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');

    // Le liste con class="x_no_column_sort" sul <tree> non si riordinano
    // cliccando sulle intestazioni di colonna: l'ordine resta quello del
    // modulo di caricamento (sequence).
    ListRenderer.include({

        _hasNoColumnSort: function () {
            var cls = this.arch && this.arch.attrs && this.arch.attrs.class;
            return !!cls && cls.split(/\s+/).indexOf('x_no_column_sort') !== -1;
        },

        _renderHeaderCell: function (node) {
            var $th = this._super.apply(this, arguments);
            if (this._hasNoColumnSort()) {
                $th.removeClass('o_column_sortable');
            }
            return $th;
        },

        _onSortColumn: function (ev) {
            if (this._hasNoColumnSort()) {
                return;
            }
            return this._super.apply(this, arguments);
        },
    });
});
