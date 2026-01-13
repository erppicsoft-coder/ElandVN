# -*- coding: utf-8 -*-
#
#    PIC Technology Solution Co.,Ltd.
#
#    Copyright (C) 2024-TODAY PIC Technology Solution(<https://www.picsolution.com.vn>)
#    Author: CuongPham (phamcuong3004@gmai.com)
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE
#
# -*- coding: utf-8 -*-
"""
NhanhVN Model Constants
Dựa trên tài liệu: https://apidocs.nhanh.vn/v3/modelconstant
"""

# ==============================================================================
# PRODUCT CONSTANTS
# ==============================================================================

NHANHVN_PRODUCT_TYPE = [
    ('1', 'Loại sản phẩm'),
    ('2', 'Loại Voucher'),
    ('3', 'Sản phẩm cân đo'),
    ('4', 'Sản phẩm theo IMEI'),
    ('5', 'Gói sản phẩm'),
    ('6', 'Sản phẩm dịch vụ'),
    ('7', 'Sản phẩm dụng cụ'),
    ('8', 'Sản phẩm bán theo lô'),
    ('9', 'Sản phẩm Combo'),
    ('10', 'Sản phẩm nhiều đơn vị tính'),
]

NHANHVN_PRODUCT_STATUS = [
    ('1', 'Mới'),
    ('2', 'Đang bán'),
    ('3', 'Ngừng bán'),
    ('4', 'Hết hàng'),
]

# ==============================================================================
# ORDER CONSTANTS
# ==============================================================================

NHANHVN_ORDER_SALE_CHANNEL = [
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

NHANHVN_ORDER_CARRIER = [
    ('2', 'Viettel'),
    ('5', 'Giao hàng nhanh'),
    ('8', 'Giao hàng tiết kiệm'),
    ('12', 'Tự vận chuyển'),
    ('18', 'Ahamove'),
    ('22', 'Việt Nam Post'),
    ('24', 'JT Express'),
    ('25', 'EMS'),
    ('26', 'Best Express'),
    ('27', 'NinjaVan'),
    ('28', 'SuperShip'),
    ('29', 'SPX'),
    ('30', 'LEX'),
    ('31', 'Grab'),
]

NHANHVN_ORDER_TYPE = [
    ('1', 'Giao hàng tận nhà'),
    ('2', 'Mua tại quầy'),
    ('3', 'Đặt trước'),
    ('5', 'Đổi quà'),
    ('10', 'Xin báo giá'),
    ('12', 'Đổi sản phẩm'),
    ('14', 'Khách trả lại hàng'),
    ('15', 'Hàng chuyển kho'),
    ('16', 'Đơn hoàn một phần'),
    ('17', 'Đền bù mất hàng'),
]

NHANHVN_ORDER_STATUS = [
    ('40', 'Đã đóng gói'),
    ('42', 'Đang đóng gói'),
    ('43', 'Chờ thu gom'),
    ('54', 'Đơn mới'),
    ('55', 'Đang xác nhận'),
    ('56', 'Đã xác nhận'),
    ('57', 'Chờ khách xác nhận'),
    ('58', 'Hãng vận chuyển hủy đơn'),
    ('59', 'Đang chuyển'),
    ('60', 'Thành công'),
    ('61', 'Thất bại'),
    ('63', 'Khách hủy'),
    ('64', 'Hệ thống hủy'),
    ('68', 'Hết hàng'),
    ('71', 'Đang chuyển hoàn'),
    ('72', 'Đã chuyển hoàn'),
    ('73', 'Đổi kho xuất hàng'),
    ('74', 'Xác nhận hoàn'),
]

NHANHVN_ORDER_REASON = [
    ('1', 'Đặt nhầm sản phẩm'),
    ('2', 'Phí vận chuyển cao'),
    ('3', 'Không muốn chuyển khoản'),
    ('4', 'Đơn trùng'),
    ('5', 'Không gọi được khách'),
    ('6', 'Hết hàng'),
    ('8', 'Chờ chuyển khoản'),
    ('9', 'Khách không thích sản phẩm'),
    ('10', 'Khách không hài lòng về nhân viên vận chuyển'),
    ('11', 'Giao hàng chậm'),
    ('12', 'Đã mua sản phẩm tại cửa hàng'),
    ('14', 'Sai địa chỉ người nhận'),
    ('16', 'Khách không muốn mua nữa'),
    ('18', 'Lý do khác'),
    ('19', 'Không liên hệ được với người gửi'),
    ('20', 'Người gửi không bán hàng Online / Ngoại tỉnh'),
    ('22', 'Người gửi không bàn giao hàng cho hãng vận chuyển'),
    ('23', 'Hãng vận chuyển lấy hàng muộn'),
    ('24', 'Sai địa chỉ kho lấy hàng'),
    ('25', 'Hãng vận chuyển làm mất hàng'),
    ('26', 'Người gửi tự vận chuyển'),
    ('29', 'Người gửi không xử lý đơn hàng'),
    ('30', 'Sai giá sản phẩm'),
    ('34', '#N/A'),
    ('35', 'Khách đi vắng (sẽ giao hàng vào hôm khác)'),
]

NHANHVN_ORDER_STEP = [
    ('1', 'Tạo đơn hàng'),
    ('2', 'Xác nhận'),
    ('3', 'In đơn hàng'),
    ('4', 'Vận chuyển'),
    ('6', 'Sửa đơn hàng'),
    ('7', 'Đổi trạng thái'),
    ('8', 'Gửi đơn sang HVC'),
    ('9', 'Cập nhật tiền chuyển khoản'),
    ('10', 'Đổi kho hàng'),
    ('11', 'Thêm đơn hàng vào biên bản'),
    ('12', 'Xóa đơn hàng khỏi biên bản'),
    ('13', 'HVC cập nhật trạng thái'),
    ('14', 'Đổi hãng vận chuyển'),
    ('15', 'Báo hãng vận chuyển hủy'),
    ('16', 'HVC trả về mã code'),
    ('17', 'Xóa đơn hàng'),
    ('18', 'Trả về trạng thái và khối lượng'),
    ('19', 'Thêm nội dung đơn hàng'),
    ('20', 'API cập nhật đơn hàng'),
    ('21', 'HVC đã nhận hàng'),
    ('22', 'Gộp đơn hàng'),
    ('23', 'Gộp đơn hàng (lỗi)'),
    ('25', 'Gửi đơn sang HVC (lỗi)'),
    ('26', 'Thay đổi mã vận đơn HVC'),
    ('27', 'Lấy trạng thái từ HVC'),
    ('28', 'Đổi trạng thái từ biên bản bàn giao'),
    ('29', 'Chuyển từ Tour sang biên bản'),
    ('30', 'Lỗi hủy đơn HVC'),
    ('31', 'Lỗi lấy lịch trình từ HVC'),
    ('32', 'Vượt cân'),
    ('33', 'Đối soát lỗi'),
    ('34', 'Import đơn hàng'),
    ('35', 'Import trạng thái đơn hàng'),
    ('36', 'Đang đối soát'),
    ('37', 'Đã đối soát'),
    ('38', 'Tạo hóa đơn bán lẻ'),
    ('39', 'Chuyển đơn hàng sang bán sỉ'),
    ('40', 'Đơn hàng chuyển kho'),
    ('41', 'Copy đơn hàng'),
    ('42', 'Đóng gói'),
    ('43', 'Cập nhật nhân viên đóng gói'),
    ('44', 'Tạo đơn giao hàng một phần'),
    ('45', 'Xóa đơn hàng khỏi tour'),
    ('46', 'Tạo link thanh toán'),
    ('47', 'Tạo phiếu xuất kho'),
    ('48', 'Tạo phiếu nhập kho'),
    ('49', 'Xóa phiếu xuất kho'),
    ('50', 'Xóa phiếu nhập kho'),
    ('51', 'Gửi thông tin sang Vpage'),
    ('52', 'Hủy ghép nối giao dịch chuyển khoản'),
    ('53', 'Nhập hoàn kho'),
    ('54', 'Tách đơn hàng'),
    ('55', 'Gửi hàng đa điểm'),
    ('56', 'Sửa COD'),
    ('57', 'Cập nhật nhân viên bán hàng'),
    ('58', 'Tạo hóa đơn điện tử'),
]

# ==============================================================================
# INVENTORY CONSTANTS
# ==============================================================================

NHANHVN_INVENTORY_TYPE = [
    ('1', 'Loại nhập kho'),
    ('2', 'Loại xuất kho'),
]

NHANHVN_INVENTORY_MODE = [
    ('1', 'Kiểu giao hàng'),
    ('2', 'Kiểu bán lẻ'),
    ('3', 'Kiểu chuyển kho'),
    ('4', 'Kiểu quà tặng ở hóa đơn bán lẻ'),
    ('5', 'Kiểu nhà cung cấp'),
    ('6', 'Kiểu bán sỉ'),
    ('8', 'Kiểu kiểm kho'),
    ('10', 'Kiểu khác'),
    ('18', 'Kiểu quà tặng ở đơn hàng'),
]

NHANHVN_INVENTORY_RELATED_TYPE = [
    ('1', 'Xuất bán giữa 2 doanh nghiệp'),
    ('2', 'Nhập giữa 2 doanh nghiệp'),
    ('3', 'Xuất quà tặng cho hóa đơn bán lẻ'),
    ('4', 'Xuất quà tặng cho đơn hàng'),
    ('5', 'Xuất quà tặng bán sỉ'),
    ('6', 'Nhập trả lại bán lẻ, bán sỉ'),
    ('7', 'Nhập xuất chuyển kho'),
    ('8', 'Nhập xuất combo'),
]

# ==============================================================================
# ACCOUNTING CONSTANTS
# ==============================================================================

NHANHVN_ACCOUNTING_TYPE = [
    ('1', 'Báo nợ (Rút tiền)'),
    ('2', 'Báo có (Nộp tiền)'),
    ('3', 'Phiếu thu'),
    ('4', 'Phiếu chi'),
    ('5', 'Phiếu trả hàng'),
    ('6', 'Phiếu bán hàng'),
    ('7', 'Khác'),
    ('8', 'Phiếu nhập'),
    ('9', 'Phiếu xuất'),
    ('12', 'Kết chuyển'),
]

NHANHVN_ACCOUNTING_MODE = [
    ('1', 'Nhập nhà cung cấp'),
    ('2', 'Xuất trả nhà cung cấp'),
    ('3', 'Bán hàng'),
    ('4', 'Hàng trả lại'),
    ('5', 'Bán sỉ'),
    ('6', 'Trả lại bán sỉ'),
    ('7', 'Nhập máy cũ'),
    ('8', 'Bảo hành'),
    ('9', 'Xuất linh kiện'),
    ('15', 'Chuyển quỹ'),
    ('20', 'Hạch toán trả góp'),
    ('21', 'Công nợ đầu kì'),
    ('22', 'Đơn hàng'),
    ('23', 'Đơn hàng trả lại'),
    ('24', 'Nhập nhà cung cấp VAT'),
    ('25', 'Xuất nhà cung cấp VAT'),
    ('26', 'XNK khác'),
    ('27', 'Thu hộ trả góp'),
    ('28', 'Nhập VAT'),
    ('29', 'Xuất VAT'),
    ('30', 'Xác nhận nhận tiền thanh toán'),
    ('31', 'Xác nhận chi tiền thanh toán vận chuyển'),
    ('32', 'Phiếu nhập quà tặng'),
    ('33', 'Phiếu xuất quà tặng'),
]

# ==============================================================================
# ECOMMERCE CONSTANTS
# ==============================================================================

NHANHVN_ECOMMERCE_APP_ID = [
    ('8142', 'Lazada'),
    ('8195', 'Shopee'),
    ('8237', 'Sendo'),
    ('8238', 'Tiki'),
    ('8855', 'Tiktok'),
]