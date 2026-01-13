# -*- coding: utf-8 -*-

from odoo import models, api, fields
from requests import Request, Session
from datetime import datetime, date, timedelta
import requests
import json
import time
from odoo.exceptions import ValidationError, UserError
from .nhanhvn_utils import NhanhVNOrderProcessor
import logging

_logger = logging.getLogger(__name__)


class PICEcommerceSession(models.Model):
    _inherit = 'pic.ecommerce.session'

    def _transaction_create_ecommerce_order(self, order_items):
        """Tạo đơn hàng từ session data"""
        res = super()._transaction_create_ecommerce_order(order_items)

        if self.config_id.type == 'nhanhvn':
            # Sử dụng bulk create với session_id
            created_orders = NhanhVNOrderProcessor.create_orders_bulk(
                self.env,
                self.config_id,
                order_items,
                session_id=self
            )
            _logger.info(f"Đã tạo {len(created_orders)} đơn hàng NhanhVN cho phiên {self.name}")

        return res

    def _nhanhvn_get_orders(self):
        """Lấy danh sách đơn hàng từ NhanhVN API"""
        access_token = self.config_id.access_token

        if not access_token:
            raise UserError("Không tìm thấy Access Token hợp lệ.")

        if not self.date_from or not self.date_to:
            raise UserError("Vui lòng chọn khoảng thời gian (Từ ngày - Đến ngày).")

        # Convert Date → Datetime với time.min và time.max
        dt_from = datetime.combine(self.date_from, datetime.min.time())  # 00:00:00
        dt_to = datetime.combine(self.date_to, datetime.max.time())  # 23:59:59

        if (dt_to - dt_from).days > 31:
            raise UserError("API Nhanh.vn chỉ hỗ trợ lấy dữ liệu trong khoảng tối đa 31 ngày.")

        from_timestamp = int(dt_from.timestamp())
        to_timestamp = int(dt_to.timestamp())

        url = "https://pos.open.nhanh.vn/v3.0/order/list"
        headers = {
            'Authorization': access_token,
            'Content-Type': 'application/json'
        }
        params = {
            'appId': self.config_id.live_partner_key,
            'businessId': self.config_id.shop_id
        }

        all_orders = []
        next_page_payload = None
        session = requests.Session()

        while True:
            payload = {
                "filters": {
                    # "createdAtFrom": from_timestamp,
                    # "createdAtTo": to_timestamp,
                    "updatedAtFrom": from_timestamp,
                    "updatedAtTo": to_timestamp
                },
                "paginator": {
                    "size": 50
                }
            }

            if next_page_payload:
                payload['paginator']['next'] = next_page_payload

            try:
                response = session.post(url, params=params, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                result = response.json()
            except Exception as e:
                raise UserError(f"Lỗi kết nối API lấy đơn hàng: {str(e)}")

            if result.get('code') == 1:
                data = result.get('data', [])

                if not data:
                    break

                all_orders.extend(data)

                paginator = result.get('paginator', {})
                next_val = paginator.get('next')

                if not next_val:
                    break

                next_page_payload = next_val
            else:
                msg = result.get('messages', 'Lỗi không xác định')
                raise UserError(f"API Error Nhanh.vn: {msg}")

        self.order_items = json.dumps(all_orders, ensure_ascii=False, separators=(',', ':'))

    def action_confirm(self):
        """Override để lấy đơn hàng NhanhVN"""
        res = super().action_confirm()
        if self.config_id.type == 'nhanhvn':
            self._nhanhvn_get_orders()
        return res
