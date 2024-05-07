from odoo import http
from odoo.http import request

class CustomDownloadController(http.Controller):
    @http.route('/my/download/<int:attachment_id>', type='http', auth="public")
    def download_attachment(self, attachment_id, **kw):
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
        if attachment and attachment.exists():
            filecontent = attachment.datas
            filename = f"custom_name_{attachment.name}"  # Personalizza qui il nome del file
            headers = [
                ('Content-Type', attachment.mimetype),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
            return request.make_response(filecontent, headers)
        else:
            return request.not_found()
