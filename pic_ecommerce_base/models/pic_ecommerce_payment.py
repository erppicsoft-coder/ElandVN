# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from datetime import datetime, time, timedelta


class PICEcommercePayment(models.Model):
    _name = 'pic.ecommerce.payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Thanh toán thương mại điện tử"
    _order = "create_time DESC"

    # THÔNG TIN CHUNG
    name = fields.Char(string='Giao dịch số')
    create_time = fields.Datetime(string='Ngày thanh toán')
    statement_time = fields.Datetime(string='Ngày quyết toán')
    date = fields.Date(string='Ngày giao dịch', compute='_compute_date', store=True)
    user_id = fields.Many2one('res.users', string='Người phụ trách')
    status = fields.Char(string='Trạng thái thanh toán')

    buyer_name = fields.Char(string='Người mua')
    origin = fields.Char(string='Tham chiếu')
    description = fields.Char(string='Nội dung giao dịch')
    state = fields.Selection([
        ('draft', 'Dự thảo'), ('confirm', 'Kiểm tra'),
        ('done', 'Hoàn thành'), ('cancel', 'Hủy')
    ], default="draft", string="Trạng thái")
    company_id = fields.Many2one(
        'res.company', string='Công ty', required=True, default=lambda self: self.env.company.id)
    currency_id = fields.Many2one(
        'res.currency', string='Tiền tệ', required=True, default=lambda self: self.env.company.currency_id.id)

    # PHÂN TÍCH
    payment_type = fields.Selection(
        selection=[('inbound', 'Tiền vào'), ('outbound', 'Tiền ra')], string='Loại thanh toán',
        compute='_compute_payment_type', store=True)
    transaction_type = fields.Char(string='Loại giao dịch')
    fee_type = fields.Char(string='Loại phí')
    wallet_type = fields.Char(string='Loại ví điện tử')
    withdrawal_type = fields.Char(string='Loại rút tiền')

    # GIÁ TRỊ
    response_data = fields.Text(string="Dữ liệu phản hồi")
    revenue_amount = fields.Float(string='Doanh thu')
    fee_amount = fields.Float(string='Chi phí')
    shipping_fee = fields.Float(string='Phí vận chuyển')
    transaction_fee = fields.Monetary(string='Phí giao dịch')

    current_balance = fields.Float(string='Cân đối')
    amount = fields.Monetary(string='Thanh toán')
    reason = fields.Char(string='Lý do')

    # THAM CHIẾU
    session_id = fields.Many2one('pic.ecommerce.session', string="Phiên đồng bộ")
    config_id = fields.Many2one('pic.ecommerce.config', string="Sàn TMĐT")

    order_sn = fields.Char(string='Đơn hàng TMĐT')
    ecommerce_id = fields.Many2one('pic.ecommerce.order', string='Đơn hàng TMĐT')

    refund_sn = fields.Char(string='Đơn hoàn TMĐT')
    refund_ecommerce_id = fields.Many2one('pic.ecommerce.order', string='Đơn hoàn TMĐT')

    # KIỂM TRA
    warning = fields.Text(string="Cảnh báo")

    @api.depends('create_time')
    def _compute_date(self):
        for record in self:
            if record.create_time:
                record.date = (record.create_time + timedelta(hours=7)).date()
            else:
                record.date = False

    @api.depends('amount')
    def _compute_payment_type(self):
        for record in self:
            if not record.amount:
                record.payment_type = False
            elif record.amount > 0:
                record.payment_type = "inbound"
            else:
                record.payment_type = "outbound"

    def action_view_ecommerce_order(self):
        ecommerce_orders = self.env['pic.ecommerce.order'].search([
            '|', ('name', '=', self.order_sn), ('name', '=', self.refund_sn)
        ])

        if not ecommerce_orders:
            raise ValidationError('Không tìm thấy bất kỳ Đơn hàng thương mại điện tử nào.')

        """Mở view Sale Orders"""
        if len(ecommerce_orders) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Đơn hàng TMĐT',
                'res_model': 'pic.ecommerce.order',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': ecommerce_orders[0].id,
            }
        else:
            return {
                'name': 'Đơn hàng TMĐT',
                'res_model': 'pic.ecommerce.order',
                'domain': [('id', 'in', ecommerce_orders.ids)],
                'view_mode': 'tree,form',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
            }
