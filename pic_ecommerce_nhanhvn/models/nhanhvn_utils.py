# -*- coding: utf-8 -*-

from odoo import fields
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class NhanhVNOrderProcessor:
    """Utility class để xử lý dữ liệu đơn hàng từ NhanhVN"""

    @staticmethod
    def safe_str_value(val):
        """Chuyển đổi giá trị sang string an toàn"""
        return str(val) if val else False

    @staticmethod
    def mapping_order_status(status_code):
        """Map status code của NhanhVN sang status của hệ thống"""
        mapping = {
            '40': 'READY_TO_SHIP',  # Đã đóng gói
            '42': 'TO_SHIP',  # Đang đóng gói
            '43': 'TO_SHIP',  # Chờ thu gom
            '54': 'UNPAID',  # Đơn mới
            '55': 'UNPAID',  # Đang xác nhận
            '56': 'TO_PACK',  # Đã xác nhận
            '57': 'UNPAID',  # Chờ khách xác nhận
            '58': 'CANCELLED',  # HVC hủy đơn
            '59': 'PROCESSED',  # Đang chuyển
            '60': 'COMPLETED',  # Thành công
            '61': 'CANCELLED',  # Thất bại
            '63': 'CANCELLED',  # Khách hủy
            '64': 'CANCELLED',  # Hệ thống hủy
            '68': 'CANCELLED',  # Hết hàng
            '71': 'TO_RETURN',  # Đang chuyển hoàn
            '72': 'RETURNED',  # Đã chuyển hoàn
            '73': 'INCIDENT',  # Đổi kho xuất hàng
            '74': 'TO_RETURN',  # Xác nhận hoàn
        }
        return mapping.get(status_code, 'UNPAID')

    @staticmethod
    def prepare_order_vals(order_data, env, config_id, session_id=None):
        """
        Chuẩn bị values để tạo 1 đơn hàng từ raw data NhanhVN

        Args:
            order_data (dict): Dữ liệu đơn hàng từ NhanhVN API/Webhook
            env: Odoo environment
            config_id: Record pic.ecommerce.config
            session_id: Record pic.ecommerce.session (optional - dùng khi tạo từ phiên đồng bộ)

        Returns:
            dict: Values để tạo pic.ecommerce.order
        """
        processor = NhanhVNOrderProcessor

        # Nhóm thông tin
        general_info = order_data.get('info', {})
        shipping_info = order_data.get('shippingAddress', {})
        products_info = order_data.get('products', [])
        carrier_info = order_data.get('carrier', {})
        payment_info = order_data.get('payment', {})
        channel_info = order_data.get('channel', {})
        ship_by_date = False
        if carrier_info.get('deliveryAt'):
            ship_by_date = datetime.fromtimestamp(carrier_info['deliveryAt'])
        if not ship_by_date and carrier_info.get('deliveryDate'):
            ship_by_date =  datetime.strptime(carrier_info['deliveryDate'], '%Y-%m-%d') or False

        # Thông tin cơ bản
        nhanhvn_id = processor.safe_str_value(general_info.get('id'))
        nhanhvn_name = channel_info.get('appOrderId') or nhanhvn_id
        nhanhvn_shop_id = channel_info.get('appShopId') or channel_info.get('shopId')

        update_time = datetime.fromtimestamp(general_info['updatedAt']) if general_info.get(
            'updatedAt') else fields.Datetime.now()
        nhanhvn_order_status = processor.safe_str_value(general_info.get('status'))
        nhanhvn_order_sale_channel = processor.safe_str_value(channel_info.get('saleChannel'))
        order_status = processor.mapping_order_status(nhanhvn_order_status)

        # Chuẩn bị order lines
        order_lines = processor._prepare_order_lines(products_info, general_info)

        # Cấu hình mặc định
        default_vals = processor._get_default_values_from_config(env, config_id, channel_info)

        import json
        response_data_str = json.dumps(order_data, ensure_ascii=False, indent=2)

        # Tạo vals
        vals = {
            # Thông tin NhanhVN
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

            # Thông tin chung
            'name': nhanhvn_name,
            'user_id': default_vals['user_id'],
            'config_id': config_id.id,
            'partner_id': default_vals['partner_id'],
            'partner_shipping_id': default_vals['partner_shipping_id'],
            'partner_invoice_id': default_vals['partner_invoice_id'],
            'warehouse_id': default_vals['warehouse_id'],
            'pricelist_id': default_vals['pricelist_id'],
            'source_id': default_vals['source_id'],
            'payment_term_id': default_vals['payment_term_id'],
            'business_model': default_vals['business_model'],

            'origin': nhanhvn_id,
            'order_status': order_status,
            'create_time': datetime.fromtimestamp(general_info.get('createdAt')) if general_info.get(
                'createdAt') else fields.Datetime.now(),
            'update_time': update_time,
            'note': general_info.get('description') or '',
            'pic_tracking_url': general_info.get('trackingUrl'),

            # Thông tin giao hàng
            'recipient_name': shipping_info.get('name'),
            'recipient_phone': shipping_info.get('mobile'),
            'recipient_email': shipping_info.get('email'),
            'recipient_full_address': shipping_info.get('address'),
            'district_name': str(shipping_info.get('districtId')) if shipping_info.get('districtId') else False,
            'ward_name': str(shipping_info.get('wardId')) if shipping_info.get('wardId') else False,
            'state_name': str(shipping_info.get('cityId')) if shipping_info.get('cityId') else False,

            'ship_by_date': ship_by_date,
            'shipping_carrier': carrier_info.get('name'),
            'tracking_no': carrier_info.get('carrierCode'),
            'ship_fee': float(carrier_info.get('shipFee') or 0),
            'cod_fee': float(carrier_info.get('codFee') or 0),
            'over_weight_ship_fee': float(carrier_info.get('overWeightShipFee') or 0),
            'return_fee': float(carrier_info.get('returnFee') or 0),
            'customer_ship_fee': float(carrier_info.get('customerShipFee') or 0),
            'ecom_fee': float(carrier_info.get('ecomFee') or 0),

            # Thông tin thanh toán
            'voucher_amount': float(payment_info.get('discount', {}).get('amount') or 0),
            'business_cod': float(payment_info.get('codAmount') or 0),
            'business_payment': float(payment_info.get('businessPayment') or 0),

            # Chi tiết đơn hàng
            'items': order_lines,
            'state_ids': [(0, 0, {
                'name': 'Đơn mới từ NhanhVN',
                'update_time': update_time,
                'order_status': order_status,
                'nhanhvn_order_status': nhanhvn_order_status,
                'response_data': response_data_str,
                'source': 'api' if session_id else 'webhook',
            })]
        }

        # Thêm session_id nếu tạo từ phiên đồng bộ
        if session_id:
            vals['session_id'] = session_id.id

        return vals

    @staticmethod
    def _prepare_order_lines(products_info, general_info):
        """Chuẩn bị order lines từ products data"""
        processor = NhanhVNOrderProcessor
        order_lines = []

        # Kiểm tra đơn trả hàng
        factor = 1
        if processor.safe_str_value(general_info.get('idReturn')):
            factor = -1

        for line in products_info:
            price_unit = float(line.get('price') or 0)
            qty = float(line.get('quantity') or 0) * factor
            discount_unit = float(line.get('discount') or 0)
            subtotal = (price_unit - discount_unit) * qty

            order_lines.append((0, 0, {
                'item_id': str(line.get('id')),
                'item_name': line.get('name'),
                'item_sku': line.get('code'),
                'variation_id': str(line.get('id')),
                'variation_name': line.get('name'),
                'variation_sku': line.get('code'),
                'quantity': qty,
                'original_price': float(line.get('originalPrice') or price_unit),
                'price': price_unit,
                'discount': discount_unit * qty,
                'discounted_price': price_unit - discount_unit,
                'subtotal': subtotal,
                'weight': float(line.get('weight') or 0),
                'is_main_item': True,
                'transaction_fee': float(line.get('transactionFee') or 0),
            }))

        return order_lines

    @staticmethod
    def _get_default_values_from_config(env, config_id, channel_info):
        """
        Lấy default values dựa trên shop_id + sale_channel

        Logic:
        1. Parse shop_id và sale_channel từ channel_info
        2. Tìm trong config_id.config_childs
        3. Found → Return values từ config_child
        4. Not found → Return values từ config chính (fallback)

        Returns:
            dict: {
                'partner_id': int,
                'partner_shipping_id': int,
                'partner_invoice_id': int,
                'warehouse_id': int,
                'pricelist_id': int,
                'source_id': int,
                'payment_term_id': int,
            }
        """
        # Parse shop_id và sale_channel
        nhanhvn_shop_id = channel_info.get('appShopId') or channel_info.get('shopId')
        nhanhvn_order_sale_channel = str(channel_info.get('saleChannel')) if channel_info.get('saleChannel') else False

        # Xác định user
        user_id = config_id.user_id.id if config_id.user_id else env.user.id

        # Tìm config_child matching
        if nhanhvn_shop_id and nhanhvn_order_sale_channel:
            config_child = config_id.child_ids.filtered(
                lambda c: c.shop_id == nhanhvn_shop_id
                          and c.code == nhanhvn_order_sale_channel
            )

            if config_child:
                child = config_child[0]
                # Found → Dùng values từ config_child
                return {
                    'user_id': child.user_id.id if child.user_id else user_id,
                    'partner_id': child.partner_id.id if child.partner_id else False,
                    'partner_shipping_id': child.partner_shipping_id.id if child.partner_shipping_id else False,
                    'partner_invoice_id': child.partner_invoice_id.id if child.partner_invoice_id else False,
                    'warehouse_id': child.warehouse_id.id if child.warehouse_id else config_id.warehouse_id.id,
                    'pricelist_id': child.pricelist_id.id if child.pricelist_id else config_id.pricelist_id.id,
                    'source_id': child.source_id.id if child.source_id else config_id.source_id.id,
                    'payment_term_id': child.payment_term_id.id if child.payment_term_id else config_id.payment_term_id.id,
                    'business_model': child.business_model if child.business_model else config_id.business_model,
                    'config_id': child.id,
                }

        # Not found → Fallback config chính
        return {
            'user_id': user_id,
            'partner_id': config_id.partner_id.id if config_id.partner_id else False,
            'partner_shipping_id': config_id.partner_shipping_id.id if config_id.partner_shipping_id else False,
            'partner_invoice_id': config_id.partner_invoice_id.id if config_id.partner_invoice_id else False,
            'warehouse_id': config_id.warehouse_id.id,
            'pricelist_id': config_id.pricelist_id.id,
            'source_id': config_id.source_id.id,
            'payment_term_id': config_id.payment_term_id.id,
            'business_model': config_id.business_model,
            'config_id': config_id.id,
        }

    @staticmethod
    def check_and_update_existing_order(env, config_id, order_data, session_id=None):
        """
        Kiểm tra đơn hàng đã tồn tại và cập nhật nếu cần

        Returns:
            tuple: (order_record, is_updated)
        """
        processor = NhanhVNOrderProcessor

        general_info = order_data.get('info', {})
        channel_info = order_data.get('channel', {})
        carrier_info = order_data.get('carrier', {})

        nhanhvn_id = processor.safe_str_value(general_info.get('id'))
        nhanhvn_name = channel_info.get('appOrderId') or nhanhvn_id

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

        # Tìm đơn hàng
        ecommerce_order = env['pic.ecommerce.order'].search([
            ('config_id', '=', config_id.id),
            ('nhanhvn_order_sale_channel', '=', nhanhvn_order_sale_channel),
            ('name', '=', nhanhvn_name)
        ], limit=1)

        if not ecommerce_order:
            return None, False

        # Kiểm tra cần update
        if ecommerce_order.update_time and ecommerce_order.update_time >= update_time:
            return ecommerce_order, False

        # Update đơn hàng
        ecommerce_order.write({
            'update_time': update_time,
            'nhanhvn_order_status': nhanhvn_order_status,
            'order_status': order_status,

            'ship_by_date': ship_by_date,
            'tracking_no': carrier_info.get('carrierCode'),
            'shipping_carrier': carrier_info.get('name')
        })

        # Tạo state log
        import json
        response_data_str = json.dumps(order_data, ensure_ascii=False, indent=2)

        env['pic.ecommerce.order.state'].create({
            'ecommerce_id': ecommerce_order.id,
            'name': 'Cập nhật từ NhanhVN',
            'update_time': update_time,
            'nhanhvn_order_status': nhanhvn_order_status,
            'order_status': order_status,
            'response_data': response_data_str,
            'source': 'api' if session_id else 'webhook',
        })

        return ecommerce_order, True

    @staticmethod
    def lock_order(env, ordersn):
        env.cr.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (ordersn,)
        )

    @staticmethod
    def create_orders_bulk(env, config_id, orders_data, session_id=None):
        processor = NhanhVNOrderProcessor
        Order = env['pic.ecommerce.order']
        created_orders = Order.browse()

        for order_data in orders_data:
            ordersn = str(order_data.get('id'))

            with env.cr.savepoint():
                processor.lock_order(env, ordersn)

                existing_order, updated = processor.check_and_update_existing_order(
                    env, config_id, order_data, session_id
                )

                if existing_order:
                    _logger.info(f"Đơn hàng {existing_order.name} đã tồn tại")
                    continue

                vals = processor.prepare_order_vals(
                    order_data, env, config_id, session_id
                )

                order = Order.with_context(
                    tracking_disable=True
                ).create(vals)

                created_orders |= order

        return created_orders
