# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.tools import float_compare


class PICEcommerceOrderLine(models.Model):
    _name = 'pic.ecommerce.order.line'
    _description = 'Chi tiết đơn hàng TMĐT'

    ecommerce_id = fields.Many2one('pic.ecommerce.order', string='Đon hàng TMĐT', ondelete='cascade')
    name = fields.Char(string='Mô tả')
    
    # Mẫu sản phẩm
    product_tmpl_id = fields.Many2one('product.template', string='Mẫu sản phẩm')
    product_uom = fields.Many2one('uom.uom', string='Đơn vị tính', related='product_tmpl_id.uom_id')
    code_product = fields.Char(string='Mã nội bộ', related='product_tmpl_id.default_code')
    item_id = fields.Char(string='Mẫu sản phẩm')
    item_name = fields.Char(string='Tên mẫu sản phẩm')
    item_sku = fields.Char(string='Mã TMĐT')
    
    # Biến thể sản phẩm
    product_id = fields.Many2one('product.product', string='Sản phẩm')
    variation_id = fields.Integer(string='Mã biến thể')
    variation_name = fields.Char(string='Tên biến thể')
    variation_sku = fields.Char(string='Mã biến thể TMĐT')
    
    # Sản phẩm combo
    combo_product_tmpl_id = fields.Many2one('product.template', string='Sản phẩm combo')
    combo_qty = fields.Float(string='Số lượng combo')
    
    # Thông tin khuyến mãi
    promotion_type = fields.Char(string='Loại khuyến mãi')
    promotion_code = fields.Float(string='Mã khuyến mãi')
    # promotion_id = fields.Many2one('pic.ecommerce.promotion', string='Chương trình khuyến mãi')
    voucher_code = fields.Char(string='Mã voucher')
    voucher_amount = fields.Float(string='Tiền voucher')
    platform_voucher_amount = fields.Float(string='Sàn trợ giá')
    
    # Thông tin giá
    pricelist_id = fields.Many2one('product.pricelist', string='Bảng giá')
    is_check_price = fields.Boolean(string='Đã kiểm tra bảng giá', default=False)

    weight = fields.Float(string='Trọng lượng')
    quantity = fields.Float(string='Số lượng')

    original_price = fields.Float(string='Giá niêm yết')
    price = fields.Float(string='Giá bán')
    discount = fields.Float(string='Chiết khấu')
    discounted_price = fields.Float(string='Giá bán sau giảm')

    subtotal = fields.Float(string='Tiền bán')
    transaction_fee = fields.Float(string='Phí giao dịch')
    shipping_fee = fields.Float(string='Phí vận chuyển')

    # Thông tin bổ sung
    is_gift = fields.Boolean(string='Khuyến mãi?', default=False)
    is_wholesale = fields.Boolean(string='Là bán sỉ')

    is_add_on_deal = fields.Boolean(string='Là khuyến mãi')
    is_main_item = fields.Boolean(string='Là sản phẩm chính')
    add_on_deal_id = fields.Float(string='Mã khuyến mãi')
    group_id = fields.Float(string='Mã nhóm')
    is_set_item = fields.Boolean(string='Là sản phẩm bộ')

    def get_pricelist_id(self):
        warning = ''
        # # Lấy bảng giá
        # if self.ecommerce_id.is_auto_check_pricelist and self.product_tmpl_id:
        #     SQL = """
        #         select ppl.id--ppv.id, ppv.name, pp.product_tmpl_id, pt.name, ppi.price_surcharge, ppi.* 
        #         from pic_sale_channel tsc
        #             inner join product_pricelist ppl on ppl.channel_id = tsc.id
        #                 and ppl.is_voucher = True and ppl.type = 'sale' and ppl.active = True
        #             inner join product_pricelist_version ppv on ppv.pricelist_id = ppl.id
        #             inner join product_pricelist_item ppi on ppi.price_version_id = ppv.id
        #             inner join product_product pp on pp.id = ppi.product_id
        #             inner join product_template pt on pt.id = pp.product_tmpl_id
        #         where tsc.name = 'SHOPEE'
        #             and ppv.date_start <= %s
        #             and ppv.date_end >= %s
        #             and ppv.state = 'approved'
        #             and pp.product_tmpl_id = %s
        #             and ppi.price_surcharge = %s
        #         """
        #     self.env.cr.execute(SQL, (self.ecommerce_id.create_time, self.ecommerce_id.create_time, self.product_tmpl_id.id, self.variation_discounted_price))
        #     data = self.env.cr.dictfetchall()
        #     if data and len(data) == 1:
        #         self.pricelist_id = data[0]['id']
        #         self.is_check_price = True
        #         self.ecommerce_id.pricelist_id = data[0]['id']
        #     elif self.product_tmpl_id.list_price == self.variation_discounted_price:
        #         self.pricelist_id = False
        #         self.is_check_price = True
        #         self.ecommerce_id.pricelist_id = False
        #     elif not self.is_add_on_deal or self.is_main_item:
        #         warning = '- Không tìm thấy Bảng giá cho SKU ' + self.item_sku + '\n'

        return warning
