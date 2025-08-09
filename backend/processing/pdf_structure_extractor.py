import json
import fitz  # PyMuPDF
import re
import sys
from pathlib import Path
import logging
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.setrecursionlimit(5000)

class PDFStructureExtractor:

    def __init__(self):
        self.min_heading_length = 10
        self.max_heading_length = 150
    
    def extract(self, pdf_path):
        result = {
            "title": "",
            "outline": []
        }

        # Used only one method of heuristics
        method_result = self._extract_via_heuristics(pdf_path)
        if method_result:
            result = method_result
            has_valid_title = bool(result.get("title") and len(result["title"].strip()) > 3)
            if result["outline"] or self._is_likely_form(pdf_path) or has_valid_title:
                logger.info("Successfully extracted structured!!")

        return result
    
    def _is_likely_form(self, pdf_path, page=0):
        doc = fitz.open(pdf_path)
        text = ""
        if page:
            for page_num in range(page, page+1):
                text += doc[page_num].get_text()
        else:
            for page_num in range(min(2, len(doc))):
                text += doc[page_num].get_text()
        
        # Form detection heuristics
        form_indicators = [
            r"application form",
            r"form for",
            r"please fill",
            r"please complete",
            r"\bdate\b.*\bsignature\b",
            r"\[\s*\]|\(\s*\)",  # Checkboxes
            r"^\s*\d+\.\s*[A-Za-z].*:$"  # Numbered form fields with colon
        ]
        
        form_score = 0
        for pattern in form_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                form_score += 1
        
        # Check for form fields
        widget_count = 0
        for page in doc:
            widget_count += len(list(page.widgets()))
        
        if widget_count > 0:
            form_score += 2
            
        return form_score >= 2
    
    def _extract_via_heuristics(self, pdf_path):
        def is_garbage_heading(text):
            # Lowercase for easier matching
            t = text.lower()

            # Rule 1: Don't allow brackets
            if "(" in t or ")" in t:
                return True

            # Rule 2: Basic address words
            address_words = ["parkway", "pkwy", "drive", "road", "street", "tn", "zip", "city", "state", "pigeon forge"]
            if any(word in t for word in address_words):
                return True

            return False
    
        def case(s: str) -> str:
            if s.isupper():
                return 'u'
            return 'l'
        
        doc = fitz.open(pdf_path)
        result = {
            "title": "",
            "outline": []
        }

        text_with_formatting = []
        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_with_formatting.append({
                                "text": span["text"],
                                "font": span["font"],
                                "size": span["size"],
                                "flags": span["flags"],  # Includes bold, italic info
                                "page": page_num
                            })
        
        # Rule 0 : Check if it's a form/etc (inference from file01.pdf)
        if self._is_likely_form(pdf_path):
            if text_with_formatting:
                result["title"] = text_with_formatting[0]["text"]
                return result

        # Rule 1 : Remove all the whitespaces objects from the list
        ptr = 0
        while ptr < len(text_with_formatting):
            if not text_with_formatting[ptr]["text"].strip():
                text_with_formatting.pop(ptr)
            else:
                ptr += 1
        
        # Rule 2: Remove all symbols
        ptr = 0
        while ptr < len(text_with_formatting):
            if text_with_formatting[ptr]["font"].lower() == "symbol":
                text_with_formatting.pop(ptr)
            else:
                ptr += 1
        
        ptr = 0
        while ptr < len(text_with_formatting):
            line = text_with_formatting[ptr]["text"].strip().lower()

            if re.search(r"\b(fig\.?|figure\.?|table\.?|image\.?|graph\.?|chart\.?)\s*\d+(\.\d+)*", line):
                text_with_formatting.pop(ptr)
            else:
                ptr += 1

        ptr = 0
        while ptr+1 < len(text_with_formatting):
            obj = text_with_formatting[ptr]
            if re.match(r'^\d+[.:)\-]\s', obj["text"].lower()):
                if len(text_with_formatting[ptr+1]["text"]) < 100 and "bold" in text_with_formatting[ptr+1]["font"].lower():
                    obj["text"] += text_with_formatting[ptr+1]["text"]
                    obj["font"] = text_with_formatting[ptr+1]["font"]
                    text_with_formatting.pop(ptr+1)
                else:
                    ptr += 1
            else:
                ptr += 1

        # Rule 3 : Content consecutive with same font and size should be together (inference - file01.pdf)
        ptr = 0
        while ptr + 1 < len(text_with_formatting):
            obj1 = text_with_formatting[ptr]
            obj2 = text_with_formatting[ptr + 1]

            if obj1["text"].strip()[-1] != ":":
                #  Don't concatenate if obj2 starts with a number (like "4", "2.1", "5)", etc.)
                if re.match(r'^(\d+)|^(\d+.\d+)', obj2["text"].strip()):
                    ptr += 1
                    continue

            if obj1["font"] == obj2["font"] and obj1["size"] == obj2["size"]:
                obj1["text"] += obj2["text"]
                text_with_formatting.pop(ptr + 1)
            else:
                ptr += 1

        # Rule 3: numbering like 3. should be concatenated with the next text if the next text is of the same size
        
        # Rule 4: Most basic rule to eliminate all the paragraphs (longer texts)
        ptr = 0
        while ptr < len(text_with_formatting):
            if len(text_with_formatting[ptr]["text"]) >= 100 and "bold" not in text_with_formatting[ptr]["font"].lower():
                text_with_formatting.pop(ptr)
            else:
                ptr += 1
        
        ptr = 0
        while ptr < len(text_with_formatting):
            if re.search(r"(https?://\S+|www\.\S+)", text_with_formatting[ptr]["text"].lower()):
                text_with_formatting.pop(ptr)
            else:
                ptr += 1
        

        date_patterns = [
    # Full formats with day and year (e.g., 1 March 2023, March 1st 2023, etc.)
    r'^\d{1,2}(st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December|'
    r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec),?\s+\d{4}$',
    
    r'^(January|February|March|April|May|June|July|August|September|October|November|December|'
    r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2}(st|nd|rd|th)?,?\s+\d{4}$',

    # Month + year (e.g., March 2023)
    r'^(January|February|March|April|May|June|July|August|September|October|November|December|'
    r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec),?\s+\d{4}$',

    # Partial dates like "April 11", "11 Apr"
    r'^\d{1,2}(st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December|'
    r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)$',

    r'^(January|February|March|April|May|June|July|August|September|October|November|December|'
    r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2}(st|nd|rd|th)?$',

    # Numeric formats (01/03/2023, 2023-03-01)
    r'^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$',
    r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$',
        ]
        # Rule 5: Remove all the dates if the date is alone
        ptr = 0
        while ptr < len(text_with_formatting):
            flag = True
            for p in date_patterns:
                if re.search(p, text_with_formatting[ptr]["text"].strip()):
                    flag = False
                    text_with_formatting.pop(ptr)
                    break
            if flag:
                ptr += 1
    
        gibberish_patterns = [
    r'^[\.\-\*_~=#]{3,}$',               # Only symbols repeated: ... , ---- , === , etc.
    r'^[\.\-\*_~=# ]{0,2}[\.\-\*_~=#]{3,}[\.\-\*_~=# ]{0,2}$',  # Minor padding allowed
    r'^[\W_]{4,}$',                      # Mostly non-alphanumeric symbols
]

        ptr = 0
        while ptr < len(text_with_formatting):
            text = text_with_formatting[ptr]["text"].strip()
            flag = True
            for p in gibberish_patterns:
                if re.match(p, text):
                    flag = False
                    text_with_formatting.pop(ptr)
                    break
            if flag:
                ptr += 1
        
        ptr = 0
        while ptr < len(text_with_formatting):
            text = text_with_formatting[ptr]["text"].strip()

            # Remove domain-like all-uppercase text (e.g., TOPJUMP.COM)
            if re.match(r'^[A-Z0-9\-]+\.(COM|ORG|NET|EDU|IN|CO|IO)\b$', text):
                text_with_formatting.pop(ptr)
            else:
                ptr += 1
        
        ptr = 0
        while ptr+1 < len(text_with_formatting):
            obj1 = text_with_formatting[ptr]
            obj2 = text_with_formatting[ptr+1]

            if obj1["text"].strip()[-1] != ":":
                #  Don't concatenate if obj2 starts with a number (like "4", "2.1", "5)", etc.)
                if re.match(r'^(\d+)|^(\d+.\d+)', obj2["text"].strip()):
                    ptr += 1
                    continue
        
            if obj1["font"] == obj2["font"] and obj1["flags"] == obj2["flags"] and obj1["page"] == obj2["page"] and ("bold" in obj1["font"].lower() and "bold" in obj2["font"].lower()):
                obj1["text"] += obj2["text"]
                obj1["size"] = max(obj1["size"], obj2["size"])
                text_with_formatting.pop(ptr+1)
            else:
                ptr += 1
        
        ptr = 0
        while ptr+1 < len(text_with_formatting):
            obj1 = text_with_formatting[ptr]
            obj2 = text_with_formatting[ptr+1]

            if obj1["text"].strip()[-1] != ":":
                #  Don't concatenate if obj2 starts with a number (like "4", "2.1", "5)", etc.)
                if re.match(r'^(\d+)|^(\d+.\d+)', obj2["text"].strip()):
                    ptr += 1
                    continue

            if obj1["font"] == obj2["font"] and obj1["flags"] == obj2["flags"] and obj1["page"] == obj2["page"]:
                obj1["text"] += obj2["text"]
                obj1["size"] = max(obj1["size"], obj2["size"])
                text_with_formatting.pop(ptr+1)
            else:
                ptr += 1
        
        ptr = 0
        while ptr < len(text_with_formatting):
            line = text_with_formatting[ptr]["text"].lstrip()

            if line and line[0].islower():
                text_with_formatting.pop(ptr)
            else:
                ptr += 1
        
        ptr = 0
        while ptr < len(text_with_formatting):
            line = text_with_formatting[ptr]["text"].lstrip()

            if line and not line[0].isalnum():
                text_with_formatting.pop(ptr)
            else:
                ptr += 1

        # Rule 5: Take only bold letters with size greater than 10 (inference file02.pdf)
        # ptr = 0
        # while ptr < len(text_with_formatting):
        #     obj = text_with_formatting[ptr]
        #     if "bold" in obj["font"].lower() and obj["size"] >= 10:
        #         ptr += 1
        #     else:
        #         text_with_formatting.pop(ptr)

        # Rule 6: If obj["font"] is not bold but it's size is relatively bigger than it's neighbours than it could be a heading

        text_counts = Counter(obj["text"].strip() for obj in text_with_formatting)

# Remove entries where the text appears more than once
        text_with_formatting = [
            obj for obj in text_with_formatting
            if text_counts[obj["text"].strip()] == 1
        ]

        # debugging for the whole text formatting
        # with open("./Fresh_start_1A/allText.json", "w", encoding="utf-8") as f:
        #     json.dump(text_with_formatting, f, indent=2, ensure_ascii=True)
        
        font_sizes = [span["size"] for span in text_with_formatting 
                      if len(span["text"].strip()) > 5]
        fonts = [span["font"] for span in text_with_formatting 
                 if len(span["text"].strip()) > 5]
        
        # Find the most common font size (likely body text)
        if font_sizes:
            body_size = Counter(font_sizes).most_common(1)[0][0]
        else:
            body_size = 10  # Fallback
        
        # Find the most common font (likely body font)
        if fonts:
            body_font = Counter(fonts).most_common(1)[0][0]
        else:
            body_font = None  # Fallback
        
        # Identify heading candidates
        heading_candidates = []
        for span in text_with_formatting:
            text = span["text"].strip()
            
            # Skip empty or very long text (paragraphs)
            if not self._is_valid_heading(text):
                continue

            if is_garbage_heading(text):
                continue

            if re.match(r'^\d{1,5}\s+\w+|\d{1,2}:\d{2}\s*[apAP][mM]', text):
                continue

            # Skip lines that contain common footer-like words
            if any(word in text.lower() for word in ["suite", "toronto", "received by", "proposal", "p.m.", "a.m."]):
                continue

            # Detect heading properties
            is_larger = span["size"] > body_size * 1.1
            is_bold = span["flags"] & 2  # Check bold flag
            is_different_font = body_font and span["font"] != body_font
            is_visually_emphasized = span["flags"] >= 16
            
            # Check for numeric prefixes common in headings (1., 1.1, etc.)
            has_numeric_prefix = bool(re.match(r'^\d+(\.\d+)*\.?\s', text))
            
            # Check for all caps which is common for headings
            is_all_caps = text.isupper() and len(text) > 3
            
            # Filter out common non-heading patterns
            if text.lower() in ["overview"] and not has_numeric_prefix:
                continue
                
            # Skip date-like strings (common in headers/footers)
            if re.match(r'^\d{1,2}\s+[A-Z]{3,}\s+\d{4}$', text):
                continue

            if span["flags"] < 8 and not has_numeric_prefix and not is_all_caps:
                continue
            
            # Combined heuristics for heading detection
            heading_score = 0
            if is_larger: heading_score += 2
            if is_bold: heading_score += 2
            if is_visually_emphasized: heading_score += 2  # NEW
            if is_different_font: heading_score += 1
            if has_numeric_prefix: heading_score += 2
            if is_all_caps: heading_score += 1
            if not any(c in text.lower() for c in '.,:;?!'): heading_score += 1
            
            # Filter based on score
            if heading_score >= 3:
                level = self._determine_heading_level(span, body_size, body_font)
                heading_candidates.append({
                    "level": level,
                    "text": text,
                    "page": span["page"],
                    "score": heading_score,
                    "size": span["size"]
                })
        
        # Sort candidates by page and score (higher score first)
        heading_candidates.sort(key=lambda x: (x["page"], -x["score"]))
        
        # Set the title (first significant heading or largest text in first page)
        title_candidates = [h for h in heading_candidates 
                          if h["page"] == 1 and h["level"] == "H1"]
        
        if title_candidates:
            result["title"] = title_candidates[0]["text"]
            # Remove the title from outline candidates
            heading_candidates = [h for h in heading_candidates if h != title_candidates[0]]
        else:
            # Fallback: use the largest text on the first page
            first_page_spans = [span for span in text_with_formatting 
                              if span["page"] == 0 and len(span["text"].strip()) > 3]
            if first_page_spans:
                largest_span = max(first_page_spans, key=lambda x: x["size"])
                candidate_title = largest_span["text"].strip()

                if self._is_valid_title_candidate(candidate_title):
                    result["title"] = candidate_title
                    heading_candidates = [h for h in heading_candidates if h["text"] != candidate_title]
                else:
                    result["title"] = ""
            else:
                result["title"] = ""

        # Add headings to outline
        result["outline"] = [
            {"level": h["level"], "text": h["text"], "page": h["page"]}
            for h in heading_candidates
        ]

        return result
    
    def _is_valid_title_candidate(self, text):
        text = text.strip()
        if len(text) < 4:
            return False
        if all(c in "-_=*~" for c in text):  # only symbols
            return False
        if text.lower() in ["hope to see you there!", "welcome", "introduction", "thank you"]:
            return False
        if not any(c.isalpha() for c in text):  # no letters at all
            return False
        return True


    def _determine_heading_level(self, span, body_size, body_font=None):
        """Determine heading level (H1, H2, H3) based on font properties"""
        size_ratio = span["size"] / body_size
        is_bold = span["flags"] & 2
        is_italic = span["flags"] & 1
        is_different_font = body_font and span["font"] != body_font
        
        # H1: Very large text or large bold text
        if size_ratio > 1.5 or (size_ratio > 1.3 and is_bold):
            return "H1"
        # H2: Moderately large text or medium bold text or different font
        elif size_ratio > 1.2 or (size_ratio > 1.1 and is_bold) or (is_different_font and is_bold):
            return "H2"
        # H3: Slightly larger than body or bold/italic normal sized text
        else:
            return "H3"
    
    def _is_valid_heading(self, text):
        """Check if text looks like a valid heading"""
        # Basic length check
        if not text or len(text) < self.min_heading_length or len(text) > self.max_heading_length:
            return False
            
        # Skip obvious non-headings
        if re.match(r'^\d+$', text):  # Just numbers (like page numbers)
            return False
        if re.match(r'^https?://', text):  # URLs
            return False
        if text.count('.') > 3 and not re.match(r'^\d+\.\d+', text):  # Likely a sentence
            return False
        if text.endswith('.') and len(text.split()) > 5:  # Likely a sentence
            return False
            
        # Special case: Forms often have numeric labels followed by a colon
        if re.match(r'^\d+\.\s*$', text):  # Just a number and a period
            return False
            
        # Special case for "Overview" which is often incorrectly identified
        if text.lower() == "overview":
            return False
            
        # Dates in specific format
        if re.match(r'^\d{1,2}\s+[A-Z]{3,}\s+\d{4}$', text):
            return False
            
        return True
    
    def _post_process_result(self, result):
        """Clean up and validate the extraction result"""
        # Ensure title doesn't contain newlines
        if result["title"]:
            result["title"] = result["title"].replace('\n', ' ').strip()
        
        # Clean up outline entries
        cleaned_outline = []
        for entry in result["outline"]:
            # Clean text
            text = entry["text"].replace('\n', ' ').strip()
            
            # Skip if after cleaning it's too short
            if len(text) < self.min_heading_length:
                continue
                
            # Skip problematic patterns:
            
            # 1. Skip standalone "Overview" 
            if text.lower() == "overview":
                continue
                
            # 2. Skip date-like strings
            if re.match(r'^\d{1,2}\s+[A-Z]{3,}\s+\d{4}$', text):
                continue
                
            # 3. Skip very common footer/header text
            if text.lower() in ["page", "copyright", "all rights reserved"]:
                continue
                
            # Add to cleaned outline
            cleaned_outline.append({
                "level": entry["level"],
                "text": text,
                "page": entry["page"]
            })
        
        # Special handling for forms
        if self._is_likely_form(None) and not cleaned_outline:
            # For forms, just keep the title and leave outline empty
            return {"title": result["title"], "outline": []}
        
        # Enforce hierarchy
        structured_outline = self._enforce_heading_hierarchy(cleaned_outline)
        
        # Update result
        result["outline"] = structured_outline
        return result
    
    def _enforce_heading_hierarchy(self, headings):
        """Ensure headings follow a proper hierarchy"""
        if not headings:
            return []
            
        # Initialize with the most prominent heading level found
        current_levels = {"H1": 0, "H2": 0, "H3": 0}
        structured_headings = []
        
        for heading in headings:
            original_level = heading["level"]
            
            # Enforce hierarchy
            if original_level == "H1":
                current_levels["H1"] += 1
                current_levels["H2"] = 0
                current_levels["H3"] = 0
            elif original_level == "H2":
                if current_levels["H1"] == 0:
                    # If no H1 exists yet, promote this to H1
                    current_levels["H1"] += 1
                    current_levels["H2"] = 0
                    current_levels["H3"] = 0
                    heading["level"] = "H1"
                else:
                    current_levels["H2"] += 1
                    current_levels["H3"] = 0
            elif original_level == "H3":
                if current_levels["H1"] == 0:
                    # If no H1 exists yet, promote this to H1
                    current_levels["H1"] += 1
                    current_levels["H2"] = 0
                    current_levels["H3"] = 0
                    heading["level"] = "H1"
                elif current_levels["H2"] == 0:
                    # If no H2 exists under the current H1, promote this to H2
                    current_levels["H2"] += 1
                    current_levels["H3"] = 0
                    heading["level"] = "H2"
                else:
                    current_levels["H3"] += 1
            
            structured_headings.append(heading)
        
        return structured_headings