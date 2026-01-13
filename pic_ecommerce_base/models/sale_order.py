# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
import requests
import time
import base64


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ================================================================
    # FIELDS
    # ================================================================

    ecommerce_id = fields.Many2one('pic.ecommerce.order', string="Đơn hàng TMĐT", copy=False)
    ecommerce_order_status = fields.Selection(string="Trạng thái đơn TMĐT", related='ecommerce_id.order_status')
    config_type = fields.Selection(related="ecommerce_id.config_type", store=True)
    carrier_tracking_ref = fields.Char(string="Mã vận đơn")
    carrier_date = fields.Datetime(string="Ngày giao hàng")
    ecommerce_attached = fields.Boolean(string="Đã đính kèm vận đơn")
    pic_tracking_url = fields.Char(
        string="Đơn hàng ECOM", compute='_compute_pic_tracking_url', store=True, readonly=False, copy=False)

    # ================================================================
    # COMPUTE METHODS
    # ================================================================

    @api.depends('ecommerce_id', 'ecommerce_id.pic_tracking_url')
    def _compute_pic_tracking_url(self):
        for record in self:
            if record.ecommerce_id:
                record.pic_tracking_url = record.ecommerce_id.pic_tracking_url
            else:
                record.pic_tracking_url = False

    @api.depends('partner_id', 'partner_shipping_id', 'ecommerce_id')
    def _compute_address(self):
        for record in self:
            if record.ecommerce_id and record.ecommerce_id.config_type != "company":
                record.region_id = record.ecommerce_id.region_id.id
                record.area_id = record.ecommerce_id.area_id.id
                record.country_id = record.ecommerce_id.country_id.id
                record.state_id = record.ecommerce_id.state_id.id
                record.district_id = record.ecommerce_id.district_id.id
                record.ward_id = record.ecommerce_id.ward_id.id
            else:
                super(SaleOrder, self)._compute_address()

    # ================================================================
    # CONSTRAINTS
    # ================================================================

    @api.constrains('partner_id')
    def _check_ecommerce_partner_id(self):
        for record in self:
            if record.partner_id:
                is_api = self.env['pic.ecommerce.config'].search([('partner_id', '=', record.partner_id.id)])
                if is_api and not record.ecommerce_id:
                    raise ValidationError("Bạn phải tạo đơn hàng bán từ nguồn Đơn hàng TMĐT")

    @api.constrains('ecommerce_id')
    def _check_ecommerce_id(self):
        for record in self:
            if record.ecommerce_id:
                check = self.env['sale.order'].search(
                    [('id', '!=', record.id), ('ecommerce_id', '=', record.ecommerce_id.id), ('state', '!=', 'cancel')])
                if check:
                    raise ValidationError(f"Đơn hàng thương mại điện tử đã được tạo: {check[0].name}")

    # ================================================================
    # VALIDATION METHODS
    # ================================================================

    def _check_ecommerce_amount_total(self):
        """
        CRITICAL: Kiểm tra tiền SO = tiền Ecommerce
        Override method này trong platform module nếu cần logic khác

        Returns:
            str: Warning message nếu không khớp, empty string nếu OK
        """
        self.ensure_one()

        if not self.ecommerce_id:
            return ''

        # Get amounts
        ecom_amount = self.ecommerce_id.ecommerce_amount
        so_amount = self.amount_total

        # Compare với precision 2 decimal places
        compare_result = float_compare(so_amount, ecom_amount, precision_digits=2)

        if compare_result != 0:
            diff = so_amount - ecom_amount
            warning = (
                f"⛔ TIỀN KHÔNG KHỚP:\n"
                f"   • Đơn TMĐT: {ecom_amount:,.0f} VND\n"
                f"   • Đơn Sale: {so_amount:,.0f} VND\n"
                f"   • Chênh lệch: {diff:,.0f} VND\n"
            )

            # Thêm info về voucher nếu có
            if self.ecommerce_id.voucher_code:
                warning += f"   • Mã voucher: {self.ecommerce_id.voucher_code}\n"

            return warning

        return ''

    def _check_ecommerce_attachment(self):
        """
        Kiểm tra vận đơn đã đính kèm chưa
        Override trong platform module nếu cần

        Returns:
            str: Warning message hoặc empty string
        """
        return ''

    def _valid_ecommerce_data(self):
        """
        Validate toàn bộ dữ liệu ecommerce trước khi confirm

        Returns:
            str: Warning message (block confirm) hoặc empty string (OK)
        """
        warning = ''

        # Check trùng mã vận đơn
        if self.carrier_tracking_ref:
            check = self.env['sale.order'].search([
                ('id', '!=', self.id),
                ('carrier_tracking_ref', '=', self.carrier_tracking_ref),
                ('state', '!=', 'cancel')
            ])
            if check:
                warning += f"⚠️ Trùng mã vận đơn: {check[0].name}\n"

        # Validate cho đơn từ ecommerce (không phải company)
        if self.config_type != "company":
            # CRITICAL: Check amount matching
            amount_warning = self._check_ecommerce_amount_total()
            if amount_warning:
                warning += amount_warning

            # Check attachment
            attachment_warning = self._check_ecommerce_attachment()
            if attachment_warning:
                warning += attachment_warning

        return warning

    # ================================================================
    # ACTION METHODS
    # ================================================================

    def action_confirm(self):
        """Override: Validate ecommerce data trước khi confirm"""
        for order in self:
            if order.ecommerce_id:
                warning = order._valid_ecommerce_data()
                if warning:
                    raise ValidationError(f"Không thể xác nhận đơn hàng {order.name}:\n\n{warning}")

        return super(SaleOrder, self).action_confirm()

    def action_ecommerce_trigger_onchange(self):
        """Trigger các onchange sau khi tạo SO"""
        return True

    def action_to_ship(self):
        """Gửi đơn sang sàn TMĐT"""
        for record in self.filtered(lambda sale: sale.ecommerce_id and sale.state in ('sale', 'done') \
                                                 and sale.ecommerce_id.order_status in ('TO_SHIP')):
            record.ecommerce_id.action_to_ship()

    def attachment_airway_bill(self):
        """Đính kèm vận đơn - Override trong platform module"""
        return True

    def pic_apply_coupon(self):
        """Apply coupon/voucher code"""
        if self.ecommerce_id.voucher_amount > 0 and self.ecommerce_id.voucher_code:
            coupon_apply_id = self.env['sale.coupon.apply.code'].with_context(active_id=self.id).create({
                'coupon_code': self.ecommerce_id.voucher_code
            })
            error_status = coupon_apply_id.apply_coupon(self, coupon_apply_id.coupon_code)

            if error_status.get('error', False) or error_status.get('not_found', False):
                ecommerce_coupon_ids = self.env["pic.ecommerce.coupon"].search(
                    [('promo_code', '=', self.ecommerce_id.voucher_code)])
                for coupon in ecommerce_coupon_ids:
                    coupon_apply_id = self.env['sale.coupon.apply.code'].with_context(active_id=self.id).create({
                        'coupon_code': coupon.coupon_id.promo_code
                    })
                    error_status = coupon_apply_id.apply_coupon(self, coupon_apply_id.coupon_code)

                    if not error_status.get('error', False) and not error_status.get('not_found', False):
                        return

    # ================================================================
    # WRITE METHOD
    # ================================================================

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for record in self:
            if 'state' in vals and record.ecommerce_id:
                record.ecommerce_id.write({
                    'state': 'done' if record.state not in ('draft', 'cancel') else 'confirm',
                })
        return res

    def _prepare_confirmation_values(self):
        """Preserve date_order khi confirm"""
        date_order = self.date_order
        res = super(SaleOrder, self)._prepare_confirmation_values()
        if date_order:
            res['date_order'] = date_order
        return res
