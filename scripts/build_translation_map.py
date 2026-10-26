import os
import sys
import json
import urllib.request
import urllib.parse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rules_file = os.path.join(BASE_DIR, "outputs", "market_basket_rules.csv")
items = []
if os.path.exists(rules_file):
    import pandas as pd
    df_r = pd.read_csv(rules_file)
    s = set()
    for col in ["antecedents_str", "consequents_str"]:
        for line in df_r[col].dropna():
            for p in line.split(", "):
                s.add(p.strip())
    items = sorted(list(s))


top_items = [
    "ANTIQUE SILVER T-LIGHT GLASS", "ASSORTED COLOUR BIRD ORNAMENT", "ASSORTED COLOURS SILK FAN",
    "BLACK RECORD COVER FRAME", "BROCADE RING PURSE", "CHILLI LIGHTS", "CHOCOLATE HOT WATER BOTTLE",
    "COLOUR GLASS T-LIGHT HOLDER HANGING", "DOORMAT KEEP CALM AND COME IN", "HEART OF WICKER SMALL",
    "HOT WATER BOTTLE TEA AND SYMPATHY", "JAM MAKING SET PRINTED", "JAM MAKING SET WITH JARS",
    "JUMBO BAG PINK POLKADOT", "JUMBO BAG RED RETROSPOT", "JUMBO BAG STRAWBERRY", "JUMBO BAG VINTAGE DOILY",
    "LUNCH BAG RED RETROSPOT", "MEDIUM CERAMIC TOP STORAGE JAR", "MINI PAINT SET VINTAGE",
    "PACK OF 12 LONDON TISSUES", "PACK OF 60 PINK PAISLEY CAKE CASES", "PACK OF 72 RETROSPOT CAKE CASES",
    "PAPER CHAIN KIT 50'S CHRISTMAS", "PAPER CHAIN KIT VINTAGE CHRISTMAS", "PAPER CRAFT , LITTLE BIRDIE",
    "PARTY BUNTING", "PICNIC BASKET WICKER SMALL", "POPCORN HOLDER", "RABBIT NIGHT LIGHT",
    "RED  HARMONICA IN BOX", "RED RETROSPOT CHARLOTTE BAG", "REGENCY CAKESTAND 3 TIER",
    "SET OF 3 CAKE TINS PANTRY DESIGN", "SPOTTY BUNTING", "VICTORIAN GLASS HANGING T-LIGHT",
    "WHITE HANGING HEART T-LIGHT HOLDER", "WOOD BLACK BOARD ANT WHITE FINISH", "WORLD WAR 2 GLIDERS ASSTD DESIGNS"
]

all_items = sorted(list(set(items + top_items)))
print(f"Tổng số sản phẩm cần dịch: {len(all_items)}")

# Từ điển ánh xạ thủ công chuẩn xác, mượt mà cho các từ hay gặp
CURATED_MAP = {
    "REGENCY TEA PLATE PINK": "Đĩa trà Regency màu hồng",
    "REGENCY TEA PLATE GREEN": "Đĩa trà Regency màu xanh lá",
    "REGENCY TEA PLATE ROSES": "Đĩa trà Regency hoa hồng",
    "POPPY'S PLAYHOUSE BEDROOM": "Nhà búp bê Poppy - Phòng ngủ",
    "POPPY'S PLAYHOUSE KITCHEN": "Nhà búp bê Poppy - Nhà bếp",
    "WOODEN TREE CHRISTMAS SCANDINAVIAN": "Cây thông Giáng sinh gỗ Bắc Âu",
    "WOODEN STAR CHRISTMAS SCANDINAVIAN": "Ngôi sao Giáng sinh gỗ Bắc Âu",
    "SET/6 RED SPOTTY PAPER CUPS": "Bộ 6 cốc giấy chấm bi đỏ",
    "SET/6 RED SPOTTY PAPER PLATES": "Bộ 6 đĩa giấy chấm bi đỏ",
    "SET/20 RED RETROSPOT PAPER NAPKINS": "Bộ 20 khăn giấy chấm bi đỏ cổ điển",
    "GREEN REGENCY TEACUP AND SAUCER": "Tách & đĩa lót trà Regency xanh lá",
    "PINK REGENCY TEACUP AND SAUCER": "Tách & đĩa lót trà Regency màu hồng",
    "ROSES REGENCY TEACUP AND SAUCER": "Tách & đĩa lót trà Regency hoa hồng",
    "ALARM CLOCK BAKELIKE GREEN": "Đồng hồ báo thức cổ điển màu xanh lá",
    "ALARM CLOCK BAKELIKE RED": "Đồng hồ báo thức cổ điển màu đỏ",
    "ALARM CLOCK BAKELIKE PINK": "Đồng hồ báo thức cổ điển màu hồng",
    "ALARM CLOCK BAKELIKE CHOCOLATE": "Đồng hồ báo thức cổ điển màu nâu",
    "ALARM CLOCK BAKELIKE IVORY": "Đồng hồ báo thức cổ điển màu ngà",
    "ALARM CLOCK BAKELIKE ORANGE": "Đồng hồ báo thức cổ điển màu cam",
    "JUMBO BAG RED RETROSPOT": "Túi cỡ lớn chấm bi đỏ cổ điển",
    "JUMBO BAG PINK POLKADOT": "Túi cỡ lớn chấm bi màu hồng",
    "JUMBO BAG STRAWBERRY": "Túi cỡ lớn họa tiết dâu tây",
    "JUMBO BAG APPLES": "Túi cỡ lớn họa tiết quả táo",
    "JUMBO BAG PEARS": "Túi cỡ lớn họa tiết quả lê",
    "JUMBO BAG OWLS": "Túi cỡ lớn họa tiết chim cú",
    "JUMBO BAG TOYS": "Túi cỡ lớn đựng đồ chơi",
    "JUMBO BAG ALPHABET": "Túi cỡ lớn họa tiết chữ cái",
    "JUMBO BAG VINTAGE DOILY": "Túi cỡ lớn họa tiết ren cổ điển",
    "JUMBO BAG VINTAGE LEAF": "Túi cỡ lớn họa tiết lá cây cổ điển",
    "JUMBO BAG WOODLAND ANIMALS": "Túi cỡ lớn hình muông thú",
    "JUMBO BAG SPACEBOY DESIGN": "Túi cỡ lớn họa tiết phi hành gia",
    "JUMBO BAG DOLLY GIRL DESIGN": "Túi cỡ lớn họa tiết cô bé búp bê",
    "JUMBO BAG 50'S CHRISTMAS": "Túi cỡ lớn Giáng sinh thập niên 50",
    "JUMBO BAG VINTAGE CHRISTMAS": "Túi cỡ lớn Giáng sinh cổ điển",
    "JUMBO STORAGE BAG SUKI": "Túi lưu trữ đồ cỡ lớn Suki",
    "JUMBO STORAGE BAG SKULLS": "Túi lưu trữ đồ cỡ lớn họa tiết đầu lâu",
    "LUNCH BAG RED RETROSPOT": "Túi đựng cơm trưa chấm bi đỏ",
    "LUNCH BAG PINK POLKADOT": "Túi đựng cơm trưa chấm bi màu hồng",
    "LUNCH BAG APPLE DESIGN": "Túi đựng cơm trưa họa tiết quả táo",
    "LUNCH BAG CARS BLUE": "Túi đựng cơm trưa hình ô tô xanh",
    "LUNCH BAG SPACEBOY DESIGN": "Túi đựng cơm trưa phi hành gia",
    "LUNCH BAG SUKI DESIGN": "Túi đựng cơm trưa họa tiết Suki",
    "LUNCH BAG DOLLY GIRL DESIGN": "Túi đựng cơm trưa bé búp bê",
    "LUNCH BAG WOODLAND": "Túi đựng cơm trưa hình muông thú",
    "LUNCH BAG VINTAGE DOILY": "Túi đựng cơm trưa ren cổ điển",
    "LUNCH BAG ALPHABET DESIGN": "Túi đựng cơm trưa bảng chữ cái",
    "WHITE HANGING HEART T-LIGHT HOLDER": "Đèn treo trái tim trắng đựng nến",
    "RED HANGING HEART T-LIGHT HOLDER": "Đèn treo trái tim đỏ đựng nến",
    "HEART OF WICKER SMALL": "Trái tim mây đan cỡ nhỏ",
    "HEART OF WICKER LARGE": "Trái tim mây đan cỡ lớn",
    "REGENCY CAKESTAND 3 TIER": "Khay bánh kem 3 tầng Regency",
    "ASSORTED COLOUR BIRD ORNAMENT": "Tượng chim trang trí nhiều màu",
    "PARTY BUNTING": "Dây cờ trang trí tiệc",
    "SPOTTY BUNTING": "Dây cờ trang trí chấm bi",
    "RABBIT NIGHT LIGHT": "Đèn ngủ hình thỏ con",
    "RED TOADSTOOL LED NIGHT LIGHT": "Đèn ngủ LED hình nấm đỏ",
    "PAPER CHAIN KIT 50'S CHRISTMAS": "Bộ dây xích giấy Giáng sinh thập niên 50",
    "PAPER CHAIN KIT VINTAGE CHRISTMAS": "Bộ dây xích giấy Giáng sinh cổ điển",
    "SET OF 3 CAKE TINS PANTRY DESIGN": "Bộ 3 hộp thiếc đựng bánh Pantry",
    "JAM MAKING SET PRINTED": "Bộ dụng cụ làm mứt họa tiết in",
    "JAM MAKING SET WITH JARS": "Bộ dụng cụ làm mứt kèm hũ thủy tinh",
    "VICTORIAN GLASS HANGING T-LIGHT": "Đèn treo nến thủy tinh phong cách Victoria",
    "NATURAL SLATE HEART CHALKBOARD": "Bảng phấn đá phiến hình trái tim",
    "WOODEN HEART CHRISTMAS SCANDINAVIAN": "Trái tim Giáng sinh gỗ Bắc Âu",
    "WOODEN FRAME ANTIQUE WHITE": "Khung tranh gỗ trắng cổ điển",
    "WOODEN PICTURE FRAME WHITE FINISH": "Khung ảnh gỗ sơn trắng",
    "SPACEBOY LUNCH BOX": "Hộp cơm trưa phi hành gia",
    "DOLLY GIRL LUNCH BOX": "Hộp cơm trưa bé búp bê",
    "POPCORN HOLDER": "Hộp đựng bắp rang bơ",
    "RECIPE BOX PANTRY YELLOW DESIGN": "Hộp đựng công thức nấu ăn màu vàng",
    "BAKING SET 9 PIECE RETROSPOT": "Bộ dụng cụ nướng bánh 9 món chấm bi",
    "BAKING SET SPACEBOY DESIGN": "Bộ dụng cụ nướng bánh phi hành gia",
    "CHILDRENS CUTLERY POLKADOT BLUE": "Bộ dao nĩa trẻ em chấm bi xanh",
    "CHILDRENS CUTLERY POLKADOT PINK": "Bộ dao nĩa trẻ em chấm bi hồng",
    "ROUND SNACK BOXES SET OF 4 FRUITS": "Bộ 4 hộp đựng đồ ăn vặt họa tiết trái cây",
    "ROUND SNACK BOXES SET OF4 WOODLAND": "Bộ 4 hộp đựng đồ ăn vặt hình muông thú",
    "SET OF 3 HEART COOKIE CUTTERS": "Bộ 3 khuôn cắt bánh hình trái tim",
    "SET OF 3 BUTTERFLY COOKIE CUTTERS": "Bộ 3 khuôn cắt bánh hình bướm",
    "SET OF 6 SPICE TINS PANTRY DESIGN": "Bộ 6 hộp thiếc đựng gia vị Pantry",
    "SET OF 3 REGENCY CAKE TINS": "Bộ 3 hộp thiếc đựng bánh Regency",
    "PACK OF 60 SPACEBOY CAKE CASES": "Hộp 60 khuôn bánh giấy phi hành gia",
    "PACK OF 60 PINK PAISLEY CAKE CASES": "Hộp 60 khuôn bánh giấy Paisley hồng",
    "PACK OF 72 RETROSPOT CAKE CASES": "Hộp 72 khuôn bánh giấy chấm bi đỏ",
    "PACK OF 60 DINOSAUR CAKE CASES": "Hộp 60 khuôn bánh giấy khủng long",
    "PACK OF 72 SKULL CAKE CASES": "Hộp 72 khuôn bánh giấy đầu lâu",
    "60 TEATIME FAIRY CAKE CASES": "Hộp 60 khuôn bánh giấy tiệc trà",
    "72 SWEETHEART FAIRY CAKE CASES": "Hộp 72 khuôn bánh giấy Sweetheart",
    "BLUE HARMONICA IN BOX": "Kèn harmonica xanh kèm hộp",
    "RED  HARMONICA IN BOX": "Kèn harmonica đỏ kèm hộp",
    "PLASTERS IN TIN CIRCUS PARADE": "Hộp thiếc băng cá nhân đoàn xiếc",
    "PLASTERS IN TIN SPACEBOY": "Hộp thiếc băng cá nhân phi hành gia",
    "PLASTERS IN TIN WOODLAND ANIMALS": "Hộp thiếc băng cá nhân muông thú",
    "BATHROOM METAL SIGN": "Biển kim loại trang trí phòng tắm",
    "TOILET METAL SIGN": "Biển kim loại trang trí toilet",
    "COOK WITH WINE METAL SIGN": "Biển kim loại Nấu ăn cùng rượu vang",
    "GIN + TONIC DIET METAL SIGN": "Biển kim loại Gin & Tonic",
    "PLEASE ONE PERSON METAL SIGN": "Biển kim loại cổ điển trang trí",
    "HAND OVER THE CHOCOLATE   SIGN": "Biển trang trí Đưa sô-cô-la đây",
    "CHOCOLATE HOT WATER BOTTLE": "Bình chườm nóng vị sô-cô-la",
    "HOT WATER BOTTLE TEA AND SYMPATHY": "Bình chườm nóng họa tiết trà",
    "HOT WATER BOTTLE I AM SO POORLY": "Bình chườm nóng giữ ấm",
    "SCOTTIE DOG HOT WATER BOTTLE": "Bình chườm nóng hình chú chó Scottie",
    "HAND WARMER BIRD DESIGN": "Túi sưởi ấm tay hình chú chim",
    "HAND WARMER OWL DESIGN": "Túi sưởi ấm tay hình cú mèo",
    "HAND WARMER SCOTTY DOG DESIGN": "Túi sưởi ấm tay hình chú chó Scotty",
    "CHARLOTTE BAG APPLES DESIGN": "Túi Charlotte họa tiết quả táo",
    "CHARLOTTE BAG PINK POLKADOT": "Túi Charlotte chấm bi hồng",
    "CHARLOTTE BAG SUKI DESIGN": "Túi Charlotte họa tiết Suki",
    "RED RETROSPOT CHARLOTTE BAG": "Túi Charlotte chấm bi đỏ",
    "WOODLAND CHARLOTTE BAG": "Túi Charlotte hình muông thú",
    "STRAWBERRY CHARLOTTE BAG": "Túi Charlotte hình dâu tây",
    "SUKI  SHOULDER BAG": "Túi đeo vai Suki",
    "RED RETROSPOT SHOPPER BAG": "Túi mua sắm chấm bi đỏ",
    "RECYCLING BAG RETROSPOT": "Túi tái chế chấm bi đỏ",
    "PINK VINTAGE PAISLEY PICNIC BAG": "Túi dã ngoại hoa văn Paisley hồng",
    "SCANDINAVIAN PAISLEY PICNIC BAG": "Túi dã ngoại hoa văn Bắc Âu",
    "SWEETHEART CERAMIC TRINKET BOX": "Hộp gốm đựng trang sức Sweetheart",
    "STRAWBERRY CERAMIC TRINKET BOX": "Hộp gốm đựng trang sức hình dâu tây",
    "VINTAGE SNAP CARDS": "Bộ bài trò chơi Snap cổ điển",
    "VINTAGE HEADS AND TAILS CARD GAME": "Bộ bài trò chơi ghép hình cổ điển",
    "IVORY KITCHEN SCALES": "Cân nhà bếp màu ngà cổ điển",
    "RED KITCHEN SCALES": "Cân nhà bếp màu đỏ cổ điển",
    "CHRISTMAS CRAFT LITTLE FRIENDS": "Bộ thủ công Giáng sinh những người bạn",
    "CHRISTMAS CRAFT TREE TOP ANGEL": "Bộ thủ công Giáng sinh thiên thần đỉnh cây thông",
    "HOME BUILDING BLOCK WORD": "Khối gỗ chữ Home trang trí",
    "LOVE BUILDING BLOCK WORD": "Khối gỗ chữ Love trang trí",
}

translations = dict(CURATED_MAP)

# Các sản phẩm còn lại gọi dịch tự động
remaining = [item for item in all_items if item not in translations]
print(f"Số sản phẩm đã có bản dịch chuẩn: {len(translations)}")
print(f"Số sản phẩm dịch tự động bổ sung: {len(remaining)}")

for item in remaining:
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=vi&dt=t&q=" + urllib.parse.quote(item)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tr = data[0][0][0].strip().capitalize()
        translations[item] = tr
    except Exception:
        translations[item] = item.title()

output_map_path = os.path.join(BASE_DIR, "data", "product_translation_map.json")
with open(output_map_path, "w", encoding="utf-8") as f:
    json.dump(translations, f, ensure_ascii=False, indent=2)

print(f"✅ Đã lưu từ điển dịch thuật ({len(translations)} sản phẩm) vào: '{output_map_path}'")
