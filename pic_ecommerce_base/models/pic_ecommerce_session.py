# -*- coding: utf-8 -*-

from odoo import models, api, fields
from datetime import datetime, date, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class PICEcommerceSession(models.Model):
    _name = 'pic.ecommerce.session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Phiên đồng bộ"
    _order = "id DESC"

    # ================================================================
    # FIELDS DEFINITION
    # ================================================================

    name = fields.Char(string="Phiên đồng bộ", copy=False)
    user_id = fields.Many2one('res.users', string="Người phụ trách", default=lambda self: self.env.user)
    config_id = fields.Many2one('pic.ecommerce.config', string="Sàn TMĐT", required=True)

    date = fields.Datetime(string="Ngày lập phiên", default=lambda self: fields.Datetime.now(), copy=False)
    date_from = fields.Date(string="Từ ngày")
    date_to = fields.Date(string="Đến ngày")
    date_confirm = fields.Datetime(string="Ngày đồng bộ", copy=False)
    date_done = fields.Date(string="Ngày hoàn thành", copy=False)

    state = fields.Selection([
        ('draft', 'Dự thảo'),
        ('confirm', 'Đồng bộ'),
        ('processing', 'Đang thực hiện'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy')
    ], default="draft", string="Trạng thái", copy=False)

    # Default values
    partner_id = fields.Many2one('res.partner', string="Khách hàng")
    partner_invoice_id = fields.Many2one('res.partner', string="Địa chỉ xuất hóa đơn")
    partner_shipping_id = fields.Many2one('res.partner', string="Địa chỉ giao hàng", required=True)
    payment_term_id = fields.Many2one("account.payment.term", string="Điều khoản thanh toán")
    pricelist_id = fields.Many2one('product.pricelist', string="Bảng giá")
    warehouse_id = fields.Many2one("stock.warehouse", string="Nhà kho")
    source_id = fields.Many2one("utm.source", string="Nguồn")
    discount = fields.Float(string="% Chiết khấu", default=0)

    # Relations
    ecommerce_ids = fields.One2many('pic.ecommerce.order', 'session_id', string="Đơn hàng TMĐT")
    payment_ids = fields.One2many('pic.ecommerce.payment', 'session_id', string="Thanh toán TMĐT")
    return_ids = fields.One2many('pic.ecommerce.return', 'session_id', string="Trả hàng TMĐT")

    count_ecommerce = fields.Integer(string="Đơn hàng", compute="_compute_count_ecommerce")
    count_payment = fields.Integer(string="Thanh toán", compute="_compute_count_payment")
    count_return = fields.Integer(string="Trả hàng", compute="_compute_count_return")

    # Sync data (raw JSON)
    orders = fields.Text(copy=False)
    order_items = fields.Text(copy=False)
    return_orders = fields.Text(copy=False)
    return_order_items = fields.Text(copy=False)
    payment_orders = fields.Text(copy=False)

    # Computed
    warning = fields.Text(string="Cảnh báo", compute="_compute_warning")
    is_user_current = fields.Boolean(compute='_compute_is_user_current')

    # ================================================================
    # COMPUTE METHODS
    # ================================================================

    @api.depends('user_id')
    def _compute_is_user_current(self):
        for record in self:
            record.is_user_current = (self.env.user == record.user_id or self.env.user.has_group('base.group_no_one'))

    @api.depends('ecommerce_ids', 'ecommerce_ids.warning')
    def _compute_warning(self):
        for record in self:
            ecommerce_warning_ids = record.ecommerce_ids.filtered(lambda x: x.warning)
            if ecommerce_warning_ids:
                all_warnings = ''.join(ecommerce_warning_ids.mapped('warning')).split('\n')
                warning = '\n'.join(set(all_warnings))
            else:
                warning = False
            record.warning = warning

    def _compute_count_ecommerce(self):
        for record in self:
            record.count_ecommerce = len(record.ecommerce_ids)

    def _compute_count_payment(self):
        for record in self:
            record.count_payment = len(record.payment_ids)

    def _compute_count_return(self):
        for record in self:
            record.count_return = len(record.return_ids)

    # ================================================================
    # ONCHANGE METHODS
    # ================================================================

    @api.onchange('config_id')
    def _onchange_config_id(self):
        """Set default values từ config"""
        if self.config_id:
            self.partner_id = self.config_id.partner_id.id
            self.partner_invoice_id = self.config_id.partner_invoice_id.id
            self.partner_shipping_id = self.config_id.partner_shipping_id.id
            self.payment_term_id = self.config_id.payment_term_id.id
            self.pricelist_id = self.config_id.pricelist_id.id
            self.warehouse_id = self.config_id.warehouse_id.id
            self.source_id = self.config_id.source_id.id

            # Tính date_from = today - number_of_day
            if self.config_id.number_of_day:
                date_from = date.today() - timedelta(days=(self.config_id.number_of_day - 1))

                # Không nhỏ hơn date_start
                if self.config_id.date_start:
                    date_start = self.config_id.date_start.date() if isinstance(self.config_id.date_start,
                                                                                datetime) else self.config_id.date_start
                    if date_from < date_start:
                        date_from = date_start

                self.date_from = date_from
                self._onchange_date_from()

    @api.onchange('date_from')
    def _onchange_date_from(self):
        """Tính date_to = date_from + number_of_day"""
        if self.date_from:
            number_of_day = self.config_id.number_of_day if self.config_id else 0
            self.date_to = self.date_from + timedelta(days=(number_of_day - 1))

    # ================================================================
    # CREATE METHOD
    # ================================================================

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('pic.ecommerce.session') or 'New'
        return super(PICEcommerceSession, self).create(vals)

    # ================================================================
    # CORE WORKFLOW METHODS
    # ================================================================

    def action_confirm(self):
        """Đồng bộ data từ platform API"""
        self._ecommerce_get_orders()
        self._ecommerce_get_returns()
        self._ecommerce_get_payments()

        self.write({
            'user_id': self.env.user.id,
            'date_confirm': fields.Datetime.now(),
            'state': 'confirm',
        })

    def action_create_ecommerce_transaction(self):
        """Tạo transactions từ data đã đồng bộ"""
        # Xóa dữ liệu draft cũ
        self.env['pic.ecommerce.order'].search([
            ('session_id', '=', self.id),
            ('state', '=', 'draft')
        ]).unlink()
        self.env['pic.ecommerce.payment'].search([
            ('session_id', '=', self.id), ('ecommerce_id', '=', False),
            ('state', '=', 'draft')
        ]).unlink()
        self.env['pic.ecommerce.return'].search([
            ('session_id', '=', self.id),
            ('state', '=', 'draft')
        ]).unlink()

        # Tạo giao dịch mới
        if self.order_items:
            order_items = eval(self.order_items)
            self._transaction_create_ecommerce_order(order_items)

        if self.return_order_items:
            return_order_items = eval(self.return_order_items)
            self._transaction_create_return_order(return_order_items)

        if self.payment_orders:
            payment_orders = eval(self.payment_orders)
            self._transaction_create_payment(payment_orders)

        # Cập nhật state
        self.write({'state': 'processing'})

        # Auto confirm orders
        self._auto_confirm_session_orders()

    def _auto_confirm_session_orders(self):
        """Tự động confirm các orders trong session"""
        orders = self.ecommerce_ids.filtered(lambda o: o.state == 'draft')

        for order in orders:
            try:
                order.action_confirm()
            except Exception as e:
                _logger.error(f"Error auto-confirm order {order.name}: {str(e)}")
                continue

    def action_create_sale_order(self):
        """Tạo Sale Order từ các orders đã confirm"""
        orders_to_process = self.ecommerce_ids.filtered(
            lambda o: o.state == 'confirm' and not o.last_sale_id
                      and (not o.config_id or not o.config_id.date_start or o.date_order >= o.config_id.date_start)
        )

        for order in orders_to_process:
            try:
                order.action_create_sale_order()
            except Exception as e:
                _logger.error(f"Error creating SO for {order.name}: {str(e)}")
                continue

        # Check hoàn thành
        if not self.warning:
            self.action_done()

    def action_done(self):
        """Hoàn thành session"""
        unprocessed = self.ecommerce_ids.filtered(lambda x: x.state not in ("done", "cancel"))

        if not unprocessed:
            self.write({
                'date_done': fields.Datetime.now(),
                'state': 'done'
            })

    def action_cancel(self):
        """Hủy session"""
        self.write({'state': 'cancel'})

    def action_draft(self):
        """Về dự thảo"""
        self.write({
            'orders': False,
            'order_items': False,
            'return_orders': False,
            'return_order_items': False,
            'payment_orders': False,
            'date_confirm': False,
            'date_done': False,
            'user_id': False,
            'state': 'draft'
        })

    # ================================================================
    # PLATFORM API METHODS (Hook methods - Override in platform module)
    # ================================================================

    def _ecommerce_get_orders(self):
        """Hook method: Lấy danh sách đơn hàng từ platform"""
        return True

    def _ecommerce_get_returns(self):
        """Hook method: Lấy danh sách trả hàng từ platform"""
        return True

    def _ecommerce_get_payments(self):
        """Hook method: Lấy danh sách thanh toán từ platform"""
        return True

    # ================================================================
    # TRANSACTION CREATION METHODS (Hook methods - Override in platform module)
    # ================================================================

    def _transaction_create_ecommerce_order(self, order_items):
        """Hook method: Tạo ecommerce orders từ order_items"""
        pass

    def _transaction_create_return_order(self, return_order_items):
        """Hook method: Tạo return orders từ return_order_items"""
        pass

    def _transaction_create_payment(self, payment_orders):
        """Hook method: Tạo payments từ payment_orders"""
        pass

    # ================================================================
    # VIEW ACTION METHODS
    # ================================================================

    def action_view_pic_ecommerce_order(self):
        """Mở view Đơn hàng TMĐT"""
        return {
            'name': 'Đơn hàng TMĐT',
            'res_model': 'pic.ecommerce.order',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'domain': [('session_id', '=', self.id)],
        }

    def action_view_pic_ecommerce_payment(self):
        """Mở view Thanh toán TMĐT"""
        return {
            'name': 'Thanh toán TMĐT',
            'res_model': 'pic.ecommerce.payment',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'domain': [('session_id', '=', self.id)],
        }

    def action_view_pic_ecommerce_return(self):
        """Mở view Trả hàng TMĐT"""
        return {
            'name': 'Trả hàng/Hoàn tiền TMĐT',
            'res_model': 'pic.ecommerce.return',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'domain': [('session_id', '=', self.id)],
        }

    # ================================================================
    # CRON JOB METHODS
    # ================================================================

    @api.model
    def auto_create_pic_ecommerce_session(self):
        """
        Cron job: Tạo phiên đồng bộ tự động
        - Tạo session
        - Đồng bộ data từ platform
        - Tạo transactions (orders)
        - Tự động confirm orders
        """
        config_ids = self.env['pic.ecommerce.config'].search([
            ('type', 'not in', [False, 'company']),
            ('environment', '=', 'live'),
        ])

        for config in config_ids:
            try:
                # Tạo session
                session = self.create({
                    'config_id': config.id,
                    'partner_id': config.partner_id.id,
                    'partner_shipping_id': config.partner_shipping_id.id,
                    'partner_invoice_id': config.partner_invoice_id.id,
                    'pricelist_id': config.pricelist_id.id,
                    'payment_term_id': config.payment_term_id.id,
                    'warehouse_id': config.warehouse_id.id,
                    'source_id': config.source_id.id,
                    'date': fields.Datetime.now(),
                })

                # Set date_from/date_to
                session._onchange_config_id()

                # Đồng bộ data
                session.action_confirm()

                # Tạo transactions
                session.action_create_ecommerce_transaction()

                _logger.info(f"Session {session.name} created and processed")

            except Exception as e:
                _logger.error(f"Error creating session for {config.name}: {str(e)}")
                continue

    @api.model
    def auto_create_sale_order(self):
        """
        Cron job: Tự động tạo Sale Order
        - Search orders ở state=confirm
        - Tạo Sale Order
        """
        orders = self.env['pic.ecommerce.order'].search([
            ('config_id.type', '!=', False),
            ('state', 'in', ('confirm', 'sale')),
            ('last_sale_id', '=', False)
        ], limit=20)

        for order in orders:
            try:
                order.action_create_sale_order()
            except Exception as e:
                _logger.error(f"Error creating SO for {order.name}: {str(e)}")
                continue

    @api.model
    def auto_confirm_sale_order(self):
        """
        Cron job: Tự động confirm Sale Order
        - Search SO ở state draft/sent
        - Validate và confirm
        """
        sale_orders = self.env['sale.order'].search([
            ('ecommerce_id.config_id.type', 'not in', ('company', 'tiktok')),
            ('state', 'in', ('draft', 'sent')),
            ('ecommerce_order_status', 'in', ('TO_SHIP', 'READY_TO_SHIP'))
        ], limit=10)

        for so in sale_orders:
            try:
                warning = so._valid_ecommerce_data()
                if not warning:
                    so.action_confirm()
            except Exception as e:
                _logger.error(f"Error confirming SO {so.name}: {str(e)}")
                continue

    @api.model
    def auto_update_delivery_result(self):
        """Cron job: Cập nhật kết quả giao hàng"""
        payments = self.env['pic.ecommerce.payment'].search([
            ('state', 'in', ('draft', 'confirm'))
        ], limit=100)

        payments.action_delivery_result()

    @api.model
    def auto_attach_awb_order(self):
        """Cron job: Đính kèm vận đơn"""
        sale_orders = self.env['sale.order'].search([
            ('state', 'in', ('draft', 'sent')),
            ('ecommerce_order_status', 'in', ('TO_SHIP', 'READY_TO_SHIP')),
            ('config_id.type', '=', 'shopee')
        ], limit=5)

        for so in sale_orders:
            try:
                so.attachment_airway_bill()
            except Exception as e:
                _logger.error(f"Error attaching AWB for {so.name}: {str(e)}")
                continue

    @api.model
    def auto_action_to_pack(self):
        """Cron job: Xử lý đơn TO_PACK"""
        orders = self.env['pic.ecommerce.order'].search([
            ('last_sale_id', '!=', False),
            ('order_status', '=', 'TO_PACK'),
            ('config_id.type', '!=', 'company')
        ], limit=5)

        for order in orders:
            try:
                order.action_to_pack()
            except Exception as e:
                _logger.error(f"Error action_to_pack for {order.name}: {str(e)}")
                continue
