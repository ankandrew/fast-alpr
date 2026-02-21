"""
Thai license plate parsing utilities.
"""

import re
from dataclasses import dataclass


@dataclass
class ThaiPlateInfo:
    """Parsed Thai license plate information."""

    category: str  # e.g., "1กก", "2กก", "นย"
    number: str  # e.g., "1234"
    province: str  # e.g., "กรุงเทพมหานคร"
    raw_text: str  # Original text


def parse_thai_plate(text: str) -> ThaiPlateInfo | None:
    """
    Parse Thai license plate format.
    
    Expected formats:
    - Standard: "1กก 1234 กรุงเทพมหานคร"
    - Variants: "2กก-5678 เชียงใหม่", "นย 9999 ภูเก็ต"
    
    Args:
        text: OCR text output
        
    Returns:
        ThaiPlateInfo if successfully parsed, None otherwise
    """
    if not text:
        return None
    
    # Clean up text: remove extra spaces, normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Common Thai provinces (extend this list as needed)
    thai_provinces = [
        'กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร',
        'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา', 'ชลบุรี', 'ชัยนาท', 'ชัยภูมิ',
        'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง', 'ตราด', 'ตาก', 'นครนายก',
        'นครปฐม', 'นครพนม', 'นครราชสีมา', 'นครศรีธรรมราช', 'นครสวรรค์',
        'นนทบุรี', 'นราธิวาส', 'น่าน', 'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี',
        'ประจวบคีรีขันธ์', 'ปราจีนบุรี', 'ปัตตานี', 'พระนครศรีอยุธยา', 'พังงา',
        'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์', 'แพร่',
        'พะเยา', 'ภูเก็ต', 'มหาสารคาม', 'มุกดาหาร', 'แม่ฮ่องสอน', 'ยโสธร',
        'ยะลา', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง', 'ราชบุรี', 'ลพบุรี', 'ลำปาง',
        'ลำพูน', 'เลย', 'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ',
        'สมุทรสงคร้าม', 'สมุทรสาคร', 'สระแก้ว', 'สระบุรี', 'สิงห์บุรี',
        'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์', 'หนองคาย',
        'หนองบัวลำภู', 'อ่างทอง', 'อุดรธานี', 'อุทัยธานี', 'อุตรดิตถ์',
        'อุบลราชธานี', 'อำนาจเจริญ'
    ]
    
    # Try to find province at the end
    province = ""
    for prov in thai_provinces:
        if text.endswith(prov):
            province = prov
            text = text[:-len(prov)].strip()
            break
    
    # If no province found, try to extract last Thai word
    if not province:
        parts = text.split()
        if len(parts) > 2 and re.search(r'[ก-๙]', parts[-1]) and not re.search(r'\d', parts[-1]):
            province = parts[-1]
            text = ' '.join(parts[:-1]).strip()
    
    # Now parse category and number from remaining text
    # Pattern: category (Thai chars + optional numbers) + number (digits)
    # Examples: "1กก 1234", "2กก-5678", "นย 9999"
    
    # Remove separators
    text = text.replace('-', ' ').replace('–', ' ')
    parts = text.split()
    
    category = ""
    number = ""
    
    if len(parts) >= 2:
        # First part is category (may contain Thai + numbers)
        category = parts[0]
        # Second part is number (should be digits)
        number = parts[1]
    elif len(parts) == 1:
        # Try to split single string into category and number
        match = re.match(r'^([ก-๙0-9]+)([0-9]+)$', parts[0])
        if match:
            category = match.group(1)
            number = match.group(2)
        else:
            # If can't parse, put everything in category
            category = parts[0]
    
    # Clean up number to contain only digits
    number = re.sub(r'[^0-9]', '', number)
    
    return ThaiPlateInfo(
        category=category,
        number=number,
        province=province,
        raw_text=text if not province else f"{text} {province}"
    )


def format_thai_plate(category: str, number: str, province: str) -> str:
    """
    Format Thai plate components into standard display format.
    
    Args:
        category: Plate category (e.g., "1กก")
        number: Plate number (e.g., "1234")
        province: Province name (e.g., "กรุงเทพมหานคร")
        
    Returns:
        Formatted plate string
    """
    parts = []
    if category:
        parts.append(category)
    if number:
        parts.append(number)
    if province:
        parts.append(province)
    return ' '.join(parts)