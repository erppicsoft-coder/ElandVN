# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from datetime import datetime, time, timedelta
import time
from odoo.osv import expression
from odoo.tools import float_compare
import re
import logging

_logger = logging.getLogger(__name__)


class PICEcommerceOrder(models.Model):
    _name = 'pic.ecommerce.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Đơn hàng thương mại điện tử'
    _order = "create_time DESC"

    # ================================================================
    # FIELDS DEFINITION
    # ================================================================

    # --- 1.1. Thông tin cơ bản ---
    name = fields.Char(string="Đơn hàng số", copy=False, required=True)
    date = fields.Date(string="Ngày thực hiện", default=lambda self: fields.Datetime.today())
    user_id = fields.Many2one('res.users', string="Người phụ trách")
    create_time = fields.Datetime(string="Ngày tạo")
    date_order = fields.Date(string='Ngày đặt', compute='_compute_date_order', store=True)
    update_time = fields.Datetime(string="Ngày cập nhật")
    origin = fields.Char(string='Tài liệu gốc', copy=False)
    note = fields.Text(string='Ghi chú')
    state = fields.Selection([
        ('draft', 'Tiếp nhận'), ('validate', 'Kiểm tra'), ('confirm', 'Sẵn sàng'),
        ('done', 'Đơn hàng'), ('cancel', 'Hủy')
    ], default='draft', string="Trạng thái", tracking=True)
    company_id = fields.Many2one('res.company', string='Công ty', required=True,
                                 default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', required=True,
                                  default=lambda self: self.env.company.currency_id.id)

    # --- 1.2. Quan hệ config & platform ---
    config_id = fields.Many2one('pic.ecommerce.config', string='Nền tảng')
    config_type = fields.Selection(related="config_id.type", store=True)
    pic_tracking_url = fields.Char(string="Đường dẫn đơn", copy=False)
    session_id = fields.Many2one('pic.ecommerce.session', string="Phiên đồng bộ")

    business_model = fields.Selection([
        ('b2b', 'B2B'),
        ('b2c', 'B2C')
    ], string='Mô hình', tracking=True, index=True, default='b2b',
        help="Copy từ config khi tạo đơn")

    # --- 1.3. Toàn trình ---
    state_ids = fields.One2many('pic.ecommerce.order.state', 'ecommerce_id', string="Toàn trình")
    last_state_id = fields.Many2one('pic.ecommerce.order.state', string="Trạng thái gần nhất",
                                    compute='_compute_last_state_id')
    last_response_data = fields.Text(related='last_state_id.response_data')

    # --- 1.4. Chi tiết đơn hàng ---
    items = fields.One2many('pic.ecommerce.order.line', 'ecommerce_id', string='Chi tiết đơn hàng')

    ecommerce_payment_ids = fields.One2many('pic.ecommerce.payment', 'ecommerce_id', string='Thanh toán')
    ecommerce_payment_count = fields.Integer(
        string='# Thanh toán', compute='_compute_ecommerce_payment_count')

    # --- 1.5. Quan hệ Sale Orders (MASTER) ---
    sale_ids = fields.One2many('sale.order', 'ecommerce_id', string='Đơn hàng bán', copy=False)
    sale_count = fields.Integer(string="Đơn hàng bán", compute="_compute_sale_ids", copy=False, store=True)
    sale_status = fields.Selection([
        ('no', 'Không có đơn hàng'),
        ('to_sale', 'Đã lập một phần'),
        ('sold', 'Đã đặt bán đủ')
    ], string="Trạng thái đơn hàng", compute='_compute_sale_status', store=True)
    last_sale_id = fields.Many2one('sale.order', 'Đơn hàng bán', compute="_compute_sale_ids", copy=False, store=True)
    last_sale_amount = fields.Monetary(string='Tổng tiền đơn bán', related='last_sale_id.amount_total')

    # --- 1.6. Aggregate Pickings ---
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string="Phiếu kho")
    picking_count = fields.Integer(string="Giao hàng", compute='_compute_picking_ids')
    delivery_status = fields.Selection([
        ('pending', 'Chưa giao'),
        ('partial', 'Đã giao một phần'),
        ('full', 'Đã giao hết'),
    ], compute='_compute_delivery_status', store=True, string="Trạng thái giao hàng")

    # --- 1.7. Aggregate Invoices ---
    invoice_ids = fields.Many2many('account.move', compute='_compute_invoice_ids', string="Hóa đơn")
    invoice_count = fields.Integer(string="Hóa đơn", compute='_compute_invoice_ids')
    invoice_status = fields.Selection([
        ('no', 'Không có hóa đơn cần xuất'),
        ('to_invoice', 'Cần xuất hóa đơn'),
        ('invoiced', 'Đã xuất hóa đơn hết')
    ], compute='_compute_invoice_status', store=True, string="Trạng thái hóa đơn")

    # --- 1.8. Thông tin giao hàng ---
    cod = fields.Boolean(string="Là đơn COD")
    tracking_no = fields.Char(string="Mã điều vận", readonly=True)
    days_to_ship = fields.Integer(string="Số ngày giao hàng")
    shipping_carrier = fields.Char("Phương thức vận tải")
    checkout_shipping_carrier = fields.Char("Gói vận chuyển")
    ship_by_date = fields.Datetime(string="Thời gian giao hàng")
    date_delivered = fields.Datetime(string="Ngày giao hàng", compute='_compute_date_delivered', store=True)
    ship_fee = fields.Float(string="Phí vận chuyển")
    cod_fee = fields.Float(string="Phí thu tiền hộ")
    over_weight_ship_fee = fields.Float(string="Phí vượt cân")
    return_fee = fields.Float(string="Phí chuyển hoàn")
    customer_ship_fee = fields.Float(string="Phí ship báo khách")
    ecom_fee = fields.Float(string="Tổng các loại phí trên sàn")

    # --- 1.9. Thông tin tiền ---
    platform_voucher_amount = fields.Float(string="Trợ giá từ sàn")
    ecommerce_amount = fields.Float("Thành tiền", compute="_compute_ecommerce_amount", store=True)
    voucher_code = fields.Char(string="Mã giảm giá")
    voucher_amount = fields.Float(string="Tiền giảm giá")
    business_cod = fields.Monetary(string="Tiền thu hộ")
    business_payment = fields.Monetary(string="Tiền đã thanh toán")

    # --- 1.10. Thông tin trạng thái ---
    auto_or_manual = fields.Selection([('auto', 'Tự động'), ('manual', 'Thủ công')], string='Hình thức tạo đơn')
    order_status = fields.Selection([
        ('UNPAID', 'Chờ thanh toán'),
        ('TO_PACK', 'Chờ lấy hàng'), ('TO_SHIP', 'Chờ đóng gói'), ('READY_TO_SHIP', 'Chờ bàn giao'),
        ('PROCESSED', 'Đang giao'), ('RETRY_SHIP', 'Giao lại'), ('SHIPPED', 'Đã giao'),
        ('TO_CONFIRM_RECEIVE', 'Chờ xác nhận nhận hàng'), ('COMPLETED', 'Hoàn thành'),
        ('INVOICE_PENDING', 'Chờ hóa đơn'), ('INCIDENT', 'Sự cố'),
        ('IN_CANCEL', 'Chờ hủy'), ('CANCELLED', 'Đã hủy'),
        ('TO_RETURN', 'Chờ thu hồi'), ('RETURNED', 'Đã thu hồi'),
    ], string="Trạng thái nghiệp vụ", tracking=True)

    # Thông tin người mua
    recipient_id = fields.Many2one('res.partner', string='Người mua', copy=False, index=True)
    recipient_full_address = fields.Char(string="Địa chỉ người mua")
    recipient_phone = fields.Char(string="Điện thoại người mua")
    recipient_name = fields.Char(string="Tên người mua")
    recipient_email = fields.Char(string="Email người mua")

    # Quản lý hóa đơn
    take_einvoice = fields.Boolean(string='Lấy hóa đơn', default=False)
    invoice_partner_name = fields.Char(
        string='Tên công ty (XHĐ)', related='partner_invoice_id.name', store=True, readonly=False)
    invoice_vat = fields.Char(string='Mã số thuế (XHĐ)', related='partner_invoice_id.vat', store=True, readonly=False)
    invoice_address = fields.Char(
        string='Địa chỉ (XHĐ))', compute='_compute_invoice_address', store=True, readonly=False)

    partner_id = fields.Many2one('res.partner', string="Khách hàng")
    partner_invoice_id = fields.Many2one('res.partner', string='Địa chỉ xuất hóa đơn')
    partner_shipping_id = fields.Many2one('res.partner', string='Địa chỉ giao hàng')

    # --- 1.11. Thông tin mặc định ---
    payment_term_id = fields.Many2one("account.payment.term", string="Điều khoản thanh toán")
    pricelist_id = fields.Many2one('product.pricelist', string='Bảng giá')
    warehouse_id = fields.Many2one("stock.warehouse", "Nhà kho")
    source_id = fields.Many2one("utm.source", "Nguồn")

    # --- 1.12. Thông tin kiểm tra ---
    warning = fields.Text(string="Cảnh báo", readonly=True)
    is_incident = fields.Boolean(string="Sự cố?", compute='_compute_is_incident', store=True)
    is_auto_check_pricelist = fields.Boolean(string="Tự động tìm kiếm bảng giá", default=True)

    # --- 1.13. Địa chỉ giao hàng---
    country_name = fields.Char('Quốc gia')
    state_name = fields.Char('Tỉnh/TP')
    district_name = fields.Char('Quận/Huyện')
    ward_name = fields.Char('Phường/Xã')
    region_id = fields.Many2one('pic.country.region', string="Vùng", compute='_compute_area_id', store=True)
    area_id = fields.Many2one('pic.country.area', string="Khu vực", compute='_compute_area_id', store=True)
    country_id = fields.Many2one('res.country', string='Quốc gia', compute='_compute_country_id', store=True)
    state_id = fields.Many2one('res.country.state', string='Tỉnh/TP', compute='_compute_state_id', store=True)
    district_id = fields.Many2one('res.country.district', string="Quận/Huyện", compute='_compute_district_id',
                                  store=True)
    ward_id = fields.Many2one('res.country.ward', string="Phường/Xã", compute='_compute_ward_id', store=True)

    # --- 1.14. Loại bỏ ---
    ordersn = fields.Char(string="Mã đơn trên sàn", compute='_compute_ordersn', store=True)

    # ================================================================
    # COMPUTE METHODS - Basic Fields
    # ================================================================

    def _compute_ecommerce_payment_count(self):
        for record in self:
            record.ecommerce_payment_count = len(record.ecommerce_payment_ids)

    @api.depends('state_ids')
    def _compute_last_state_id(self):
        """Tính trạng thái gần nhất từ toàn trình"""
        for record in self:
            if record.state_ids:
                sorted_states = record.state_ids.sorted(key=lambda s: s.update_time or fields.Datetime.min,
                                                        reverse=True)
                record.last_state_id = sorted_states[0].id
            else:
                record.last_state_id = False

    @api.depends('name')
    def _compute_ordersn(self):
        """DEPRECATED - Tương thích ngược"""
        for record in self:
            record.ordersn = record.name

    @api.depends('create_time')
    def _compute_date_order(self):
        """Tính ngày đặt hàng từ create_time"""
        for record in self:
            if record.create_time:
                record.date_order = (record.create_time + timedelta(hours=7)).date()
            else:
                record.date_order = False

    @api.depends('ship_by_date')
    def _compute_date_delivered(self):
        """Tính ngày giao hàng từ ship_by_date"""
        for record in self:
            if record.ship_by_date:
                record.date_delivered = (record.ship_by_date + timedelta(hours=7)).date()
            else:
                record.date_delivered = False

    @api.depends("items", "voucher_amount", "platform_voucher_amount")
    def _compute_ecommerce_amount(self):
        """Tính tổng tiền đơn hàng"""
        for record in self:
            record.ecommerce_amount = sum(record.items.mapped('subtotal'))

    @api.depends('tracking_no', 'last_sale_id', 'order_status', 'ecommerce_amount', 'last_sale_amount')
    def _compute_is_incident(self):
        """Kiểm tra sự cố"""
        for record in self:
            record.is_incident = False
            if (record.last_sale_id and record.platform_voucher_amount and
                    record.last_sale_amount != record.ecommerce_amount):
                record.is_incident = True

    # ================================================================
    # COMPUTE METHODS - Aggregate Sale Orders
    # ================================================================

    @api.depends('sale_ids', 'sale_ids.state')
    def _compute_sale_ids(self):
        """Tính sale_count và last_sale_id"""
        for record in self:
            record.sale_count = len(record.sale_ids)
            sale_ids = record.sale_ids.filtered(lambda x: x.state != 'cancel')
            # if not sale_ids:
            #     sale_ids = record.sale_ids.filtered(
            #         lambda x: x.state == 'cancel' and x.delivery_order_id and x.delivery_order_id.state != "cancel")
            record.last_sale_id = sale_ids[0] if sale_ids else False

    @api.depends('sale_ids', 'sale_ids.state', 'sale_ids.order_line', 'sale_ids.order_line.price_total',
                 'ecommerce_amount')
    def _compute_sale_status(self):
        for record in self:
            # Get active sale orders
            sale_orders = record.sale_ids.filtered(lambda x: x.state != 'cancel')

            if not sale_orders:
                record.sale_status = 'no' if record.state in ('confirm', 'sale') else False
                continue

            # Calculate total SO amount
            total_sale_amount = sum(sale_orders.mapped('amount_total'))

            # Compare với precision 2 decimal places (tiền tệ)
            compare_result = float_compare(total_sale_amount, record.ecommerce_amount, precision_digits=2)

            if compare_result >= 0:
                record.sale_status = 'sold'
            else:
                record.sale_status = 'partial'

    # ================================================================
    # COMPUTE METHODS - Aggregate Pickings
    # ================================================================

    @api.depends('sale_ids', 'sale_ids.picking_ids')
    def _compute_picking_ids(self):
        """Aggregate pickings từ tất cả Sale Orders"""
        for order in self:
            order.picking_ids = order.sale_ids.mapped('picking_ids')
            order.picking_count = len(order.picking_ids)

    @api.depends('picking_ids.state')
    def _compute_delivery_status(self):
        """Tính trạng thái giao hàng từ pickings"""
        for order in self:
            picking_ids = order.picking_ids
            if not picking_ids or all(p.state == 'cancel' for p in picking_ids):
                order.delivery_status = False
            elif all(p.state in ['done', 'cancel'] for p in picking_ids):
                order.delivery_status = 'full'
            elif any(p.state == 'done' for p in picking_ids):
                order.delivery_status = 'partial'
            else:
                order.delivery_status = 'pending'

    # ================================================================
    # 5️⃣ COMPUTE METHODS - Aggregate Invoices
    # ================================================================

    @api.depends('sale_ids', 'sale_ids.invoice_ids')
    def _compute_invoice_ids(self):
        """Aggregate invoices từ tất cả Sale Orders"""
        for order in self:
            order.invoice_ids = order.sale_ids.mapped('invoice_ids')
            order.invoice_count = len(order.invoice_ids)

    @api.depends('sale_ids.invoice_status')
    def _compute_invoice_status(self):
        """Tính trạng thái hóa đơn từ Sale Orders"""
        for order in self:
            active_sos = order.sale_ids.filtered(lambda s: s.state != 'cancel')
            if not active_sos:
                order.invoice_status = False
            elif all(so.invoice_status == 'invoiced' for so in active_sos):
                order.invoice_status = 'invoiced'
            elif all(so.invoice_status == 'no' for so in active_sos):
                order.invoice_status = 'no'
            else:
                order.invoice_status = 'to_invoice'

    # ================================================================
    # COMPUTE METHODS - Address
    # ================================================================

    @api.depends('country_name')
    def _compute_country_id(self):
        """Tính country_id từ country_name"""
        for record in self:
            record.country_id = False

    @api.depends('state_name')
    def _compute_state_id(self):
        """Tính state_id từ state_name"""
        for record in self:
            record.state_id = False

    @api.depends('state_id', 'district_name')
    def _compute_district_id(self):
        """Tính district_id từ district_name"""
        for record in self:
            record.district_id = False

    @api.depends('district_id', 'ward_name')
    def _compute_ward_id(self):
        """Tính ward_id từ ward_name"""
        for record in self:
            record.ward_id = False

    @api.depends('state_id', 'district_id', 'ward_id')
    def _compute_area_id(self):
        """Tính area_id và region_id"""
        for record in self:
            record.area_id = False
            record.region_id = False

    # ================================================================
    # DATA SYNC METHODS
    # ================================================================

    def action_update_order_info(self, force_api_call=False, payload_data=None):
        """
        Cập nhật thông tin đơn hàng từ platform

        Logic cascade:
            1. force_api_call=True → Call API (bỏ qua cache)
            2. Có payload_data → Dùng payload_data
            3. Có last_response_data → Parse và dùng cache
            4. Không có gì → Bắt buộc call API
        """
        self.ensure_one()

        # CASE 1: Force call API
        if force_api_call:
            payload_data = self._fetch_order_from_platform()
            if not payload_data:
                raise ValidationError(_("Không thể lấy thông tin đơn hàng từ sàn TMĐT!"))
            self._update_from_payload(payload_data)
            self._log_state_change('Cập nhật thông tin từ API (force)', payload_data, source='api')
            return True

        # CASE 2: Có payload_data truyền vào
        if payload_data:
            self._update_from_payload(payload_data)
            self._log_state_change('Cập nhật thông tin từ webhook', payload_data, source='webhook')
            return True

        # CASE 3: Dùng last_response_data (cache)
        if self.last_response_data:
            try:
                import json
                cached_payload = json.loads(self.last_response_data)
                self._update_from_payload(cached_payload)
                return True
            except Exception:
                pass

        # CASE 4: Bắt buộc call API
        payload_data = self._fetch_order_from_platform()
        if not payload_data:
            raise ValidationError(_("Không thể lấy thông tin đơn hàng từ sàn TMĐT!"))
        self._update_from_payload(payload_data)
        self._log_state_change('Cập nhật thông tin từ API (auto)', payload_data, source='api')
        return True

    def _fetch_order_from_platform(self):
        """Hook method: Fetch order từ platform API - Override trong platform module"""
        return None

    def _update_from_payload(self, payload_data):
        """Update order fields từ payload data"""
        if not payload_data:
            return

        vals = self._prepare_update_vals_from_payload(payload_data)
        if vals:
            self.write(vals)

        self._update_order_lines_from_payload(payload_data)

    def _prepare_update_vals_from_payload(self, payload_data):
        """Hook method: Parse payload → vals - Override trong platform module"""
        return {}

    def _update_order_lines_from_payload(self, payload_data):
        """Hook method: Update order lines - Override trong platform module"""
        pass

    def _log_state_change(self, description, response_data, source='api'):
        """Ghi log vào toàn trình"""
        import json
        self.env['pic.ecommerce.order.state'].create({
            'ecommerce_id': self.id,
            'name': description,
            'update_time': fields.Datetime.now(),
            'order_status': self.order_status,
            'response_data': json.dumps(response_data, ensure_ascii=False, indent=2) if response_data else False,
            'source': source,
        })

    # ================================================================
    # ACTION METHODS - State Transitions
    # ================================================================

    # ================================================================
    # ACTION METHODS - State Transitions
    # ================================================================

    def action_confirm(self):
        """Button: Tiếp nhận đơn (draft → validate/confirm)"""
        self.ensure_one()

        # Link SO nếu đã tồn tại
        self.set_so_exists()
        if self.last_sale_id:
            self.state = 'done'
            return

        # Validate dữ liệu
        self._action_validate()

        # Check đơn hủy
        if self.order_status in ('IN_CANCEL', 'CANCELLED'):
            self.action_cancel()
            return

        # Chuyển state dựa trên kết quả validate
        if self.warning:
            self.state = 'validate'
        else:
            self.state = 'confirm'

    def action_validate(self):
        """Button: Kiểm tra (validate → confirm)"""
        self.ensure_one()
        self._action_validate()
        if not self.warning:
            self.state = 'confirm'

    def action_force_confirm(self):
        """Button: Bỏ qua cảnh báo (validate → confirm) - Admin only"""
        self.ensure_one()
        self.state = 'confirm'

    def action_create_sale_order(self):
        """Button: Tạo đơn hàng (confirm → done)"""
        self.ensure_one()
        if self.last_sale_id:
            return self.action_view_last_sale_id()

        if self.config_id and self.config_id.date_start and self.date_order < self.config_id.date_start.date():
            raise ValidationError(
                _('Không thể tạo đơn hàng bán lớn hơn ngày bắt đầu được khai báo trong cấu hình sàn!'))

        sale_order = self._action_create_sale_order()
        if sale_order:
            self.state = 'done'
            return self.action_view_sale_order()

    def action_done(self):
        """DEPRECATED - Giữ lại để tương thích code cũ"""
        pass

    def action_cancel(self):
        """Hủy đơn hàng ecommerce và sale orders"""
        for record in self:
            if record.order_status not in ("IN_CANCEL", "CANCELLED"):
                raise ValidationError(_('Bạn cần hủy đơn hàng trên sàn TMĐT trước khi thực hiện thao tác này!'))

            if record.last_sale_id:
                # Phải kiểm tra phiếu kho, hóa đơn, v.v. trước khi hủy đơn bán
                # if record.picking_ids.filtered(lambda p: p.state == 'done'):
                #     raise ValidationError(_('Không thể hủy đơn hàng bán khi có phiếu kho hoàn thành!'))
                # if record.invoice_ids.filtered(lambda inv: inv.state not in ('cancel', 'draft')):
                #     raise ValidationError(_('Không thể hủy đơn hàng bán khi có hóa đơn chưa hủy hoặc chưa ở trạng thái bản nháp!'))
                #
                # record.last_sale_id.with_context({'disable_cancel_warning': True}).action_cancel()
                continue
            else:
                record.state = "cancel"

    def action_draft(self):
        """Button: Về dự thảo - Admin only"""
        self.ensure_one()
        if self.last_sale_id:
            raise ValidationError(_("Không thể về dự thảo khi đã có đơn hàng bán!"))
        self.write({'state': 'draft', 'warning': False})

    def action_force_update_order_info(self):
        """Button wrapper: Force update từ API"""
        return self.action_update_order_info(force_api_call=True, payload_data=False)

    # ================================================================
    # VALIDATION METHODS
    # ================================================================

    def _action_validate(self):
        """Master validation - kiểm tra toàn bộ"""
        warning = ''

        # Validate products
        for line in self.items:
            if not line.item_sku and 1 == 0:
                warning = warning + '- Chưa có mã thương mại điện tử cho: ' + line.item_name + '\n'
            else:
                product_tmpl_ids = self.env['product.template'].search([
                    ('sale_ok', '=', True), ('detailed_type', '=', 'product'), ('default_code', '!=', False),
                    ('default_code', '=', line.item_sku)
                ])

                if not product_tmpl_ids or len(product_tmpl_ids) > 1:
                    product_tmpl_ids = self.env['product.template'].search([
                        ('sale_ok', '=', True), ('detailed_type', '=', 'product'),
                        ('name', '=', line.item_name)
                    ])
                if len(product_tmpl_ids) > 1:
                    warning = warning + '- Tồn tại nhiều mã thương mại điện tử: ' + line.item_sku + '\n'
                elif len(product_tmpl_ids) == 0:
                    warning = warning + '- Chưa có mã thương mại điện tử: ' + line.item_sku + '\n'
                elif len(product_tmpl_ids) == 1:
                    line.product_tmpl_id = product_tmpl_ids[0].id
                    line.code_product = product_tmpl_ids[0].default_code
                else:
                    line.product_tmpl_id = product_tmpl_ids[0].id
                    line.code_product = product_tmpl_ids[0].default_code

        # Validate address
        if not self.country_id and self.country_name:
            self._compute_country_id()
        if not self.state_id and self.state_name:
            self._compute_state_id()
        if not self.district_id and self.district_name:
            self._compute_district_id()
        if not self.ward_id and self.ward_name:
            self._compute_ward_id()

        # Validate tracking number
        if not self.tracking_no:
            self.get_tracking_no()

        # Validate order status
        if not self.order_status or self.order_status in ('UNPAID', 'IN_CANCEL', 'CANCELLED', 'TO_RETURN', 'RETURNED'):
            order_status_name = dict(self._fields['order_status'].selection).get(
                self.order_status, self.order_status)
            warning = warning + f"- Không thể tạo Đơn hàng bán ở trạng thái {order_status_name}.\n"

        if self.business_model == 'b2c':
            err = self._validate_recipient_info()
            if err:
                warning += f"\n{err}"

        if self.take_einvoice:
            err = self._validate_invoice_info()
            if err:
                warning += f"\n{err}"

        self.warning = warning

        return warning

    # ================================================================
    # SALE ORDER CREATION
    # ================================================================

    # ================================================================
    # SALE ORDER CREATION METHODS
    # ================================================================

    def _action_create_sale_order(self):
        """
        Main orchestrator: Tạo Sale Order từ Ecommerce Order

        Returns:
            sale.order: Sale Order đã tạo
        """
        self.ensure_one()

        # Nếu đã có SO → return
        if self.last_sale_id:
            return self.last_sale_id

        # 1. Prepare order lines
        order_lines = self._prepare_sale_order_lines()
        if not order_lines:
            raise ValidationError(_("Không có sản phẩm nào để tạo đơn hàng!"))

        # 2. Create Sale Order
        sale_order = self.sudo()._create_sale_order(order_lines)

        # 3. Process lines (discount, gift, etc.)
        self._process_sale_order_lines(sale_order)

        # 4. Apply voucher
        self._apply_voucher_to_sale_order(sale_order)

        # 5. Update logistics info
        self._update_sale_order_logistics(sale_order)

        return sale_order

    def _prepare_sale_order_lines(self):
        """
        Prepare order lines từ ecommerce items

        Returns:
            list: [(0, 0, {...}), ...]
        """
        lines = []

        for item in self.items:
            # Get product
            if not item.product_tmpl_id:
                _logger.warning(f"[{self.name}] Line {item.item_name} missing product, skip")
                continue

            product = item.product_tmpl_id.product_variant_ids[0]

            # Prepare line vals
            line_vals = self._prepare_sale_order_line_vals(item, product)
            lines.append((0, 0, line_vals))

        return lines

    def _prepare_sale_order_line_vals(self, ecom_line, product):
        """
        Hook method: Prepare vals cho 1 sale order line
        Override trong platform module nếu cần custom

        Args:
            ecom_line: pic.ecommerce.order.line
            product: product.product

        Returns:
            dict: Line values
        """
        return {
            'name': product.name,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': ecom_line.quantity,
            # 'price_unit': ecom_line.price,
            'price_unit': ecom_line.discounted_price,
            'ecommerce_line_id': ecom_line.id,
            'ecommerce_price': ecom_line.subtotal,
            'discount': 0,  # Sẽ tính sau trong _process_sale_order_lines, neéu láy giá sau chiet khau thi khoi can
        }

    def _prepare_sale_order_vals(self, order_lines):
        """
        Prepare vals để create Sale Order

        Args:
            order_lines: list of tuples [(0, 0, {...})]

        Returns:
            dict: Sale Order values
        """
        vals = self._get_ecommerce_sale_order_vals()
        vals['order_line'] = order_lines
        return vals

    def _create_sale_order(self, order_lines):
        """
        Create Sale Order và trigger onchange

        Args:
            order_lines: list of tuples

        Returns:
            sale.order: Sale Order đã tạo
        """
        # Prepare vals
        vals = self._prepare_sale_order_vals(order_lines)

        # Create SO
        sale_order = self.env['sale.order'].sudo().create(vals)

        # Trigger onchange
        sale_order.action_ecommerce_trigger_onchange()

        # Set shipping address
        if self.partner_shipping_id:
            sale_order.partner_shipping_id = self.partner_shipping_id.id

        return sale_order

    def _process_sale_order_lines(self, sale_order):
        """
        Process các sale order lines:
        - Apply discount
        - Handle gift products
        - Create cost lines

        Args:
            sale_order: sale.order
        """
        # Get product lines (không phải reward lines)
        product_lines = sale_order.order_line.filtered(lambda x: not x.is_reward_line_ecommerce)

        for line in product_lines:
            # Apply discount
            # self._apply_line_discount(line) # Đang lấy giá sau chiết khâu nên khong dung

            # Handle gift product
            if line.ecommerce_line_id and line.ecommerce_line_id.is_gift:
                self._create_gift_cost_line(sale_order, line)

    def _apply_line_discount(self, line):
        """
        Apply discount cho 1 sale order line

        Args:
            line: sale.order.line
        """
        if not line.ecommerce_line_id:
            return

        ecom_line = line.ecommerce_line_id
        original_price = line.price_unit

        # Tính giá sau discount
        discounted_price = ecom_line.discounted_price

        # Cộng lại platform voucher amount (nếu có)
        if ecom_line.platform_voucher_amount:
            discounted_price += ecom_line.platform_voucher_amount / ecom_line.quantity

        # Nếu là gift và không có giá → dùng giá gốc
        if ecom_line.is_gift and not discounted_price:
            discounted_price = ecom_line.original_price or original_price

        # Calculate discount percentage
        if original_price and discounted_price != original_price:
            discount_pct = 100 - (discounted_price / original_price * 100)
            line.discount = max(0, min(100, discount_pct))  # Clamp 0-100

    def _create_gift_cost_line(self, sale_order, product_line):
        """
        Tạo line chi phí cho gift product

        Args:
            sale_order: sale.order
            product_line: sale.order.line (gift product)
        """
        gift_product = self.config_id.gift_cost_product_id
        if not gift_product:
            return

        # Calculate cost = -price_total của gift line
        gift_cost = -product_line.price_total / product_line.product_uom_qty

        self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'name': f"Chi phí tặng: {product_line.product_id.name}",
            'product_id': gift_product.id,
            'product_uom': gift_product.uom_id.id,
            'product_uom_qty': product_line.product_uom_qty,
            'price_unit': gift_cost,
            'is_reward_line_ecommerce': True,
            'free_product_id': product_line.product_id.id,
        })

    def _apply_voucher_to_sale_order(self, sale_order):
        """
        Apply voucher cho Sale Order

        Args:
            sale_order: sale.order
        """
        if not self.voucher_amount:
            return

        voucher_product = self.config_id.voucher_cost_product_id
        if not voucher_product:
            _logger.warning(f"[{self.name}] Missing voucher_cost_product_id in config")
            return

        # Prepare voucher name
        voucher_name = voucher_product.name
        if self.voucher_code:
            voucher_name += f" - Mã: {self.voucher_code}"

        # Create voucher line
        self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'name': voucher_name,
            'product_id': voucher_product.id,
            'product_uom': voucher_product.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': -self.voucher_amount,
            'is_reward_line_ecommerce': True,
        })

    def _update_sale_order_logistics(self, sale_order):
        """
        Hook method: Update logistics info cho Sale Order
        Override trong platform module

        Args:
            sale_order: sale.order
        """
        self._ecommerce_update_logistic_data(sale_order)

    # ================================================================
    # HELPER METHODS
    # ================================================================

    def _get_ecommerce_sale_order_vals(self):
        vals = {
            'name': self.name,
            'ecommerce_id': self.id,
            'warehouse_id': self.warehouse_id.id,
            'source_id': self.source_id.id,
            'pricelist_id': self.pricelist_id.id,
            'payment_term_id': self.payment_term_id.id,
            'origin': self.get_client_order_ref(),
            'client_order_ref': self.name,
            'date_order': self.create_time,
            'commitment_date': self.ship_by_date,
        }

        if self.business_model == 'b2b':
            vals.update({
                'partner_id': self.partner_id.id,
                'partner_invoice_id': self.partner_invoice_id.id,
                'partner_shipping_id': self.partner_shipping_id.id,
            })
        else:
            platform = self._get_platform_partner()
            recipient = self._get_or_create_recipient_contact()
            invoice = self._get_or_create_invoice_partner()
            vals.update({
                'partner_id': platform.id,
                'partner_invoice_id': invoice.id if invoice else platform.id,
                'partner_shipping_id': recipient.id if recipient else platform.id,
            })

        return vals

    def action_confirm_sale_order(self):
        """Xác nhận Sale Order đã tạo"""
        warning = ""
        if self.last_sale_id and self.last_sale_id.state == "draft":
            warning = self.last_sale_id._valid_ecommerce_data()
            if warning == "":
                self.last_sale_id.action_confirm()
        self.warning = warning

    def set_so_exists(self):
        """Link SO hiện tại với ecommerce order"""
        sale_ids = self.env['sale.order'].sudo().search([
            ('state', 'not in', ('draft', 'cancel')),
            ('client_order_ref', '=', self.name)
        ])
        if sale_ids and self.name:
            sale_ids.write({'ecommerce_id': self.id})

    # ================================================================
    # 10. PLATFORM INTEGRATION HOOKS
    # ================================================================

    def action_to_pack(self):
        """Hook cho platform - Xử lý đơn TO_PACK"""
        return True

    def action_to_ship(self):
        """Hook cho platform - POST TO_SHIP"""
        return True

    def get_tracking_no(self):
        """Hook cho platform - Lấy tracking number"""
        return True

    def get_voucher(self):
        """Hook cho platform - Lấy thông tin voucher"""
        return True

    def _ecommerce_get_free_product_data(self, element):
        """Hook cho platform - Xác định sản phẩm miễn phí"""
        return False, 0.0

    def _ecommerce_get_line_discount(self, order_line):
        """Hook cho platform - Tính discount cho line"""
        return 0.0

    def _ecommerce_get_voucher_amount(self, current_voucher_amount, **vals):
        """Hook cho platform - Tính voucher amount"""
        return current_voucher_amount

    def _ecommerce_update_logistic_data(self, order_id):
        """Hook cho platform - Cập nhật logistics"""
        order_id.warehouse_id = self.warehouse_id.id
        return True

    # ================================================================
    # 11. VIEW ACTIONS
    # ================================================================

    def action_view_ecommerce_payment(self):
        """Mở view Sale Orders"""
        if self.ecommerce_payment_count == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Thanh toán TMĐT',
                'res_model': 'pic.ecommerce.payment',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': self.ecommerce_payment_ids[0].id,
            }
        else:
            return {
                'name': 'Thanh toán TMĐT',
                'res_model': 'pic.ecommerce.payment',
                'domain': [('ecommerce_id', 'in', self.ids)],
                'view_mode': 'tree,form',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
            }


    def action_view_sale_order(self):
        """Mở view Sale Orders"""
        if self.sale_count == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sales Order',
                'res_model': 'sale.order',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': self.sale_ids[0].id,
            }
        else:
            return {
                'name': 'Đơn Hàng',
                'res_model': 'sale.order',
                'domain': [('ecommerce_id', 'in', self.ids)],
                'view_mode': 'tree,form',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
            }

    def action_view_last_sale_id(self):
        """Mở view Sale Order chính"""
        if self.last_sale_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sales Order',
                'res_model': 'sale.order',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': self.last_sale_id.id,
            }

    def action_view_delivery(self):
        """Mở view Deliveries"""
        return self._get_action_view_picking(self.picking_ids)

    def _get_action_view_picking(self, pickings):
        """Helper: Chuẩn bị action view picking"""
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id

        picking_id = pickings.filtered(lambda l: l.picking_type_id.code == 'outgoing')
        if picking_id:
            picking_id = picking_id[0]
        else:
            picking_id = pickings[0]

        cleaned_context = {k: v for k, v in self._context.items() if k != 'form_view_ref'}
        action['context'] = dict(cleaned_context, default_partner_id=self.partner_id.id,
                                 default_picking_type_id=picking_id.picking_type_id.id, default_origin=self.name,
                                 default_group_id=picking_id.group_id.id)
        return action

    def action_view_invoice(self, invoices=False):
        """Mở view Invoices"""
        if not invoices:
            invoices = self.mapped('invoice_ids')
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {'default_move_type': 'out_invoice'}
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_partner_shipping_id': self.partner_shipping_id.id,
                'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or
                                                   self.env['account.move'].default_get(
                                                       ['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.name,
            })
        action['context'] = context
        return action

    # ================================================================
    # 12. HELPER METHODS
    # ================================================================

    def get_client_order_ref(self):
        """Tạo client_order_ref dựa trên shipping carrier"""
        client_order_ref = ''
        if self.shipping_carrier == 'BEST Express':
            client_order_ref = 'BEST-' + self.ordersn
        elif self.shipping_carrier == 'VNPost Nhanh':
            client_order_ref = 'VNP-' + self.ordersn
        elif self.shipping_carrier == 'Ninja Van':
            client_order_ref = 'NINJA-' + self.ordersn
        elif self.shipping_carrier == 'Shopee Express' or self.shipping_carrier == 'Shopee Xpress':
            client_order_ref = 'SHOPEE-' + self.ordersn
        elif self.shipping_carrier == 'J&T Express':
            client_order_ref = 'J&T-' + self.ordersn
        elif self.shipping_carrier == 'Viettel Post':
            client_order_ref = 'VTP-' + self.ordersn
        else:
            client_order_ref = self.ordersn
        return client_order_ref

    def action_update_address(self):
        """Cập nhật địa chỉ từ session data (legacy)"""
        records = self.env['pic.ecommerce.order'].search([('state', 'in', ('draft', 'validate'))])
        for record in records:
            if record.state_id and record.district_id:
                continue
            if record.district_name == "****" and record.state_name == "****":
                record.country_id = record.partner_id.country_id.id
                record.state_id = record.partner_id.state_id.id
                record.district_id = record.partner_id.district_id.id
                record.ward_id = record.partner_id.ward_id.id

            # Process address from session
            if not record.district_name:
                if record.config_id.type == "shopee":
                    try:
                        orders = eval(record.session_id.order_items)
                    except:
                        pass
                    for order in orders:
                        if 'order_sn' in order.keys():
                            if str(order['order_sn']) == record.ordersn:
                                record.write({
                                    'country_name': order['recipient_address']['region'],
                                    'state_name': order['recipient_address']['state'],
                                    'district_name': order['recipient_address']['city'],
                                    'ward_name': order['recipient_address']['district'],
                                })
                        elif 'ordersn' in order.keys():
                            if str(order['ordersn']) == record.ordersn:
                                record.write({
                                    'country_name': order['recipient_address']['country'],
                                    'state_name': order['recipient_address']['state'],
                                    'district_name': order['recipient_address']['city'],
                                    'ward_name': order['recipient_address']['district'],
                                })
                elif record.config_id.type == "lazada":
                    try:
                        orders = eval(record.session_id.orders)
                    except:
                        raise ValidationError(record.session_id.name)
                    for order in orders:
                        if str(order['order_id']) == record.ordersn:
                            record.write({
                                'country_name': order['address_billing']['country'],
                                'state_name': '',
                                'district_name': order['address_billing']['city'],
                                'ward_name': '',
                            })

            # Compute address IDs
            if not record.district_id and record.district_name:
                record._compute_country_id()
                record._compute_state_id()
                record._compute_district_id()
            if not record.ward_id and record.ward_name:
                record._compute_ward_id()

            # Update sale orders
            if record.sale_ids and record.district_id:
                record.sale_ids.write({
                    'region_id': record.region_id.id,
                    'area_id': record.area_id.id,
                    'country_id': record.country_id.id,
                    'state_id': record.state_id.id,
                    'district_id': record.district_id.id,
                    'ward_id': record.ward_id.id,
                })

    # ================================================================
    # 13. ORM OVERRIDES
    # ================================================================

    def unlink(self):
        """Ngăn xóa nếu đã có Sale Order"""
        context = self.env.context
        pass_unlink = context.get('pass_unlink')
        if not pass_unlink:
            if self.last_sale_id:
                raise ValidationError(_('Bạn không được xóa đơn hàng TMĐT đã có đơn hàng bán !'))
        return super(PICEcommerceOrder, self).unlink()

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """Search by name, origin, ordersn"""
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', ('name', operator, name), ('origin', operator, name), ('ordersn', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
        rules = self.search(domain + args, limit=limit)
        return [(record.id, record.display_name) for record in rules.sudo()]

    # ================================================================
    # CRON JOBS
    # ================================================================
    @api.model
    def cron_auto_confirm_orders(self):
        """Cron job: Tự động tiếp nhận đơn hàng draft"""
        orders = self.search([
            ('state', '=', 'draft'),
            ('order_status', '!=', 'UNPAID'),
            ('last_sale_id', '=', False),
        ], limit=100, order='create_time asc')

        for order in orders:
            try:
                order.action_confirm()
            except Exception as e:
                continue

    # ================================================================
    # INVOICE MANAGEMENT
    # ================================================================
    @api.depends('partner_invoice_id.street', 'partner_invoice_id.city', 'partner_invoice_id.state_id')
    def _compute_invoice_address(self):
        for rec in self:
            if rec.partner_invoice_id:
                parts = [p for p in [rec.partner_invoice_id.street, rec.partner_invoice_id.city,
                                     rec.partner_invoice_id.state_id.name] if p]
                rec.invoice_address = ', '.join(parts) if parts else False
            else:
                rec.invoice_address = False

    @api.onchange('take_einvoice')
    def _onchange_take_einvoice(self):
        if not self.take_einvoice:
            if self.config_id and self.config_id.partner_invoice_id:
                self.partner_invoice_id = self.config_id.partner_invoice_id
        else:
            if self.business_model == 'b2c':
                self.partner_invoice_id = False

    @api.onchange('invoice_vat')
    def _onchange_invoice_vat(self):
        if self.invoice_vat and len(self.invoice_vat) >= 10:
            partner = self.env['res.partner'].search([
                ('vat', '=', self.invoice_vat),
                '|', ('type', '=', 'invoice'), ('type', '=', 'contact')
            ], limit=1)
            if partner:
                self.partner_invoice_id = partner
                return {'warning': {'title': _('Tìm thấy!'), 'message': _('Công ty: %s') % partner.name}}

    def _validate_vat_number(self, vat):
        """Validate VN tax code: 10 or 13 digits. Return: (valid, cleaned, error)"""
        if not vat:
            return False, None, _("MST không được trống")
        cleaned = re.sub(r'[\s-]', '', vat)
        if not re.match(r'^\d{10}(-\d{3})?$', cleaned):
            return False, None, _("MST phải 10 hoặc 13 số")
        return True, cleaned, None

    def _validate_invoice_info(self):
        """Validate invoice info when take_einvoice = True"""
        self.ensure_one()
        if not self.take_einvoice:
            return ''

        errors = []
        if not self.invoice_vat:
            errors.append(_("- MST bắt buộc khi xuất HĐ"))
        else:
            valid, cleaned, err = self._validate_vat_number(self.invoice_vat)
            if not valid:
                errors.append(f"- {err}")
            else:
                self.invoice_vat = cleaned

        if not self.invoice_partner_name:
            errors.append(_("- Tên công ty bắt buộc"))
        if not self.invoice_address:
            errors.append(_("- Địa chỉ công ty bắt buộc"))

    def _get_or_create_invoice_partner(self):
        """Get or create invoice partner. Key: VAT"""
        self.ensure_one()
        if not self.take_einvoice:
            return self.config_id.partner_invoice_id if self.config_id else False

        error = self._validate_invoice_info()
        if error:
            raise ValidationError(_("Thông tin hóa đơn:\n%s") % error)

        partner = self.env['res.partner'].search([
            ('vat', '=', self.invoice_vat),
            '|', ('type', '=', 'invoice'), ('type', '=', 'contact')
        ], limit=1)

        if partner:
            self._update_invoice_partner_info(partner)
            self.partner_invoice_id = partner
            _logger.info(f"[{self.name}] Found invoice partner: {partner.id}")
            return partner

        partner = self._create_invoice_partner()
        self.partner_invoice_id = partner
        _logger.info(f"[{self.name}] Created invoice partner: {partner.id}")
        return partner

    def _create_invoice_partner(self):
        parent_id = self._get_platform_partner().id if self.business_model == 'b2c' else False
        vals = {
            'name': self.invoice_partner_name,
            'parent_id': parent_id,
            'type': 'invoice',
            'vat': self.invoice_vat,
            'street': self.invoice_address,
            'comment': _('Auto từ TMĐT: %s') % self.name,
        }
        return self.env['res.partner'].create(vals)

    def _update_invoice_partner_info(self, partner):
        vals = {}
        if partner.name != self.invoice_partner_name:
            vals['name'] = self.invoice_partner_name
        if partner.street != self.invoice_address:
            vals['street'] = self.invoice_address
        if vals:
            partner.write(vals)
            _logger.info(f"[{self.name}] Updated partner {partner.id}")

    def action_create_invoice_partner(self):
        """Manual: Create/update invoice partner"""
        self.ensure_one()
        if not self.take_einvoice:
            raise ValidationError(_("Check 'Lấy hóa đơn' trước!"))
        partner = self._get_or_create_invoice_partner()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công!'),
                'message': _('Công ty: %s') % partner.name,
                'type': 'success',
            }
        }

    # ================================================================
    # RECIPIENT CONTACT MANAGEMENT (B2C)
    # ================================================================
    def _get_platform_partner(self):
        if not self.config_id or not self.config_id.partner_id:
            raise ValidationError(_("Chưa cấu hình Partner: %s") % (self.config_id.name if self.config_id else 'N/A'))
        return self.config_id.partner_id

    def _search_contact_by_phone(self, phone, parent):
        return self.env['res.partner'].search([
            ('phone', '=', phone), ('parent_id', '=', parent.id)
        ], limit=1)

    def _validate_recipient_info(self):
        """Validate recipient info for B2C orders"""
        self.ensure_one()
        errors = []
        if not self.recipient_name:
            errors.append(_("- Tên người nhận bắt buộc"))
        valid, cleaned, err = self._validate_phone_number(self.recipient_phone)
        if not valid:
            errors.append(f"- {err}")
        else:
            self.recipient_phone = cleaned
        if not self.recipient_full_address:
            errors.append(_("- Địa chỉ người nhận bắt buộc"))
        return '\n'.join(errors)

    def _get_or_create_recipient_contact(self):
        """B2C: Get or create recipient contact. Key: phone"""
        self.ensure_one()
        if self.recipient_id:
            return self.recipient_id
        if self.business_model == 'b2b':
            return False

        error = self._validate_recipient_info()
        if error:
            raise ValidationError(_("Thông tin người nhận:\n%s") % error)

        platform = self._get_platform_partner()
        contact = self._search_contact_by_phone(self.recipient_phone, platform)

        if contact:
            # self._update_recipient_contact()
            self.recipient_id = contact
            _logger.info(f"[{self.name}] Found recipient: {contact.id}")
            return contact

        contact = self._create_recipient_contact(platform)
        self.recipient_id = contact
        _logger.info(f"[{self.name}] Created recipient: {contact.id}")
        return contact

    def _create_recipient_contact(self, parent):
        vals = {
            'name': self.recipient_name,
            'phone': self.recipient_phone,
            'email': self.recipient_email,
            'street': self.recipient_full_address,
            'customer_rank': 1,
            'comment': _('Auto từ TMĐT B2C: %s') % self.name,
        }
        if self.country_id:
            vals['country_id'] = self.country_id.id

        if self.state_id:
            vals['state_id'] = self.state_id.id
        if self.district_id:
            vals['district_id'] = self.district_id.id
        if self.ward_id:
            vals['ward_id'] = self.ward_id.id
        return self.env['res.partner'].create(vals)

    def _validate_phone_number(self, phone):
        """Validate phone number. Return: (valid, cleaned, error)"""
        if not phone:
            return False, None, _("Số điện thoại không được trống")
        #
        # cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        # if not re.match(r'^(0|\+84)(\d{9,10})$', cleaned):
        #     return False, None, _("Số điện thoại không hợp lệ")

        cleaned = phone
        return True, cleaned, None

    def _update_recipient_contact(self):
        """Manual: Update recipient contact"""
        for order in self:
            if not order.recipient_id:
                continue
            vals = {}
            if order.recipient_name and order.recipient_id.name != order.recipient_name:
                vals['name'] = order.recipient_name
            if order.recipient_phone and order.recipient_id.phone != order.recipient_phone:
                valid, cleaned, _ = order._validate_phone_number(order.recipient_phone)
                if valid:
                    vals['phone'] = cleaned
            if order.recipient_email and order.recipient_id.email != order.recipient_email:
                vals['email'] = order.recipient_email
            if order.recipient_full_address and order.recipient_id.street != order.recipient_full_address:
                vals['street'] = order.recipient_full_address
            if vals:
                order.recipient_id.write(vals)
                _logger.info(f"Updated recipient {order.recipient_id.id} for {order.name}")

    def action_create_recipient_contact(self):
        self.ensure_one()
        partner = self._get_or_create_recipient_contact()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công!'),
                'message': _('Người mua: %s') % partner.name,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def write(self, vals):
        """Override: Auto-correct partner chỉ khi cần thiết"""
        res = super().write(vals)

        # Chỉ chạy khi vals có field liên quan
        if any(k in vals for k in ['business_model', 'recipient_id']):
            for rec in self:
                update_vals = {}

                # B2C: Sync partner với recipient
                if rec.business_model == 'b2c' and rec.recipient_id:
                    if rec.partner_id != rec.recipient_id:
                        update_vals['partner_id'] = rec.recipient_id.id
                    if rec.partner_shipping_id != rec.recipient_id:
                        update_vals['partner_shipping_id'] = rec.recipient_id.id
                #
                # # B2B: Sync partner với config
                # elif rec.business_model == 'b2b' and rec.config_id:
                #     if rec.partner_id != rec.config_id.partner_id:
                #         update_vals['partner_id'] = rec.config_id.partner_id.id
                #     if rec.partner_shipping_id != rec.config_id.partner_shipping_id:
                #         update_vals['partner_shipping_id'] = rec.config_id.partner_shipping_id.id

                # Chỉ write nếu thực sự cần update
                if update_vals:
                    super(PICEcommerceOrder, rec).write(update_vals)

        return res
