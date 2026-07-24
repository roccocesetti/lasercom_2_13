odoo.define('lasercom_2_13.goto_tab_widget', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var widgetRegistry = require('web.widget_registry');
    var FormRenderer = require('web.FormRenderer');

    // Attiva, dentro $notebook, la pagina il cui titolo corrisponde a "text".
    // Ritorna true se la pagina è stata trovata ed attivata.
    function activateTabByText($notebook, text) {
        var $tab = $notebook.find('.o_notebook_headers .nav-link').filter(function () {
            return $(this).text().trim() === text;
        });
        if ($tab.length) {
            $tab.eq(0).tab('show');
        }
        return $tab.length > 0;
    }

    // Widget generico da usare con <widget name="goto_tab" target="..." label="..."/>
    // per creare un pulsante che porta ad un'altra pagina dello stesso notebook.
    var GotoTabWidget = Widget.extend({
        tagName: 'button',
        className: 'o_goto_tab_widget',
        events: {
            click: '_onClick',
        },

        init: function (parent, record, node) {
            this._super.apply(this, arguments);
            this.target = node.attrs.target;
            this.label = node.attrs.label || this.target;
            // _handleAttributes del renderer ignora i tag <button>, quindi
            // applichiamo qui la classe passata nell'arch (default: btn-secondary).
            this.buttonClass = node.attrs.class || 'btn-secondary';
        },

        start: function () {
            this.$el.attr('type', 'button');
            this.$el.addClass(this.buttonClass);
            this.$el.text(this.label);
            return this._super.apply(this, arguments);
        },

        _onClick: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();

            var $notebook = this.$el.closest('.o_form_view').find('.o_notebook').first();
            activateTabByText($notebook, this.target);
        },
    });

    widgetRegistry.add('goto_tab', GotoTabWidget);

    // Se il form viene aperto con il context 'open_notebook_tab' (es. dal
    // pulsante presente nella vista "Caricamento a pagina piena"), una volta
    // renderizzato il form viene attivata automaticamente la pagina del
    // notebook con quel titolo.
    FormRenderer.include({
        on_attach_callback: function () {
            this._super.apply(this, arguments);

            var tabToOpen = this.state && this.state.context && this.state.context.open_notebook_tab;
            if (!tabToOpen) {
                return;
            }

            var $notebook = this.$('.o_notebook').first();
            activateTabByText($notebook, tabToOpen);
        },
    });

    return GotoTabWidget;
});
