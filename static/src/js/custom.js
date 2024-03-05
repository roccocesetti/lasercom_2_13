odoo.define('custom.main', function (require) {
    "use strict";

    var KanbanRecord = require('web.KanbanRecord');

    KanbanRecord.include({
         _get_M2M_data: function (field) {
            var categories = [];
            if (field in this.recordData && this.recordData[field].data) {
                categories = this.recordData.category_id.data;
            }
            return categories;
         },
         _setState: function (recordState) {
            var self = this;
            this._super(recordState);
            self.qweb_context['get_m2m_data'] = self._get_M2M_data.bind(self);
        },
    });

});