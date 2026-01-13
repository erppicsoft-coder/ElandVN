# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from datetime import datetime
import requests
import logging
from .nhanhvn_constants import (
    NHANHVN_ORDER_SALE_CHANNEL,
    NHANHVN_ORDER_CARRIER,
    NHANHVN_ORDER_TYPE,
    NHANHVN_ORDER_STATUS,
    NHANHVN_ORDER_REASON,
    NHANHVN_ORDER_STEP,
)
from .nhanhvn_utils import NhanhVNOrderProcessor

_logger = logging.getLogger(__name__)


class PICEcommerceOrder(models.Model):
    _inherit = 'pic.ecommerce.order'

    # ================================================================
    # FIELDS DEFINITION - NhanhVN Specific
    # ================================================================

    nhanhvn_id = fields.Char(string="Nhanhvn Order ID")
    nhanhvn_original_order_id = fields.Char(string="Nhanhvn Original Order ID")
    nhanhvn_return_from_id = fields.Char(string="Nhanhvn Return From ID")
    nhanhvn_id_return = fields.Char(string="Nhanhvn ID Return")
    nhanhvn_shop_id = fields.Char(string="Nhanhvn Shop ID")
    nhanhvn_info_url = fields.Char(string="Nhanhvn Info URL", compute='_compute_nhanhvn_info_url')
    nhanhvn_order_sale_channel = fields.Selection(NHANHVN_ORDER_SALE_CHANNEL, string="Kênh bán hàng")
    nhanhvn_order_carrier = fields.Selection(NHANHVN_ORDER_CARRIER, string="Đơn vị vận chuyển")
    nhanhvn_order_type = fields.Selection(NHANHVN_ORDER_TYPE, string="Loại đơn hàng")
    nhanhvn_order_status = fields.Selection(NHANHVN_ORDER_STATUS, string="Trạng thái đơn hàng")
    nhanhvn_order_reason = fields.Selection(NHANHVN_ORDER_REASON, string="Lý do hủy/trả hàng")
    nhanhvn_order_step = fields.Selection(NHANHVN_ORDER_STEP, string="Bước đơn hàng")

    sql_constraints = [
        ('nhanhvn_id_uniq', 'unique(nhanhvn_id)', 'NhanhVN Order ID phải là duy nhất!'),
    ]

    # ================================================================
    # COMPUTE METHODS
    # ================================================================

    def _compute_nhanhvn_info_url(self):
        """Compute NhanhVN order info URL"""
        for order in self:
            if order.nhanhvn_id and order.config_id and order.config_id.type == 'nhanhvn':
                order.nhanhvn_info_url = f"https://nhanh.vn/order/manage/detail?id={order.nhanhvn_id}&businessId=184314&tab=info"
            else:
                order.nhanhvn_info_url = False

    # ================================================================
    # OVERRIDE: Platform-specific implementations
    # ================================================================

    def _fetch_order_from_platform(self):
        """Fetch order từ NhanhVN API"""
        self.ensure_one()

        if self.config_id.type != 'nhanhvn':
            return super()._fetch_order_from_platform()

        if not self.nhanhvn_id:
            _logger.warning(f"[{self.name}] Missing nhanhvn_id, cannot fetch")
            return None

        access_token = self.config_id.access_token
        url = "https://pos.open.nhanh.vn/v3.0/order/list"
        headers = {
            'Authorization': access_token,
            'Content-Type': 'application/json'
        }
        params = {
            'appId': self.config_id.live_partner_key,
            'businessId': self.config_id.shop_id
        }

        payload = {
            "filters": {
                # "createdAtFrom": from_timestamp,
                # "createdAtTo": to_timestamp,
                # "updatedAtFrom": from_timestamp,
                # "updatedAtTo": to_timestamp
                "ids": [int(self.nhanhvn_id)]
            },
            "paginator": {
                "size": 50
            }
        }
        session = requests.Session()
        try:
            response = session.post(url, params=params, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()

            if result.get('code') == 1:
                data = result.get('data', [])
                return data[0] if data else None
            else:
                _logger.error(f"[{self.name}] NhanhVN API Error: {result.get('messages')}")
                return None

        except Exception as e:
            _logger.exception(f"[{self.name}] Lỗi khi fetch order từ NhanhVN: {str(e)}")
            return None

    def _prepare_update_vals_from_payload(self, payload_data):
        """Parse payload NhanhVN → vals"""
        if self.config_id.type != 'nhanhvn':
            return super()._prepare_update_vals_from_payload(payload_data)

        if not payload_data:
            return {}

        processor = NhanhVNOrderProcessor

        # Nhóm thông tin
        general_info = payload_data.get('info', {})
        shipping_info = payload_data.get('shippingAddress', {})
        products_info = payload_data.get('products', [])
        carrier_info = payload_data.get('carrier', {})
        payment_info = payload_data.get('payment', {})
        channel_info = payload_data.get('channel', {})

        # Thông tin cơ bản
        nhanhvn_id = processor.safe_str_value(general_info.get('id'))
        nhanhvn_shop_id = channel_info.get('appShopId') or channel_info.get('shopId')

        update_time = datetime.fromtimestamp(general_info['updatedAt']) if general_info.get(
            'updatedAt') else fields.Datetime.now()
        nhanhvn_order_status = processor.safe_str_value(general_info.get('status'))
        nhanhvn_order_sale_channel = processor.safe_str_value(channel_info.get('saleChannel'))
        order_status = processor.mapping_order_status(nhanhvn_order_status)

        ship_by_date = False
        if carrier_info.get('deliveryAt'):
            ship_by_date = datetime.fromtimestamp(carrier_info['deliveryAt'])
        if not ship_by_date and carrier_info.get('deliveryDate'):
            ship_by_date = datetime.strptime(carrier_info['deliveryDate'], '%Y-%m-%d') or False

        vals = {
            'nhanhvn_shop_id': nhanhvn_shop_id,
            'nhanhvn_order_sale_channel': nhanhvn_order_sale_channel,
            'nhanhvn_order_carrier': processor.safe_str_value(carrier_info.get('id')),
            'nhanhvn_order_type': processor.safe_str_value(general_info.get('type')),
            'nhanhvn_order_status': nhanhvn_order_status,
            'nhanhvn_order_reason': processor.safe_str_value(general_info.get('reason')),

            'nhanhvn_id': nhanhvn_id,
            'nhanhvn_original_order_id': processor.safe_str_value(general_info.get('originalOrderId')),
            'nhanhvn_return_from_id': processor.safe_str_value(general_info.get('returnFromId')),
            'nhanhvn_id_return': processor.safe_str_value(general_info.get('idReturn')),

            'update_time': update_time,
            'order_status': order_status,

            'ship_by_date': ship_by_date,
            'tracking_no': carrier_info.get('carrierCode'),
            'shipping_carrier': carrier_info.get('name'),
            'ship_fee': float(carrier_info.get('shipFee') or 0),
            'cod_fee': float(carrier_info.get('codFee') or 0),
        }

        return vals

    # ================================================================
    # ORDER LINES UPDATE
    # ================================================================

    def _update_order_lines_from_payload(self, payload_data):
        """
        Update order lines từ payload NhanhVN
        Sử dụng lại logic từ NhanhVNOrderProcessor._prepare_order_lines
        """
        if self.config_id.type != 'nhanhvn':
            return super()._update_order_lines_from_payload(payload_data)

        # Safety check: Không update nếu đã có SO
        if self.last_sale_id:
            _logger.warning(f"[{self.name}] Đã có SO, bỏ qua update lines")
            return

        # Safety check: Chỉ update ở draft/validate
        if self.state not in ('draft', 'validate'):
            _logger.warning(f"[{self.name}] State={self.state}, bỏ qua update lines")
            return

        # Parse products từ payload
        products_info = payload_data.get('products', [])
        general_info = payload_data.get('info', {})
        if not products_info:
            return

        try:
            # Tạo lines mới - Sử dụng logic có sẵn
            new_lines_vals = NhanhVNOrderProcessor._prepare_order_lines(
                products_info,
                general_info
            )

            # Create lines
            if new_lines_vals:
                self.write({
                    'items': [(5, 0, 0)] + new_lines_vals
                })
                _logger.info(f"[{self.name}] Updated {len(new_lines_vals)} lines")

        except Exception as e:
            _logger.error(f"[{self.name}] Lỗi update lines: {str(e)}")
            raise

    # ================================================================
    # WEBHOOK PROCESSOR
    # ================================================================

    @api.model
    def process_nhanhvn_order_webhook(self, payload_data, shop_id):
        """
        Xử lý order webhook từ NhanhVN
        Flow: Tạo/update order → Commit → Auto-trigger workflow
        """
        self = self.sudo()
        order = None

        try:
            # 1. Tìm config
            config_id = self.env['pic.ecommerce.config'].sudo().search([
                ('type', '=', 'nhanhvn'),
                ('shop_id', '=', shop_id)
            ], limit=1)

            if not config_id:
                _logger.warning(f"[Webhook] Không tìm thấy cấu hình cho BusinessId {shop_id}")
                return False

            # 2. Parse order info
            general_info = payload_data.get('info', {})
            channel_info = payload_data.get('channel', {})

            nhanhvn_id = str(general_info.get('id'))
            nhanhvn_name = channel_info.get('appOrderId') or nhanhvn_id
            nhanhvn_order_sale_channel = str(channel_info.get('saleChannel'))

            # 3. Tìm hoặc tạo order
            order = self.search([
                ('config_id', '=', config_id.id),
                ('nhanhvn_order_sale_channel', '=', nhanhvn_order_sale_channel),
                ('name', '=', nhanhvn_name)
            ], limit=1)

            if order:
                # Update existing order
                order.sudo().action_update_order_info(force_api_call=False, payload_data=payload_data)
                _logger.info(f"[Webhook] Đã cập nhật đơn {order.name}")
            else:
                # Create new order
                vals = NhanhVNOrderProcessor.prepare_order_vals(payload_data, self.env, config_id, session_id=None)
                order = self.sudo().create(vals)
                _logger.info(f"[Webhook] Đã tạo đơn {order.name}")

            # 4. Commit transaction trước khi trigger workflow
            self.env.cr.commit()

            # 5. Auto-trigger workflow (nếu bật trong config)
            if config_id.auto_process_webhook:
                order._webhook_auto_trigger_workflow()

            return order

        except Exception as e:
            _logger.exception(f"[Webhook] Lỗi khi xử lý webhook: {str(e)}")
            if order:
                _logger.error(f"[Webhook] Đơn hàng bị lỗi: {order.name}")
            # Rollback nếu có lỗi
            self.env.cr.rollback()
            return False

    def _webhook_auto_trigger_workflow(self):
        """
        Auto-trigger workflow sau webhook
        Safe execution - không raise exception ra ngoài
        """
        self.ensure_one()

        try:
            with (self.env.cr.savepoint()):
                _logger.info(f"[Webhook] Bắt đầu workflow cho {self.name}")

                # Step 1: Confirm order (draft → validate/confirm)
                if self.state == 'draft':
                    if self.order_status != 'UNPAID':
                        self.action_confirm()
                        _logger.info(f"[Webhook] → Đã tiếp nhận {self.name} (state={self.state})")

                if self.state == 'validate':
                    self.action_validate()
                    _logger.info(f"[Webhook] → Đã xác nhận {self.name} (state={self.state})")

                # Step 2: Create Sale Order (confirm → done)
                if self.state == 'confirm' and not self.last_sale_id and (not self.config_id or
                        not self.config_id.date_start or self.date_order >= self.config_id.date_start.date()):
                    self.action_create_sale_order()
                    _logger.info(f"[Webhook] → Đã tạo SO cho {self.name}")

            # Step 3: Confirm Sale Order
            if self.last_sale_id and self.last_sale_id.state in ('draft', 'sent'):
                warning = self.last_sale_id._valid_ecommerce_data()
                if not warning:
                    self.last_sale_id.action_confirm()
                    _logger.info(f"[Webhook] → Đã xác nhận SO {self.last_sale_id.name}")
                else:
                    _logger.warning(f"[Webhook] → SO validation failed: {warning}")

            _logger.info(f"[Webhook] ✓ Hoàn thành workflow cho {self.name}")

        except Exception as e:
            _logger.error(f"[Webhook] ✗ Lỗi workflow cho {self.name}: {str(e)}")
            # Không raise để không ảnh hưởng webhook
