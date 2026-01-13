import json
import odoo
import secrets
import string
import hmac
import hashlib
from odoo import http, api
from odoo.addons.web.controllers.dataset import DataSet
from odoo.exceptions import ValidationError, UserError
from odoo.http import request, Response

import logging
from datetime import datetime, timedelta
from odoo.tools.config import config
from odoo.tools import consteq, safe_eval

_logger = logging.getLogger(__name__)


class EcommerceNhanhVNAPIController(http.Controller):

    def _get_nhanh_webhook_token(self):
        return request.env['ir.config_parameter'].sudo().get_param('nhanhvn.webhook_verify_token', default='')

    def verify_webhook_token(self, token_from_request):
        saved_token = self._get_nhanh_webhook_token()
        if not saved_token:
            return True
        return token_from_request == saved_token

    @http.route(['/api/oms/nhanhvn/webhook'], methods=['POST'], type='json', auth='public', csrf=False)
    def oms_nhanhvn_webhook(self):
        try:
            raw_body = request.httprequest.data.decode('utf-8')
            json_data = json.loads(raw_body)
            _logger.info(f"NhanhVN Webhook Raw: {json_data}")

            token_from_header = request.httprequest.headers.get('Authorization')

            if not token_from_header:
                token_from_header = request.params.get('token')

            if not self.verify_webhook_token(token_from_header):
                _logger.warning("NhanhVN Webhook: Invalid Token")
                return {'status': 'error', 'msg': 'Invalid Token'}

            event_type = json_data.get('event')
            payload_data = json_data.get('data', {})
            business_id = json_data.get('businessId')

            record_id = payload_data.get('id') or payload_data.get('orderId') or 'N/A'

            request.env['xml.rpc.log'].create({
                'model': "pic.ecommerce.order",
                'method': f'nhanhvn_webhook_{event_type}',
                'args': f"Event: {event_type} - ID: {record_id} - BusinessID: {business_id}",
                'kwargs': str(json_data),
                'return_msg': 'Processing',
            })

            handlers = {
                'orderAdd': self._handle_order_webhook,
                'orderUpdate': self._handle_order_webhook,
                'productAdd': self._handle_product_webhook,
                'productUpdate': self._handle_product_webhook,
            }

            handler = handlers.get(event_type)

            if handler:
                _logger.info(f"NhanhVN Webhook: Processing event '{event_type}'")
                handler(json_data)
            else:
                _logger.info(f"NhanhVN Webhook: Unhandled event '{event_type}'")

            return {'status': 'success'}

        except Exception as e:
            _logger.exception("NhanhVN Webhook Error: %s", str(e))
            return {'status': 'error', 'msg': str(e)}

    def _handle_order_webhook(self, data):
        """
        Handle order webhook - CHỈ SYNC DATA, KHÔNG VALIDATE
        """
        payload_data = data.get('data', {})
        shop_id = data.get('businessId')

        request.env['pic.ecommerce.order'].sudo().process_nhanhvn_order_webhook(
            payload_data=payload_data,
            shop_id=shop_id
        )

    def _handle_product_webhook(self, data):
        pass
