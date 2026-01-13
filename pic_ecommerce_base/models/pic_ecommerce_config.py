# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression

PLATFORM_CODE = [
    ('1', 'Admin'),
    ('2', 'Website'),
    ('10', 'API'),
    ('20', 'Facebook'),
    ('21', 'Instagram'),
    ('41', 'Lazada'),
    ('42', 'Shopee'),
    ('43', 'Sendo'),
    ('45', 'Tiki'),
    ('48', 'Tiktok'),
    ('49', 'Zalo OA'),
    ('50', 'Shopee chat'),
    ('51', 'Lazada chat'),
    ('52', 'Zalo cá nhân'),
]


class PICEcommerceConfig(models.Model):
    _name = 'pic.ecommerce.config'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sàn thương mại điện tử'
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'parent_path'

    # ================================================================
    # BASIC INFO
    # ================================================================
    name = fields.Char(string='Tên nền tảng', required=True, tracking=True)
    code = fields.Selection(PLATFORM_CODE, string="Nền tảng", copy=False, index=True)
    user_id = fields.Many2one('res.users', string='Đại diện bán hàng', tracking=True)
    active = fields.Boolean(string='Hiệu lực', default=True, tracking=True)
    type = fields.Selection([], string='Kiểu kết nối')

    # NEW: Business Model & Environment
    business_model = fields.Selection([
        ('b2b', 'B2B'),
        ('b2c', 'B2C')
    ], string='Mô hình', default='b2c', required=True, tracking=True,
        help="B2B: Khai báo đầy đủ thông tin khách hàng\n"
             "B2C: Partner là nền tảng, địa chỉ giao hàng từ đơn TMĐT")

    environment = fields.Selection([
        ('sandbox', 'Thử nghiệm'),
        ('live', 'Chính thức')
    ], string='Môi trường', default='sandbox', required=True, tracking=True,
        help="Sandbox: Môi trường test\nLive: Môi trường production")

    auto_create_sale_order = fields.Boolean(
        string='Tự động tạo đơn hàng bán', default=False, tracking=True,
        help="Tự động tạo Sale Order khi đồng bộ đơn TMĐT.\n"
             "Nếu tắt: Nhân viên cần confirm thủ công từng đơn."
    )

    auto_confirm_sale_order = fields.Boolean(
        string='Tự động xác nhận đơn hàng bán', default=False, tracking=True,
        help="Tự động confirm Sale Order sau khi tạo.\n"
             "Chỉ áp dụng khi 'Tự động tạo đơn hàng bán' được bật."
    )

    # ================================================================
    # HIERARCHY
    # ================================================================
    has_child_config = fields.Boolean(string='Có nền tảng con', default=False)
    parent_id = fields.Many2one('pic.ecommerce.config', string='Nền tảng cha', index=True, ondelete='restrict')
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('pic.ecommerce.config', 'parent_id', string='Nền tảng con')
    child_count = fields.Integer(string='# Nền tảng con', compute='_compute_child_count')
    complete_name = fields.Char('Tên đầy đủ', compute='_compute_complete_name', recursive=True, store=True)

    # ================================================================
    # CONFIGURATION
    # ================================================================
    date_start = fields.Datetime(string='Ngày sử dụng', default=lambda self: fields.Datetime.now(), required=True)
    number_of_day = fields.Integer(string='Thời gian đối soát', default=7, help="Số ngày đồng bộ dữ liệu")
    fee_rate = fields.Float(string='Phí giao dịch (%)', default=0, digits=(5, 2))

    # ================================================================
    # DEFAULT MASTER DATA (VISIBLE FOR ALL)
    # ================================================================
    partner_id = fields.Many2one('res.partner', string='Khách hàng', tracking=True,
                                 help="B2C: Nền tảng TMĐT | B2B: Khách hàng chính")
    partner_invoice_id = fields.Many2one('res.partner', string='Địa chỉ xuất hóa đơn', tracking=True)
    partner_shipping_id = fields.Many2one('res.partner', string='Địa chỉ giao hàng', tracking=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Điều khoản thanh toán')
    pricelist_id = fields.Many2one('product.pricelist', string='Bảng giá')
    warehouse_id = fields.Many2one('stock.warehouse', string='Nhà kho')
    source_id = fields.Many2one('utm.source', string='Nguồn')

    # Cost products
    voucher_cost_product_id = fields.Many2one('product.product', string='Chi phí Voucher')
    gift_cost_product_id = fields.Many2one('product.product', string='Chi phí hàng tặng')
    ship_cost_product_id = fields.Many2one('product.product', string='Chi phí giao hàng')

    # ================================================================
    # API CONFIGURATION (SYSTEM ONLY)
    # ================================================================
    shop_id = fields.Char(string='Shop ID')
    live_partner_key = fields.Char(string='App ID / Partner Key')
    live_key = fields.Text(string='Secret Key')
    oauth_url = fields.Char(string='URL lấy code')
    oauth_code = fields.Char(string='Authorization Code',
                             help='Code để lấy token, hiệu lực 1 tháng')
    access_token = fields.Char(string='Access Token')
    refresh_token = fields.Char(string='Refresh Token')
    expires_in = fields.Datetime(string='Hạn Access Token')
    refresh_expires_in = fields.Datetime(string='Hạn Refresh Token')

    # ================================================================
    # RELATIONS
    # ================================================================
    ecommerce_ids = fields.One2many('pic.ecommerce.order', 'config_id', string='Đơn hàng TMĐT')
    company_id = fields.Many2one('res.company', string='Công ty', required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Tiền tệ')

    # ================================================================
    # COMPUTE METHODS
    # ================================================================
    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f"{category.parent_id.complete_name} / {category.name}"
            else:
                category.complete_name = category.name

    @api.depends('child_ids')
    def _compute_child_count(self):
        for record in self:
            record.child_count = len(record.child_ids)

    @api.depends('name', 'code', 'environment')
    def _compute_display_name(self):
        """Display name with environment badge"""
        for record in self:
            name = record.name
            if record.code:
                name = f"{record.code}. {name}"
            if record.environment == 'sandbox':
                name = f"[TEST] {name}"
            record.display_name = name

    # ================================================================
    # ONCHANGE METHODS
    # ================================================================
    @api.onchange('business_model')
    def _onchange_business_model(self):
        """Clear shipping/invoice addresses when switching to B2C"""
        if self.business_model == 'b2c':
            self.partner_shipping_id = False
            self.partner_invoice_id = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Auto-fill addresses and payment terms from partner"""
        if not self.partner_id:
            return

        if self.business_model == 'b2b':
            # B2B: Fill full customer info
            address = self.partner_id.address_get(['invoice', 'delivery'])
            self.partner_invoice_id = address.get('invoice')
            self.partner_shipping_id = address.get('delivery')
            self.payment_term_id = self.partner_id.property_payment_term_id.id
            self.pricelist_id = self.partner_id.property_product_pricelist.id
        else:
            # B2C: Only partner_id (platform), no shipping/invoice
            self.partner_invoice_id = False
            self.partner_shipping_id = False

    # ================================================================
    # CONSTRAINTS
    # ================================================================
    @api.constrains('business_model', 'partner_shipping_id', 'partner_invoice_id')
    def _check_business_model_addresses(self):
        """Validate address requirements based on business model"""
        for record in self:
            if record.business_model == 'b2b':
                if not record.partner_shipping_id:
                    raise ValidationError(_("B2B: Địa chỉ giao hàng là bắt buộc"))
            elif record.business_model == 'b2c':
                if record.partner_shipping_id:
                    raise ValidationError(
                        _("B2C: Không cần khai báo địa chỉ giao hàng/xuất hóa đơn.\n"
                          "Địa chỉ sẽ được lấy từ đơn hàng TMĐT.")
                    )

    @api.constrains('environment', 'access_token')
    def _check_live_environment(self):
        """Warning when going live without proper credentials"""
        for record in self:
            if record.environment == 'live' and not record.access_token and record.type:
                raise ValidationError(
                    _("Không thể chuyển sang môi trường Chính thức khi chưa có Access Token!")
                )

    # ================================================================
    # BUSINESS METHODS
    # ================================================================
    def action_generate_child_config(self):
        """Override in platform-specific modules"""
        return True

    def action_view_child(self):
        """View child configurations"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('pic_ecommerce_base.action_pic_ecommerce_config')
        action['domain'] = [('parent_id', '=', self.id)]
        action['context'] = {'default_parent_id': self.id}

        if len(self.child_ids) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.child_ids.id

        return action

    def action_get_auth_url(self):
        """Override in platform-specific modules"""
        return True

    def action_get_access_token(self):
        """Override in platform-specific modules"""
        return True

    def action_get_refresh_token(self):
        """Override in platform-specific modules"""
        return True

    # ================================================================
    # SEARCH & NAME
    # ================================================================
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """Search by name, code, and shop_id"""
        args = args or []
        domain = []
        if name:
            domain = [
                '|', '|',
                ('name', operator, name),
                ('code', operator, name),
                ('shop_id', operator, name)
            ]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain

        configs = self.search(domain + args, limit=limit)
        return configs.name_get()
