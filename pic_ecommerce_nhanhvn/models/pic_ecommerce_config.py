# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import hmac
import json
import time
import requests
import hashlib
from requests import Request, Session
from odoo.exceptions import ValidationError, UserError
import urllib
import string
import random
import logging

_logger = logging.getLogger(__name__)


class PICEcommerceConfig(models.Model):
    _inherit = 'pic.ecommerce.config'

    type = fields.Selection(selection_add=[("nhanhvn", "NhanhVn")],
                            ondelete={
                                'nhanhvn': 'set null',
                            })
    product_category_ids = fields.One2many('product.category', 'ecommerce_config_id', string="Danh mục sản phẩm")
    product_template_ids = fields.One2many('product.template', 'ecommerce_config_id', string="Danh sách sản phẩm")
    default_tax_id = fields.Many2one('account.tax', string="Thuế mặc định cho sản phẩm",
                                     domain="[('type_tax_use', '=', 'sale')]")
    count_product_category = fields.Integer(string="Danh mục", compute='_compute_count_product_data')
    count_product_template = fields.Integer(string="Sản phẩm", compute='_compute_count_product_data')
    ecommerce_shop_ids = fields.One2many('pic.ecommerce.shop', 'ecommerce_config_id', string="Shop TMĐT")
    count_ecommerce_shop = fields.Integer(string="Shop TMĐT", compute='_compute_count_product_data')
    product_data = fields.Text(string="Products Data", readonly=True)
    channel_data = fields.Text(string="Channel Data", readonly=True)
    product_category_data = fields.Text(string="Product Category", readonly=True)

    def action_generate_child_config(self):
        """Tự động tạo child configs từ đơn hàng"""
        self.ensure_one()
        super(PICEcommerceConfig, self).action_generate_child_config()

        if not self.ecommerce_ids:
            raise ValidationError("Chưa có đơn hàng nào. Vui lòng đồng bộ đơn hàng trước!")

        groups = self.env['pic.ecommerce.order'].read_group(
            domain=[
                ('nhanhvn_shop_id', '!=', False),
                ('nhanhvn_order_sale_channel', '!=', False),
            ],
            fields=['nhanhvn_shop_id', 'nhanhvn_order_sale_channel'],
            groupby=['nhanhvn_shop_id', 'nhanhvn_order_sale_channel'],
            lazy=False,
        )

        created = 0
        for g in groups:
            shop_id = g['nhanhvn_shop_id']
            order_sale_channel = g['nhanhvn_order_sale_channel']

            if not shop_id or not order_sale_channel:
                continue

            exists = self.with_context(active_test=True).search_count([
                ('shop_id', '=', shop_id),
                ('code', '=', order_sale_channel),
            ])

            if exists:
                continue
            created += 1
            channel_name = dict(self.env['pic.ecommerce.order']._fields['nhanhvn_order_sale_channel'].selection).get(
                order_sale_channel, order_sale_channel)
            shop_name = f"(Shop: {shop_id})" if shop_id not in (False, None, '', '0') else ''
            self.env['pic.ecommerce.config'].create({
                'name': f"{channel_name} {shop_name}",
                'code': order_sale_channel,
                'shop_id': shop_id,
                'parent_id': self.id,
            })

        if created == 0:
            notification_message = "Không có cấu hình con mới nào được tạo."
        else:
            notification_message = f"Đã tạo thành công {created} cấu hình con từ đơn hàng."

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': notification_message,
                'type': 'success' if created > 0 else 'info',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    @api.depends('product_category_ids', 'product_template_ids', 'ecommerce_shop_ids')
    def _compute_count_product_data(self):
        for record in self:
            record.count_product_category = len(record.product_category_ids)
            record.count_product_template = len(record.product_template_ids)
            record.count_ecommerce_shop = len(record.ecommerce_shop_ids)

    def action_view_product_template(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('sale.product_template_action')
        action['context'] = {}
        action['domain'] = [('id', 'in', self.product_template_ids.ids)]
        return action

    def action_view_product_category(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('product.product_category_action_form')
        action['context'] = {}
        action['domain'] = [('id', 'in', self.product_category_ids.ids)]
        return action

    def action_view_ecommerce_shop(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('pic_ecommerce_nhanhvn.action_pic_ecommerce_shop')
        action['context'] = {}
        action['domain'] = [('id', 'in', self.ecommerce_shop_ids.ids)]
        return action

    def _nhanhvn_get_auth_url(self):
        self.ensure_one()
        timest = int(time.time())
        host = "https://nhanh.vn"
        path = "/oauth"
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        redirect_url = base_url + '/nhanh/oauth/callback'
        partner_id = self.live_partner_key
        url = host + path + "?version=3.0&appId=%s&returnLink=%s" % (self.live_partner_key, redirect_url)
        self.oauth_url = url

    def action_get_auth_url(self):
        if self.type == 'nhanhvn':
            self._nhanhvn_get_auth_url()

        return super(PICEcommerceConfig, self).action_get_auth_url()

    def _nhanhvn_get_access_token(self):
        url = "https://pos.open.nhanh.vn/v3.0/app/getaccesstoken"

        params = {
            'appId': int(self.live_partner_key)
        }

        payload = {
            "accessCode": self.shopee_code,
            "secretKey": self.live_key
        }

        try:
            response = requests.post(url, params=params, json=payload, timeout=30)

            response.raise_for_status()

            result = response.json()

        except requests.exceptions.RequestException as e:
            raise UserError(f"Lỗi kết nối đến Nhanh.vn: {str(e)}")
        except ValueError:
            raise UserError("Phản hồi từ Nhanh.vn không đúng định dạng JSON.")

        if result.get('code') == 1:
            data = result.get('data', {})
            self.update({
                'access_token': data.get('accessToken'),
                'expires_in': datetime.utcfromtimestamp(data.get('expiredAt', 0)),
                'shop_id': data.get('businessId'),
            })

        else:
            error_messages = result.get('messages', [])
            if isinstance(error_messages, list):
                msg = ", ".join(str(x) for x in error_messages)
            else:
                msg = str(error_messages)

            raise UserError(f"Không thể lấy Token Nhanh.vn: {msg}")

    def action_get_access_token(self):
        if self.type == 'nhanhvn':
            self._nhanhvn_get_access_token()

        return super(PICEcommerceConfig, self).action_get_access_token()

    def nhanhvn_create_product_template(self):
        if not self.product_data:
            return

        try:
            products_data = json.loads(self.product_data)
        except ValueError:
            raise UserError("Dữ liệu product_data không đúng định dạng JSON.")

        if not products_data:
            return

        incoming_codes = [item.get('code') if item.get('code') else item.get('barcode') for item in products_data if
                          item.get('code')]

        if not incoming_codes:
            return

        existing_templates = self.env['product.template'].search([
            ('default_code', 'in', incoming_codes)
        ])
        existing_codes = set(existing_templates.mapped('default_code'))

        vals_list = []
        processed_codes_in_batch = set()

        for item in products_data:
            code = item.get('code') if item.get('code') else item.get('id')

            if not code:
                continue

            if code in existing_codes or code in processed_codes_in_batch:
                continue

            prices = item.get('prices', {})
            retail_price = prices.get('retail', 0) if prices else 0

            val = {
                'name': item.get('name'),
                'default_code': code,
                'barcode': item.get('barcode'),
                'list_price': retail_price,
                'detailed_type': 'product',
                'nhanhvn_id': item.get('id'),
                'nhanhvn_parent_id': item.get('parentId'),
                'taxes_id': [(6, 0, [self.default_tax_id.id])],
                'ecommerce_config_id': self.id,
            }

            vals_list.append(val)
            processed_codes_in_batch.add(code)

        if vals_list:
            try:
                self.env['product.template'].create(vals_list)
                _logger.info(f"Đã tạo mới {len(vals_list)} sản phẩm từ Nhanh.vn")
            except Exception as e:
                raise UserError(f"Lỗi khi tạo sản phẩm: {str(e)}")
        else:
            _logger.info("Không có sản phẩm mới nào cần tạo.")

    def nhanhvn_create_ecommerce_shop(self):
        if not self.channel_data:
            return

        try:
            raw_data = json.loads(self.channel_data)
        except ValueError:
            raise UserError("Dữ liệu channel_data không đúng định dạng JSON.")

        if not raw_data:
            return

        ShopModel = self.env['pic.ecommerce.shop']

        platform_map = {
            8142: 'lazada',
            8195: 'shopee',
            8855: 'tiktok',
            8237: 'sendo',
            8238: 'tiki'
        }

        unique_shops = {}
        for item in raw_data:
            s_id = str(item.get('shopId'))
            unique_shops[s_id] = item

        existing_records = ShopModel.search([
            ('ecommerce_config_id', '=', self.id)
        ])
        existing_map = {rec.shop_id: rec for rec in existing_records}

        vals_create_list = []

        for shop_id, item in unique_shops.items():
            app_id = item.get('appId')
            shop_name = item.get('shopName')

            val = {
                'name': shop_name,
                'shop_id': shop_id,
                'type': platform_map.get(app_id, False),
                'app_id': app_id,
                'ecommerce_config_id': self.id,
                'expired_at': datetime.fromtimestamp(item.get('expiredAt'))
            }

            if shop_id in existing_map:
                existing_record = existing_map[shop_id]
                if existing_record.name != val['name']:
                    existing_record.write({'name': val['name']})
            else:
                vals_create_list.append(val)

        if vals_create_list:
            ShopModel.create(vals_create_list)

    def nhanhvn_get_channel_data_v2(self):
        url = "https://open.nhanh.vn/api/ecom/shops"

        platform_ids = [8195, 8855, 8142, 8237, 8238]

        if not self.access_token:
            raise UserError("Chưa có Access Token. Vui lòng lấy Token trước.")

        all_shops = []
        session = requests.Session()

        for platform_id in platform_ids:
            current_page = 1

            while True:
                data_dict = {
                    "appId": platform_id,
                    "page": current_page
                }

                payload = {
                    "version": "2.0",
                    "appId": self.live_partner_key,
                    "businessId": self.shop_id,
                    "accessToken": self.access_token,
                    "data": json.dumps(data_dict)
                }

                try:
                    response = session.post(url, data=payload, timeout=30)
                    response.raise_for_status()
                    result = response.json()
                except Exception as e:
                    break

                if result.get('code') == 1:
                    res_data = result.get('data', {})
                    shops = res_data.get('shops', [])

                    if shops:
                        all_shops.extend(shops)

                    total_pages = res_data.get('totalPages', 1)

                    if current_page >= total_pages:
                        break

                    current_page += 1
                else:
                    break

        if all_shops:
            self.channel_data = json.dumps(all_shops, ensure_ascii=False, separators=(',', ':'))
        else:
            self.channel_data = json.dumps([], separators=(',', ':'))

    def nhanhvn_get_channel_data(self):
        access_token = self.access_token

        if not access_token:
            raise UserError("Không tìm thấy Access Token hợp lệ.")

        url = "https://pos.open.nhanh.vn/v3.0/ecom/shop"

        headers = {
            'Authorization': access_token,
            'Content-Type': 'application/json'
        }

        params = {
            'appId': self.live_partner_key,
            'businessId': self.shop_id
        }

        all_channels = []
        next_page_payload = None
        session = requests.Session()

        while True:
            payload = {
                "filters": {
                },
                "paginator": {
                    "size": 50
                }
            }

            if next_page_payload:
                payload['paginator']['next'] = next_page_payload

            try:
                response = session.post(url, params=params, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()
            except Exception as e:
                raise UserError(f"Lỗi kết nối API lấy danh sách gian hàng: {str(e)}")

            if result.get('code') == 1:
                data = result.get('data', [])

                if not data:
                    break

                all_channels.extend(data)

                paginator = result.get('paginator', {})
                next_val = paginator.get('next')

                if not next_val:
                    break

                next_page_payload = next_val
            else:
                msg = result.get('messages', 'Lỗi không xác định')
                raise UserError(f"API Error Nhanh.vn: {msg}")

        self.channel_data = json.dumps(all_channels, ensure_ascii=False, separators=(',', ':'))

    def nhanhvn_get_product_data(self):
        access_token = self.access_token

        if not access_token:
            raise UserError("Không tìm thấy Access Token hợp lệ.")

        url = "https://pos.open.nhanh.vn/v3.0/product/list"

        headers = {
            'Authorization': access_token,
            'Content-Type': 'application/json'
        }

        params = {
            'appId': self.live_partner_key,  # appId
            'businessId': self.shop_id  # businessId (Cần đảm bảo field này có trong model)
        }

        all_products = []
        next_page_payload = None

        session = requests.Session()

        while True:
            payload = {
                "filters": {
                },
                "paginator": {
                    "size": 50,
                    "sort": {"id": "asc"}
                }
            }

            if next_page_payload:
                payload['paginator']['next'] = next_page_payload

            try:
                response = session.post(url, params=params, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                result = response.json()
            except Exception as e:
                raise UserError(f"Lỗi khi đồng bộ sản phẩm: {str(e)}")

            if result.get('code') == 1:
                data = result.get('data', [])

                if not data:
                    break

                all_products.extend(data)

                paginator = result.get('paginator', {})
                next_val = paginator.get('next')

                if not next_val:
                    break

                next_page_payload = next_val
            else:
                msg = result.get('messages', 'Lỗi không xác định từ Nhanh.vn')
                raise UserError(f"API Error: {msg}")

        self.product_data = json.dumps(all_products, ensure_ascii=False, separators=(',', ':'))

    def nhanhvn_get_product_category_data(self):
        access_token = self.access_token

        if not access_token:
            raise UserError("Không tìm thấy Access Token hợp lệ.")

        url = "https://pos.open.nhanh.vn/v3.0/product/category"

        headers = {
            'Authorization': access_token,
            'Content-Type': 'application/json'
        }

        params = {
            'appId': self.live_partner_key,
            'businessId': self.shop_id
        }

        all_categories = []
        next_page_payload = None
        session = requests.Session()

        while True:
            payload = {
                "filters": {
                },
                "paginator": {
                    "size": 50
                }
            }

            if next_page_payload:
                payload['paginator']['next'] = next_page_payload

            try:
                response = session.post(url, params=params, json=payload, headers=headers, timeout=30)
                response.raise_for_status()
                result = response.json()
            except Exception as e:
                raise UserError(f"Lỗi kết nối API lấy danh mục: {str(e)}")

            if result.get('code') == 1:
                data = result.get('data', [])

                if not data:
                    break

                all_categories.extend(data)

                paginator = result.get('paginator', {})
                next_val = paginator.get('next')

                if not next_val:
                    break

                next_page_payload = next_val
            else:
                msg = result.get('messages', 'Lỗi không xác định')
                raise UserError(f"API Error Nhanh.vn: {msg}")

        self.product_category_data = json.dumps(all_categories, ensure_ascii=False, separators=(',', ':'))

    def nhanhvn_create_product_category(self):
        if not self.product_category_data:
            return

        try:
            categories_data = json.loads(self.product_category_data)
        except ValueError:
            raise UserError("Dữ liệu danh mục không đúng định dạng JSON.")

        if not categories_data:
            return

        Category = self.env['product.category']

        existing_cats = Category.search([('nhanhvn_id', '!=', False)])
        nhanh_map = {rec.nhanhvn_id: rec for rec in existing_cats}

        for item in categories_data:
            n_id = item.get('id')
            n_name = item.get('name')
            n_code = item.get('code')
            n_parent_id = item.get('parentId')

            if not n_id:
                continue

            vals = {
                'name': n_name,
                'nhanhvn_code': n_code,
                'nhanhvn_id': n_id,
                'nhanhvn_parent_id': n_parent_id,
                'ecommerce_config_id': self.id,
            }

            if n_id in nhanh_map:
                nhanh_map[n_id].write(vals)
            else:
                new_cat = Category.create(vals)
                nhanh_map[n_id] = new_cat

        for item in categories_data:
            child_n_id = item.get('id')
            parent_n_id = item.get('parentId')

            child_record = nhanh_map.get(child_n_id)

            if not child_record:
                continue

            if parent_n_id and parent_n_id != 0:
                parent_record = nhanh_map.get(parent_n_id)

                if parent_record:
                    if child_record.parent_id.id != parent_record.id:
                        child_record.parent_id = parent_record.id
                else:
                    _logger.warning(f"Danh mục {child_n_id} có cha là {parent_n_id} nhưng không tìm thấy cha.")
            else:
                if child_record.parent_id:
                    child_record.parent_id = False

        _logger.info(f"Đã đồng bộ xong {len(categories_data)} danh mục sản phẩm.")
